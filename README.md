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

Note that an application using actfw-gstreamer must call [`actfw_gstreamer.init()`](https://idein.github.io/actfw-gstreamer/latest/actfw_gstreamer.html#actfw_gstreamer.init) at first.

actfw-gstreamer provides:

(no component is provided yet)

## Example

(no example is provided yet)

## Development Guide

### Installation of dev requirements

```console
pip3 install pipenv
pipenv install --dev -e .
```

### Running tests

```console
pipenv run nose2 -v
```

### Releasing package & API doc

CI will automatically do.
Follow the following branch/tag rules.

1. Make changes for next version in `master` branch (via pull-requests).
2. Update `actfw_gstreamer/_version.py` with new version in `master` branch.
3. Create Git tag from `master` branch's HEAD named `release-<New version>`. E.g. `release-1.4.0`.
4. Then CI will build/upload package to PyPI & API doc to GitHub Pages.
