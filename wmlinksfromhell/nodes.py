"""structured link wrappers and in-place transformations"""

from __future__ import annotations

from typing import Any, Optional
import mwparserfromhell
from mwparserfromhell.nodes import ExternalLink, Wikilink

from .destination import Destination
from .exceptions import ConversionError
from .models import DestinationType, ResolutionStatus, SyntaxType, WikiInfo
from .resolver import ResolutionResult, Resolver

_FLAG_FILTERS = {"wikimedia_only", "wiki_only", "external_only", "interwiki_only", "local_only"}


class WMLink:
    def __init__(self, node, code: "mwparserfromhell.wikicode.Wikicode", root: "mwparserfromhell.wikicode.Wikicode", resolver: Resolver, source: Any = None, index: int = 0, in_comment: bool = False, comment_node=None):
        self._node = node
        self._code = code
        self._root = root
        self._resolver = resolver
        self._source = source
        self.index = index
        self.in_comment = in_comment
        self._comment_node = comment_node
        self._result: Optional[ResolutionResult] = None

    @property
    def node(self):
        return self._node

    @property
    def original(self) -> str:
        return str(self._node)

    @property
    def is_wikilink(self) -> bool:
        return isinstance(self._node, Wikilink)

    @property
    def is_external_link(self) -> bool:
        return isinstance(self._node, ExternalLink)

    @property
    def leading_colon(self) -> bool:
        return self.is_wikilink and str(self._node.title).lstrip().startswith(":")

    @property
    def is_category_link(self) -> bool:
        namespace = self.namespace
        return self.is_wikilink and namespace is not None and namespace.casefold() == "category" and not self.leading_colon

    @property
    def is_file_link(self) -> bool:
        namespace = self.namespace
        return self.is_wikilink and namespace is not None and namespace.casefold() in {"file", "image"} and not self.leading_colon

    @property
    def link_type(self) -> str:
        if self.is_category_link:
            return "category"
        if self.is_file_link:
            return "file"
        if self.in_comment:
            return "comment_external_link" if self.is_external_link else "comment_wikilink"
        return "external_link" if self.is_external_link else "wikilink"

    @property
    def is_self_link(self) -> bool:
        result = self._resolve()
        source_title = getattr(self._source, "title", None)
        if not callable(source_title) or result.destination is None or result.destination.destination_type is not DestinationType.WIKI:
            return False
        try:
            source_title = str(source_title())
        except Exception:
            return False
        source_wiki = result.source_wiki
        if source_wiki is None or result.destination.dbname != source_wiki.dbname:
            return False
        return result.destination.same_page_as(
            self._resolver.resolve_interwiki(source_title, self._source).destination
        )

    @property
    def raw(self) -> str:
        if self.is_wikilink:
            return str(self._node.title)
        return str(self._node.url)

    @property
    def label(self) -> Optional[str]:
        if self.is_wikilink:
            return str(self._node.text) if self._node.text is not None else None
        return str(self._node.title) if self._node.title is not None else None

    def refresh(self) -> None:
        self._result = None

    def _resolve(self) -> ResolutionResult:
        if self._result is None:
            self._result = self._resolver.resolve_interwiki(self.raw, self._source) if self.is_wikilink else self._resolver.resolve_url(self.raw, self._source)
        return self._result

    @property
    def result(self) -> ResolutionResult:
        return self._resolve()

    @property
    def source_wiki(self) -> Optional[WikiInfo]: return self._resolve().source_wiki
    @property
    def status(self) -> str: return self._resolve().status.value
    @property
    def confidence(self) -> float: return self._resolve().confidence
    @property
    def reason(self) -> str: return self._resolve().reason
    @property
    def syntax_type(self) -> str:
        if self.is_external_link and getattr(self._node, "brackets", False):
            return SyntaxType.EXTERNAL_LINK.value
        return self._resolve().syntax_type.value
    @property
    def input_type(self) -> str:
        return self.syntax_type

    @property
    def prefix(self): return self._resolve().prefix
    @property
    def canonical_prefix(self): return self._resolve().canonical_prefix
    @property
    def prefix_kind(self): return self._resolve().prefix_kind
    @property
    def destination(self) -> Optional[Destination]: return self._resolve().destination

    def _dest(self, name: str, default=None):
        destination = self.destination
        return getattr(destination, name, default) if destination is not None else default

    family = property(lambda s: s._dest("family"))
    project = property(lambda s: s._dest("project"))
    language = property(lambda s: s._dest("language"))
    dbname = property(lambda s: s._dest("dbname"))
    wikiid = property(lambda s: s._dest("wikiid"))
    hostname = property(lambda s: s._dest("hostname"))
    title = property(lambda s: s._dest("title"))
    namespace = property(lambda s: s._dest("namespace"))
    fragment = property(lambda s: s._dest("fragment"))
    revision = property(lambda s: s._dest("revision"))
    diff = property(lambda s: s._dest("diff"))
    action = property(lambda s: s._dest("action"))
    special_page = property(lambda s: s._dest("special_page"))
    organization_name = property(lambda s: s._dest("organization_name"))
    service_name = property(lambda s: s._dest("service_name"))
    is_standard_project = property(lambda s: s._dest("is_standard_project"))
    page_id = property(lambda s: s._dest("page_id"))

    @property
    def destination_type(self):
        destination = self.destination
        return destination.destination_type.value if destination is not None else None
    @property
    def is_wikimedia(self) -> bool:
        destination = self.destination
        return bool(destination and destination.is_wikimedia_project)

    @property
    def is_wiki(self) -> bool:
        return self.destination_type == DestinationType.WIKI.value

    @property
    def is_external(self) -> bool:
        # kept for compatibility: this means the original syntax was an external link/url.
        return self.is_url

    @property
    def is_url(self) -> bool:
        return self.syntax_type in {
            SyntaxType.EXTERNAL_LINK.value,
            SyntaxType.BARE_URL.value,
        }

    @property
    def is_bare_url(self) -> bool:
        return self.syntax_type == SyntaxType.BARE_URL.value

    @property
    def is_wiki_url(self) -> bool:
        return self.is_url and self.is_wiki

    @property
    def is_external_url(self) -> bool:
        return self.is_url and self.destination_type == DestinationType.EXTERNAL.value

    @property
    def is_interwiki(self) -> bool:
        return self.syntax_type == SyntaxType.INTERWIKI_WIKILINK.value

    @property
    def is_local(self) -> bool:
        return self.syntax_type == SyntaxType.LOCAL_WIKILINK.value

    @property
    def is_revision(self) -> bool:
        return self.revision is not None

    @property
    def is_diff(self) -> bool:
        return self.diff is not None

    @property
    def is_action(self) -> bool:
        return self.action is not None

    @property
    def is_service(self) -> bool:
        return self.destination_type == DestinationType.SERVICE.value

    @property
    def is_tool(self) -> bool:
        return self.destination_type == DestinationType.TOOL.value

    @property
    def is_comment(self) -> bool:
        return self.in_comment

    @property
    def has_title(self) -> bool:
        return self.title is not None

    # kept as aliases for the is_* names above; some callers prefer this phrasing
    has_revision = is_revision
    has_diff = is_diff
    has_action = is_action

    @property
    def wiki(self) -> Optional[WikiInfo]:
        dbname = self.dbname
        return self._resolver.metadata.wiki_by_dbname(dbname) if dbname else None


    @property
    def canonical_url(self):
        if self.destination is None or self.status != ResolutionStatus.RESOLVED.value:
            return None
        try:
            return self._resolver.to_url(self.destination)
        except ConversionError:
            return self.destination.canonical_url
    @property
    def canonical_interwiki(self):
        if self.destination is None or self.status != ResolutionStatus.RESOLVED.value:
            return None
        try:
            return self._resolver.to_interwiki(self.destination, self._source)
        except ConversionError:
            return None
    @property
    def interwiki(self):
        return self.canonical_interwiki

    @property
    def url(self):
        return self.canonical_url

    @property
    def is_project_prefix(self) -> bool:
        return self.prefix_kind == "project"

    @property
    def is_language_prefix(self) -> bool:
        return self.prefix_kind == "language"

    @property
    def is_language_project(self) -> bool:
        return self.prefix_kind == "language_project"

    @property
    def canonical_wikilink(self):
        if self.destination is None or self.status != ResolutionStatus.RESOLVED.value:
            return None
        try:
            return self._resolver.to_local(self.destination, self._source)
        except Exception:
            return None

    def _node_offset(self) -> int:
        ancestors = self._code.get_ancestors(self._node)
        path = [*ancestors, self._node]
        offset = 0
        code = self._code

        for position, target in enumerate(path):
            for node in code.nodes:
                if node is target:
                    break
                offset += len(str(node))
            else:
                return -1

            if target is self._node:
                return offset

            next_target = path[position + 1]
            node_text = str(target)
            cursor = 0
            child_code = None
            for child in target.__children__():
                child_text = str(child)
                child_start = node_text.find(child_text, cursor)
                if child_start < 0:
                    return -1
                if child.contains(next_target):
                    offset += child_start
                    child_code = child
                    break
                cursor = child_start + len(child_text)
            if child_code is None:
                return -1
            code = child_code

        return -1

    @property
    def line_number(self) -> int:
        """Return the 1-based line number of this parsed link."""
        start = self._node_offset()
        return str(self._code).count("\n", 0, start) + 1 if start >= 0 else 0

    @property
    def line_text(self) -> Optional[str]:
        """Return the complete source line containing this parsed link."""
        text = str(self._code)
        start = self._node_offset()
        if start < 0:
            return None
        begin = text.rfind("\n", 0, start) + 1
        end = text.find("\n", start)
        return text[begin:] if end < 0 else text[begin:end]

    def matches(self, **kwargs) -> bool:
        for key, expected in kwargs.items():
            if key in _FLAG_FILTERS:
                if not self._flag(key, expected):
                    return False
                continue
            if key == "url":
                other = self._resolver.resolve_url(str(expected), self._source)
                if other.status is not ResolutionStatus.RESOLVED or self.canonical_url != other.canonical_url:
                    return False
                continue
            if key == "interwiki":
                other = self._resolver.resolve_interwiki(str(expected), self._source)
                if other.status is not ResolutionStatus.RESOLVED or self.canonical_interwiki != other.canonical_interwiki:
                    return False
                continue
            if key in {"destination", "same_page_as"}:
                target = expected
                if isinstance(target, str):
                    target_result = self._resolver.resolve(target, self._source)
                    target = target_result.destination
                if target is None or self.destination is None:
                    return False
                if key == "same_page_as":
                    if not self.destination.same_page_as(target):
                        return False
                elif self.destination != target:
                    return False
                continue
            if key.endswith("_in"):
                attr = key[:-3]
                actual = getattr(self, attr, object())
                if hasattr(actual, "value"):
                    actual = actual.value
                values = {v.value if hasattr(v, "value") else v for v in expected}
                if actual not in values:
                    return False
                continue
            actual = getattr(self, key, object())
            if hasattr(expected, "value"):
                expected = expected.value
            if hasattr(actual, "value"):
                actual = actual.value
            if actual != expected:
                return False
        return True

    def _flag(self, name: str, expected: bool) -> bool:
        destination = self.destination
        if name == "wikimedia_only":
            value = bool(destination and destination.is_wikimedia_project)
        elif name == "wiki_only":
            value = destination is not None and destination.destination_type is DestinationType.WIKI
        elif name == "external_only":
            value = destination is not None and destination.destination_type is DestinationType.EXTERNAL
        elif name == "interwiki_only":
            value = self.syntax_type == SyntaxType.INTERWIKI_WIKILINK.value
        else:
            value = self.syntax_type == SyntaxType.LOCAL_WIKILINK.value
        return value == bool(expected)

    def set_label(self, text: Optional[str]) -> None:
        if self.is_wikilink:
            new_text = f"[[{self.raw}|{text}]]" if text else f"[[{self.raw}]]"
        else:
            new_text = f"[{self.raw} {text}]" if text else f"[{self.raw}]"
        self._replace(new_text)

    def convert(self, to: str, source: Any = None, long_project_prefix: bool = False) -> "WMLink":
        # keep the common conversion entry point tiny and obvious
        target = to.casefold()
        if target in {"url", "external"}:
            self.set_url()
        elif target in {"interwiki", "iw"}:
            self.set_interwiki(source, long_project_prefix=long_project_prefix)
        elif target in {"local", "wikilink"}:
            self.set_local(source)
        else:
            raise ValueError("to must be 'url', 'interwiki', or 'local'")
        return self

    def set_interwiki(self, source: Any = None, long_project_prefix: bool = False) -> None:
        self._require_clickable_link()
        destination = self._require_resolved()
        target = self._resolver.to_interwiki(destination, source or self._source, long_project_prefix=long_project_prefix)
        self._replace_wikilink(target)

    def set_url(self) -> None:
        self._require_clickable_link()
        destination = self._require_resolved()
        url = self._resolver.to_url(destination)
        label = self.label
        if self.is_external_link and not self._node.brackets:
            new_text = url
        elif label:
            new_text = f"[{url} {label}]"
        else:
            new_text = f"[{url}]"
        self._replace(new_text)

    def set_local(self, source: Any = None) -> None:
        self._require_clickable_link()
        destination = self._require_resolved()
        target = self._resolver.to_local(destination, source or self._source)
        self._replace_wikilink(target, leading_colon=False)

    def _require_clickable_link(self) -> None:
        if self.is_category_link:
            raise ConversionError("category membership is not a clickable link; use [[:Category:...]] for a visible link")
        if self.is_file_link:
            raise ConversionError("file transclusion is not a clickable link; use [[:File:...]] for a visible link")

    def _require_resolved(self) -> Destination:
        result = self._resolve()
        if result.status is not ResolutionStatus.RESOLVED or result.destination is None:
            raise ConversionError(f"can't convert an unresolved link (status={result.status.value}: {result.reason})")
        return result.destination

    def _replace_wikilink(self, target: str, leading_colon: bool = True) -> None:
        label = self.label
        prefix = ":" if leading_colon else ""
        body = f"{prefix}{target}|{label}" if label else f"{prefix}{target}"
        self._replace(f"[[{body}]]")

    def _replace(self, new_text: str) -> None:
        try:
            self._code.index(self._node, recursive=True)
        except ValueError as exc:
            raise ConversionError("this link node is no longer attached; re-parse the text") from exc
        self._code.replace(self._node, new_text)
        parsed = mwparserfromhell.parse(new_text)
        if len(parsed.nodes) == 1:
            self._node = parsed.nodes[0]
        if self._comment_node is not None:
            self._comment_node.contents = str(self._code)
        self._result = None

    def as_dict(self) -> dict:
        data = self.result.as_dict()
        data.update({
            "original": self.original,
            "raw": self.raw,
            "label": self.label,
            "link_type": self.link_type,
            "is_self_link": self.is_self_link,
            "page_id": self.page_id,
            "index": self.index,
            "is_wikilink": self.is_wikilink,
            "is_external_link": self.is_external_link,
            "is_wikimedia": self.is_wikimedia,
            "in_comment": self.in_comment,
            "leading_colon": self.leading_colon,
            "is_category_link": self.is_category_link,
            "is_file_link": self.is_file_link,
        })
        return data

    def __repr__(self) -> str:
        return f"<WMLink {self.original!r} status={self.status!r}>"
