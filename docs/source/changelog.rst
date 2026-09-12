Changelog
=========

0.1.3
-----

Fixed legacy ``Image:`` namespace links returning the namespace as ``file`` instead of the canonical ``File`` casing.

0.1.2
-----

Expanded the public API with serialization, batch resolution, metadata enumeration, filtering, link-label editing, and a minimal command-line interface.

* Added destination and resolution-result JSON/dict symmetry helpers.
* Added batch resolution and metadata/interwiki enumeration helpers.
* Added membership-style link matching and destination collection helpers.
* Added destination type convenience properties.
* Added in-place link-label editing.
* Added metadata freshness and membership checks.
* Added ``python -m wmlinksfromhell resolve`` command-line support.

0.1.0
-----

First public release of ``wmlinksfromhell``.

* Wikimedia-aware link parsing and resolution.
* Interwiki and language/project prefix support.
* Wikimedia URL, revision, diff, action, and page-ID handling.
* SiteMatrix and interwiki metadata support with local caching.
* Link matching and conversion between local, interwiki, and URL forms.
* Pywikibot page integration.
