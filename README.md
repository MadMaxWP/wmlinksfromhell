# wmlinksfromhell

[![CI](https://github.com/MadMaxWP/wmlinksfromhell/actions/workflows/ci.yml/badge.svg)](https://github.com/MadMaxWP/wmlinksfromhell/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/wmlinksfromhell.svg)](https://pypi.org/project/wmlinksfromhell/)
[![Python](https://img.shields.io/pypi/pyversions/wmlinksfromhell.svg)](https://pypi.org/project/wmlinksfromhell/)
[![License](https://img.shields.io/github/license/MadMaxWP/wmlinksfromhell.svg)](https://github.com/MadMaxWP/wmlinksfromhell/blob/main/LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/MadMaxWP/wmlinksfromhell.svg)](https://github.com/MadMaxWP/wmlinksfromhell/releases/latest)

**wmlinksfromhell** is a Python package for working with links on Wikimedia and other MediaWiki sites. It is mainly focused on Wikimedia interwiki links, language and project prefixes, and Wikimedia URLs, with support for local links and external URLs too.

It can resolve links to their destination wiki and page, convert them between interwiki and URL forms, and give you the details you need to work with them in your code.

Developed by [Max](https://github.com/MadMaxWP).

Full documentation is available on [Read the Docs](https://wmlinksfromhell.readthedocs.io/en/latest/). Development takes place on [GitHub](https://github.com/MadMaxWP/wmlinksfromhell), and bugs and feature requests can be reported in the [issue tracker](https://github.com/MadMaxWP/wmlinksfromhell/issues).

## Project links

- [Documentation](https://wmlinksfromhell.readthedocs.io/en/latest/)
- [API Reference](https://wmlinksfromhell.readthedocs.io/en/latest/api.html)
- [Changelog](https://github.com/MadMaxWP/wmlinksfromhell/blob/main/CHANGELOG.md)
- [Issues](https://github.com/MadMaxWP/wmlinksfromhell/issues)
- [Repository](https://github.com/MadMaxWP/wmlinksfromhell)

## Install

```bash
python3 -m pip install wmlinksfromhell
```

Pywikibot support is optional:

```bash
python3 -m pip install 'wmlinksfromhell[pywikibot]'
```

Supports Python 3.9 and newer.

## Quick start

Get information about a wiki:

```python
import wmlinksfromhell

wiki = wmlinksfromhell.wiki("enwiki")

print(wiki.language)       # en
print(wiki.hostname)       # en.wikipedia.org
print(wiki.page_url("Apple"))
print(wiki.interwiki("Apple"))
```

Resolve a Wikimedia link:

```python
result = wmlinksfromhell.resolve("w:en:Apple")

print(result.dbname)        # enwiki
print(result.title)         # Apple
print(result.url)           # https://en.wikipedia.org/wiki/Apple
```

Use the full project name for project/language interwiki output when needed:

```python
result = wmlinksfromhell.resolve_url(
    "https://hi.wikipedia.org/wiki/Apple",
    long_project_prefix=True,
)

print(result.canonical_interwiki)  # wikipedia:hi:Apple
```

The short form remains the default, and `wikipedia:hi:Apple` is accepted as input.

Parse links from MediaWiki text:

```python
import wmlinksfromhell

code = wmlinksfromhell.parse(
    "[[w:en:Apple]] https://de.wikipedia.org/wiki/Berlin https://example.org/",
    source="metawiki",
)

for link in code.filter_links():
    print(link.original)
    print(link.dbname, link.title, link.url)
```

The parser keeps the original way a link was written separate from the destination it resolves to. This lets you work with the same destination whether it came from an interwiki link, a wiki URL, or another supported form.

## Wikimedia links

The resolver understands Wikimedia language and project prefixes, including prefix chains:

```text
w:en:Apple
wikt:simple:uppercase
b:de:Main Page
:de:q:Hauptseite
:m:en:About
:w:it:b:Wiskunde
```

It also handles Wikimedia URL forms such as article paths and `index.php`, including fragments, revisions, diffs, actions, and page IDs.

For example:

```python
result = wmlinksfromhell.resolve(
    "https://en.wikipedia.org/w/index.php?title=Apple&oldid=123456",
)

print(result.dbname)       # enwiki
print(result.revision)     # 123456
print(result.interwiki)    # w:en:Special:PermanentLink/123456
```

A leading colon changes MediaWiki's special handling for some links, but it does not necessarily change the destination. For example, `[[en:Apple]]` and `[[:en:Apple]]` both point to English Wikipedia's `Apple` page; the leading-colon form is used when the link should be shown as a normal link in the page.

## Local and external links

Local targets are resolved when a source wiki is available:

```python
result = wmlinksfromhell.resolve(
    "Apple",
    source="enwiki",
)

print(result.dbname)       # enwiki
print(result.title)        # Apple
```

Ordinary external URLs are kept as external destinations:

```python
result = wmlinksfromhell.resolve("https://example.org/page")

print(result.status)             # ResolutionStatus.EXTERNAL
print(result.destination_type)   # DestinationType.EXTERNAL
print(result.url)
```

## Finding links

`filter_links()` can select links by the things you care about:

```python
code.filter_links(dbname="enwiki")
code.filter_links(family="wikipedia", language="en")
code.filter_links(namespace="MediaWiki")
code.filter_links(hostname="en.wikipedia.org")

code.filter_links(wiki_only=True)
code.filter_links(interwiki_only=True)
code.filter_links(local_only=True)
code.filter_links(external_only=True)
code.filter_links(dbname_in={"enwiki", "dewiki"})
```

`code.destinations` returns the resolved destinations for parsed links.

Links inside HTML comments are ignored by default. Include them when needed:

```python
code.filter_links(comment_links=True)
```

## Working with a link

Links expose both the original link and its resolved destination:

```python
for link in code.filter_links():
    print(link.original)
    print(link.dbname)
    print(link.title)
    print(link.interwiki)
    print(link.url)
    print(link.destination)
```

Links can also be matched and converted:

```python
link.matches(dbname="enwiki", title="Apple")

link.set_url()
link.set_interwiki()
link.set_local(source="enwiki")
link.set_label("New label")
```

## Metadata and serialization

Metadata can be enumerated without reaching into private state:

```python
metadata = wmlinksfromhell.MetadataStore()
wmlinksfromhell.wikis(metadata)
metadata.wikis_for_family("wikipedia")
metadata.languages()
metadata.canonical_namespaces("enwiki")
metadata.interwiki_map("enwiki").prefixes()
```

`Destination` objects can be reconstructed from `as_dict()` output, and
`ResolutionResult` objects can be serialized directly with `as_json()`.

## Command line

Resolve a value from the command line:

```bash
python -m wmlinksfromhell resolve "w:en:Apple"
python -m wmlinksfromhell resolve "Apple" --source enwiki --json
```

## Pywikibot

When Pywikibot is installed, a `Page` can be passed directly to `parse_page()`:

```python
import pywikibot
import wmlinksfromhell

site = pywikibot.Site("en", "wikipedia")
page = pywikibot.Page(site, "Apple")

code = wmlinksfromhell.parse_page(page)

for link in code.filter_links():
    print(link.original, link.url)
```

## Metadata

Wikimedia SiteMatrix and interwiki metadata can be loaded and cached locally. The lower-level `MetadataStore`, `Resolver`, and `Destination` APIs are available when you need more control.

See the [API Reference](https://wmlinksfromhell.readthedocs.io/en/latest/api.html) for the full API.
