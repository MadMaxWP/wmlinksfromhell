"""Wikimedia interwiki chain parsing and rendering."""

from __future__ import annotations

from typing import NamedTuple, Optional
from urllib.parse import unquote, urlsplit

from . import constants
from .constants import (
    CHAPTER_FIXED_URLS,
    CHAPTER_HOSTS,
    COMMON_NAMESPACE_NAMES,
    MULTILINGUAL_FAMILY_NAMES,
    PREFERRED_FAMILY_PREFIX,
    PREFERRED_SERVICE_PREFIX,
    PREFERRED_SINGLE_WIKI_PREFIX,
)
from .destination import Destination, normalize_title, split_namespace
from .exceptions import ConversionError
from .metadata import MetadataStore
from .models import DestinationType, InterwikiEntry, ResolutionStatus, WikiInfo
from .operations import special_operation_destination


class ChainResult(NamedTuple):
    destination: Optional[Destination]
    status: ResolutionStatus
    reason: str
    prefix: Optional[str] = None
    canonical_prefix: Optional[str] = None
    prefix_kind: Optional[str] = None


def _local_destination(
    title: str,
    fragment: Optional[str],
    source: Optional[WikiInfo],
    metadata: MetadataStore,
) -> Destination:
    namespace, bare = split_namespace(
        title,
        metadata.namespace_names(source.dbname if source else None) or COMMON_NAMESPACE_NAMES,
    )
    if namespace:
        namespace = metadata.namespace_aliases(source.dbname if source else None).get(
            namespace.casefold(), namespace
        )
    return Destination(
        destination_type=DestinationType.WIKI,
        family=source.family if source else None,
        project=source.project if source else None,
        language=source.language if source else None,
        dbname=source.dbname if source else None,
        wikiid=source.wikiid if source else None,
        hostname=source.hostname if source else None,
        title=normalize_title(bare),
        namespace=namespace,
        fragment=fragment,
        metadata_source=source.metadata_source if source else None,
        is_multilingual=source.is_multilingual if source else None,
        is_standard_project=source.is_standard_project if source else None,
        is_wikimedia_project=source is not None,
    )


def _preferred_family_prefix(family: str) -> str:
    return PREFERRED_FAMILY_PREFIX.get(family.casefold(), family)


def _preferred_single_prefix(dbname: str) -> str:
    return PREFERRED_SINGLE_WIKI_PREFIX.get(dbname, dbname)


def _default_project_language(
    family: str,
    metadata: MetadataStore,
    source: Optional[WikiInfo] = None,
) -> Optional[str]:
    family = family.casefold()

    # A short project prefix normally carries the source language when it
    # switches to another family. Multilingual sources use English, and a
    # shortcut naming the source family itself also uses the English project.
    if source is not None:
        source_family = source.family.casefold()
        if source.is_multilingual or source_family == family:
            if metadata.wiki_for_family_language(family, "en") is not None:
                return "en"
        elif family in constants.MULTILINGUAL_FAMILIES:
            language = source.language.casefold()
            if metadata.wiki_for_family_language(family, language) is not None:
                return language

    if metadata.wiki_for_family_language(family, "en") is not None:
        return "en"
    languages = constants.BOOTSTRAP_LANGS_BY_FAMILY.get(family, ())
    return languages[0] if languages else None


def _canonical_chain(prefixes: list[str], kinds: list[str], destinations: list[Optional[WikiInfo]], metadata: Optional[MetadataStore] = None) -> str:
    if not prefixes:
        return ""
    if len(prefixes) == 1:
        if kinds[0] == "project" and destinations[0] is not None:
            if destinations[0].dbname in PREFERRED_SINGLE_WIKI_PREFIX:
                return _preferred_single_prefix(destinations[0].dbname)
            if prefixes[0].casefold() in constants.FAMILY_PREFIXES:
                return _preferred_family_prefix(destinations[0].family)
            if prefixes[0].casefold() in constants.SINGLE_WIKI_PREFIXES:
                return prefixes[0]
            if not destinations[0].is_standard_project:
                return prefixes[0]
            return _preferred_family_prefix(destinations[0].family)
        return prefixes[0]
    parts: list[str] = []
    for prefix, kind, destination in zip(prefixes, kinds, destinations):
        if kind == "project" and destination is not None:
            key = prefix.casefold()
            if key in constants.FAMILY_PREFIXES or key in constants.MULTILINGUAL_FAMILY_NAMES:
                parts.append(_preferred_family_prefix(destination.family))
            elif key in constants.SINGLE_WIKI_PREFIXES:
                parts.append(prefix)
            else:
                parts.append(_preferred_family_prefix(destination.family))
        else:
            parts.append(prefix)
    if len(parts) == 2 and kinds == ["project", "language"] and destinations[-1] is not None and metadata is not None:
        parts[1] = destinations[-1].language
    return ":".join(parts)


