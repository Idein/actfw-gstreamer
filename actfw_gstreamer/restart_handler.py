from abc import ABC, abstractmethod
from typing import Optional, Union

from .gstreamer.exception import ConnectionLostError, PipelineBuildError

__all__ = [
    "RestartAction",
    "Stop",
    "Restart",
    "RestartHandlerBase",
    "SimpleRestartHandler",
]


class Stop:
    pass


class Restart:
    pass


RestartAction = Union[Stop, Restart]


class RestartHandlerBase(ABC):
    @abstractmethod
    def connection_lost_secs_threshold(self) -> Optional[float]:
        """
        :class:`~GstCapture.run` waits a new frame this seconds.  If cannot get no frames more than
        this seconds, raise :class:`~ConnectionLostError`.
        """

        raise NotImplementedError()

    @abstractmethod
    def pipeline_build_error(self, err: PipelineBuildError) -> RestartAction:
        """
        Called from :class:`~GstCapture.run` when got :class:`~PipelineBuildError`.
        """

        raise NotImplementedError()

    @abstractmethod
    def connection_lost(self, err: ConnectionLostError) -> RestartAction:
        """
        Called from :class:`~GstCapture.run` when got :class:`~ConnectionLostError`.
        """

        raise NotImplementedError()


class SimpleRestartHandler(RestartHandlerBase):
    _connection_lost_secs_threshold: int
    _error_count_threshold: int
    _error_count: int

    def __init__(self, connection_lost_secs_threshold: int, error_count_threshould: int) -> None:
        self._connection_lost_secs_threshold = connection_lost_secs_threshold
        self._error_count_threshold = error_count_threshould
        self._error_count = 0

    def connection_lost_secs_threshold(self) -> Optional[float]:
        return self._connection_lost_secs_threshold

    def pipeline_build_error(self, err: PipelineBuildError) -> RestartAction:
        self._error_count += 1

        if self._error_count_threshold < self._error_count:
            raise err
        else:
            print("pipeline build error.  restarting...", flush=True)

            return Restart()

    def connection_lost(self, err: ConnectionLostError) -> RestartAction:
        self._error_count += 1

        if self._error_count_threshold < self._error_count:
            raise err
        else:
            print("suspicious connection lost.  restarting...", flush=True)

            return Restart()
