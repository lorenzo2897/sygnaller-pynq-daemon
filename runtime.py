import subprocess
import os
import shlex
from threading import Thread
from time import sleep, time
from queue import Queue, Empty

base = '/home/xilinx/projects'

# process variables
start_time = 0
running_process = None
stdin_buffer = Queue()
stdout_buffer = Queue()
imgout_buffer = Queue()
stderr_buffer = Queue()
handler_thread = None
stdout_thread = None
stderr_thread = None


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
    while not stdout_buffer.empty():
        stdout_buffer.get(False)
    while not stderr_buffer.empty():
        stderr_buffer.get(False)

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
    stderr_buffer.put("Program terminated.")
    running_process = None
    handler_thread = None


def _handle_stdout():
    global stdout_thread

    while running_process is not None and running_process.poll() is None:  # is still running
        line = running_process.stdout.readline()
        if line != '':
            if line.startswith('~data:image'):
                imgout_buffer.put(line[1:])
            else:
                stdout_buffer.put(line)  # blocking
    stdout_thread = None


def _handle_stderr():
    global stderr_thread

    while running_process is not None and running_process.poll() is None:  # is still running
        line = running_process.stderr.readline()
        if line != '':
            stderr_buffer.put(line)  # blocking
    stderr_thread = None


def stop_python():
    global running_process, handler_thread, stdout_thread, stderr_thread

    if running_process is None:
        return {}

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
        "stdout": [],
        "stderr": [],
        "images": [],
        "running": running_process is not None
    }
    if 'stdin' in data and data['stdin'] is not None:
        stdin_buffer.put(data['stdin'])
    while not stdout_buffer.empty():
        response["stdout"].append(stdout_buffer.get_nowait())
    while not imgout_buffer.empty():
        response["images"].append(imgout_buffer.get_nowait())
    while not stderr_buffer.empty():
        response["stderr"].append(stderr_buffer.get_nowait())

    return response
