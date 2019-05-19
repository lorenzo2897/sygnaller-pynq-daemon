import os
import pwd
import base64

base = '/home/xilinx/projects'

userid = pwd.getpwnam('xilinx')


def fix_owner_and_permissions(path):
    try:
        os.chmod(path, 0o777)
        os.chown(path, userid.pw_uid, userid.pw_gid)
    except:
        pass


def upload_files(data):
    project_dir = os.path.join(base, data['project'])
    data_dir = os.path.join(base, data['project'], 'data')
    api_dir = os.path.join(base, data['project'], 'software', 'sygnaller')
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(api_dir, exist_ok=True)
    fix_owner_and_permissions(project_dir)
    fix_owner_and_permissions(data_dir)

    files = data['files']

    files_to_keep = set()

    # update any changed files
    for f in files:
        containing_dir = os.path.join(project_dir, os.path.dirname(f['path']))
        fullpath = os.path.join(project_dir, f['path'])

        files_to_keep.add(fullpath)

        if f['contents'] is None:
            continue

        os.makedirs(containing_dir, exist_ok=True)
        fix_owner_and_permissions(containing_dir)

        with open(fullpath, "wb") as fh:
            fh.write(base64.decodebytes(bytes(f['contents'], encoding='utf-8')))
        fix_owner_and_permissions(fullpath)

    # get rid of source files that have been deleted
    category = data['directory']
    if category in ['software', 'hardware']:
        for r, d, f in os.walk(os.path.join(project_dir, category)):
            if r.endswith('sygnaller'):
                continue
            for file in f:
                found = os.path.join(r, file)
                if found not in files_to_keep:
                    try:
                        os.remove(found)
                    except:
                        pass

    # make sure the API files are still there
    if not os.path.exists(os.path.join(api_dir, 'terminal.py')):
        with open(os.path.join(api_dir, 'terminal.py'), 'w') as f:
            f.write("""
import sys
import base64

def error(msg):
    print(msg, file=sys.stderr)

def imageFromDataURI(uri):
    print("~"+uri)
    
def imageFromFile(filename):
    with open(filename, "rb") as f:
        print("~data:image;base64,"+ base64.b64encode(f.read()).decode('utf-8'))

def showFigure(plt):
    import io
    buf = io.BytesIO()
    plt.gcf().savefig(buf, format='png')
    buf.seek(0)
    print("~data:image;base64,"+ base64.b64encode(buf.read()).decode('utf-8'))

""")
    if not os.path.exists(os.path.join(api_dir, '__init__.py')):
        with open(os.path.join(api_dir, '__init__.py'), 'w') as f:
            f.write("")

    return {}
