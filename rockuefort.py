#!/usr/bin/python3
"""
Usage: rockuefort copy <file> <destination>
       rockuefort symlink <file> <destination>
       rockuefort list <file>
"""
from collections import OrderedDict
import subprocess
import sys

from docopt import docopt

def log(*args, **kwargs):
    print("rockuefort:", *args, file=sys.stderr, **kwargs)

if __name__ == '__main__':
    args = docopt(__doc__)

    # Load and evaluate queries
    files = OrderedDict()
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
    for c, query in queries:
        r = subprocess.check_output(['quodlibet', '--print-query', query])
        matched_files = [mf.decode() for mf in r.splitlines() if mf]
        nm = len(matched_files)
        if nm != c:
            log("Matched {} (expected {}): {}".format(nm, c, query))
            for file in matched_files:
                log("  match: {}".format(file))
        for file in matched_files:
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
