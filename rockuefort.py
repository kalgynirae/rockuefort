#!/usr/bin/python3
"""
Usage: rockuefort copy <playlist> <destination>
       rockuefort link <playlist> <destination>
       rockuefort list <playlist>
"""
from collections import OrderedDict
import itertools
import os
import os.path as op
import subprocess
import sys
import tempfile

from docopt import docopt

def log(*args, **kwargs):
    print("rockuefort:", *args, file=sys.stderr, **kwargs)

def make_links(targets, dest_dir):
    for target in targets:
        base, ext = op.splitext(op.join(dest_dir, op.basename(target)))
        for n in itertools.count():
            link_name = '{}-{}{}'.format(base, n, ext) if n else base + ext
            try:
                os.symlink(target, link_name)
            except FileExistsError:
                log("Filename collision; renamed to: {}"
                    "".format(op.basename(link_name)))
            else:
                break

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
            files.setdefault(file, []).append(query)

    # Check for multiply-matched files
    for file, queries in files.items():
        if len(queries) > 1:
            log("Matched by multiple: {}".format(file))
            for q in queries:
                log("  query: {}".format(q))

    # Perform the requested action
    if args['copy']:
        dest = args['<destination>']
        with tempfile.TemporaryDirectory() as temp_dir:
            make_links(files, temp_dir)
            rsync_args = ['rsync', '-vrLt', '--delete', temp_dir + '/', dest]
            subprocess.check_call(rsync_args)
    elif args['link']:
        dest = args['<destination>']
        try:
            os.mkdir(dest)
        except FileExistsError:
            pass
        make_links(files, dest)
    else:  # args['list']
        for file in files:
            print(file)
