rockuefort
==========

**Rockuefort** "compiles" your playlists. It indexes your music
directory and then searches through the metadata to locate the files
corresponding to the entries in your playlist. This keeps your playlist
decoupled from the actual paths and filenames of your music library.
Rockuefort can build your playlist and copy or link the songs into a
destination directory. It uses `rsync` to copy so that only new or
changed files need to be copied.

Set-up
------

1.  Install `rsync` if you want to use the `copy` mode.

2.  Obtain the latest Rockuefort source.

        $ git clone https://github.com/kalgynirae/rockuefort.git
        $ cd rockuefort

3.  Set up a virtual environment and install the required dependencies.

        $ virtualenv3 .
        $ bin/pip install -r requirements.txt

4.  Run Rockuefort using the local Python.

        $ bin/python rockuefort.py

Usage
-----

Index the `/var/music/` directory:

    $ bin/python rockuefort.py index /var/music/

List the files that match the entries in the file `chiptunes`:

    $ bin/python rockuefort.py list chiptunes

Link those files into the `muzic/blerg/` directory:

    $ bin/python rockuefort.py link chiptunes muzic/blerg/

Copy those files into the `muzic/wheeeeeeee/` directory:

    $ bin/python rockuefort.py copy chiptunes muzic/wheeeeeeee/

What's with the name?
---------------------

Rockuefort is named after [Roquefort cheese].

[Quod Libet]: https://code.google.com/p/quodlibet/
[Roquefort cheese]: https://en.wikipedia.org/wiki/Roquefort
