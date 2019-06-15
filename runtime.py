import subprocess
import os
import shlex
import signal
from threading import Thread
from time import sleep, time
from queue import Queue

base = '/home/xilinx/projects'

# process variables
start_time = 0
running_process: subprocess.Popen = None
stdin_buffer = Queue()
output_buffer = Queue()
handler_thread = None
stdout_thread = None
stderr_thread = None


# output stream descriptors
fd_stdout = 1
fd_stderr = 2
fd_imgout = 3


def is_running():
    return running_process is not None


def run_python(data):
    global running_process, handler_thread, stdout_thread, stderr_thread, start_time

    if is_running():
        return {'error': 'Process already running'}

    target_py = os.path.join(base, data['project'], data['target'])

    # command with optional arguments
    cmd = ['python3', '-u', target_py]
    if 'args' in data and data['args'] != '':
        cmd += shlex.split(data['args'])

    # open process
    print("Starting Python process", target_py)
    start_time = time()
    running_process = subprocess.Popen(cmd,
                                       cwd=os.path.join(base, data['project'], 'data'),
                                       bufsize=0,
                                       universal_newlines=True,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

    while not stdin_buffer.empty():
        stdin_buffer.get(False)
    while not output_buffer.empty():
        output_buffer.get(False)

    # start handling standard streams
    handler_thread = Thread(target=_handle_subprocess)
    handler_thread.daemon = True
    handler_thread.start()
    # stdout
    stdout_thread = Thread(target=_handle_stdout)
    stdout_thread.daemon = True
    stdout_thread.start()
    # stderr
    stderr_thread = Thread(target=_handle_stderr)
    stderr_thread.daemon = True
    stderr_thread.start()

    return {}


def _handle_subprocess():
    global running_process, handler_thread

    while running_process is not None and running_process.poll() is None:  # is still running
        while not stdin_buffer.empty():
            val = stdin_buffer.get_nowait()
            print("Stdin:", val)
            running_process.stdin.write(val)
        sleep(0.1)
        if time() > start_time + 3600:
            stop_python()

    print("Python process exited")
    output_buffer.put((fd_stderr, "Program terminated."))
    running_process = None
    handler_thread = None


def _handle_stdout():
    global stdout_thread

    while running_process is not None and running_process.poll() is None:  # is still running
        line = running_process.stdout.readline()
        if line != '':
            if line.startswith('~data:image'):
                output_buffer.put((fd_imgout, line[1:]))
            else:
                output_buffer.put((fd_stdout, line))  # blocking
    stdout_thread = None


def _handle_stderr():
    global stderr_thread

    while running_process is not None and running_process.poll() is None:  # is still running
        line = running_process.stderr.readline()
        if line != '':
            output_buffer.put((fd_stderr, line))  # blocking
    stderr_thread = None


def stop_python():
    global running_process, handler_thread, stdout_thread, stderr_thread

    if running_process is None:
        return {}

    os.kill(running_process.pid, signal.SIGINT)

    try:
        running_process.wait(timeout=5000)
    except:
        running_process.kill()

    if handler_thread is not None:
        handler_thread.join()  # wait for it to close
    if stdout_thread is not None:
        stdout_thread.join()
    if stderr_thread is not None:
        stderr_thread.join()

    return {}


def terminal(data):
    response = {
        "output": [],
        "running": running_process is not None
    }
    if 'stdin' in data and data['stdin'] is not None:
        stdin_buffer.put(data['stdin'])
    while not output_buffer.empty():
        fd, data = output_buffer.get_nowait()
        response["output"].append([fd, data])

    return response


# *****************************************
# Unit tests
# *****************************************

import unittest


class TestRuntime(unittest.TestCase):

    def setUp(self):
        import shutil
        shutil.rmtree('/home/xilinx/projects/_test_dummy')
        os.makedirs("/home/xilinx/projects/_test_dummy/data")
        with open("/home/xilinx/projects/_test_dummy/main.py", 'w') as f:
            f.write("""
from time import sleep
print('hello')
sleep(3)
""")

    def test_no_running(self):
        self.assertFalse(is_running())

    def test_running(self):
        # run
        run_python({
            "project": "_test_dummy",
            "target": "main.py"
        })

        # check
        self.assertTrue(is_running())
        sleep(4)
        self.assertFalse(is_running())

    def test_terminal(self):
        # run
        run_python({
            "project": "_test_dummy",
            "target": "main.py"
        })

        # check
        self.assertEqual(terminal({}), {
            "output": [
                [fd_stdout, "hello"]
            ],
            "running": True
        })
        sleep(5)
        self.assertEqual(terminal({}), {
            "output": [
                [fd_stderr, "Program terminated."]
            ],
            "running": False
        })

    def test_stopping(self):
        run_python({
            "project": "_test_dummy",
            "target": "main.py"
        })
        self.assertTrue(is_running())
        stop_python()
        self.assertFalse(is_running())


if __name__ == '__main__':
    unittest.main()
