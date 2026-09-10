"""MediaWiki special-page operation representations used by URL and interwiki parsing."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .destination import Destination, normalize_title
from .models import DestinationType, WikiInfo

if TYPE_CHECKING:
    from .metadata import MetadataStore


def special_operation_destination(
    wiki: WikiInfo,
    title: str,
    fragment: Optional[str],
    metadata: "MetadataStore",
    query_parameters: tuple[tuple[str, str], ...] = (),
) -> Optional[Destination]:
    namespace, bare = metadata_namespace_split(title, wiki.dbname, metadata)
    if not namespace or namespace.casefold() != "special":
        return None

    key, separator, value = bare.partition("/")
    if not separator or not value:
        return None

    common = dict(
        destination_type=DestinationType.WIKI,
        family=wiki.family,
        project=wiki.project,
        language=wiki.language,
        dbname=wiki.dbname,
        wikiid=wiki.wikiid,
        hostname=wiki.hostname,
        fragment=fragment,
        metadata_source=wiki.metadata_source,
        is_multilingual=wiki.is_multilingual,
        is_standard_project=wiki.is_standard_project,
        is_wikimedia_project=True,
        query_parameters=query_parameters,
    )

    key = key.casefold()
    if key in {"edit", "editpage"}:
        target_namespace, target_title = metadata_namespace_split(value, wiki.dbname, metadata)
        return Destination(
            **common,
            namespace=target_namespace,
            title=normalize_title(target_title),
            action="edit",
            special_page="Edit",
        )

    if key == "permanentlink" and value.isdigit():
        return Destination(**common, revision=int(value), special_page="PermanentLink")

    if key == "diff":
        parts = value.split("/", 1)
        revision = int(parts[0]) if len(parts) == 2 and parts[0].isdigit() else None
        diff = parts[1] if len(parts) == 2 else parts[0]
        if diff:
            return Destination(
                **common,
                revision=revision,
                diff=int(diff) if diff.isdigit() else diff,
                special_page="Diff",
            )

    return None


def metadata_namespace_split(title: str, dbname: Optional[str], metadata: "MetadataStore") -> tuple[Optional[str], str]:
    from .destination import split_namespace

    namespace, bare = split_namespace(
        title,
        metadata.namespace_names(dbname) or frozenset({"special"}),
    )
    if namespace:
        namespace = metadata.namespace_aliases(dbname).get(namespace.casefold(), namespace)
    return namespace, bare
