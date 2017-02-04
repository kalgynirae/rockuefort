#!/usr/bin/env python3
"""
Rockuefort reads playlists written in simple plaintext, searches your
music library, and outputs the songs matched by the playlist in a few
different ways.

Usage: rockuefort index [--add DIR|--remove DIR]
       rockuefort list [--strip PREFIX] [--prepend PREFIX] [--null]
                       [--shuffle] <playlist>
       rockuefort (copy|link) [--no-number] [--shuffle]
                              <playlist> <destination>
       rockuefort render [--shuffle] <playlist> <outfile>
       rockuefort scan
       rockuefort --help
       rockuefort --version

Options:
  --add DIR         Add DIR to the list of directories to scan
  --null            Terminate printed filenames with null characters
  --prepend PREFIX  Prepend PREFIX to each printed filename
  --remove DIR      Remove DIR from the list of directories to scan
  --reset           Forget previously indexed files
  --shuffle         Randomize the order of the output
  --strip PREFIX    Strip PREFIX from each printed filename
"""
from collections import namedtuple
import itertools
import logging
import math
import multiprocessing
import os
import pickle
import random
import re
import subprocess
import sys
import tempfile

from docopt import docopt
import mutagen

logger = logging.getLogger(__name__)

ACTIONS = {}
CACHE_PATH = os.path.expanduser("~/.cache/rockuefort/index")
DIRS_CONFIG_PATH = os.path.expanduser("~/.config/rockuefort/dirs")
KNOWN_OPTIONS = "@|+-"
PLAYLIST_LOAD_ARGS = "shuffle".split()
PREFERRED_EXTENSIONS = ".oga .ogg .mp3 .flac".split()
TAGS = "title artist album genre composer".split()


def main():
    logging.basicConfig(
        format="%(name)s:%(levelname)s: %(message)s",
        level=logging.DEBUG,
    )

    args = docopt(__doc__, version="Rockuefort 1.1")
    func = next(func for action, func in ACTIONS.items() if args[action])
    return func(args)


def action(func):
    """Register func as an action that can be run from the command line

    Trailing underscores are stripped from the function name so that it's
    possible to have actions called things like 'list' without shadowing the
    built-in.
    """
    ACTIONS[func.__name__.rstrip('_')] = func
    return func


@action
def copy(args):
    files = load_playlist(args["<playlist>"], **playlist_load_args(args))
    with tempfile.TemporaryDirectory() as temp_dir:
        make_links(files, temp_dir, args["--no-number"])
        logger.info("Performing a dry run of rsync...")
        rsync_args = ["rsync", "--recursive", "--itemize-changes",
                      "--copy-links", "--times", "--delete", "--dry-run",
                      temp_dir + "/", args["<destination>"]]
        call(rsync_args, ignore_return_code=True)
        if confirm("Proceed with the rsync?"):
            rsync_args.remove("--dry-run")
            call(rsync_args, ignore_return_code=True)


@action
def index(args):
    dirs = load_dirs_config(DIRS_CONFIG_PATH)
    if args["--add"]:
        dirs.add(args["--add"])
    elif args["--remove"]:
        dirs.remove(args["--remove"])
    else:
        for dir in dirs:
            print(dir)
        return

    os.makedirs(os.path.dirname(DIRS_CONFIG_PATH), exist_ok=True)
    with open(DIRS_CONFIG_PATH, "w") as f:
        f.write("\n".join(dirs) + "\n")


@action
def link(args):
    files = load_playlist(args["<playlist>"], **playlist_load_args(args))
    try:
        os.mkdir(args["<destination>"])
    except FileExistsError:
        pass
    make_links(files, args["<destination>"], args["--no-number"])


@action
def list_(args):
    files = load_playlist(args["<playlist>"], **playlist_load_args(args))
    for file in files:
        if args["--strip"] and file.startswith(args["--strip"]):
            file = file[len(args["--strip"]):]
        if args["--prepend"]:
            file = args["--prepend"] + file
        print(file, end=("\0" if args["--null"] else "\n"))


