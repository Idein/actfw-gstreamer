# actfw-gstreamer

actfw's components using GStreamer for implementation.
actfw is a framework for Actcast Application written in Python.

## Installation

```console
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil 
sudo apt-get install libgstreamer1.0-dev libgirepository1.0-dev ibgstreamer-plugins-base1.0-dev libglib2.0-dev
pip3 install actfw-gstreamer
```

## Document

- [API References](https://idein.github.io/actfw-gstreamer/latest/)

## Usage

See [actfw-core](https://github.com/Idein/actfw-core) for basic usage of `actfw` framework.

### Initalization

An application using `actfw-gstreamer` have to initialize GStreamer library before using `actfw-gstreamer`'s components.

```python
if __name__ == '__main__':
    import gi

    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)

    main()
```

### `videotestsrc`

You can learn basic usage of `actfw-gstreamer` by using `videotestsrc`.

```python
from actfw_gstreamer.capture import GstreamerCapture
from actfw_gstreamer.gstreamer.converter import ConverterPIL
from actfw_gstreamer.gstreamer.stream import GstStreamBuilder
from actfw_gstreamer.restart_handler import SimpleRestartHandler


def videotestsrc_capture() -> GstreamerCapture:
    pipeline_generator = preconfigured_pipeline.videotestsrc()
    builder = GstStreamBuilder(pipeline_generator, ConverterPIL())
    restart_handler = SimpleRestartHandler(10, 5)
    return GstreamerCapture(builder, restart_handler)


def main():
    app = actfw_core.Application()

    capture = videotestsrc_capture()
    app.register_task(capture)

    consumer = YourConsumer()
    app.register_task(consumer)

    capture.connect(consumer)

    app.run()
```

This generates [`Frame`](https://idein.github.io/actfw-core/latest/actfw_core.html#actfw_core.capture.Frame)s using [videotestsrc](https://gstreamer.freedesktop.org/documentation/videotestsrc/index.html).

- `GstreamerCapture` is a [`Producer`](https://idein.github.io/actfw-core/latest/actfw_core.task.html#actfw_core.task.producer.Producer).
  - It generates `Frame`s consists of an output of `ConverterBase`.  In this case, converter class is `ConverterPIL` and output is `PIL.Image.Image`.
- `GstStreamBuilder` and `PipelineGenerator` determines how to build gstreamer pipelines.
- `preconfigured_pipeline` provides preconfigured `PipelineGenerator`s.
- `SimpleRestartHandler` is a simple implementation of `RestartHandlerBase`, which determines "restart strategy".

For more details, see [tests](tests/intergation_test/test_gstreamer_output.py).

### `rtspsrc`

You can use [rtspsrc](https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html) using `preconfigured_pipeline.rtsp_h264()`.

Note that, as of now (2021-04), [Actcast application](https://actcast.io/docs/ForVendor/ApplicationDevelopment/) cannot use multicast UDP with dynamic address and unicast UDP.
(RTSP client communicates with RTSP server in RTP and determines adderss of mulitcast UDP.)
Therefore, you can use only the option `protocols = "tcp"`.
See also https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html#rtspsrc:protocols .

You should also pay attention to decoders. Available decoders are below:

| decoder (package) \ device                                     | Raspberry Pi 3 | Raspberry Pi 4 | Jetson Nano |
| -------------------------------------------------------------- | -------------- | -------------- | ----------- |
| `omxh264` (from `gstreamer1.0-omx` and `gstreamer1.0-omx-rpi`) | o              | x              | ?           |
| `v4l2h264dec` (from `gstreamer1.0-plugins-good`)               | very slow      | o              | ?           |

If your application supports various devices, you should branch by hardware types and select appropriate `decoder_type`.
For example, it is recommended to use `decoder_type` `omx` for Raspberry Pi 3 and `v4l2` for Raspberry Pi 4.
Currently, this library does not provide auto determination.

## Development Guide

### Installation of dev requirements

```console
pip3 install poetry
poetry install
```

### Running tests

```console
poetry run nose2 -v
```

### Releasing package & API doc

CI will automatically do.
Follow the following branch/tag rules.

1. Make changes for next version in `master` branch (via pull-requests).
2. Make a PR that updates version in `pyproject.toml` and merge it to `master` branch.
3. Create Git tag from `master` branch's HEAD named `release-<New version>`. E.g. `release-1.4.0`.
4. Then CI will build/upload package to PyPI & API doc to GitHub Pages.
