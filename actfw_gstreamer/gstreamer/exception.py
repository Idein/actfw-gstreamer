__all__ = [
    "GstNotInitializedError",
    "PipelineBuildError",
]


class GstNotInitializedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("You must initialize Gst first. See document.")


class PipelineBuildError(RuntimeError):
    pass
