#!/usr/bin/python3
"""
Usage: rockuefort copy <playlist> <destination>
       rockuefort link <playlist> <destination>
       rockuefort list <playlist>
"""
from collections import OrderedDict
import itertools
import operator
import os
import os.path as op
import subprocess
import sys
import tempfile

from docopt import docopt

def log(*args, **kwargs):
    print("rockuefort:", *args, file=sys.stderr, **kwargs)

def make_links(targets, dest_dir):
    digits = len(str(len(targets)))
    for i, target in enumerate(targets, 1):
        basename = ("{:0%d}-{}" % digits).format(i, op.basename(target))
        dest = op.join(dest_dir, basename)
        try:
            os.symlink(target, dest)
        except FileExistsError:
            log("File exists: {}".format(dest))

if __name__ == '__main__':
    args = docopt(__doc__)

    # Try to make directories
    dest = args['<destination>']
    if dest:
        try:
            os.mkdir(dest)
        except FileExistsError:
            fs = os.listdir(dest)
            if args['copy'] and fs and '.rockuefort-dir' not in fs:
                log("Refusing to write to non-empty non-rockuefort directory.")
                log("Place a .rockuefort-dir file in the directory to force.")
                sys.exit(1)

    # Load queries
    queries = []
    with open(args['<playlist>']) as f:
        for line in f:
            try:
                c, query = line.strip().split(':', 1)
                c = int(c)
            except ValueError:
                c = 1
                query = line.strip()
            queries.append((c, query))

    # Query quodlibet and build list of files
    files = []
    for c, query in queries:
        r = subprocess.check_output(['quodlibet', '--print-query', query])
        matched_files = [mf.decode() for mf in r.splitlines() if mf]

        # De-duplicate by preferring .ogg, .mp3 versions of songs
        matched_files_exts = {}
        for file in matched_files:
            base, ext = op.splitext(file)
            matched_files_exts.setdefault(base, []).append(ext)
        matched_files_deduped = []
        for base, exts in matched_files_exts.items():
            try:
                ext = next(e for e in '.ogg .mp3 .flac'.split() if e in exts)
            except StopIteration:
                ext = exts[0]
            matched_files_deduped.append(base + ext)

        # Check whether the query matched the expected number of files
        nm = len(matched_files_deduped)
        if nm != c:
            log("Matched {} (expected {}): {}".format(nm, c, query))
            for file in matched_files_deduped:
                log("  match: {}".format(file))
        for file in matched_files_deduped:
            files.append(file)

    # Perform the requested action
    if args['copy']:
        dest = args['<destination>']
        with tempfile.TemporaryDirectory() as temp_dir:
            make_links(files, temp_dir)
            open(op.join(temp_dir, '.rockuefort-dir'), 'a').close()
            rsync_args = ['rsync', '-vrLt', '--delete', temp_dir + '/', dest]
            subprocess.check_call(rsync_args)
    elif args['link']:
        dest = args['<destination>']
        make_links(files, dest)
    else:  # args['list']
        for file in files:
            print(file)
