import os


def rm_empty_dir(_dir):
    if not os.path.isdir(_dir):
        return

    for d in os.listdir(_dir):
        if d == '.DS_Store':
            os.remove(os.path.join(_dir, d))
        else:
            path = os.path.join(_dir, d)
            if os.path.isdir(path):
                rm_empty_dir(path + os.path.sep)

    if not os.listdir(_dir):
        os.rmdir(_dir)
