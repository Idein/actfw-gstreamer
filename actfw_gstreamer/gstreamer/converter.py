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

from typing import Any, Optional, Tuple, Union

import PIL

from ..util import get_gst

__all__ = [
    "ConverterBase",
    "ConverterRaw",
    "ConverterPIL",
]


class ConverterBase:
    def convert_sample(self, sample: "GstSample") -> Tuple[Any, Optional[Exception]]:  # type: ignore  # noqa F821
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

    def convert_sample(self, sample: "GstSample") -> Tuple[Optional[bytes], Optional[RuntimeError]]:  # type: ignore  # noqa F821
        """
        returns:
            - :class:`~bytes`
            - :class:`~RuntimeError`
        """

        # Note that `gst_buffer_extract_dup()` cause a memory leak.
        # c.f. https://github.com/beetbox/audioread/pull/84
        buf = sample.get_buffer()
        success, info = buf.map(self._Gst.MapFlags.READ)
        if success:
            data = info.data
            ret = bytes(data)
            buf.unmap(info)
            return ret, None
        else:
            return None, RuntimeError("`gst_buffer_map()` failed")


class ConverterPIL(ConverterBase):
    def __init__(self) -> None:
        self._Gst = get_gst()

    def convert_sample(self, sample: "GstSample") -> Tuple[Optional[PIL.Image], Optional[Union[RuntimeError, ValueError]]]:  # type: ignore  # noqa F821
        """
        returns:
            - :class:`~PIL.Image`
            - :class:`~RuntimeError` or :class:`~ValueError`
        """

        caps = sample.get_caps()
        structure = caps.get_structure(0)
        logger.info(f"structure: {structure}")
        format_ = structure.get_value("format")
        logger.info(f"format: {format_}")
        if format_ == "BGR":
            raw_mode = "BGR"
        elif format_ == "RGB":
            raw_mode = "RGB"
        elif format_ == "RGBx":
            raw_mode = "RGBX"
        else:
            return None, ValueError(f"Unknown format: {format_}")
        shape = (structure.get_value("width"), structure.get_value("height"))
        logger.info(f"shape: {shape}")

        # Note that `gst_buffer_extract_dup()` cause a memory leak.
        # c.f. https://github.com/beetbox/audioread/pull/84
        buf = sample.get_buffer()
        success, info = buf.map(self._Gst.MapFlags.READ)
        if success:
            data = info.data
            ret = PIL.Image.frombytes("RGB", shape, data, "raw", raw_mode)
            buf.unmap(info)
            return ret, None
        else:
            return None, RuntimeError("`gst_buffer_map()` failed")