@action
def render(args):
    files = load_playlist(args["<playlist>"], **playlist_load_args(args))
    with tempfile.TemporaryDirectory() as temp_dir:
        commands = []
        processed_files = []
        # Pre-process each file to remove silences
        max_digits = math.ceil(math.log10(len(files)))
        for n, file in enumerate(files, start=1):
            base, _ = os.path.splitext(os.path.basename(file))
            out = os.path.join(temp_dir, ("{:0%sd}-{}.flac" % max_digits)
                                         .format(n, base))

            try:
                volume_options = [
                    "--norm=%s" % file.gain,
                ]
            except AttributeError:
                volume_options = []
            sox_args = [
                "sox",
                "--no-clobber",
            ] + volume_options + [
                file,
                out,
                "silence", "1", "0.05", "0.1%", # remove silence at the beginning
                "reverse",
                "silence", "1", "0.05", "0.2%", # remove silence at the end
                "reverse",
            ]
            commands.append(sox_args)
            processed_files.append(out)

        with multiprocessing.Pool() as pool:
            pool.map(call, commands)

        # Concatenate the files
        sox_args = [
            "sox",
            "--no-clobber",
        ]
        for file in processed_files:
            sox_args.append(file)
        sox_args.append(args["<outfile>"])
        call(sox_args)


@action
def scan(args):
    mutable_cache = {}
    # Open the cache file *before* scanning so that we haven't wasted time
    # scanning if we find out the cache file can't be opened.
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "wb") as out:
        for dir in load_dirs_config(DIRS_CONFIG_PATH):
            for base, _, files in os.walk(dir):
                paths = (os.path.join(base, f) for f in files)
                for path in paths:
                    logger.info(path)
                    try:
                        entry = CacheEntry.from_path(path)
                    except UnknownFileFormatError:
                        logger.debug("skipping: %s", path)
                    else:
                        mutable_cache[path] = entry
        cache = tuple(mutable_cache.values())
        pickle.dump(cache, out)


class CacheEntry(namedtuple("CacheEntry", ["path"] + TAGS)):
    @classmethod
    def from_path(cls, path):
        mf = mutagen.File(path, easy=True)
        if mf:
            abspath = os.path.abspath(path)
            info = {tag: mf.get(tag, []) for tag in TAGS}
            info["path"] = abspath
            return cls(**info)
        else:
            raise UnknownFileFormatError(path)


class FileWrapper(str):
    def __new__(cls, *args, gain=None, **kwargs):
        instance = super().__new__(cls, *args, **kwargs)
        instance.gain = gain
        return instance


class MatchResult(list):
    def __init__(self, file_or_list):
        if isinstance(file_or_list, list):
            super().__init__(file_or_list)
        else:
            super().__init__([file_or_list])
        self.fixed_position = False

class GroupedMatchResult(MatchResult):
    pass


class PlaylistEntry(namedtuple("PlaylistEntry", "query count options")):
    _matcher = re.compile(
        r"""(?P<options>[^\w]+)?
            (?:(?P<count>[\d]+):)?
            (?P<query>
                [\w]+=[^|]+
                (?:\|[\w]+=[^|]+)*
            )""",
        re.VERBOSE).fullmatch

    @classmethod
    def from_string(cls, string):
        match = cls._matcher(string)
        if match:
            query_str, count, options = match.group("query", "count", "options")
            count = int(count) if count is not None else 1
            query_parts = query_str.split("|")
            query = [part.split("=", maxsplit=1) for part in query_parts
                     if part.split("=")[0] != "crop"]
            if not all(tag in TAGS for tag, _ in query):
                raise QueryInvalidTagError
            options = options or ''
            unknown_options = set(options) - set(KNOWN_OPTIONS)
            if unknown_options:
                logger.warn("Ignoring unknown query options %r",
                            "".join(unknown_options))
            return cls(query, count, options)
        else:
            raise QueryParseError


class QueryInvalidTagError(Exception):
    pass


class QueryParseError(Exception):
    pass


class UnknownFileFormatError(Exception):
    pass


def call(args, ignore_return_code=False):
    logger.info(" ".join(args))
    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError as e:
        if not ignore_return_code:
            logger.error(e)
            sys.exit(2)


