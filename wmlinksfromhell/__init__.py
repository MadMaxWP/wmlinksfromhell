"""small Wikimedia-aware link tools for wikitext"""

from .cache import MetadataCache
from .destination import Destination
from .exceptions import CacheError, ConversionError, MetadataMissingError, ResolutionError, SourceResolutionError, WMLinkFromHellError, WMLinksFromHellError
from .metadata import InterwikiMap, MetadataStore
from .models import DestinationType, InterwikiEntry, InterwikiInfo, ResolutionStatus, SyntaxType, WikiInfo
from .nodes import WMLink
from .parser import WMCode, parse
from .pywikibot_support import parse_page
from .resolver import ResolutionResult, Resolver

# short names cover the usual case; longer names stay available too
Code = WMCode
Link = WMLink
Wiki = WikiInfo
Metadata = MetadataStore
Result = ResolutionResult
Error = WMLinksFromHellError


def wiki(dbname: str, metadata: MetadataStore = None) -> WikiInfo:
    result = (metadata or MetadataStore()).wiki_by_dbname(dbname)
    if result is None:
        raise MetadataMissingError(f"no metadata known for dbname {dbname!r}")
    return result


def wikis(metadata: MetadataStore = None) -> tuple[WikiInfo, ...]:
    return (metadata or MetadataStore()).all_wikis()


def interwiki(dbname: str, metadata: MetadataStore = None, source=None) -> InterwikiInfo:
    result = (metadata or MetadataStore()).interwiki(dbname, source=source)
    if result is None:
        raise MetadataMissingError(f"no interwiki prefix known for dbname {dbname!r}")
    return result


def url(dbname: str, title: str, metadata: MetadataStore = None, source=None) -> str:
    return wiki(dbname, metadata=metadata).page_url(title, metadata=metadata, source=source)


def link(dbname: str, title: str, label: str = None, metadata: MetadataStore = None, source=None) -> str:
    return wiki(dbname, metadata=metadata).link(title, label=label, metadata=metadata, source=source)


def resolve_url(value: str, source=None, metadata: MetadataStore = None, long_project_prefix: bool = False) -> ResolutionResult:
    return Resolver(metadata).resolve_url(value, source=source, long_project_prefix=long_project_prefix)


def resolve_interwiki(value: str, source=None, metadata: MetadataStore = None, long_project_prefix: bool = False) -> ResolutionResult:
    return Resolver(metadata).resolve_interwiki(value, source=source, long_project_prefix=long_project_prefix)


def to_url(destination: Destination, metadata: MetadataStore = None) -> str:
    return Resolver(metadata).to_url(destination)


def to_interwiki(destination: Destination, source=None, metadata: MetadataStore = None, long_project_prefix: bool = False) -> str:
    return Resolver(metadata).to_interwiki(destination, source=source, long_project_prefix=long_project_prefix)


def to_local(destination: Destination, source=None, metadata: MetadataStore = None) -> str:
    return Resolver(metadata).to_local(destination, source=source)

__version__ = "0.1.2"

__all__ = [
    "parse", "parse_page", "resolve", "resolve_url", "resolve_interwiki", "to_url", "to_interwiki", "to_local", "wiki", "wikis", "interwiki", "url", "link", "Code", "Link", "Wiki", "Metadata", "Result", "WMCode", "WMLink", "Resolver", "ResolutionResult", "MetadataStore", "MetadataCache",
    "InterwikiMap", "InterwikiEntry", "InterwikiInfo", "Destination", "DestinationType", "ResolutionStatus", "SyntaxType", "WikiInfo",
    "Error", "WMLinksFromHellError", "WMLinkFromHellError", "ConversionError", "MetadataMissingError", "CacheError", "SourceResolutionError", "ResolutionError",
]


def resolve(value: str, source=None, metadata: MetadataStore = None, long_project_prefix: bool = False) -> ResolutionResult:
    return Resolver(metadata).resolve(value, source=source, long_project_prefix=long_project_prefix)
