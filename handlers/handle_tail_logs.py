#!/usr/bin/env python3
from core.phonearena_core import tail_file
def run(path, lines=200):
    return "\\n".join(tail_file(path, lines))
