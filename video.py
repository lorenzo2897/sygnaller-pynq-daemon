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


# *****************************************
# Unit tests
# *****************************************

import unittest


class TestVideo(unittest.TestCase):

    def test_no_select_file(self):
        try:
            os.remove("/home/xilinx/projects/videoSELECT.jpg")
        except:
            pass
        result = get_last_frame({"flushCache": False})
        self.assertEqual(result, {"video-error": "No active video"})

    def test_no_image_file(self):
        # remove image
        try:
            os.remove("/home/xilinx/projects/videoA.jpg")
        except:
            pass
        # set ping pong selector
        with open("/home/xilinx/projects/videoSELECT.txt", 'w') as f:
            f.write("A")
        # run
        result = get_last_frame({"flushCache": False})
        self.assertEqual(result, {"video-error": "No active video"})

    def test_read_image(self):
        # create image
        from PIL import Image
        Image.new('RGB', (1280, 720)).save("/home/xilinx/projects/videoA.jpg")
        # set ping pong selector
        with open("/home/xilinx/projects/videoSELECT.txt", 'w') as f:
            f.write("A")
        # run
        result = get_last_frame({"flushCache": False})
        self.assertEqual(result, {"file": "/home/xilinx/projects/videoA.jpg"})

    def test_stale_video(self):
        # create image
        from PIL import Image
        Image.new('RGB', (1280, 720)).save("/home/xilinx/projects/videoA.jpg")
        # set ping pong selector
        with open("/home/xilinx/projects/videoSELECT.txt", 'w') as f:
            f.write("A")
        # wait for timeout
        time.sleep(20)
        # run
        result = get_last_frame({"flushCache": False})
        self.assertEqual(result, {"video-error": "No active video"})


if __name__ == '__main__':
    unittest.main()
