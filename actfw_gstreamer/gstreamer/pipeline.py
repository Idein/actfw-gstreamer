import logging as _logging

# noqa idiom
if True:
    logger = _logging.getLogger(__name__)
    handler = _logging.StreamHandler()
    _level = _logging.WARNING
    handler.setLevel(_level)
    logger.setLevel(_level)
    logger.addHandler(handler)
    logger.propagate = False


import copy
from typing import Any, List, NamedTuple, Optional

from ..util import get_gst
from .exception import PipelineBuildError

__all__ = [
    "PipelineBuilder",
    "PipelineGenerator",
    "BuiltPipeline",
    "PreconfiguredPipeline",
]


def _make_element(Gst: "Gst", element: str, props: dict[str, Any]) -> "Gst.Element":  # type: ignore  # noqa F821
    """
    exceptions:
        - :class:`~PipelineBuildError`
    """

    x = Gst.ElementFactory.make(element)
    if not x:
        raise PipelineBuildError(f"failed to create `{element}`")

    for (k, v) in props.items():
        logger.info(f"set property: {k} => {v}")
        x.set_property(k, v)

    return x


def _make_capsfilter(Gst: "Gst", caps_string: str) -> "Gst.Element":  # type: ignore  # noqa F821
    """
    exceptions:
        - :class:`~PipelineBuildError`
    """

    caps = Gst.caps_from_string(caps_string)
    return _make_element(Gst, "capsfilter", {"caps": caps})


class PipelineBuilder:
    def __init__(self, force_format: Optional[str] = None):
        assert force_format in [None, "BGR", "RGB", "RGBx"]

        self._Gst = get_gst()
        self._thunks: List[Any] = []
        self._caps_string: Optional[str] = None
        self._finalized = False

        if force_format is None:
            self._caps_base = "video/x-raw,format=(string){BGR,RGB,RGBx}"
        else:
            self._caps_base = f"video/x-raw,format={force_format}"

    def is_finalized(self) -> bool:
        return self._finalized

    def add(self, element: str, props: dict[str, Any] = {}) -> PipelineBuilder:  # type: ignore  # noqa B006
        self._thunks.append(lambda: _make_element(self._Gst, element, props))
        return self

    def add_capsfilter(self, caps_string: str) -> PipelineBuilder:  # noqa F821
        self._thunks.append(lambda: _make_capsfilter(self._Gst, caps_string))
        return self

    def add_appsink_with_caps(self, props: dict[str, Any] = {}, caps: dict[str, Any] = {}) -> PipelineBuilder:  # type: ignore  # noqa B006
        """
        Effect: Change `self.is_finalized()` to be true.

        args:
            - caps: `dict`
                {
                    'width': int,
                    'height': int,
                    'framerate': Optional[int], # Used as `framerate={framerate}/1`.
                }
        """

        assert "width" in caps
        assert "height" in caps
        assert "framerate" in caps

        self.add("appsink", props)

        s = self._caps_base
        for key in ["width", "height"]:
            if key in caps:
                s += f",{key}={caps[key]}"
        framerate = caps["framerate"]
        if framerate is not None:
            s += f",framerate={framerate}/1"
        self._caps_string = s
        self._finalized = True

        return self

    def finalize(self) -> PipelineGenerator:  # noqa F821 (Hey linter, see below.)
        """
        returns:
            - :class:`~PipelineGenerator`
        """

        assert self._finalized

        return PipelineGenerator(self._thunks, self._caps_string)  # type: ignore


class PipelineGenerator:
    """
    Users should make instances of this class through :class:`~PipelineBuilder`.
    """

    def __init__(self, thunks: List[Any], caps_string: str):
        self._Gst = get_gst()
        self._thunks = thunks
        self._caps_string = caps_string

    def build(self) -> BuiltPipeline:  # noqa F821 (Hey linter, see below.)
        """
        returns:
            - :class:`~BuiltPipeline`

        exceptions:
            - :class:`~PipelineBuildError`
        """

        elements = [f() for f in self._thunks]
        logger.debug(f"_caps_string: {self._caps_string}")
        caps = self._Gst.caps_from_string(self._caps_string)
        elements[-1].set_property("caps", caps)
        pipeline = self._Gst.Pipeline()
        for x in elements:
            pipeline.add(x)
        for (x, y) in zip(elements, elements[1:]):
            # c.f. http://gstreamer-devel.966125.n4.nabble.com/Problem-linking-rtspsrc-to-any-other-element-td3051725.html
            if x.get_static_pad("src"):
                logger.info(f"get static pad of src of {x}")
                if not x.link(y):
                    raise PipelineBuildError(f"failed to link {x} {y}")
            else:

                def f(x: "Gst.Element", y: "Gst.Element") -> None:  # type: ignore  # noqa F821
                    logger.info(f"linking {x} and {y}")
                    x.link(y)

                x.connect("pad-added", lambda _a, _b, x=x, y=y: f(x, y))

        return BuiltPipeline(pipeline=pipeline, sink=elements[-1])


class BuiltPipeline(NamedTuple):
    pipeline: Any  # Gst.Pipeline
    sink: Any  # Gst.GstAppSink


DEFAULT_CAPS = {
    "width": 640,
    "height": 480,
}


class PreconfiguredPipeline:
    @classmethod
    def videotestsrc(cls, caps: dict[str, Any] = DEFAULT_CAPS) -> PipelineGenerator:  # type: ignore
        """
        Create a pipeline like:
            videotestsrc
            ! video/x-raw,format=RGB,... \
            ! appsink

        args:
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
            PipelineBuilder(force_format="RGB")
            .add("videotestsrc")
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

    @classmethod
    def rtsp_h264(
        cls,
        proxy: str,
        location: str,
        protocols: str,
        caps: dict[str, Any] = DEFAULT_CAPS,  # type: ignore
        decoder_type: str = "v4l2",
    ) -> PipelineGenerator:
        """
        Create a pipeline like:
            rtspsrc proxy=<proxy> location=<location> \
            ! rtph264depay ! h264parse ! <decoder> \
            ! videorate ! videoconvert ! videoscale \
            ! video/x-raw,format=RGB,... \
            ! appsink
        where
            <decoder> = v4l2h264dec (if decoder_type == 'v4l2')
                      = omxh264dec (if decoder_type == 'omx')

        args:
            - proxy: proxy URL 'tcp://...'
            - location: rtsp resource location URL 'rtsp://<host>:<port>/<path>'
            - caps: `dict`
                {
                    'width': int,
                    'height': int,
                    'framerate': Option[int], // Default: 10
                }
            - decoder_type: string, 'v4l2' | 'omx'
        returns:
            - :class:`~PipelineGenerator`
        """

        if decoder_type == "v4l2":
            decoder = "v4l2h264dec"
        elif decoder_type == "omx":
            decoder = "omxh264dec"
        else:
            raise ValueError(f"decoder_type should be 'v4l2' | 'omx', but got: {decoder_type}")

        return cls._rtsp_h264(proxy, location, protocols, caps, decoder)

    @classmethod
    def _rtsp_h264(
        cls,
        proxy: str,
        location: str,
        protocols: str,
        caps: dict[str, Any],  # type: ignore
        decoder: str,
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
            # 'do-retransmission': False,
            # 'udp-reconnect': True,
            # 'teardown-timeout': 5000,
            # 'timeout': 5000,
            # 'is-live': False,
        }
        if proxy is not None:
            rtspsrc_props["proxy"] = proxy

        return (
            PipelineBuilder(force_format="RGB")
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
            .add("videoconvert")
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
