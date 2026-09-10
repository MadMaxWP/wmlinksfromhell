"""URL parsing/rendering for Wikimedia wikis and related services."""

from __future__ import annotations

from typing import Optional
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from . import constants
from .constants import CHAPTER_HOSTS, COMMON_NAMESPACE_NAMES, SERVICE_PREFIXES
from .destination import Destination, normalize_title, split_namespace
from .exceptions import ConversionError
from .metadata import MetadataStore
from .models import DestinationType, WikiInfo
from .operations import special_operation_destination

_OPERATION_PARAMS = {"title", "oldid", "diff", "action", "curid"}


_BAD_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _unquote_strict(raw: str) -> str:
    if _BAD_PERCENT_RE.search(raw):
        raise ValueError("invalid percent-encoding")
    return unquote(raw, errors="strict")


def decode_title_component(raw: str) -> str:
    """decode a MediaWiki title component once and normalize underscores."""
    return normalize_title(_unquote_strict(raw))


def decode_fragment(raw: str) -> str:
    """decode a URL fragment without applying title/underscore normalization."""
    return _unquote_strict(raw)


def encode_title_component(title: str) -> str:
    return quote(title.replace(" ", "_"), safe=":/,()')")


def _normalize_namespace(namespace: Optional[str], metadata: MetadataStore, dbname: Optional[str]) -> Optional[str]:
    if not namespace:
        return None
    aliases = metadata.namespace_aliases(dbname)
    return aliases.get(namespace.casefold(), namespace)


def _parse_wiki_title(wiki: WikiInfo, title: str, metadata: MetadataStore) -> tuple[Optional[str], str]:
    namespace, bare = split_namespace(title, metadata.namespace_names(wiki.dbname) or COMMON_NAMESPACE_NAMES)
    return _normalize_namespace(namespace, metadata, wiki.dbname), bare


def _query_parts(query: str) -> tuple[tuple[str, str], dict[str, str], tuple[tuple[str, str], ...]]:
    pairs = tuple(parse_qsl(query, keep_blank_values=True))
    values = dict(pairs)
    extras = tuple((key, value) for key, value in pairs if key not in _OPERATION_PARAMS)
    return pairs, values, extras


def _wiki_destination(
    wiki: WikiInfo,
    title: Optional[str],
    fragment: Optional[str],
    query_pairs: tuple[tuple[str, str], ...],
    query: dict[str, str],
    metadata: MetadataStore,
) -> Destination:
    if title is not None:
        operation = special_operation_destination(
            wiki,
            title,
            fragment,
            metadata,
            tuple((k, v) for k, v in query_pairs if k not in _OPERATION_PARAMS),
        )
        if operation is not None:
            return operation
    namespace, bare = _parse_wiki_title(wiki, title or "", metadata) if title is not None else (None, None)
    revision = _as_revision(query.get("oldid"))
    diff = _as_diff(query.get("diff"))
    page_id = _as_revision(query.get("curid"))
    extras = [(k, v) for k, v in query_pairs if k not in _OPERATION_PARAMS]
    if "oldid" in query and revision is None:
        extras.append(("oldid", query["oldid"]))
    return Destination(
        destination_type=DestinationType.WIKI,
        family=wiki.family,
        project=wiki.project,
        language=wiki.language,
        dbname=wiki.dbname,
        wikiid=wiki.wikiid,
        hostname=wiki.hostname,
        title=bare,
        namespace=namespace,
        fragment=fragment,
        revision=revision,
        diff=diff,
        action=query.get("action"),
        page_id=page_id,
        query_parameters=tuple(extras),
        metadata_source=wiki.metadata_source,
        is_multilingual=wiki.is_multilingual,
        is_standard_project=wiki.is_standard_project,
        is_wikimedia_project=True,
    )


