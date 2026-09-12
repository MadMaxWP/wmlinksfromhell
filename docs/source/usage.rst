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

Use ``long_project_prefix=True`` when the full Wikimedia project name is
preferred for a project/language interwiki target::

   result = wmlinksfromhell.resolve_url(
       "https://hi.wikipedia.org/wiki/Apple",
       long_project_prefix=True,
   )
   print(result.canonical_interwiki)
   wmlinksfromhell.to_interwiki(result.destination, long_project_prefix=True)

The default remains the short form, such as ``w:hi:Apple``; the long form
``wikipedia:hi:Apple`` is also accepted as input and resolves to the same
destination.

Use the batch and enumeration helpers when working with multiple values or
metadata collections::

   resolver = wmlinksfromhell.Resolver()
   metadata = wmlinksfromhell.MetadataStore()
   resolver.resolve_many(["w:en:Apple", "w:de:Berlin"])
   metadata.wikis_for_family("wikipedia")
   metadata.languages()
   metadata.canonical_namespaces("enwiki")
   metadata.interwiki_map("enwiki").prefixes()

The :doc:`api` page covers the complete public API.

Command-line lookup
-------------------

Resolve a value from the command line::

   python -m wmlinksfromhell resolve "w:en:Apple"

Use ``--source`` for a source wiki and ``--json`` for machine-readable JSON::

   python -m wmlinksfromhell resolve "Apple" --source enwiki --json
