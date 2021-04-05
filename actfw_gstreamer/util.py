from typing import Any, Dict, List

from .gstreamer.exception import GstNotInitializedError

__all__ = [
    "dict_rec_get",
    "get_gst",
]


def dict_rec_get(d: Dict[Any, Any], path: List[Any], default: Any) -> Any:
    """
    Get an element of path from dict.

    >>> d = {'a': 'a', 'b': {'c': 'bc', 'd': {'e': 'bde'}}}

    Simple get:

    >>> dict_rec_get(d, ['a'], None)
    'a'

    Returns default if key does not exist:

    >>> dict_rec_get(d, ['c'], None) is None
    True
    >>> dict_rec_get(d, ['c'], 0)
    0

    Get recursive:

    >>> dict_rec_get(d, ['b', 'c'], None)
    'bc'
    >>> dict_rec_get(d, ['b', 'd'], None)
    {'e': 'bde'}
    >>> dict_rec_get(d, ['b', 'd', 'e'], None)
    'bde'
    >>> dict_rec_get(d, ['b', 'nopath'], None) is None
    True
    """

    assert isinstance(path, list)

    while len(path) != 0:
        p = path[0]
        path = path[1:]
        if isinstance(d, dict) and (p in d):  # type: ignore
            d = d[p]
        else:
            return default

    return d


CACHED_GST = None


def get_gst() -> "Gst":  # type: ignore  # noqa F821
    global CACHED_GST

    if CACHED_GST is None:
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            CACHED_GST = Gst
            if not Gst.is_initialized():
                raise GstNotInitializedError()
        except Exception as e:
            raise GstNotInitializedError() from e

    return CACHED_GST
