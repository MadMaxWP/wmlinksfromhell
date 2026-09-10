"""top-level semantic resolver"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional
from urllib.parse import urlsplit

from . import interwiki, url as url_module
from .destination import Destination
from .metadata import MetadataStore
from .models import DestinationType, ResolutionStatus, SyntaxType, WikiInfo
from .exceptions import ResolutionError


@dataclasses.dataclass(frozen=True)
class ResolutionResult:
    raw: str
    syntax_type: SyntaxType
    status: ResolutionStatus
    reason: str
    destination: Optional[Destination] = None
    source_wiki: Optional[WikiInfo] = None
    confidence: float = 0.0
    prefix: Optional[str] = None
    canonical_prefix: Optional[str] = None
    prefix_kind: Optional[str] = None
    canonical_url: Optional[str] = None
    canonical_interwiki: Optional[str] = None

    @property
    def input_type(self) -> str:
        return self.syntax_type.value

    @property
    def family(self): return self.destination.family if self.destination else None
    @property
    def project(self): return self.destination.project if self.destination else None
    @property
    def language(self): return self.destination.language if self.destination else None
    @property
    def dbname(self): return self.destination.dbname if self.destination else None
    @property
    def title(self): return self.destination.title if self.destination else None
    @property
    def namespace(self): return self.destination.namespace if self.destination else None
    @property
    def fragment(self): return self.destination.fragment if self.destination else None
    @property
    def wikiid(self): return self.destination.wikiid if self.destination else None
    @property
    def page_id(self): return self.destination.page_id if self.destination else None
    @property
    def hostname(self): return self.destination.hostname if self.destination else None
    @property
    def revision(self): return self.destination.revision if self.destination else None
    @property
    def diff(self): return self.destination.diff if self.destination else None
    @property
    def action(self): return self.destination.action if self.destination else None
    @property
    def special_page(self): return self.destination.special_page if self.destination else None
    @property
    def organization_name(self): return self.destination.organization_name if self.destination else None
    @property
    def service_name(self): return self.destination.service_name if self.destination else None
    @property
    def is_standard_project(self): return self.destination.is_standard_project if self.destination else None
    @property
    def destination_type(self): return self.destination.destination_type if self.destination else None
    @property
    def url(self): return self.canonical_url

    @property
    def interwiki(self): return self.canonical_interwiki

    @property
    def is_wikimedia(self) -> bool:
        return bool(self.destination and self.destination.is_wikimedia_project)

    @property
    def is_project_prefix(self) -> bool:
        return self.prefix_kind in {"project", "language_project"}

    @property
    def is_language_prefix(self) -> bool:
        return self.prefix_kind in {"language", "language_project"}

    @property
    def is_language_project(self) -> bool:
        return self.prefix_kind == "language_project"

    @property
    def is_revision(self) -> bool:
        return bool(self.destination and self.destination.is_revision)

    @property
    def is_diff(self) -> bool:
        return bool(self.destination and self.destination.is_diff)

    @property
    def is_action(self) -> bool:
        return bool(self.destination and self.destination.is_action)

    def as_dict(self) -> dict:
        return {
            "raw": self.raw,
            "input_type": self.input_type,
            "syntax_type": self.syntax_type.value,
            "status": self.status.value,
            "reason": self.reason,
            "prefix": self.prefix,
            "canonical_prefix": self.canonical_prefix,
            "prefix_kind": self.prefix_kind,
            "canonical_url": self.canonical_url,
            "canonical_interwiki": self.canonical_interwiki,
            "destination": self.destination.as_dict() if self.destination else None,
            "source_dbname": self.source_wiki.dbname if self.source_wiki else None,
            "confidence": self.confidence,
        }


_CONFIDENCE = {
    ResolutionStatus.RESOLVED: 1.0,
    ResolutionStatus.EXTERNAL: 1.0,
    ResolutionStatus.AMBIGUOUS: 0.3,
    ResolutionStatus.METADATA_MISSING: 0.0,
    ResolutionStatus.CONTEXT_REQUIRED: 0.0,
    ResolutionStatus.UNKNOWN_PREFIX: 0.0,
    ResolutionStatus.UNKNOWN_DESTINATION: 0.0,
    ResolutionStatus.MALFORMED: 0.0,
    ResolutionStatus.UNSUPPORTED: 0.0,
}


class Resolver:
    def __init__(self, metadata: Optional[MetadataStore] = None):
        self.metadata = metadata or MetadataStore()

    def _source_title(self, source: Any = None) -> Optional[str]:
        if isinstance(source, (str, WikiInfo)):
            return None
        title_method = getattr(source, "title", None)
        if callable(title_method):
            try:
                return str(title_method())
            except Exception:
                return None
        return None

    def resolve_url(self, value: str, source: Any = None, strict: bool = False) -> ResolutionResult:
        source_wiki = self.metadata.resolve_source(source)
        destination, reason = url_module.parse_url(value, self.metadata)
        if destination is not None:
            if destination.destination_type is DestinationType.UNKNOWN:
                result = ResolutionResult(
                    value, SyntaxType.BARE_URL, ResolutionStatus.METADATA_MISSING, reason, destination,
                    source_wiki, 0.0, canonical_url=destination.canonical_url,
                )
            elif destination.destination_type is DestinationType.EXTERNAL:
                result = ResolutionResult(
                    value, SyntaxType.BARE_URL, ResolutionStatus.EXTERNAL, reason, destination, source_wiki,
                    1.0, canonical_url=destination.canonical_url,
                )
            else:
                try:
                    canonical_url = self.to_url(destination)
                except Exception:
                    canonical_url = destination.canonical_url
                try:
                    canonical_interwiki = self.to_interwiki(destination, source_wiki)
                except Exception:
                    canonical_interwiki = None
                result = ResolutionResult(
                    value, SyntaxType.BARE_URL, ResolutionStatus.RESOLVED, reason, destination, source_wiki,
                    1.0, canonical_url=canonical_url, canonical_interwiki=canonical_interwiki,
                )
        else:
            parts = url_module.urlsplit(value)
            if parts.scheme in ("http", "https") and parts.hostname:
                if self.metadata.is_wikimedia_hostname(parts.hostname):
                    unknown = Destination(
                        destination_type=DestinationType.UNKNOWN,
                        hostname=parts.hostname,
                        canonical_url=value,
                        is_wikimedia_project=True,
                        metadata_source="missing",
                    )
                    result = ResolutionResult(
                        value, SyntaxType.BARE_URL, ResolutionStatus.UNSUPPORTED, reason, unknown, source_wiki, 0.0,
                        canonical_url=value,
                    )
                else:
                    external = Destination(
                        destination_type=DestinationType.EXTERNAL,
                        hostname=parts.hostname,
                        canonical_url=value,
                    )
                    result = ResolutionResult(
                        value, SyntaxType.BARE_URL, ResolutionStatus.EXTERNAL, reason, external, source_wiki, 1.0,
                        canonical_url=value,
                    )
            elif value.startswith("//") and parts.hostname:
                external = Destination(
                    destination_type=DestinationType.EXTERNAL,
                    hostname=parts.hostname,
                    canonical_url=value,
                )
                result = ResolutionResult(
                    value, SyntaxType.BARE_URL, ResolutionStatus.EXTERNAL, reason, external, source_wiki, 1.0,
                    canonical_url=value,
                )
            else:
                result = ResolutionResult(value, SyntaxType.BARE_URL, ResolutionStatus.MALFORMED, reason, None, source_wiki, 0.0)
        return self._strict(result, strict)

    def resolve_interwiki(self, value: str, source: Any = None, strict: bool = False) -> ResolutionResult:
        source_wiki = self.metadata.resolve_source(source)
        chain = interwiki.resolve_chain(
            value,
            source_wiki,
            self.metadata,
            page_title=self._source_title(source),
        )
        syntax = SyntaxType.LOCAL_WIKILINK if chain.destination is not None and interwiki.is_local_to(chain.destination, source_wiki) else SyntaxType.INTERWIKI_WIKILINK
        canonical_url = canonical_interwiki = None
        if chain.destination is not None and chain.status is ResolutionStatus.RESOLVED:
            try:
                canonical_url = self.to_url(chain.destination)
            except Exception:
                canonical_url = chain.destination.canonical_url
            try:
                canonical_interwiki = self.to_interwiki(chain.destination, source_wiki)
            except Exception:
                canonical_interwiki = None
        result = ResolutionResult(value, syntax, chain.status, chain.reason, chain.destination, source_wiki, _CONFIDENCE[chain.status], chain.prefix, chain.canonical_prefix, chain.prefix_kind, canonical_url, canonical_interwiki)
        return self._strict(result, strict)

    def resolve(self, value: str, source: Any = None, strict: bool = False) -> ResolutionResult:
        if not isinstance(value, str):
            raise TypeError("resolve() expects a string")
        stripped = value.strip()
        scheme = urlsplit(stripped).scheme.casefold() if stripped else ""
        prefix = stripped.split(":", 1)[0].casefold() if ":" in stripped else ""
        known = prefix in self.metadata.interwiki_map(source) if prefix else False
        if stripped.startswith(("//", "http://", "https://", "ftp://")) or (scheme and not known and scheme in {"mailto", "tel", "sms", "ssh", "irc", "ircs", "news", "skype"}):
            return self.resolve_url(stripped, source, strict)
        return self.resolve_interwiki(stripped, source, strict)

    @staticmethod
    def _strict(result: ResolutionResult, strict: bool) -> ResolutionResult:
        if strict and result.status not in {ResolutionStatus.RESOLVED, ResolutionStatus.EXTERNAL}:
            raise ResolutionError(f"resolution failed: {result.status.value}: {result.reason}")
        return result

    def to_url(self, destination: Destination) -> str:
        return url_module.build_url(destination, self.metadata)

    def to_interwiki(self, destination: Destination, source: Any = None) -> str:
        return interwiki.render_interwiki_target(destination, self.metadata, self.metadata.resolve_source(source))

    def to_local(self, destination: Destination, source: Any = None) -> str:
        source_wiki = self.metadata.resolve_source(source)
        if source_wiki is None:
            raise ValueError("a local wikilink representation needs a source wiki")
        return interwiki.render_local_target(destination, source_wiki)
