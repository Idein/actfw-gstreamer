import logging as _logging

# noqa idiom
if True:
    logger = _logging.getLogger(__name__)
    logger.addHandler(_logging.NullHandler())

from abc import ABC, abstractmethod
from typing import Any, Union

import PIL
from PIL.Image import Image as PIL_Image
from result import Err, Ok, Result

from ..util import _get_gst
from .pipeline import AppsinkColorFormat

__all__ = [
    "ConverterBase",
    "ConverterRaw",
    "ConverterPIL",
]


class ConverterBase(ABC):
    # Associated type.  See also `_GstStream`.
    # type ConvertResult;

    # Here, Any = Self::ConvertResult.
    @abstractmethod
    def convert_sample(
        self,
        sample: "GstSample",  # type: ignore  # noqa F821
    ) -> Result[Any, Exception]:
        """
        Convert :class:`~GstSample` to some value.
        This class is intended to be used in :class:`~_GstStream`.

        args:
            - sample: :class:`~GstSample`
        returns:
            - `Any`, depends on concrete classes
            - :class:`~Exception`
        """

        raise NotImplementedError()


class ConverterRaw(ConverterBase):
    # type ConvertResult = bytes;

    _Gst: "Gst"  # type: ignore  # noqa F821

    def __init__(self) -> None:
        self._Gst = _get_gst()

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
    # type ConvertResult = PIL_Image;

    _Gst: "Gst"  # type: ignore  # noqa F821

    def __init__(self) -> None:
        self._Gst = _get_gst()

    def convert_sample(  # type: ignore  # reason: incompatible return type, but actually compatible
        self,
        sample: "GstSample",  # type: ignore  # noqa F821
    ) -> Result[PIL_Image, Union[RuntimeError, ValueError]]:
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        logger.debug(f"structure: {structure}")
        format_ = structure.get_value("format")
        logger.debug(f"format: {format_}")
        format__ = AppsinkColorFormat._from_caps_format(format_)
        if format__.is_err():
            return Err(format__.unwrap_err())
        raw_mode = format__.unwrap()._to_PIL_raw_mode()
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
