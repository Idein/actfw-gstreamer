import time
import traceback
from queue import Full

from actfw_core.capture import Frame
from actfw_core.task import Producer

from .gstreamer.exception import PipelineBuildError
from .gstreamer.stream import GstStreamBuilder
from .util import dict_rec_get

__all__ = [
    "GstreamerCapture",
]


class GstreamerCapture(Producer):
    def __init__(self, builder, config={}):  # noqa B006
        """
        args:
            - builder: :class:`~GstStreamBuilder`
            - config: dict,
                  {
                      'restart': {
                          'pipeline_build_error': { // existance means turn on.
                              'callback': function 0-args-0-returns,
                          },
                          'suspicious_connection_lost': {
                              'secs_approx': int, // Restart if suspicious connection lost continues this seconds.
                              'callback': function 0-args-0-returns,
                          }
                      },
                  }
        """

        assert isinstance(
            builder, GstStreamBuilder
        ), f"builder should be instance of GstStreamBuilder, but got: {type(builder)}"

        super(GstreamerCapture, self).__init__()

        self._builder = builder
        self._config = config

        self.frames = []

    def run(self):
        class ConnectionLost(Exception):
            pass

        connection_lost_threshold = dict_rec_get(self._config, ["restart", "suspicious_connection_lost", "secs_approx"], None)

        try:
            while True:
                try:
                    self._loop(ConnectionLost, connection_lost_threshold)
                except PipelineBuildError as e:
                    print(e)
                    if dict_rec_get(self._config, ["restart", "pipeline_build_error"], False):
                        cb = dict_rec_get(self._config, ["restart", "pipeline_build_error", "callback"], None)
                        if cb:
                            cb()
                        time.sleep(1)
                        continue
                    else:
                        raise e
                except ConnectionLost:
                    cb = dict_rec_get(self._config, ["restart", "suspicious_connection_lost", "callback"], None)
                    if cb:
                        cb()
                    continue

                break
        finally:
            self.stop()

    def _loop(self, ConnectionLost, connection_lost_threshold):
        no_sample = 0
        with self._builder.start_streaming() as stream:
            while self._is_running():
                if not stream.is_running():
                    raise ConnectionLost()

                if connection_lost_threshold and (no_sample >= connection_lost_threshold):
                    raise ConnectionLost()

                value = stream.capture(timeout=1000)
                if value is None:
                    no_sample += 1
                    continue
                else:
                    no_sample = 0

                updated = 0
                for frame in reversed(self.frames):
                    if frame._update(value):
                        updated += 1
                    else:
                        break
                self.frames = self.frames[len(self.frames) - updated :]

                frame = Frame(value)

                if self._outlet(frame):
                    pass
                    self.frames.append(frame)

    def _outlet(self, o):
        length = len(self.out_queues)
        while self._is_running():
            try:
                self.out_queues[self.out_queue_id % length].put(o, block=False)
                self.out_queue_id += 1
                return True
            except Full:
                return False
            except Exception:
                traceback.print_exc()
        return False
