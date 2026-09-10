"""semantic destinations independent of link syntax"""

from __future__ import annotations

import dataclasses
import json
import re
from typing import Optional

from .models import DestinationType

_WHITESPACE_RE = re.compile(r"[ \t_]+")


def normalize_title(title: str) -> str:
    return _WHITESPACE_RE.sub(" ", title).strip()


def split_namespace(title: str, known_namespaces: frozenset[str]) -> tuple[Optional[str], str]:
    if ":" not in title:
        return None, title
    head, rest = title.split(":", 1)
    candidate = normalize_title(head).casefold()
    if candidate not in known_namespaces:
        return None, title
    return head.strip(), rest.strip()


@dataclasses.dataclass(frozen=True, eq=False)
class Destination:
    """a syntax-independent Wikimedia destination"""

    destination_type: DestinationType
    family: Optional[str] = None
    project: Optional[str] = None
    language: Optional[str] = None
    dbname: Optional[str] = None
    wikiid: Optional[str] = None
    hostname: Optional[str] = None
    title: Optional[str] = None
    namespace: Optional[str] = None
    fragment: Optional[str] = None
    revision: Optional[int] = None
    diff: Optional[object] = None
    action: Optional[str] = None
    special_page: Optional[str] = None
    organization_name: Optional[str] = None
    service_name: Optional[str] = None
    query_parameters: tuple[tuple[str, str], ...] = ()
    page_id: Optional[int] = None
    canonical_url: Optional[str] = None
    metadata_source: Optional[str] = None
    is_multilingual: Optional[bool] = None
    is_standard_project: Optional[bool] = None
    is_wikimedia_project: Optional[bool] = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Destination):
            return NotImplemented
        return self.identity_key() == other.identity_key()

    def __hash__(self) -> int:
        return hash(self.identity_key())

    def as_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["destination_type"] = self.destination_type.value
        data["query_parameters"] = list(self.query_parameters)
        return data

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)

    @property
    def full_title(self) -> Optional[str]:
        if self.title is None:
            return None
        return f"{self.namespace}:{self.title}" if self.namespace else self.title

    def page_identity_key(self) -> tuple:
        if self.destination_type in {DestinationType.EXTERNAL, DestinationType.UNKNOWN}:
            return (self.destination_type, self.canonical_url or self.hostname or self.full_title)
        base = (
            self.destination_type,
            self.dbname,
            self.hostname if self.dbname is None else None,
            self.organization_name,
            self.service_name,
        )
        # a diff is its own operation target, even when it includes an oldid.
        # don't collapse it to the permanent-link identity of that oldid.
        if self.diff is not None:
            return base + ("diff", self.revision, self.diff)
        if self.revision is not None:
            return base + ("revision", self.revision)
        if self.page_id is not None:
            return base + ("page_id", self.page_id)
        return base + (normalize_title(self.full_title) if self.full_title else None,)

    def identity_key(self) -> tuple:
        """complete semantic identity, including fragment and operations."""
        return self.page_identity_key() + (
            self.fragment,
            self.revision,
            self.diff,
            self.action,
            self.query_parameters,
        )

    def same_page_as(self, other: "Destination") -> bool:
        if not isinstance(other, Destination):
            return NotImplemented
        return self.page_identity_key() == other.page_identity_key()

    @property
    def is_revision(self) -> bool:
        return self.revision is not None

    @property
    def is_diff(self) -> bool:
        return self.diff is not None

    @property
    def is_action(self) -> bool:
        return self.action is not None
