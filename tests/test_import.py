import pytest


@pytest.mark.parametrize(
    "from_, import_",
    [
        ("actfw_gstreamer.capture", "GstreamerCapture"),
        ("actfw_gstreamer.gstreamer.pipeline", "PipelineBuilder, PipelineGenerator"),
        ("actfw_gstreamer.gstreamer.converter", "ConverterBase, ConverterRaw, ConverterPIL"),
        ("actfw_gstreamer.gstreamer.exception", "GstNotInitializedError, PipelineBuildError, ConnectionLostError"),
        ("actfw_gstreamer.gstreamer.preconfigured_pipeline", "videotestsrc, rtsp_h264"),
        ("actfw_gstreamer.gstreamer.stream", "GstStreamBuilder"),
        ("actfw_gstreamer.restart_handler", "RestartAction, Stop, Restart, RestartHandlerBase, SimpleRestartHandler"),
    ],
)
def test_import_actfw_gstreamer(from_, import_):
    exec(f"""from {from_} import {import_}""")