def parse_url(url: str, metadata: MetadataStore) -> tuple[Optional[Destination], str]:
    """parse one URL without performing network access."""
    original = url
    if url.startswith("//"):
        url = "https:" + url
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        return None, f"malformed URL: {exc}"

    # Explicit non-http URLs are still URLs; they are just ordinary external
    # destinations for this Wikimedia-aware resolver.
    if parts.scheme not in ("http", "https"):
        if parts.scheme:
            return Destination(
                destination_type=DestinationType.EXTERNAL,
                hostname=parts.hostname,
                fragment=parts.fragment or None,
                canonical_url=original,
            ), "external URL"
        return None, "not a URL"
    if not parts.hostname:
        return None, "URL has no hostname"

    try:
        fragment = decode_fragment(parts.fragment) if parts.fragment else None
    except (ValueError, UnicodeDecodeError):
        return None, "malformed percent-encoding in fragment"

    if parts.hostname.casefold().rstrip(".") in constants.WIKIMEDIA_PORTAL_HOSTS:
        return Destination(
            destination_type=DestinationType.EXTERNAL,
            hostname=parts.hostname,
            fragment=fragment,
            canonical_url=urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, parts.fragment)),
            is_wikimedia_project=True,
            metadata_source="bootstrap",
        ), "Wikimedia portal"
    wiki = metadata.resolve_wikimedia_hostname(parts.hostname)
    if wiki is not None:
        if parts.path in {"", "/"} and not parts.query:
            return Destination(
                destination_type=DestinationType.WIKI,
                family=wiki.family,
                project=wiki.project,
                language=wiki.language,
                dbname=wiki.dbname,
                wikiid=wiki.wikiid,
                hostname=wiki.hostname,
                title=None,
                fragment=fragment,
                canonical_url=urlunsplit(("https", wiki.hostname, "/", "", parts.fragment)),
                metadata_source=wiki.metadata_source,
                is_multilingual=wiki.is_multilingual,
                is_standard_project=wiki.is_standard_project,
                is_wikimedia_project=True,
            ), "resolved wiki root"
        article_prefix = wiki.article_path.split("$1", 1)[0]
        if parts.path.startswith(article_prefix) and len(parts.path) > len(article_prefix):
            try:
                title = decode_title_component(parts.path[len(article_prefix):])
            except (ValueError, UnicodeDecodeError):
                return None, "malformed percent-encoding in title"
            if not title:
                return None, "empty title"
            query_pairs, query, _ = _query_parts(parts.query)
            return _wiki_destination(wiki, title, fragment, query_pairs, query, metadata), "resolved"

        script_paths = {
            wiki.script_path,
            "/index.php",
            "/wiki.phtml",
            "/w/wiki.phtml",
            "/w/index.php",
        }
        if parts.path in script_paths:
            query_pairs, query, _ = _query_parts(parts.query)
            if not any(key in query for key in ("title", "oldid", "diff", "curid", "action")):
                return None, "index.php URL without a page target or operation"
            title = None
            if "title" in query:
                try:
                    title = decode_title_component(query["title"])
                except (ValueError, UnicodeDecodeError):
                    return None, "malformed percent-encoding in title"
                if not title:
                    return None, "empty title"
            return _wiki_destination(wiki, title, fragment, query_pairs, query, metadata), "resolved"
        return None, "Wikimedia wiki host recognized but URL path is not a known wiki route"

    dtype = metadata.related_destination_type(parts.hostname)
    if dtype in {DestinationType.SERVICE, DestinationType.TOOL, DestinationType.ORGANIZATION}:
        return _parse_related_url(parts.hostname, parts.path, parts.query, fragment, dtype, metadata), "resolved"

    if metadata.is_wikimedia_hostname(parts.hostname):
        return Destination(
            destination_type=DestinationType.UNKNOWN,
            hostname=parts.hostname,
            fragment=fragment,
            canonical_url=urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, parts.fragment)),
            is_wikimedia_project=True,
            metadata_source="missing",
        ), "Wikimedia-related hostname recognized, but exact metadata is unavailable"

    return None, "hostname is not a known Wikimedia-related site"


def _decode_related_path(path: str) -> Optional[str]:
    if not path:
        return None
    try:
        return decode_title_component(path.lstrip("/"))
    except (ValueError, UnicodeDecodeError):
        return path.lstrip("/") or None


def _parse_related_url(
    hostname: str,
    path: str,
    query: str,
    fragment: Optional[str],
    dtype: DestinationType,
    metadata: MetadataStore,
) -> Destination:
    host = hostname.casefold().rstrip(".")
    canonical_url = urlunsplit(("https", hostname, path, query, quote(fragment) if fragment else ""))

    for prefix, entry in metadata.interwiki_map().entries.items():
        entry_host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
        if entry_host.casefold().rstrip(".") != host:
            continue
        if entry.destination_type is DestinationType.ORGANIZATION:
            return Destination(
                destination_type=DestinationType.ORGANIZATION,
                hostname=hostname,
                title=_decode_related_path(path),
                organization_name=entry.prefix,
                fragment=fragment,
                query_parameters=tuple(parse_qsl(query, keep_blank_values=True)),
                canonical_url=canonical_url,
                is_wikimedia_project=True,
                metadata_source="live",
            )
        if entry.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}:
            return Destination(
                destination_type=entry.destination_type,
                hostname=hostname,
                title=_decode_related_path(path),
                service_name=entry.sitename or entry.prefix,
                fragment=fragment,
                query_parameters=tuple(parse_qsl(query, keep_blank_values=True)),
                canonical_url=canonical_url,
                is_wikimedia_project=True,
                metadata_source="live",
            )

    for info in SERVICE_PREFIXES.values():
        if host == info["hostname"].casefold().rstrip("."):
            return Destination(
                destination_type=dtype,
                hostname=hostname,
                title=_decode_related_path(path),
                service_name=info["name"],
                fragment=fragment,
                query_parameters=tuple(parse_qsl(query, keep_blank_values=True)),
                canonical_url=canonical_url,
                is_wikimedia_project=True,
                metadata_source="bootstrap",
            )

    for prefix, host_value in CHAPTER_HOSTS.items():
        if host == host_value.casefold().rstrip("."):
            return Destination(
                destination_type=DestinationType.ORGANIZATION,
                hostname=hostname,
                title=_decode_related_path(path),
                organization_name=prefix,
                fragment=fragment,
                query_parameters=tuple(parse_qsl(query, keep_blank_values=True)),
                canonical_url=canonical_url,
                is_wikimedia_project=True,
                metadata_source="bootstrap",
            )

    return Destination(
        destination_type=dtype,
        hostname=hostname,
        title=_decode_related_path(path),
        fragment=fragment,
        query_parameters=tuple(parse_qsl(query, keep_blank_values=True)),
        canonical_url=canonical_url,
        is_wikimedia_project=True,
        metadata_source="bootstrap",
    )


