Using wmlinksfromhell
=====================

Install from PyPI::

   python3 -m pip install wmlinksfromhell

For optional Pywikibot support::

   python3 -m pip install "wmlinksfromhell[pywikibot]"

Quick start
-----------

Resolve a Wikimedia interwiki link::

   import wmlinksfromhell

   result = wmlinksfromhell.resolve("w:en:Apple")

   print(result.dbname)
   print(result.title)
   print(result.url)

Parse links from MediaWiki text::

   code = wmlinksfromhell.parse(
       "[[w:en:Apple]] https://de.wikipedia.org/wiki/Berlin https://example.org/",
       source="metawiki",
   )

   for link in code.filter_links():
       print(link.original)
       print(link.dbname, link.title, link.url)

Build a wiki URL or interwiki link::

   wmlinksfromhell.url("enwiki", "Apple")
   wmlinksfromhell.link("enwiki", "Apple")

The :doc:`api` page covers the complete public API.
