import uuid
import hashlib
import json
import os
from threading import Thread
from urllib.request import Request, urlopen, urlretrieve

base = '/home/xilinx/projects'
compilation_server = 'http://sygnaller.silvestri.io:9000'

downloading_files_thread = None


def _project_id(project_name):
    return "%012X_%s" % (uuid.getnode(), hashlib.md5(project_name.encode('utf-8')).hexdigest())


def clear_cache(data):
    project_name = data['project']
    project_id = _project_id(project_name)

    url = compilation_server + '/clear_cache'
    data = {'project_id': project_id}

    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    return json.loads(response)


def run_build(data):
    project_name = data['project']
    project_id = _project_id(project_name)

    # collect all source files
    sources = {}
    proj_dir = os.path.join(base, data['project'])
    hw_dir = os.path.join(proj_dir, 'hardware')
    for r, d, f in os.walk(hw_dir):
        for file in f:
            if file.lower().endswith('.v'):
                fname = os.path.join(r, file)
                try:
                    with open(fname) as fp:
                        sources[os.path.relpath(fname, hw_dir)] = fp.read()
                except OSError:
                    pass

    if len(sources) == 0:
        raise RuntimeError("Empty")

    # prepare request
    data = {
        "project_id": project_id,
        "sources": sources,
        "components": data['components']
    }

    # relay it to compilation server
    url = compilation_server + '/compile'
    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    return json.loads(response)


def stop_build(data):
    project_name = data['project']
    project_id = _project_id(project_name)

    url = compilation_server + '/cancel_build'
    data = {"project_id": project_id}

    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    return json.loads(response)


def get_build_status(data):
    global downloading_files_thread

    project_name = data['project']
    project_id = _project_id(project_name)

    url = compilation_server + '/build_progress'
    data = {'project_id': project_id}

    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    # update overlay files if there are newer ones on the server
    status = json.loads(response)
    if status['last_completed'] > local_last_modified_overlay(project_name) and not status['running']:
        status['running'] = True
        status['downloading'] = True
        if downloading_files_thread is None:
            status['logs'] += "Copying bit files back to Pynq board\n"
            downloading_files_thread = Thread(target=download_overlay_files, args=(project_name,), daemon=True).start()

    return status


def local_last_modified_overlay(project_name):
    overlay_dir = os.path.join(base, project_name)
    bitfile = os.path.join(overlay_dir, 'overlay.bit')
    tclfile = os.path.join(overlay_dir, 'overlay.tcl')
    if os.path.exists(bitfile) and os.path.exists(tclfile):
        return min(os.path.getmtime(bitfile), os.path.getmtime(tclfile))
    else:
        return 0


def download_overlay_files(project_name):
    try:
        overlay_dir = os.path.join(base, project_name)
        api_dir = os.path.join(base, project_name, 'software/sygnaller')

        project_id = _project_id(project_name)
        data = json.dumps({'project_id': project_id}).encode('utf-8')

        urlretrieve(compilation_server + '/download_overlay_bit', os.path.join(overlay_dir, 'overlay.bit'), data=data)
        urlretrieve(compilation_server + '/download_overlay_tcl', os.path.join(overlay_dir, 'overlay.tcl'), data=data)
        urlretrieve(compilation_server + '/download_python_api', os.path.join(api_dir, 'hw.py'), data=data)
    except Exception as e:
        print("Overlay download failed:", e.__name__)

    global downloading_files_thread
    downloading_files_thread = None


# *****************************************
# Unit tests
# *****************************************

import unittest


class TestCompiler(unittest.TestCase):

    def test_project_id(self):
        # make
        name = "randomProjectName123!#"
        id = _project_id(name)
        # test
        self.assertEqual(len(id), 12+1+32)
        self.assertRegex(id, "^[0-9A-F]+_[0-9a-f]+$")

    def test_local_last_modified(self):
        result = local_last_modified_overlay("_non_existent_project_xxxx")
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
