from .gstreamer.exception import GstNotInitializedError

__all__ = []  # type: ignore


CACHED_GST = None


def _get_gst() -> "Gst":  # type: ignore  # noqa F821
    global CACHED_GST

    if CACHED_GST is None:
        try:
            import gi  # type: ignore[import]

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # type: ignore[import]

            CACHED_GST = Gst
            if not Gst.is_initialized():
                raise GstNotInitializedError()
        except Exception as e:
            raise GstNotInitializedError() from e

    return CACHED_GST
