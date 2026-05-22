"""Frame sources: images, videos, RTSP streams."""

from retail_monitor.io.rtsp import RTSPStream
from retail_monitor.io.video import VideoFileSource, iter_image_files

__all__ = ["RTSPStream", "VideoFileSource", "iter_image_files"]
