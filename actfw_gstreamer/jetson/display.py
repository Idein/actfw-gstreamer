import threading

from PIL import Image
from gi.repository import Gst, GObject


class Display:
    """Display using nvoverlaysink plugin"""

    def __init__(self, size, fps):
        """
        Args:
            size (int, int): display area resolution
            fps (int): framerate
        """
        self._pipeline = Gst.Pipeline()

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', Display._on_bus_error)

        # define elements
        self._appsrc = Gst.ElementFactory.make('appsrc')
        self._appsrc.set_property('emit-signals', 'True')
        self._appsrc.set_property('is-live', 'True')
        self._appsrc.set_property('block', 'True')

        capsfilter1 = Gst.ElementFactory.make('capsfilter')
        capsfilter1.set_property('caps', Gst.caps_from_string(
            f'video/x-raw,format=RGBA,width={size[0]},height={size[1]},framerate={fps}/1'
        ))

        nvvidconv = Gst.ElementFactory.make('nvvidconv')

        capsfilter2 = Gst.ElementFactory.make('capsfilter')
        capsfilter2.set_property('caps', Gst.caps_from_string(
            'video/x-raw(memory:NVMM),format=NV12'
        ))

        nvoverlaysink = Gst.ElementFactory.make('nvoverlaysink')

        # add elements
        self._pipeline.add(self._appsrc)
        self._pipeline.add(capsfilter1)
        self._pipeline.add(nvvidconv)
        self._pipeline.add(capsfilter2)
        self._pipeline.add(nvoverlaysink)

        # link elements
        self._appsrc.link(capsfilter1)
        capsfilter1.link(nvvidconv)
        nvvidconv.link(capsfilter2)
        capsfilter2.link(nvoverlaysink)

        self._pipeline.set_state(Gst.State.PLAYING)

        self._glib_loop = GObject.MainLoop()
        threading.Thread(target=self._glib_loop.run).start()

    def update(self, src_im: Image):
        """
        Update display.

        Args:
            src_im (PIL.Image): update image (RGB)
        """
        gst_buffer = Display._im_to_gst_buffer(src_im)
        self._appsrc.emit('push-buffer', gst_buffer)
        return Gst.FlowReturn.OK

    def stop(self):
        self._pipeline.set_state(Gst.State.NULL)
        self._glib_loop.quit()

    @classmethod
    def _on_bus_error(cls, bus, msg):
        print('on_error():', msg.parse_error())

    @classmethod
    def _im_to_gst_buffer(cls, im: Image) -> Gst.Buffer:
        """Converts PIL Image (RGB) to Gst.Buffer (RGBA)"""
        im.putalpha(255)
        return Gst.Buffer.new_wrapped(im.tobytes())