def _as_revision(value: Optional[str]) -> Optional[int]:
    if value is None or not value.isdigit():
        return None
    return int(value)


def _as_diff(value: Optional[str]):
    if value is None:
        return None
    return int(value) if value.isdigit() else value


def build_url(destination: Destination, metadata: MetadataStore) -> str:
    if destination.destination_type in {DestinationType.WIKI, DestinationType.SPECIAL}:
        if not destination.dbname:
            raise ConversionError("destination has no dbname; can't build a Wikimedia URL")
        wiki = metadata.wiki_by_dbname(destination.dbname)
        if wiki is None:
            raise ConversionError(f"no metadata known for dbname {destination.dbname!r}")
        fragment = quote(destination.fragment) if destination.fragment else ""
        if destination.revision is not None or destination.diff is not None or destination.action is not None or destination.page_id is not None or destination.query_parameters:
            params = [] if destination.full_title is None else [("title", destination.full_title)]
            if destination.page_id is not None:
                params.append(("curid", str(destination.page_id)))
            if destination.revision is not None:
                params.append(("oldid", str(destination.revision)))
            if destination.diff is not None:
                params.append(("diff", str(destination.diff)))
            if destination.action is not None:
                params.append(("action", destination.action))
            params.extend(destination.query_parameters)
            return urlunsplit(("https", wiki.hostname, wiki.script_path, urlencode(params), fragment))
        if destination.full_title is None:
            raise ConversionError("destination has no title")
        path = wiki.article_path.replace("$1", encode_title_component(destination.full_title))
        return urlunsplit(("https", wiki.hostname, path, urlencode(destination.query_parameters), fragment))

    if destination.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}:
        if not destination.hostname:
            raise ConversionError("service destination has no hostname")
        base = next(
            (info["url"] for info in SERVICE_PREFIXES.values() if info["hostname"].casefold() == destination.hostname.casefold()),
            None,
        )
        if base is None:
            for entry in metadata.interwiki_map().entries.values():
                if entry.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}:
                    entry_host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
                    if entry_host.casefold() == destination.hostname.casefold():
                        base = entry.url
                        if destination.service_name and destination.service_name.casefold() == entry.prefix.casefold():
                            break
        if base:
            target = destination.title or ""
            if "$1" in base:
                rendered = base.replace("$1", quote(target, safe=":/,()'"))
                if destination.query_parameters:
                    separator = "&" if "?" in rendered else "?"
                    rendered += separator + urlencode(destination.query_parameters)
                if destination.fragment:
                    rendered += "#" + quote(destination.fragment)
                return rendered
        return destination.canonical_url or urlunsplit(("https", destination.hostname, "/" + (destination.title or ""), urlencode(destination.query_parameters), quote(destination.fragment) if destination.fragment else ""))

    if destination.destination_type is DestinationType.ORGANIZATION:
        base = None
        if destination.organization_name:
            entry = metadata.global_interwiki_entry(destination.organization_name)
            if entry is not None:
                base = entry.url
        if base is None and destination.canonical_url:
            base = destination.canonical_url
        if base:
            if "$1" in base:
                rendered = base.replace("$1", quote(destination.title or "", safe=":/,()'"))
            else:
                rendered = base
            if destination.query_parameters:
                separator = "&" if "?" in rendered else "?"
                rendered += separator + urlencode(destination.query_parameters)
            if destination.fragment:
                rendered += "#" + quote(destination.fragment)
            return rendered
        host = destination.hostname
        if destination.organization_name:
            host = CHAPTER_HOSTS.get(destination.organization_name.casefold(), host)
        if not host:
            raise ConversionError("organization destination has no hostname")
        path = "/wiki/" + encode_title_component(destination.title) if destination.title else "/wiki/"
        return urlunsplit(("https", host, path, urlencode(destination.query_parameters), quote(destination.fragment) if destination.fragment else ""))

    if destination.destination_type is DestinationType.EXTERNAL:
        if not destination.canonical_url:
            raise ConversionError("external destination has no URL")
        return destination.canonical_url

    raise ConversionError(f"can't build a Wikimedia URL for {destination.destination_type.value} destination")
