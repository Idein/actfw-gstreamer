import threading
from pathlib import Path
from typing import Callable, Optional

import actfw_core
import actfw_gstreamer.gstreamer.preconfigured_pipeline as preconfigured_pipeline
import numpy as np
import PIL
from actfw_core.task import Consumer, Pipe
from actfw_gstreamer.capture import GstreamerCapture
from actfw_gstreamer.gstreamer.converter import ConverterPIL
from actfw_gstreamer.gstreamer.exception import GstNotInitializedError, PipelineBuildError
from actfw_gstreamer.gstreamer.pipeline import PipelineBuilder
from actfw_gstreamer.gstreamer.stream import GstStreamBuilder
from actfw_gstreamer.restart_handler import SimpleRestartHandler

DEFAULT_CAPS = {
    "width": 640,
    "height": 480,
    "framerate": 10,
}


def videotestsrc_capture() -> GstreamerCapture:
    pipeline_generator = preconfigured_pipeline.videotestsrc("smpte100", DEFAULT_CAPS)
    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 0)
    return GstreamerCapture(builder, restart_handler)


def _test_not_inited() -> None:
    try:
        videotestsrc_capture()
        raise RuntimeError("unreachable")
    except Exception as err:
        assert type(err) is GstNotInitializedError


INITALIZED = False
LOCK = threading.Lock()


def init_gst() -> None:
    global INITALIZED

    with LOCK:
        if not INITALIZED:
            # Tricky: There's no other timing.
            _test_not_inited()

            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            Gst.init(None)
            INITALIZED = True


def test_missing_plugin() -> None:
    init_gst()

    pattern = "smpte100"
    caps = DEFAULT_CAPS

    pipeline_generator = (
        PipelineBuilder(force_format="RGB")
        .add(
            "dummy-videotestsrc",
            {"pattern": pattern},
        )
        .add("videoscale")
        .add_appsink_with_caps(
            {
                "max-buffers": 1,
                "drop": True,
                "emit-signals": True,
            },
            caps,
        )
        .finalize()
    )

    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 5)
    capture = GstreamerCapture(builder, restart_handler)

    # Tricky: len(Pipe.out_queues) must be > 0.
    capture.connect(Pipe())

    try:
        capture.run()
        raise RuntimeError("unreachable")
    except Exception as err:
        assert type(err) is PipelineBuildError
        assert err.args[0] == "failed to create `dummy-videotestsrc`"


def test_wrong_property_key() -> None:
    init_gst()

    pattern = "smpte100"
    caps = DEFAULT_CAPS

    pipeline_generator = (
        PipelineBuilder(force_format="RGB")
        .add(
            "videotestsrc",
            {"wrong-property-key": pattern},
        )
        .add("videoscale")
        .add_appsink_with_caps(
            {
                "max-buffers": 1,
                "drop": True,
                "emit-signals": True,
            },
            caps,
        )
        .finalize()
    )

    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 5)
    capture = GstreamerCapture(builder, restart_handler)

    # Tricky: len(Pipe.out_queues) must be > 0.
    capture.connect(Pipe())

    try:
        capture.run()
        raise RuntimeError("unreachable")
    except Exception as err:
        assert type(err) is PipelineBuildError
        # assert err.__cause__ == TypeError("object of type `GstVideoTestSrc' does not have property `wrong-property-key'")
        assert type(err.__cause__) is TypeError
        assert err.__cause__.args[0] == "object of type `GstVideoTestSrc' does not have property `wrong-property-key'"


def test_wrong_property_value() -> None:
    init_gst()

    pattern = "wrong-propetry-value"
    caps = DEFAULT_CAPS

    pipeline_generator = (
        PipelineBuilder(force_format="RGB")
        .add(
            "videotestsrc",
            {"pattern": pattern},
        )
        .add("videoscale")
        .add_appsink_with_caps(
            {
                "max-buffers": 1,
                "drop": True,
                "emit-signals": True,
            },
            caps,
        )
        .finalize()
    )

    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 5)
    capture = GstreamerCapture(builder, restart_handler)

    # Tricky: len(Pipe.out_queues) must be > 0.
    capture.connect(Pipe())

    try:
        capture.run()
        raise RuntimeError("unreachable")
    except Exception as err:
        assert type(err) is PipelineBuildError
        # assert err.__cause__ == TypeError("could not convert 'wrong-propetry-value' to type 'GstVideoTestSrcPattern' when setting property 'GstVideoTestSrc.pattern'")  # noqa B950
        assert type(err.__cause__) is TypeError
        assert (
            err.__cause__.args[0]
            == "could not convert 'wrong-propetry-value' to type 'GstVideoTestSrcPattern' when setting property 'GstVideoTestSrc.pattern'"
        )


