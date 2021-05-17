import logging as _logging

# noqa idiom
if True:
    logger = _logging.getLogger(__name__)
    logger.addHandler(_logging.NullHandler())

import time
from typing import Optional

from actfw_core.task import Producer
from PIL.Image import Image as PIL_Image

from .gstreamer.exception import ConnectionLostError, PipelineBuildError
from .gstreamer.stream import GstStreamBuilder
from .restart_handler import Restart, RestartHandlerBase, Stop

__all__ = [
    "GstreamerCapture",
]


class GstreamerCapture(Producer[PIL_Image]):
    _builder: GstStreamBuilder
    _restart_handler: RestartHandlerBase

    def __init__(self, builder: GstStreamBuilder, restart_handler: RestartHandlerBase):
        """
        Captured Frame Producer using GStreamer.

        Genrates `Frame`s of given `GonverterBase::ConvertResult`, where `ConverterBase` is in `builder`.

        args:
            - builder: :class:`~GstStreamBuilder`
            - restart_handler: :class:`~RestartHandlerBase`
        """

        assert isinstance(
            builder, GstStreamBuilder
        ), f"builder should be instance of GstStreamBuilder, but got: {type(builder)}"
        assert isinstance(
            restart_handler, RestartHandlerBase
        ), f"restart_handler should be instance of RestartHandler, but got: {type(restart_handler)}"

        super().__init__()

        self._builder = builder
        self._restart_handler = restart_handler

    def run(self) -> None:
        connection_lost_threshold = self._restart_handler.connection_lost_secs_threshold()

        try:
            while True:
                try:
                    self._loop(connection_lost_threshold)
                except PipelineBuildError as e:
                    logger.debug(e)

                    action = self._restart_handler.pipeline_build_error(e)
                    if isinstance(action, Stop):
                        return None
                    elif isinstance(action, Restart):
                        continue
                    else:
                        raise RuntimeError("unreachable")
                except ConnectionLostError as e:
                    logger.debug(e)

                    action = self._restart_handler.connection_lost(e)
                    if isinstance(action, Stop):
                        return None
                    elif isinstance(action, Restart):
                        continue
                    else:
                        raise RuntimeError("unreachable")

                break
        finally:
            self.stop()

    def _loop(self, connection_lost_threshold: Optional[float]) -> None:
        no_sample_start: Optional[float] = None
        with self._builder.start_streaming() as stream:
            while self._is_running():
                if not stream.is_running():
                    raise ConnectionLostError()

                if (connection_lost_threshold is not None) and (no_sample_start is not None):
                    if (time.time() - no_sample_start) > connection_lost_threshold:
                        raise ConnectionLostError()

                value = stream.capture(timeout_secs=1)
                if value is None:
                    if no_sample_start is None:
                        no_sample_start = time.time()
                else:
                    no_sample_start = None
                    self._outlet(value)
