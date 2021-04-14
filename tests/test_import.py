from nose2.tools import params


@params(
    {
        "from": "actfw_gstreamer.capture",
        "import": "GstreamerCapture",
    },
    {
        "from": "actfw_gstreamer.gstreamer.pipeline",
        "import": "PipelineBuilder, PipelineGenerator",
    },
    {
        "from": "actfw_gstreamer.gstreamer.converter",
        "import": "ConverterBase, ConverterRaw, ConverterPIL",
    },
    {
        "from": "actfw_gstreamer.gstreamer.exception",
        "import": "GstNotInitializedError, PipelineBuildError, ConnectionLostError",
    },
    {
        "from": "actfw_gstreamer.gstreamer.preconfigured_pipeline",
        "import": "videotestsrc, rtsp_h264",
    },
    {
        "from": "actfw_gstreamer.gstreamer.stream",
        "import": "GstStreamBuilder",
    },
    {
        "from": "actfw_gstreamer.restart_handler",
        "import": "RestartAction, Stop, Restart, RestartHandlerBase, SimpleRestartHandler",
    },
)
def test_import_actfw_gstreamer(param):
    exec(f"""from {param['from']} import {param['import']}""")