def confirm(question):
    while True:
        answer = input("{} (Y/n): ".format(question))
        if answer in "Yy":
            # Note that this branch also wins when answer is empty
            return True
        elif answer in "Nn":
            return False


def filter_extensions(files):
    extensions = {}
    for file in files:
        base, ext = os.path.splitext(file)
        extensions.setdefault(base, []).append(ext)
    deduped = []
    for base, exts in extensions.items():
        ext = next((e for e in PREFERRED_EXTENSIONS if e in exts), exts[0])
        deduped.append(base + ext)
    return deduped


def playlist_load_args(args):
    load_args = {}
    for arg, value in args.items():
        cleaned_arg = arg.lstrip('-').replace('-', '_')
        if cleaned_arg in PLAYLIST_LOAD_ARGS:
            load_args[cleaned_arg] = value
    return load_args


def get_results(entries, cache=None):
    results = []
    for entry in entries:
        matched_files = filter_extensions(match_files(entry.query, cache))
        n = len(matched_files)
        if n != entry.count:
            file_info = "".join("\n  match: %s" % f for f in matched_files)
            logger.warn("Matched %s files (expected %s): %r%s",
                        n, entry.count, entry.query, file_info)
        volume_adjustment = entry.options.count('+') - entry.options.count('-')
        if volume_adjustment:
            try:
                gain = 10 * math.log2(volume_adjustment + 8) - 30
            except ValueError:
                logger.warn("Ignoring out-of-bounds volume adjustment %r",
                            volume_adjustment)
            matched_files = [FileWrapper(file, gain=gain)
                             for file in matched_files]
        if '|' in entry.options:
            if results and isinstance(results[-1], GroupedMatchResult):
                results[-1].extend(matched_files)
            else:
                results.append(GroupedMatchResult(matched_files))
        else:
            results.extend(MatchResult(file) for file in matched_files)
        if '@' in entry.options:
            results[-1].fixed_position = True
    return results


def load_cache(path):
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        logger.warn("No cache file found. You should run `rockuefort scan`.")
        return Cache()


def load_dirs_config(path):
    try:
        with open(path) as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        logger.warn("No dirs config file found.")
        return set()


def load_playlist(path, *, shuffle=False):
    cache = load_cache(CACHE_PATH)
    with open(path) as f:
        entries = parse_entries(f)
    results = get_results(entries, cache)
    if shuffle:
        results = shuffled(results)
    return list(itertools.chain(*results))


def make_links(targets, dest_dir, no_number=False):
    digits = len(str(len(targets)))
    for i, target in enumerate(targets, 1):
        basename = os.path.basename(target)
        if not no_number:
            basename = ("{:0%d}-{}" % digits).format(i, basename)
        dest = os.path.join(dest_dir, basename)
        try:
            os.symlink(target, dest)
        except FileExistsError:
            logger.warn("File exists: %s", dest)


def match_files(query, cache):
    matched_files = cache
    for attr, value in query:
        matched_files = [x for x in matched_files
                           if matches(value, getattr(x, attr))]
    return [x.path for x in matched_files]


def matches(value, attr_list):
    """Return whether value matches the attribute described by attr_list

    Attributes come from mutagen as lists of strings (except for the "path"
    attribute). We want to be able to look for both full matches and substring
    matches, so we surround each string with double quotes and then join them
    togehter. Then, if value is surrounded by double quotes, it will
    effectively only match for full string matches; otherwise, it will match
    substrings.
    """
    combined_attr_values = "".join('"%s"' % s for s in attr_list).lower()
    return value.lower() in combined_attr_values


def parse_entries(lines):
    entries = []
    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = PlaylistEntry.from_string(line)
        except QueryInvalidTagError:
            logger.warn("Ignoring query using invalid tag [line %s]: %r",
                        line_number, line)
        except QueryParseError:
            logger.warn("Ignoring invalid query [line %s]: %r",
                        line_number, line)
        else:
            entries.append(entry)
    return entries


def shuffled(results):
    fixed = []
    non_fixed = []
    for position, result in enumerate(results):
        if result.fixed_position:
            fixed.append((position, result))
        else:
            non_fixed.append(result)
    random.shuffle(non_fixed)
    for position, result in fixed:
        non_fixed.insert(position, result)
    return non_fixed
