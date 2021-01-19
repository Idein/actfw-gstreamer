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

See [actfw-core](https://github.com/Idein/actfw-core) for basic usage.

actfw-gstreamer provides:

- `actfw_gstreamer.jetson.Display` : Display using `nvoverlaysink` element in [NVIDIA's Accelerated GStreamer](https://docs.nvidia.com/jetson/l4t/index.html#page/Tegra%20Linux%20Driver%20Package%20Development%20Guide/accelerated_gstreamer.html).

## Example

- `example/hello_jetson` : The simplest application example for Jetson
  - Use HDMI display as 1280x720 area
  - Generate 640x480 single-colored image
  - Draw "Hello, Actcast!" text
  - Display it as 1280x720 image
  - Notice message for each frame
  - Support application setting
  - Support application heartbeat
  - Support "Take Photo" command
  - Depends: fonts-dejavu-core

## Development Guide

### Installation of dev requirements

```console
pip3 install pipenv
pipenv sync --dev
```

### Running tests

```console
pipenv run nose2 -v
```

### Running examples

On a Jetson Nano connected to HDMI display:

```console
apt-get install fonts-dejavu-core
pipenv run python example/hello_jetson
```

### Releasing package & API doc

CI will automatically do.
Follow the following branch/tag rules.

1. Make changes for next version in `master` branch (via pull-requests).
2. Update `actfw_gstreamer/_version.py` with new version in `master` branch.
3. Create Git tag from `master` branch's HEAD named `release-<New version>`. E.g. `release-1.4.0`.
4. Then CI will build/upload package to PyPI & API doc to GitHub Pages.
