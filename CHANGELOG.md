# Changelog

## 0.1.2 — 2026-09-12

Expanded the public API with serialization, batch resolution, metadata enumeration, filtering, link-label editing, and a minimal command-line interface.

- Added destination and resolution-result JSON/dict symmetry helpers.
- Added batch resolution and metadata/interwiki enumeration helpers.
- Added membership-style link matching and destination collection helpers.
- Added destination type convenience properties.
- Added in-place link-label editing.
- Added metadata freshness and membership checks.
- Added `python -m wmlinksfromhell resolve` command-line support.
- Fixed canonical namespace fallback casing.
- Added optional long Wikimedia project prefixes such as `wikipedia:hi:Apple` for resolution and interwiki conversion while preserving the default short forms.

## 0.1.1 — 2026-09-10

Small documentation and robustness fixes following final pre-release review.

- Hardened malformed metadata-cache handling.
- Corrected duplicate-link position reporting.
- Improved handling of unresolved fixed Wikimedia prefixes.
- Refined the Sphinx API documentation.

## 0.1.0 — 2026-09-10

First public release of wmlinksfromhell.

- Wikimedia interwiki and language/project link resolution.
- Wikimedia wiki URL and `index.php` URL resolution.
- Support for local and external links.
- Prefix chains, namespaces, fragments, revisions, diffs, actions, and page IDs.
- Link matching and conversion between URL, interwiki, and local forms.
- SiteMatrix and interwiki metadata with local caching.
- Pywikibot `Site` and `Page` support.
