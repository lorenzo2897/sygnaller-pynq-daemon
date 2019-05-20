import os
import time

last_served = 0


def get_last_frame(data):
    global last_served

    # does it exist at all?
    if not os.path.exists("/home/xilinx/projects/videoSELECT.txt"):
        return {"video-error": "No active video"}

    with open("/home/xilinx/projects/videoSELECT.txt") as f:
        sel = f.read()
        if len(sel) != 1:
            sel = "A"

    if not os.path.exists(f"/home/xilinx/projects/video{sel}.jpg"):
        return {"video-error": "No active video"}

    # has video been updating in the past 15 seconds?
    last_updated = os.path.getmtime(f"/home/xilinx/projects/video{sel}.jpg")
    if time.time() - last_updated > 15:
        return {"video-error": "No active video"}

    # has it been updated since the last time it was sent?
    if last_served == last_updated and data['flushCache'] is not True:
        return {"video-error": "USE_CACHED"}

    # serve it!
    last_served = last_updated
    return {
        "file": f"/home/xilinx/projects/video{sel}.jpg"
    }