def _build_destination(
    wiki: WikiInfo,
    title: str,
    fragment: Optional[str],
    metadata: MetadataStore,
) -> Destination:
    namespace, bare = split_namespace(
        title,
        metadata.namespace_names(wiki.dbname) or COMMON_NAMESPACE_NAMES,
    )
    if namespace:
        namespace = metadata.namespace_aliases(wiki.dbname).get(namespace.casefold(), namespace)
    return Destination(
        destination_type=DestinationType.WIKI,
        family=wiki.family,
        project=wiki.project,
        language=wiki.language,
        dbname=wiki.dbname,
        wikiid=wiki.wikiid,
        hostname=wiki.hostname,
        title=normalize_title(bare),
        namespace=namespace,
        fragment=fragment,
        metadata_source=wiki.metadata_source,
        is_multilingual=wiki.is_multilingual,
        is_standard_project=wiki.is_standard_project,
        is_wikimedia_project=True,
    )


def _fixed_entry_destination(entry: InterwikiEntry, fragment: Optional[str], metadata: MetadataStore) -> Optional[Destination]:
    host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
    if entry.destination_type is DestinationType.ORGANIZATION:
        path = unquote(urlsplit(entry.url).path).rstrip("/")
        title = normalize_title(path.rsplit("/", 1)[-1]) if path else None
        wiki = metadata.resolve_wikimedia_hostname(host)
        return Destination(
            destination_type=DestinationType.ORGANIZATION,
            family=wiki.family if wiki else None,
            project=wiki.project if wiki else None,
            language=wiki.language if wiki else None,
            dbname=wiki.dbname if wiki else None,
            wikiid=wiki.wikiid if wiki else None,
            hostname=host,
            title=title,
            organization_name=entry.prefix,
            fragment=fragment,
            canonical_url=entry.url,
            metadata_source="live",
            is_multilingual=wiki.is_multilingual if wiki else None,
            is_standard_project=wiki.is_standard_project if wiki else None,
            is_wikimedia_project=True,
        )
    wiki = metadata.resolve_wikimedia_hostname(host)
    if wiki is not None:
        parsed = urlsplit(entry.url)
        path = unquote(parsed.path)
        article_prefix = wiki.article_path.split("$1", 1)[0]
        title = path[len(article_prefix):].replace("_", " ").strip() if path.startswith(article_prefix) else None
        return Destination(
            destination_type=entry.destination_type or DestinationType.WIKI,
            family=wiki.family,
            project=wiki.project,
            language=wiki.language,
            dbname=wiki.dbname,
            wikiid=wiki.wikiid,
            hostname=wiki.hostname,
            title=title,
            fragment=fragment,
            canonical_url=entry.url if "$1" not in entry.url else None,
            metadata_source="live",
            is_multilingual=wiki.is_multilingual,
            is_standard_project=wiki.is_standard_project,
            is_wikimedia_project=True,
        )
    dtype = entry.destination_type
    if dtype in {DestinationType.SERVICE, DestinationType.TOOL}:
        return Destination(
            destination_type=dtype,
            hostname=host,
            title=None,
            service_name=entry.sitename or entry.prefix,
            fragment=fragment,
            canonical_url=entry.url,
            metadata_source="live",
            is_wikimedia_project=True,
        )
    return None


