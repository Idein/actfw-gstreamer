from ._version import __version__


def init():
    """Initializes GObject thread and GStreamer.

    An application using actfw-gstreamer must call this function at first.

    Examples:

        >>> import actfw_gstreamer
        >>> 
        >>> if __name__ == '__main__':
        >>>     actfw_gstreamer.init()
        >>>     # ...
    """
    if not init.initialized:
        import gi
        gi.require_version('Gst', '1.0')
        gi.require_version('GstVideo', '1.0')

        from gi.repository import Gst, GObject
        GObject.threads_init()
        Gst.init(None)

        init.initialized = True


init.initialized = False
