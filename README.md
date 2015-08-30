Rockuefort
==========

**Rockuefort** "compiles" your playlists. It indexes your music
directory and then searches through the metadata to locate the files
corresponding to the entries in your playlist. This keeps your playlist
decoupled from the actual paths and filenames of your music library.
Rockuefort can build your playlist and copy or link the songs into a
destination directory. It uses `rsync` to copy so that only new or
changed files need to be copied.

Quick set-up
------------

1.  Install `rsync` if you want to use the `copy` mode.

2.  Obtain the latest Rockuefort source.

        $ git clone https://github.com/kalgynirae/rockuefort.git
        $ cd rockuefort

3.  Set up a virtual environment and install the required dependencies.

        $ python3 -m venv env
        $ env/bin/pip install -e .

4.  Put the installed Rockuefort script on your path.

        # Assuming ~/bin is in your $PATH
        $ ln -s --relative env/bin/rockuefort ~/bin/rockuefort

Usage
-----

Scan the `/var/music` directory:

    $ rockuefort index --add /var/music
    $ rockuefort scan

List the files that match the entries in the file `chiptunes`:

    $ rockuefort list chiptunes

Link those files into the `muzic/blerg/` directory:

    $ rockuefort link chiptunes muzic/blerg/

Copy those files into the `muzic/wheeeeeeee/` directory:

    $ rockuefort copy chiptunes muzic/wheeeeeeee/

Play the playlist with VLC:

    $ rockuefort list chiptunes | xargs -d '\n' vlc

Queue songs using `mpc` (`mpc` only likes relative paths):

    $ rockuefort list --strip '/var/music/' chiptunes | mpc add

Playlist format
---------------

Rockuefort playlists are text files with one query per line. Blank lines
and lines starting with `#` are ignored.

A query takes the following format:

    [O][N:]TAG=VALUE[|TAG=VALUE...]

*   `O`: zero or more special option characters (defaults to nothing)
*   `N`: the number of files this query is expected to match (defaults
    to `1`)
*   `TAG`: one of `title`, `artist`, `album`, or `genre`
*   `VALUE`: a substring of the value to match. It can contain any
    character except `|`. Matching files will have this as a substring
    of the real tag value. It can be surrounded with double quotes to
    perform an exact match (instead of substring).

### Special options for queries

*   `|`: consecutive queries with this option will be treated as a single unit
    when reordering tracks (e.g., with the `--shuffle` option)

### Example playlists

*   [kalgynirae/playlists/bedtime](https://bitbucket.org/kalgynirae/playlists/src/f25098b617df69227113b4a76050c84e95d348d9/bedtime?at=master)
*   [kalgynirae/playlists/chiptune](https://bitbucket.org/kalgynirae/playlists/src/f25098b617df69227113b4a76050c84e95d348d9/chiptune?at=master)

What's with the name?
---------------------

Rockuefort is named after [Roquefort
cheese](https://en.wikipedia.org/wiki/Roquefort).