def resolve_chain(raw_target: str, source: Optional[WikiInfo], metadata: MetadataStore, page_title: Optional[str] = None) -> ChainResult:
    text = raw_target[1:] if raw_target.startswith(":") else raw_target
    if not text:
        return ChainResult(None, ResolutionStatus.MALFORMED, "empty link target")

    if "#" in text:
        text, fragment = text.split("#", 1)
        fragment = fragment.strip() or None
    else:
        fragment = None

    if text.startswith(("/", "../")):
        if page_title and source is not None:
            if text.startswith("/"):
                relative_title = f"{page_title}{text}"
                return ChainResult(
                    _local_destination(relative_title, fragment, source, metadata),
                    ResolutionStatus.RESOLVED,
                    "resolved local subpage link from source page context",
                )
            parts = page_title.split("/")
            while text.startswith("../") and len(parts) > 1:
                parts.pop()
                text = text[3:]
            if text.startswith("../") or not parts:
                return ChainResult(
                    None,
                    ResolutionStatus.CONTEXT_REQUIRED,
                    "relative link goes above the known page path",
                )
            relative_title = "/".join(parts + ([text] if text else []))
            return ChainResult(
                _local_destination(relative_title, fragment, source, metadata),
                ResolutionStatus.RESOLVED,
                "resolved local relative link from source page context",
            )
        return ChainResult(
            None,
            ResolutionStatus.CONTEXT_REQUIRED,
            "relative link needs source page context",
        )

    if not text:
        if fragment and page_title and source is not None:
            return ChainResult(
                _local_destination(page_title, fragment, source, metadata),
                ResolutionStatus.RESOLVED,
                "resolved local page anchor from source page context",
            )
        if fragment:
            return ChainResult(
                None,
                ResolutionStatus.CONTEXT_REQUIRED,
                "local anchor needs source page context",
            )
        return ChainResult(None, ResolutionStatus.MALFORMED, "empty link target")

    segments = text.split(":")
    empty_title = len(segments) > 1 and not segments[-1].strip()

    current = source
    if empty_title and current is not None and metadata.is_namespace(segments[0].strip(), current):
        return ChainResult(
            None,
            ResolutionStatus.MALFORMED,
            "namespace has no title",
            segments[0].strip(),
            segments[0].strip(),
            "namespace",
        )
    if empty_title:
        segments.pop()
    destination_wiki: Optional[WikiInfo] = None
    prefix_parts: list[str] = []
    prefix_kinds: list[str] = []
    prefix_destinations: list[Optional[WikiInfo]] = []
    i = 0

    while i < len(segments):
        segment = segments[i].strip()
        if not segment:
            return ChainResult(None, ResolutionStatus.MALFORMED, "empty segment in prefix chain")

        active_map = metadata.interwiki_map(current)
        key = segment.casefold()

        # a language prefix is interpreted in the current wiki family when
        # that family has a matching wiki. this is more specific than a
        # conflicting generic interwiki entry such as bho -> enwiki.
        language_wiki = None
        if current is not None:
            family = _default_family(current)
            language_wiki = metadata.wiki_for_family_language(family, segment)
        if language_wiki is not None:
            prefix_parts.append(segment)
            prefix_kinds.append("language")
            prefix_destinations.append(language_wiki)
            destination_wiki = language_wiki
            current = language_wiki
            i += 1
            continue

        entry = active_map.get(segment)
        family = active_map.family_prefixes.get(key) or (key if key in constants.MULTILINGUAL_FAMILY_NAMES and i + 2 < len(segments) and metadata.is_known_language(segments[i + 1]) else None)
        single = active_map.single_wiki_prefixes.get(key)
        service = active_map.service_prefixes.get(key)
        chapter = active_map.chapter_prefixes.get(key)

        # special pages such as Special:Diff and Special:PermanentLink are operations,
        # not ordinary pages, so check them before the normal namespace path.
        if i == 0 and metadata.is_namespace(segment, current):
            if source is not None and segment.casefold() == "special":
                operation = special_operation_destination(
                    source, text, fragment, metadata
                )
                if operation is not None:
                    return ChainResult(
                        operation,
                        ResolutionStatus.RESOLVED,
                        "resolved local special-page operation",
                    )
            return ChainResult(
                _local_destination(text, fragment, source, metadata),
                ResolutionStatus.RESOLVED,
                "matched a local namespace",
            )

        if entry is not None and "$1" not in entry.url and family is None:
            if i != len(segments) - 1:
                return ChainResult(
                    None,
                    ResolutionStatus.UNSUPPORTED,
                    f"fixed interwiki prefix {entry.prefix!r} does not accept a target",
                    entry.prefix,
                    entry.prefix,
                    "project",
                )
            fixed = _fixed_entry_destination(entry, fragment, metadata)
            if fixed is not None:
                return ChainResult(
                    fixed,
                    ResolutionStatus.RESOLVED,
                    "matched a fixed Wikimedia interwiki destination",
                    entry.prefix,
                    entry.prefix,
                    "project",
                )
            return ChainResult(
                None,
                ResolutionStatus.METADATA_MISSING,
                f"could not resolve fixed interwiki prefix {entry.prefix!r} with current metadata",
                entry.prefix,
                entry.prefix,
                "project",
            )

        if service or (entry is not None and entry.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}):
            info = service
            used_prefix = segment
            if info is None and entry is not None:
                info = {
                    "hostname": urlsplit(entry.url.replace("$1", "x")).hostname or "",
                    "name": entry.sitename or entry.prefix,
                    "destination_type": (entry.destination_type or DestinationType.SERVICE).value,
                    "url": entry.url,
                }
                used_prefix = entry.prefix
            target = ":".join(segments[i + 1:]).strip() or None
            dtype = DestinationType(info.get("destination_type", "service"))
            return ChainResult(
                Destination(
                    destination_type=dtype,
                    hostname=info["hostname"],
                    title=target,
                    service_name=info.get("name"),
                    fragment=fragment,
                    metadata_source="live" if active_map.entries else "bootstrap",
                    is_wikimedia_project=True,
                ),
                ResolutionStatus.RESOLVED,
                "matched a Wikimedia service/tool prefix",
                ":".join(prefix_parts + [used_prefix]),
                used_prefix,
                "service",
            )

        if entry is not None and entry.destination_type is DestinationType.ORGANIZATION:
            target = ":".join(segments[i + 1:]).strip() or None
            return ChainResult(
                Destination(
                    destination_type=DestinationType.ORGANIZATION,
                    hostname=urlsplit(entry.url.replace("$1", "x")).hostname or None,
                    title=target,
                    organization_name=entry.prefix,
                    fragment=fragment,
                    canonical_url=entry.url if target is None and "$1" not in entry.url else None,
                    metadata_source="live" if active_map.entries else "bootstrap",
                    is_wikimedia_project=True,
                ),
                ResolutionStatus.RESOLVED,
                "matched a Wikimedia organization/chapter prefix",
                entry.prefix,
                entry.prefix,
                "organization",
            )

        if entry is not None and not family and not single:
            if entry.destination_dbname:
                single = entry.destination_dbname
            elif entry.language and not entry.destination_dbname:
                family = _default_family(current)
                language = str(entry.language).casefold()
                wiki = metadata.wiki_for_family_language(family, language)
                if wiki is None:
                    return ChainResult(
                        None,
                        ResolutionStatus.METADATA_MISSING,
                        f"no cached wiki metadata for {family}/{language}; update metadata explicitly",
                        entry.prefix,
                        entry.prefix,
                        "language",
                    )
                prefix_parts.append(entry.prefix)
                prefix_kinds.append("language")
                prefix_destinations.append(wiki)
                destination_wiki = wiki
                current = wiki
                i += 1
                continue

        # wikimedia family prefix, optionally followed by a language code.
        if family:
            if i + 1 < len(segments) and metadata.is_known_language(segments[i + 1]):
                language = segments[i + 1].casefold()
                wiki = metadata.wiki_for_family_language(family, language)
                if wiki is None:
                    return ChainResult(
                        None,
                        ResolutionStatus.METADATA_MISSING,
                        f"no cached wiki metadata for {family}/{language}; update metadata explicitly",
                        segment,
                        _preferred_family_prefix(family) + ":" + language,
                        "language_project",
                    )
                prefix_parts.extend((segment, segments[i + 1]))
                prefix_kinds.extend(("project", "language"))
                prefix_destinations.extend((wiki, wiki))
                destination_wiki = wiki
                current = wiki
                i += 2
                continue
            default_language = _default_project_language(family, metadata, current)
            wiki = metadata.wiki_for_family_language(family, default_language) if default_language else None
            if wiki is None and current is None:
                return ChainResult(
                    None,
                    ResolutionStatus.CONTEXT_REQUIRED,
                    f"project prefix {segment!r} needs a known project language",
                    segment,
                    _preferred_family_prefix(family),
                    "project",
                )
            if wiki is None:
                return ChainResult(
                    None,
                    ResolutionStatus.METADATA_MISSING,
                    f"no cached wiki metadata for {family}/{current.language}; update metadata explicitly",
                    segment,
                    _preferred_family_prefix(family),
                    "project",
                )
            prefix_parts.append(segment)
            prefix_kinds.append("project")
            prefix_destinations.append(wiki)
            destination_wiki = wiki
            current = wiki
            i += 1
            continue

        # language prefix. when it is immediately followed by a project prefix,
        # the pair is self-contained and can be resolved without a source wiki.
        if metadata.is_known_language(segment):
            if i + 1 < len(segments):
                next_key = segments[i + 1].casefold()
                next_family = active_map.family_prefixes.get(next_key)
                if next_family:
                    wiki = metadata.wiki_for_family_language(next_family, segment)
                    if wiki is None:
                        return ChainResult(
                            None,
                            ResolutionStatus.METADATA_MISSING,
                            f"no cached wiki metadata for {next_family}/{segment}; update metadata explicitly",
                            segment + ":" + segments[i + 1],
                            segment + ":" + _preferred_family_prefix(next_family),
                            "language_project",
                        )
                    prefix_parts.extend((segment, segments[i + 1]))
                    prefix_kinds.extend(("language", "project"))
                    prefix_destinations.extend((wiki, wiki))
                    destination_wiki = wiki
                    current = wiki
                    i += 2
                    continue
            if current is None:
                return ChainResult(
                    None,
                    ResolutionStatus.CONTEXT_REQUIRED,
                    f"language prefix {segment!r} needs source wiki context",
                    segment,
                    segment,
                    "language",
                )
            family = _default_family(current)
            wiki = metadata.wiki_for_family_language(family, segment)
            if wiki is None:
                return ChainResult(
                    None,
                    ResolutionStatus.METADATA_MISSING,
                    f"no cached wiki metadata for {family}/{segment}; update metadata explicitly",
                    segment,
                    segment,
                    "language",
                )
            prefix_parts.append(segment)
            prefix_kinds.append("language")
            prefix_destinations.append(wiki)
            destination_wiki = wiki
            current = wiki
            i += 1
            continue

        if single:
            wiki = metadata.wiki_by_dbname(single)
            if wiki is None:
                return ChainResult(
                    None,
                    ResolutionStatus.METADATA_MISSING,
                    f"no metadata for dbname {single!r}",
                    segment,
                    segment,
                    "project",
                )
            prefix_parts.append(segment)
            prefix_kinds.append("project")
            prefix_destinations.append(wiki)
            destination_wiki = wiki
            current = wiki
            i += 1
            continue

        if chapter:
            fixed_url = CHAPTER_FIXED_URLS.get(key)
            if fixed_url:
                if i != len(segments) - 1:
                    return ChainResult(
                        None,
                        ResolutionStatus.UNSUPPORTED,
                        f"fixed chapter prefix {segment!r} does not accept a target",
                        segment,
                        segment,
                        "organization",
                    )
                fixed = _fixed_entry_destination(
                    InterwikiEntry(
                        prefix=segment,
                        url=fixed_url,
                        destination_type=DestinationType.ORGANIZATION,
                    ),
                    fragment,
                    metadata,
                )
                return ChainResult(
                    fixed,
                    ResolutionStatus.RESOLVED,
                    "matched a fixed Wikimedia chapter destination",
                    segment,
                    segment,
                    "organization",
                )
            target = ":".join(segments[i + 1:]).strip() or chapter
            return ChainResult(
                Destination(
                    destination_type=DestinationType.ORGANIZATION,
                    organization_name=segment,
                    title=target,
                    hostname=CHAPTER_HOSTS.get(key),
                    fragment=fragment,
                    metadata_source="bootstrap",
                    is_wikimedia_project=True,
                ),
                ResolutionStatus.RESOLVED,
                "matched a Wikimedia chapter/organization prefix",
                segment,
                segment,
                "organization",
            )

        break

    if destination_wiki is None:
        if source is not None:
            operation = special_operation_destination(source, text, fragment, metadata)
            if operation is not None:
                return ChainResult(
                    operation,
                    ResolutionStatus.RESOLVED,
                    "resolved local special-page operation",
                )
        return ChainResult(
            _local_destination(text, fragment, source, metadata),
            ResolutionStatus.RESOLVED,
            "no interwiki prefix matched; treated as local",
        )

    title = ":".join(segments[i:]).strip() if i < len(segments) else ""
    if not title and empty_title and destination_wiki is not None:
        title = "Main Page"

    if not title:
        return ChainResult(
            None,
            ResolutionStatus.MALFORMED,
            "interwiki prefix has no title",
            ":".join(prefix_parts) or None,
            _canonical_chain(prefix_parts, prefix_kinds, prefix_destinations, metadata) or None,
            "language_project" if {"language", "project"} <= set(prefix_kinds) else (prefix_kinds[-1] if prefix_kinds else None),
        )

    prefix_kind = None
    if "language" in prefix_kinds and "project" in prefix_kinds:
        prefix_kind = "language_project"
    elif prefix_kinds:
        prefix_kind = prefix_kinds[-1]

    prefix = ":".join(prefix_parts) or None
    canonical_prefix = _canonical_chain(prefix_parts, prefix_kinds, prefix_destinations, metadata) or None
    operation = special_operation_destination(destination_wiki, title, fragment, metadata)
    destination = operation or _build_destination(destination_wiki, title, fragment, metadata)
    return ChainResult(
        destination,
        ResolutionStatus.RESOLVED,
        "resolved interwiki prefix chain",
        prefix,
        canonical_prefix,
        prefix_kind,
    )


