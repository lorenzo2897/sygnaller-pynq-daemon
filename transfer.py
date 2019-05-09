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
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    fix_owner_and_permissions(project_dir)
    fix_owner_and_permissions(data_dir)

    files = data['files']

    for f in files:
        containing_dir = os.path.join(project_dir, os.path.dirname(f['path']))
        os.makedirs(containing_dir, exist_ok=True)
        fix_owner_and_permissions(containing_dir)

        fullpath = os.path.join(project_dir, f['path'])
        with open(fullpath, "wb") as fh:
            fh.write(base64.decodebytes(bytes(f['contents'], encoding='utf-8')))
        fix_owner_and_permissions(fullpath)

    return {}
