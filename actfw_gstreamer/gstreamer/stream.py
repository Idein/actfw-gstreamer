from queue import Empty, Full, Queue
from typing import Any, NamedTuple

from ..util import get_gst
from .converter import ConverterBase, ConverterRaw
from .exception import PipelineBuildError
from .pipeline import PipelineGenerator

__all__ = [
    "GstStreamBuilder",
    "GstStream",
]


class GstStreamBuilder:
    def __init__(self, pipeline_generator, converter=None):
        """
        args:
            - pipeline_generator: :class:`~PipelineGenerator`
            - converter: :class:`~ConverterBase`, defaults to :class:`~ConverterRaw`.
        """

        if converter is None:
            converter = ConverterRaw()

        assert isinstance(
            pipeline_generator, PipelineGenerator
        ), f"pipeline_generator should be instance of PipelineGenerator, but got: {type(pipeline_generator)}"
        assert isinstance(
            converter, ConverterBase
        ), f"converter should be instance of ConverterBase, but got: {type(converter)}"

        self._pipeline_generator = pipeline_generator
        self._converter = converter

    def start_streaming(self):
        """
        return:
            - :class:`~GstStream`
        exceptions:
            - :class:`~PipelineBuildError`
        """

        built_pipeline = self._pipeline_generator.build()
        inner = Inner(built_pipeline, self._converter)
        return GstStream(inner)


class GstStream:
    def __init__(self, inner):
        self._inner = inner

    def __enter__(self):
        err = self._inner.start()
        if err:
            raise err

        return self

    def __exit__(self, _ex_type, _ex_value, _trace):
        # Forgot errors in stopping pipeline.
        _err = self._inner.stop()  # noqa F841

        return False

    def is_running(self):
        return self._inner.is_running()

    def capture(self, timeout=None):
        ret, err = self._inner.capture(timeout)
        if err:
            raise err

        return ret


class InternalMessageKind:
    FROM_NEW_SAMPLE = 0
    FROM_MESSAGE = 1


class InternalMessage(NamedTuple):
    kind: int
    payload: Any


class Inner:
    def __init__(self, built_pipeline, converter):
        self._Gst = get_gst()
        self._built_pipeline = built_pipeline
        self._converter = converter
        self._queue = Queue(1)
        self._is_running = None

        self._built_pipeline.sink.connect("new-sample", self._cb_new_sample)
        self._bus = self._built_pipeline.pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message::eos", self._cb_message)
        self._bus.connect("message::error", self._cb_message)

    def is_running(self):
        return self._is_running

    def _change_pipeline_state(self, desired):
        """
        Blocking function to change pipeline state to be `desired` or fail.

        args:
            - desired: One of enum `~Gst.State`.

        returns:
            - Option[error]
        """

        self._built_pipeline.pipeline.set_state(desired)
        # Note that x is _ResultTuple of type (<Gst.StateChangeReturn>, state=<Gst.State>, pending=<Gst.State>).
        x = self._built_pipeline.pipeline.get_state(self._Gst.CLOCK_TIME_NONE)
        if x[0] == self._Gst.StateChangeReturn.FAILURE:
            return PipelineBuildError(f"failed to change state of pipeline: desired = {desired}, {x}")
        elif x.state == desired:
            return None
        else:
            return RuntimeError("unreachable")

    def start(self):
        err = self._change_pipeline_state(self._Gst.State.PLAYING)
        if err:
            return err

        self._is_running = True
        return None

    def stop(self):
        if self._is_running:
            self._is_running = False
            self._bus.remove_signal_watch()
            return self._change_pipeline_state(self._Gst.State.NULL)
        else:
            return None

    def capture(self, timeout):
        try:
            im = self._queue.get(block=True, timeout=timeout / 1000)
            got = True
        except Empty:
            im = None
            got = False

        if not got:
            return None, None
        elif im.kind == InternalMessageKind.FROM_NEW_SAMPLE:
            # Note that there is a case we cannot get sample via `pull-sample` while got `new-sample` signal:
            # (This is because we decoupled these signals.)
            #
            #   1. (thread A) Called this method `capture`.
            #   2. (thread B) Got a signal `new-sample`.  Enqueue.
            #   3. (thread A) Dequeue & interrupted.
            #   4. (thread B) Got a signal `new-sample`.  Enqueue.
            #   5. (thread A) Emit `pull-sample` and process.
            #   6. (thread A) Called `capture`, dequeue, emit, but there is no sample if `max-buffers=1`.
            #
            # While lots of examples (e.g., https://gstreamer.freedesktop.org/documentation/tutorials/basic/short-cutting-the-pipeline.html)
            # emit `pull-sample` in `new-sample` callback, we use this decoupling because this affects performance in python case.
            sample = self._built_pipeline.sink.emit("pull-sample")
            if sample is None:
                return None, None
            else:
                return self._converter.convert_sample(sample)
        elif im.kind == InternalMessageKind.FROM_MESSAGE:
            message = im.payload
            if message.type == self._Gst.MessageType.EOS:
                self.stop()
                return None, None
            elif message.type == self._Gst.MessageType.ERROR:
                return None, Exception(message)
            else:
                return None, RuntimeError("unreachable")
        else:
            return None, RuntimeError("unreachable")

    def _cb_new_sample(self, _):
        im = InternalMessage(InternalMessageKind.FROM_NEW_SAMPLE, None)
        try:
            self._queue.put_nowait(im)
        except Full:
            pass
        return self._Gst.FlowReturn.OK

    def _cb_message(self, _, message):
        im = InternalMessage(InternalMessageKind.FROM_MESSAGE, message)
        self._queue.put(im)


class DummyMessage:
    def __init__(self, t):
        self.type = t
