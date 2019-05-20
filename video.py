import os
import time

last_served = 0


def get_last_frame():
    global last_served

    # does it exist at all?
    if not os.path.exists("/home/xilinx/projects/video.jpg"):
        return {"video-error": "No active video"}

    # has video been updating in the past 15 seconds?
    last_updated = os.path.getmtime("/home/xilinx/projects/video.jpg")
    if time.time() - last_updated > 15:
        return {"video-error": "No active video"}

    # has it been updated since the last time it was sent?
    if last_served == last_updated:
        return {"video-error": "USE_CACHED"}

    # serve it!
    last_served = last_updated
    return {
        "file": "/home/xilinx/projects/video.jpg"
    }
