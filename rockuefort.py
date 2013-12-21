"""
Usage: rockuefort index <directory>
       rockuefort list <playlist>
       rockuefort copy <playlist> <destination>
       rockuefort link <playlist> <destination>
"""
import operator
import os
import os.path as path
import pickle
import subprocess
import sys
import tempfile

from docopt import docopt
import mutagenx as mutagen

CACHE_FILE = path.expanduser('~/.cache/rockuefort/index')

def ask(question):
    while True:
        answer = input("{} (Y/n): ".format(question))
        if answer in "Yy":
            return True
        elif answer in "Nn":
            return False

def mkdir_if_needed(path):
    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError as e:
        if e.errno == 17:
            # 17 means the permissions are abnormal, but we don't care
            pass
        else:
            raise

def index(directory):
    with open(CACHE_FILE, 'wb') as out:
        attrs = ['title', 'artist', 'album', 'genre']
        songs = []
        for base, dirs, files in os.walk(directory):
            for file in (path.join(base, f) for f in files):
                q = mutagen.File(file, easy=True)
                if q:
                    print(file)
                    song = {attr: q.get(attr, []) for attr in attrs}
                    song['file'] = file
                    songs.append(song)
        pickle.dump(songs, out)

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def make_links(targets, dest_dir):
    digits = len(str(len(targets)))
    for i, target in enumerate(targets, 1):
        basename = ("{:0%d}-{}" % digits).format(i, path.basename(target))
        dest = path.join(dest_dir, basename)
        try:
            os.symlink(target, dest)
        except FileExistsError:
            log("File exists: {}".format(dest))

def normalize(list_or_string):
    # We do substring matching on track attributes, but the attributes come as
    # lists of strings (except for the 'file' attribute). So, when given a list
    # we join its items together with unicode snowmen and return the result to
    # do substring matching on.
    if isinstance(list_or_string, list):
        return '\u2603'.join(list_or_string)
    else:
        return list_or_string

if __name__ == '__main__':
    args = docopt(__doc__)

    # Try to load the cache
    data = None
    try:
        opened = open(CACHE_FILE, 'rb')
    except FileNotFoundError:
        pass
    else:
        with opened as f:
            try:
                data = pickle.load(f)
            except (pickle.UnpicklingError, EOFError):
                pass

    if not data and not args['index']:
        print("Invalid cache. Please `rockuefort index` something first.",
              file=sys.stderr)
        sys.exit(1)

    if args['index']:
        mkdir_if_needed(path.dirname(CACHE_FILE))
        index(args['<directory>'])
        sys.exit(0)

    # Load entries
    entries = []
    with open(args['<playlist>']) as f:
        for line in f:
            try:
                c, rest = line.strip().split(':', 1)
                c = int(c)
            except ValueError:
                c = 1
                rest = line.strip()
            parts = rest.split('|')
            queries = [part.split('=') for part in parts]
            entries.append((c, queries))

    # Query quodlibet and build list of files
    files = []
    for c, queries in entries:
        matched_files = data
        try:
            for attr, value in queries:
                matched_files = [x for x in matched_files
                                 if value in normalize(x[attr])]
        except ValueError:
            log("Badly-formatted entry; skipping")
            continue

        matched_files = [x['file'] for x in matched_files]

        # De-duplicate by preferring .ogg, .mp3 versions of songs
        matched_files_exts = {}
        for file in matched_files:
            base, ext = path.splitext(file)
            matched_files_exts.setdefault(base, []).append(ext)
        matched_files_deduped = []
        for base, exts in matched_files_exts.items():
            try:
                ext = next(e for e in ['.ogg', '.mp3'] if e in exts)
            except StopIteration:
                ext = exts[0]
            matched_files_deduped.append(base + ext)

        # Check whether the query matched the expected number of files
        nm = len(matched_files_deduped)
        if nm != c:
            log("Matched {} (expected {}): {}".format(nm, c, queries))
            for file in matched_files_deduped:
                log("  match: {}".format(file))
        for file in matched_files_deduped:
            files.append(file)

    # Perform the requested action
    if args['copy']:
        dest = args['<destination>']
        with tempfile.TemporaryDirectory() as temp_dir:
            make_links(files, temp_dir)
            log("Performing a dry run of rsync...")
            rsync_args = ['rsync', '--recursive', '--itemize-changes',
                          '--copy-links', '--times', '--delete', '--dry-run',
                          temp_dir + '/', dest]
            try:
                subprocess.check_call(rsync_args)
            except subprocess.CalledProcessError:
                pass
            if ask("Proceed with the rsync?"):
                rsync_args.remove('--dry-run')
                try:
                    subprocess.check_call(rsync_args)
                except subprocess.CalledProcessError:
                    pass
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
