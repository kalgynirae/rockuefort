rockuefort
==========

**Rockuefort** uses [Quod Libet]'s flexible querying to build playlists
on-the-fly from a list of music queries. This keeps your playlists decoupled
from the actual paths and filenames of your music library. Rockuefort can build
your playlist and copy or link the songs into a destination directory. It uses
`rsync` to copy so that only new or changed files need to be copied.

Prerequisites
-------------

*   Install Quod Libet and have it scan your music library.
*   Install rsync if you want to use the `copy` mode.

Usage
-----

List the files that match the queries in the file `chiptunes`:

    $ rockuefort list chiptunes

Link those files into the `muzic/blerg/` directory:

    $ rockuefort link chiptunes muzic/blerg/

Copy those files into the `muzic/wheeeeeeee/` directory:

    $ rockuefort copy chiptunes muzic/wheeeeeeee/

What's with the name?
---------------------

Rockuefort is named after [Roquefort cheese].

[Quod Libet]: https://code.google.com/p/quodlibet/
[Roquefort cheese]: https://en.wikipedia.org/wiki/Roquefort
