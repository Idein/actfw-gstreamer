import logging as _logging

# noqa idiom
if True:
    logger = _logging.getLogger(__name__)
    logger.addHandler(_logging.NullHandler())

import copy
from typing import Any, Dict

from .pipeline import AppsinkColorFormat, PipelineBuilder, PipelineGenerator

__all__ = [
    "videotestsrc",
    "rtsp_h264",
]


DEFAULT_CAPS = {
    "width": 640,
    "height": 480,
}


def videotestsrc(pattern: str = "smpte", caps: Dict[str, Any] = DEFAULT_CAPS) -> PipelineGenerator:
    """
    Create a pipeline like:
        videotestsrc pattern=<pattern>
        ! video/x-raw,format=RGB,... \
        ! appsink

    args:
        - pattern: `str`, defaults "smpte".
        - caps: `dict`,
            {
                'width': int,
                'height': int,
                'framerate': Option[int], // Default: 10
            }
    returns:
        - :class:`~PipelineGenerator`
    """

    caps = copy.copy(caps)
    assert "width" in caps
    assert "height" in caps
    if "framerate" not in caps:
        caps["framerate"] = 10

    return (
        PipelineBuilder(force_format=AppsinkColorFormat.RGB)
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


def rtsp_h264(
    proxy: str,
    location: str,
    protocols: str,
    decoder_type: str,
    caps: Dict[str, Any] = DEFAULT_CAPS,
) -> PipelineGenerator:
    """
    Create a pipeline like:
        rtspsrc proxy=<proxy> location=<location> \
        ! rtph264depay ! h264parse ! <decoder> \
        ! videorate ! videoscale ! videoconvert \
        ! video/x-raw,format=RGB,... \
        ! appsink
    where
        <decoder> = v4l2h264dec (if decoder_type == 'v4l2')
                  = omxh264dec (if decoder_type == 'omx')

    args:
        - proxy: proxy URL 'tcp://...'
        - location: rtsp resource location URL 'rtsp://<host>:<port>/<path>'
        - decoder_type: string, 'v4l2' | 'omx' | 'libav'
        - caps: `dict`
            {
                'width': int,
                'height': int,
                'framerate': Option[int], // Default: 10
            }
    returns:
        - :class:`~PipelineGenerator`
    """

    if decoder_type == "v4l2":
        decoder = "v4l2h264dec"
    elif decoder_type == "omx":
        decoder = "omxh264dec"
    elif decoder_type == "libav":
        decoder = "avdec_h264"
    else:
        raise ValueError(f"decoder_type should be 'v4l2' | 'omx' | 'libav', but got: {decoder_type}")

    return _rtsp_h264(proxy, location, protocols, decoder, caps)


def _rtsp_h264(
    proxy: str,
    location: str,
    protocols: str,
    decoder: str,
    caps: Dict[str, Any],
) -> PipelineGenerator:
    assert "width" in caps
    assert "height" in caps
    assert "framerate" in caps

    rtspsrc_props = {
        "location": location,
        "protocols": protocols,
        "latency": 0,
        "max-rtcp-rtp-time-diff": 100,
        "drop-on-latency": True,
    }
    if proxy is not None:
        rtspsrc_props["proxy"] = proxy

    return (
        PipelineBuilder(force_format=AppsinkColorFormat.RGB)
        .add("rtspsrc", rtspsrc_props)
        .add("rtph264depay")
        .add("h264parse")
        .add(decoder)
        .add(
            "videorate",
            {
                # We don't use `drop-only` because omxh264dec generates a frame with `framerate=0/1`
                # in the startup for some cameras, and it causes a fatal error.
                # 'drop-only': True,
                "skip-to-first": True,
            },
        )
        .add("videoscale")
        .add("videoconvert")
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