def _default_family(source: Optional[WikiInfo]) -> str:
    if source and source.family in MULTILINGUAL_FAMILY_NAMES:
        return source.family
    return "wikipedia"


def is_local_to(destination: Destination, source: Optional[WikiInfo]) -> bool:
    return bool(
        source
        and destination.destination_type is DestinationType.WIKI
        and destination.dbname == source.dbname
    )


def _operation_target(destination: Destination) -> Optional[str]:
    title = destination.full_title or ""
    if destination.diff is not None:
        if destination.revision is not None:
            return f"Special:Diff/{destination.revision}/{destination.diff}"
        if isinstance(destination.diff, int):
            return f"Special:Diff/{destination.diff}"
        return None
    if destination.revision is not None:
        return f"Special:PermanentLink/{destination.revision}"
    if destination.action:
        if destination.action.casefold() == "edit" and destination.full_title and not destination.query_parameters:
            return f"Special:Edit/{destination.full_title}"
        return None
    if not title:
        return None
    return title


def render_interwiki_target(
    destination: Destination,
    metadata: MetadataStore,
    source: Optional[WikiInfo] = None,
    long_project_prefix: bool = False,
) -> str:
    suffix = f"#{destination.fragment}" if destination.fragment else ""
    if destination.destination_type is DestinationType.ORGANIZATION:
        active = metadata.interwiki_map(source)
        prefix = None
        if destination.organization_name:
            key = destination.organization_name.casefold()
            if key in active.organization_entries or key in active.chapter_prefixes:
                prefix = key
            if prefix is None:
                prefix = next(
                    (p for p, name in active.chapter_prefixes.items() if name.casefold() == key),
                    None,
                )
        if prefix is None and destination.hostname:
            prefix = metadata.organization_prefix_for_hostname(destination.hostname)
        if prefix is None:
            raise ConversionError("no chapter/organization prefix known for destination")
        entry = active.organization_entries.get(prefix)
        if entry is not None and "$1" not in entry.url:
            return prefix + suffix
        if prefix in CHAPTER_FIXED_URLS:
            return prefix + suffix
        if not destination.title or destination.title.casefold() == (destination.organization_name or "").casefold():
            return prefix + suffix
        return f"{prefix}:{destination.title}{suffix}"

    if destination.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}:
        prefix = PREFERRED_SERVICE_PREFIX.get(destination.service_name or "")
        if prefix is None:
            prefix = next(
                (
                    p
                    for p, info in metadata.interwiki_map(source).service_prefixes.items()
                    if info.get("name") == destination.service_name
                ),
                None,
            )
        if prefix is None:
            prefix = next(
                (
                    p
                    for p, info in metadata.interwiki_map().service_prefixes.items()
                    if info.get("name") == destination.service_name
                ),
                None,
            )
        if prefix is None:
            raise ConversionError("no service prefix known")
        return f"{prefix}:{destination.title}{suffix}" if destination.title else f"{prefix}{suffix}"

    if destination.destination_type is not DestinationType.WIKI or not destination.dbname:
        raise ConversionError(f"don't know how to render a {destination.destination_type.value} destination as interwiki")

    wiki = metadata.wiki_by_dbname(destination.dbname)
    if wiki is None:
        raise ConversionError(f"no metadata known for dbname {destination.dbname!r}")

    # use an exact special-page representation only when no extra URL state
    # would be lost; otherwise fall back to the ordinary page target.
    title = _operation_target(destination) if not destination.query_parameters else None
    if title is None:
        title = destination.full_title

    # some global prefixes are fixed aliases for one page on an ordinary wiki,
    # such as wmin -> Meta-Wiki/Wikimedia_India. prefer them only on that exact page.
    fixed_prefix = metadata.interwiki_prefix_for_destination(destination, source)
    fixed_entry = metadata.global_interwiki_entry(fixed_prefix) if fixed_prefix else None
    if fixed_entry is not None and "$1" not in fixed_entry.url:
        return fixed_prefix + suffix

    # special/private wikimedia wikis do not automatically inherit the w:xx convention.
    # only use a real prefix from the source map for them.
    if not wiki.is_standard_project:
        prefix = metadata.interwiki_prefix_for_destination(destination, source)
        if prefix is None:
            raise ConversionError(f"no interwiki prefix is available for Wikimedia wiki {wiki.dbname!r}")
        if title is None:
            title = destination.full_title
        if title is None:
            raise ConversionError(
                f"no exact interwiki target is available for Wikimedia wiki {wiki.dbname!r}"
            )
        return f"{prefix}:{title}{suffix}"

    if wiki.dbname in PREFERRED_SINGLE_WIKI_PREFIX:
        prefix = PREFERRED_SINGLE_WIKI_PREFIX[wiki.dbname]
        if title is None:
            title = destination.full_title
        if title is None:
            raise ConversionError(
                f"no exact interwiki target is available for Wikimedia wiki {wiki.dbname!r}"
            )
        return f"{prefix}:{title}{suffix}"
    if wiki.family in PREFERRED_FAMILY_PREFIX:
        prefix = wiki.family if long_project_prefix else PREFERRED_FAMILY_PREFIX[wiki.family]
        language = metadata.interwiki_language_for_wiki(wiki)
        if title is None:
            title = destination.full_title
        if title is None:
            raise ConversionError(
                f"no exact interwiki target is available for Wikimedia wiki {wiki.dbname!r}"
            )
        return f"{prefix}:{language}:{title}{suffix}"
    raise ConversionError(f"no interwiki prefix convention known for wiki family {wiki.family!r}")


def render_local_target(destination: Destination, source: WikiInfo) -> str:
    if not is_local_to(destination, source):
        raise ConversionError("destination is not on the source wiki")
    # keep the exact operation when possible; otherwise use the ordinary page target.
    title = _operation_target(destination) if not destination.query_parameters else None
    if title is None:
        title = destination.full_title
    if title is None:
        raise ConversionError("destination has no local page target")
    return f"{title}#{destination.fragment}" if destination.fragment else title
