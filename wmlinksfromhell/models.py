"""small value objects shared by wmlinksfromhell"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Optional


class DestinationType(str, Enum):
    """what kind of thing a link points at"""

    WIKI = "wiki"
    ORGANIZATION = "organization"
    SERVICE = "service"
    TOOL = "tool"
    SPECIAL = "special"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ResolutionStatus(str, Enum):
    """explicit outcome of a resolution attempt"""

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    CONTEXT_REQUIRED = "context_required"
    UNKNOWN_PREFIX = "unknown_prefix"
    UNKNOWN_DESTINATION = "unknown_destination"
    METADATA_MISSING = "metadata_missing"
    EXTERNAL = "external"
    MALFORMED = "malformed"
    UNSUPPORTED = "unsupported"


class SyntaxType(str, Enum):
    """the link form reported by the wrapper; wikilink locality follows resolution"""

    LOCAL_WIKILINK = "local_wikilink"
    INTERWIKI_WIKILINK = "interwiki_wikilink"
    EXTERNAL_LINK = "external_link"
    BARE_URL = "bare_url"


@dataclasses.dataclass(frozen=True)
class WikiInfo:
    """metadata for one Wikimedia wiki"""

    dbname: str
    family: str
    project: str
    language: str
    language_name: str
    hostname: str
    article_path: str = "/wiki/$1"
    script_path: str = "/w/index.php"
    wikiid: Optional[str] = None
    sitename: Optional[str] = None
    api_url: Optional[str] = None
    metadata_source: str = "bootstrap"
    site_code: Optional[str] = None
    is_multilingual: bool = False
    is_standard_project: bool = False

    def __post_init__(self) -> None:
        if self.wikiid is None:
            object.__setattr__(self, "wikiid", self.dbname)
        if self.api_url is None:
            object.__setattr__(self, "api_url", f"https://{self.hostname}/w/api.php")

    @property
    def url(self) -> str:
        return f"https://{self.hostname}"

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)

    def interwiki_info(self, metadata=None, source=None):
        from .metadata import MetadataStore
        return (metadata or MetadataStore()).interwiki(self.dbname, source=source)

    def interwiki(self, title: Optional[str] = None, metadata=None, source=None) -> str:
        info = self.interwiki_info(metadata=metadata, source=source)
        if info is None:
            raise ValueError(f"no interwiki prefix known for {self.dbname!r}")
        return info.target(title)

    def page_url(self, title: Optional[str] = None, metadata=None, source=None) -> str:
        from .metadata import MetadataStore
        from .resolver import Resolver
        title = "Main Page" if title is None else title
        metadata = metadata or MetadataStore()
        info = self.interwiki_info(metadata=metadata, source=source)
        if info is None:
            raise ValueError(f"no interwiki prefix known for {self.dbname!r}")
        result = Resolver(metadata).resolve_interwiki(
            info.target(title),
            source=source,
        )
        if result.status.value != "resolved" or result.url is None:
            raise ValueError(f"could not build URL for {self.dbname!r}:{title}")
        return result.url

    def link(self, title: Optional[str] = None, label: Optional[str] = None, metadata=None, source=None) -> str:
        target = self.interwiki("Main Page" if title is None else title, metadata=metadata, source=source)
        return f"[[{target}|{label}]]" if label is not None else f"[[{target}]]"

    main_page_url = page_url


@dataclasses.dataclass(frozen=True)
class InterwikiInfo:
    """canonical interwiki identity for one Wikimedia wiki"""

    prefix: str
    project: str
    language: Optional[str]
    dbname: str
    wiki: WikiInfo

    def target(self, title: Optional[str] = None) -> str:
        return self.prefix if title is None else f"{self.prefix}:{title}"

    def url(self, title: str = "Main Page", metadata=None, source=None) -> str:
        return self.wiki.page_url(title, metadata=metadata, source=source)

    def link(self, title: str = "Main Page", label: Optional[str] = None, metadata=None, source=None) -> str:
        return self.wiki.link(title, label=label, metadata=metadata, source=source)

    def as_dict(self) -> dict:
        return {
            "prefix": self.prefix,
            "project": self.project,
            "language": self.language,
            "dbname": self.dbname,
            "wiki": self.wiki.as_dict(),
        }

    def __str__(self) -> str:
        return self.prefix


@dataclasses.dataclass(frozen=True)
class InterwikiEntry:
    """one source-wiki interwiki table entry"""

    prefix: str
    url: str
    local: bool = False
    trans: bool = False
    language: Optional[str] = None
    localinterwiki: bool = False
    extralanglink: bool = False
    linktext: Optional[str] = None
    sitename: Optional[str] = None
    wikiid: Optional[str] = None
    api: Optional[str] = None
    destination_dbname: Optional[str] = None
    destination_type: Optional[DestinationType] = None

    def as_dict(self) -> dict:
        data = dataclasses.asdict(self)
        if self.destination_type is not None:
            data["destination_type"] = self.destination_type.value
        return data
