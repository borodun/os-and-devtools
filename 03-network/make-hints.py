#!/usr/bin/env python3
import base64
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"KPS1"


def main():
    src = os.path.join(ROOT, "solution", "hints.json")
    if not os.path.exists(src):
        print("нет solution/hints.json — файл преподавателя")
        sys.exit(1)
    data = open(src).read()
    json.loads(data)
    blob = MAGIC + base64.b64encode(zlib.compress(data.encode(), 9))
    with open(os.path.join(ROOT, "hints.bin"), "wb") as f:
        f.write(blob)
    n = sum(len(v) for v in json.loads(data).values())
    print("hints.bin записан: %d этапов, %d записей" % (len(json.loads(data)), n))


if __name__ == "__main__":
    main()
