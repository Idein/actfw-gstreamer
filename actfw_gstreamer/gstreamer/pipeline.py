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


from typing import Any, Dict, List, NamedTuple, Optional

from result import Err, Ok, Result

from ..util import _get_gst
from .exception import PipelineBuildError

__all__ = [
    "PipelineBuilder",
    "PipelineGenerator",
]


def _make_element(Gst: "Gst", element: str, props: Dict[str, Any]) -> "Gst.Element":  # type: ignore  # noqa F821
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
    _Gst: "Gst"  # type: ignore  # noqa F821
    _thunks: List[Any]
    _caps_string: Optional[str]
    _finalized: bool

    def __init__(self, force_format: Optional[str] = None):
        assert force_format in [None, "BGR", "RGB", "RGBx"]

        self._Gst = _get_gst()
        self._thunks = []
        self._caps_string = None
        self._finalized = False

        if force_format is None:
            self._caps_base = "video/x-raw,format=(string){BGR,RGB,RGBx}"
        else:
            self._caps_base = f"video/x-raw,format={force_format}"

    def is_finalized(self) -> bool:
        return self._finalized

    def add(self, element: str, props: Dict[str, Any] = {}) -> "PipelineBuilder":  # noqa B006
        self._thunks.append(lambda: _make_element(self._Gst, element, props))
        return self

    def add_capsfilter(self, caps_string: str) -> "PipelineBuilder":  # noqa F821
        self._thunks.append(lambda: _make_capsfilter(self._Gst, caps_string))
        return self

    def add_appsink_with_caps(self, props: Dict[str, Any] = {}, caps: Dict[str, Any] = {}) -> "PipelineBuilder":  # noqa B006
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

    def finalize(self) -> "PipelineGenerator":  # noqa F821 (Hey linter, see below.)
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

    _Gst: "Gst"  # type: ignore  # noqa F821
    _thunks: List[Any]
    _caps_string: Optional[str]

    def __init__(self, thunks: List[Any], caps_string: str):
        self._Gst = _get_gst()
        self._thunks = thunks
        self._caps_string = caps_string

    def build(self) -> Result["_BuiltPipeline", PipelineBuildError]:  # noqa F821 (Hey linter, see below.)
        """
        returns:
            - :class:`~_BuiltPipeline`
        """

        try:
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
                        return Err(PipelineBuildError(f"failed to link {x} {y}"))
                else:

                    def f(x: "Gst.Element", y: "Gst.Element") -> None:  # type: ignore  # noqa F821
                        logger.info(f"linking {x} and {y}")
                        x.link(y)

                    x.connect("pad-added", lambda _a, _b, x=x, y=y: f(x, y))

            return Ok(_BuiltPipeline(pipeline=pipeline, sink=elements[-1]))
        except PipelineBuildError as err:
            return Err(err)
        except Exception as err:
            try:
                raise PipelineBuildError(err) from err
            except PipelineBuildError as err:
                return Err(err)


class _BuiltPipeline(NamedTuple):
    pipeline: "Gst.Pipeline"  # type: ignore  # noqa F821
    sink: "Gst.GstAppSink"  # type: ignore  # noqa F821
