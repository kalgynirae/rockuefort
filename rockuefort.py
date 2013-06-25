#!/usr/bin/python3
"""
Usage: rockuefort copy <file> <destination>
       rockuefort symlink <file> <destination>
       rockuefort list <file>
"""
from collections import OrderedDict
import os.path
import subprocess
import sys

from docopt import docopt

def log(*args, **kwargs):
    print("rockuefort:", *args, file=sys.stderr, **kwargs)

if __name__ == '__main__':
    args = docopt(__doc__)

    # Load queries
    queries = []
    with open(args['<file>']) as f:
        for line in f:
            try:
                c, query = line.strip().split(':', 1)
                c = int(c)
            except ValueError:
                c = 1
                query = line.strip()
            queries.append((c, query))

    # Query quodlibet and build list of files
    files = OrderedDict()
    for c, query in queries:
        r = subprocess.check_output(['quodlibet', '--print-query', query])
        matched_files = [mf.decode() for mf in r.splitlines() if mf]

        # De-duplicate by preferring .ogg, .mp3 versions of songs
        matched_files_exts = {}
        for file in matched_files:
            base, ext = os.path.splitext(file)
            matched_files_exts.setdefault(base, []).append(ext)
        matched_files_deduped = []
        for base, exts in matched_files_exts.items():
            try:
                ext = next(e for e in '.ogg .mp3 .flac'.split() if e in exts)
            except StopIteration:
                ext = exts[0]
            matched_files_deduped.append(base + ext)

        nm = len(matched_files_deduped)
        if nm != c:
            log("Matched {} (expected {}): {}".format(nm, c, query))
            for file in matched_files_deduped:
                log("  match: {}".format(file))
        for file in matched_files_deduped:
            files.setdefault(file, []).append(query)

    # Check for multiply-matched files
    for file, queries in files.items():
        if len(queries) > 1:
            log("Matched by multiple: {}".format(file))
            for q in queries:
                log("  query: {}".format(q))

    # Perform the requested action
    if args['copy']:
        log("Copying to {}".format(args['<destination>']))
        ...
    elif args['symlink']:
        log("Symlinking to {}".format(args['<destination>']))
        ...
    else:  # args['list']
        for file in files:
            print(file)