def test_rtsp_h264_with_wrong_url():
    init_gst()

    pipeline_generator = preconfigured_pipeline.rtsp_h264(None, "rtsp://localhost:554/h264", "tcp", "libav", DEFAULT_CAPS)

    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 0)
    capture = GstreamerCapture(builder, restart_handler)

    # Tricky: len(Pipe.out_queues) must be > 0.
    capture.connect(Pipe())

    try:
        capture.run()
        raise RuntimeError("unreachable")
    except Exception as err:
        assert type(err) is PipelineBuildError
        assert err.args[0] == (
            "failed to change state of pipeline:"
            " desired = <enum GST_STATE_PLAYING of type Gst.State>, (<enum GST_STATE_CHANGE_FAILURE of type Gst.StateChangeReturn>,"
            " state=<enum GST_STATE_PAUSED of type Gst.State>, pending=<enum GST_STATE_PLAYING of type Gst.State>)"
        )


SMPTE_100_PATH = Path(__file__).parent / "data" / "smpte100.png"


class Saver(Consumer):
    _stop_callback: Callable[[], None]

    def __init__(self, stop_callback: Callable[[], None]) -> None:
        super().__init__()

        self._stop_callback = stop_callback

    def proc(self, frame) -> None:
        image = frame.getvalue()
        image.save(SMPTE_100_PATH, "PNG")
        self.stop()
        self._stop_callback()


def generate_reference_data() -> None:
    print("Generating reference data...")

    init_gst()

    app = actfw_core.Application()

    capture = videotestsrc_capture()
    app.register_task(capture)

    def stop_callback() -> None:
        app._handler(None, None)

    saver = Saver(stop_callback)
    app.register_task(saver)

    capture.connect(saver)

    app.run()

    print("Generating reference data... done")


class Validator(Consumer):
    """
    Test the `Prodecer` generates the same frames `count_threshould` times that consists of the same image to `self._image`.
    """

    _count_threshold: int
    _count: int
    _stop_callback: Callable[[], None]
    _err: Optional[Exception]

    def __init__(self, count_threshould: int, stop_callback: Callable[[], None]) -> None:
        super().__init__()

        self._count_threshold = count_threshould
        self._count = 0
        self._stop_callback = stop_callback
        self._image = PIL.Image.open(SMPTE_100_PATH)
        self._err = None

    def ensure_ok(self) -> None:
        if self._err is None:
            return None
        else:
            raise self._err

    def proc(self, frame) -> None:
        image = frame.getvalue()
        # Tricky: actfw does not propagate errors to main thread automatically.
        try:
            assert np.array_equal(np.asarray(self._image), np.asarray(image))
        except Exception as err:
            self._err = err
            self.stop()
            self._stop_callback()

        self._count += 1
        if self._count_threshold < self._count:
            self.stop()
            self._stop_callback()


def test_videotestsrc():
    FORMATS = [
        "BGR",
        "RGB",
        "RGBx",
    ]
    for format_ in FORMATS:
        test_videotestsrc_aux(format_)


def test_videotestsrc_aux(format_):
    init_gst()

    app = actfw_core.Application()

    pattern = "smpte100"
    caps = DEFAULT_CAPS

    pipeline_generator = (
        PipelineBuilder(force_format=format_)
        .add(
            "videotestsrc",
            {"pattern": pattern},
        )
        .add("videoscale")
        .add_appsink_with_caps(
            {
                "max-buffers": 1,
                "drop": True,
                "emit-signals": True,
            },
            caps,
        )
        .finalize()
    )

    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 5)
    capture = GstreamerCapture(builder, restart_handler)
    app.register_task(capture)

    def stop_callback() -> None:
        app._handler(None, None)

    validator = Validator(10, stop_callback)
    app.register_task(validator)

    capture.connect(validator)

    app.run()

    validator.ensure_ok()


if __name__ == "__main__":
    generate_reference_data()
