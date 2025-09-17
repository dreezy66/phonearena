#!/usr/bin/env python3
import shutil, os
def pack_app(path):
    if not os.path.isdir(path):
        return False, "not a directory"
    base = os.path.abspath(path)
    out = base + ".zip"
    shutil.make_archive(base, "zip", base)
    return True, out
