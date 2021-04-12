from queue import Empty, Full, Queue
from typing import Any, NamedTuple, Optional, Union

from result import Err, Ok, Result

from ..util import get_gst
from .converter import ConverterBase, ConverterRaw
from .exception import PipelineBuildError
from .pipeline import BuiltPipeline, PipelineGenerator

__all__ = [
    # pub
    "GstStreamBuilder",
    # pub (module)
    # "GstStream",
]


class GstStreamBuilder:
    _pipeline_generator: PipelineGenerator
    _converter: ConverterBase

    def __init__(self, pipeline_generator: PipelineGenerator, converter: Optional[ConverterBase] = None):
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

    def start_streaming(self) -> "GstStream":  # noqa F821 (Hey linter, see below.)
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
    _inner: "Inner"  # noqa F821 (Hey linter, see below.)

    def __init__(self, inner: "Inner"):  # noqa F821 (Hey linter, see below.)
        self._inner = inner

    def __enter__(self) -> "GstStream":  # noqa F821 (Hey linter, see above.)
        err = self._inner.start()
        if err:
            raise err

        return self

    def __exit__(self, _ex_type: Any, _ex_value: Any, _trace: Any) -> bool:  # type: ignore
        # Forgot errors in stopping pipeline.
        _err = self._inner.stop()  # noqa F841

        return False

    def is_running(self) -> bool:
        return self._inner.is_running()

    # Here, Any = ConverterBase::ConvertResult, but we can't yet express associated types.
    # c.f. https://github.com/python/mypy/issues/7790
    def capture(self, timeout: Optional[float] = None) -> Any:
        res = self._inner.capture(timeout)
        if res.is_ok():
            return res.unwrap()
        else:
            raise res.unwrap_err()


class InternalMessageKind:
    FROM_NEW_SAMPLE = 0
    FROM_MESSAGE = 1


class InternalMessage(NamedTuple):
    kind: int  # InternalMessageKind
    payload: Any


class Inner:
    _Gst: "Gst"  # type: ignore  # noqa F821
    _built_pipeline: BuiltPipeline
    _converter: ConverterBase
    _queue: "Queue[InternalMessage]"
    _is_running: bool

    def __init__(self, built_pipeline: BuiltPipeline, converter: ConverterBase):
        self._Gst = get_gst()
        self._built_pipeline = built_pipeline
        self._converter = converter
        self._queue = Queue(1)
        self._is_running = False

        self._built_pipeline.sink.connect("new-sample", self._cb_new_sample)
        self._bus = self._built_pipeline.pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message::eos", self._cb_message)
        self._bus.connect("message::error", self._cb_message)

    def is_running(self) -> bool:
        return self._is_running

    def _change_pipeline_state(self, desired: "Gst.State") -> Optional[Union[PipelineBuildError, RuntimeError]]:  # type: ignore  # noqa F821
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

    def start(self) -> Optional[Union[PipelineBuildError, RuntimeError]]:
        err = self._change_pipeline_state(self._Gst.State.PLAYING)
        if err:
            return err

        self._is_running = True
        return None

    def stop(self) -> Optional[Union[PipelineBuildError, RuntimeError]]:
        if self._is_running:
            self._is_running = False
            self._bus.remove_signal_watch()
            return self._change_pipeline_state(self._Gst.State.NULL)
        else:
            return None

    def capture(self, timeout: Optional[float]) -> Result[Optional[Any], Exception]:
        if timeout is not None:
            timeout = timeout / 1000

        im: Optional[InternalMessage]
        try:
            im = self._queue.get(block=True, timeout=timeout)
        except Empty:
            im = None

        if im is None:
            return Ok(None)
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
                return Ok(None)
            else:
                return self._converter.convert_sample(sample)
        elif im.kind == InternalMessageKind.FROM_MESSAGE:
            message = im.payload
            if message.type == self._Gst.MessageType.EOS:
                self.stop()
                return Ok(None)
            elif message.type == self._Gst.MessageType.ERROR:
                return Err(Exception(message))
            else:
                return Err(RuntimeError("unreachable"))
        else:
            return Err(RuntimeError("unreachable"))

    def _cb_new_sample(self, _: Any) -> "Gst.FlowReturn":  # type: ignore  # noqa F821
        im = InternalMessage(InternalMessageKind.FROM_NEW_SAMPLE, None)
        try:
            self._queue.put_nowait(im)
        except Full:
            pass
        return self._Gst.FlowReturn.OK

    def _cb_message(self, _: Any, message: Any):  # type: ignore
        im = InternalMessage(InternalMessageKind.FROM_MESSAGE, message)
        self._queue.put(im)


class DummyMessage:
    def __init__(self, t: Any):
        self.type = t
