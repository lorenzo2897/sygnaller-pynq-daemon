import uuid
import hashlib
import json
import os
from threading import Thread
from urllib.request import Request, urlopen, urlretrieve

base = '/home/xilinx/projects'
compilation_server = 'http://sygnaller.silvestri.io:9000'


def __project_id(project_name):
    return "%012X_%s" % (uuid.getnode(), hashlib.md5(project_name.encode('utf-8')).hexdigest())


def clear_cache(data):
    project_name = data['project']
    project_id = __project_id(project_name)

    url = compilation_server + '/clear_cache'
    data = {'project_id': project_id}

    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    return json.loads(response)


def run_build(data):
    project_name = data['project']
    project_id = __project_id(project_name)

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


def get_build_status(data):
    project_name = data['project']
    project_id = __project_id(project_name)

    url = compilation_server + '/build_progress'
    data = {'project_id': project_id}

    request = Request(url, json.dumps(data).encode('utf-8'))
    response = urlopen(request, timeout=8).read().decode()

    # update overlay files if there are newer ones on the server
    status = json.loads(response)
    if status['last_completed'] > local_last_modified_overlay(project_name):
        print("Downloading bit and tcl files")
        status['downloading'] = True
        Thread(target=download_overlay_files, args=(project_name,), daemon=True).start()

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
    overlay_dir = os.path.join(base, project_name)

    project_id = __project_id(project_name)
    data = json.dumps({'project_id': project_id}).encode('utf-8')

    urlretrieve(compilation_server + '/download_overlay_bit', os.path.join(overlay_dir, 'overlay.bit'), data=data)
    urlretrieve(compilation_server + '/download_overlay_tcl', os.path.join(overlay_dir, 'overlay.tcl'), data=data)

