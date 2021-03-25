__all__ = [
    "dict_rec_get",
]


def dict_rec_get(d, path, default):
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
        if isinstance(d, dict) and (p in d):
            d = d[p]
        else:
            return default

    return d
