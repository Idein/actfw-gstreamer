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

from typing import Any, Union

import PIL
from result import Err, Ok, Result

from ..util import get_gst

__all__ = [
    "ConverterBase",
    "ConverterRaw",
    "ConverterPIL",
]


class ConverterBase:
    def convert_sample(
        self,
        sample: "GstSample",  # type: ignore  # noqa F821
    ) -> Result[Any, Exception]:
        """
        args:
            - sample: :class:`~GstSample`
        returns:
            - `Any`, depends on concrete classes
            - :class:`~Exception`
        """

        raise NotImplementedError()


class ConverterRaw(ConverterBase):
    def __init__(self) -> None:
        self._Gst = get_gst()

    def convert_sample(  # type: ignore  # reason: incompatible return type, but actually compatible
        self,
        sample: "GstSample",  # type: ignore  # noqa F821
    ) -> Result[bytes, RuntimeError]:
        # Note that `gst_buffer_extract_dup()` cause a memory leak.
        # c.f. https://github.com/beetbox/audioread/pull/84
        buf = sample.get_buffer()
        success, info = buf.map(self._Gst.MapFlags.READ)
        if success:
            data = info.data
            ret = bytes(data)
            buf.unmap(info)
            return Ok(ret)
        else:
            return Err(RuntimeError("`gst_buffer_map()` failed"))


class ConverterPIL(ConverterBase):
    def __init__(self) -> None:
        self._Gst = get_gst()

    def convert_sample(  # type: ignore  # reason: incompatible return type, but actually compatible
        self,
        sample: "GstSample",  # type: ignore  # noqa F821
    ) -> Result[PIL.Image.Image, Union[RuntimeError, ValueError]]:
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        logger.debug(f"structure: {structure}")
        format_ = structure.get_value("format")
        logger.debug(f"format: {format_}")
        if format_ == "BGR":
            raw_mode = "BGR"
        elif format_ == "RGB":
            raw_mode = "RGB"
        elif format_ == "RGBx":
            raw_mode = "RGBX"
        else:
            return Err(ValueError(f"Unknown format: {format_}"))
        shape = (structure.get_value("width"), structure.get_value("height"))
        logger.debug(f"shape: {shape}")

        # Note that `gst_buffer_extract_dup()` cause a memory leak.
        # c.f. https://github.com/beetbox/audioread/pull/84
        buf = sample.get_buffer()
        success, info = buf.map(self._Gst.MapFlags.READ)
        if success:
            data = info.data
            ret = PIL.Image.frombytes("RGB", shape, data, "raw", raw_mode)
            buf.unmap(info)
            return Ok(ret)
        else:
            return Err(RuntimeError("`gst_buffer_map()` failed"))
