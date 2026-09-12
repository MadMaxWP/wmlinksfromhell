"""public text-in parser and structural wrapper"""

from __future__ import annotations

from typing import Any, Callable, Optional

import mwparserfromhell
from mwparserfromhell.nodes import ExternalLink, Wikilink

from .destination import Destination
from .metadata import MetadataStore
from .nodes import WMLink
from .resolver import Resolver


class WMCode:
    def __init__(self, wikicode: "mwparserfromhell.wikicode.Wikicode", resolver: Resolver, source: Any = None, root: Optional["mwparserfromhell.wikicode.Wikicode"] = None):
        self.wikicode = wikicode
        self.resolver = resolver
        self.source = source
        self._root = root if root is not None else wikicode

    @property
    def links(self) -> list[WMLink]:
        return self.filter_links()

    @property
    def destinations(self) -> list["Destination"]:
        return [link.destination for link in self.filter_links() if link.destination is not None]

    def _make_links(
        self,
        nodes,
        container,
        comment=False,
        start_index=0,
    ) -> list[WMLink]:
        return [
            WMLink(
                node,
                container,
                self._root,
                self.resolver,
                self.source,
                start_index + i,
                in_comment=comment,
            )
            for i, node in enumerate(nodes)
        ]

    def _comment_links(
        self,
        recursive: bool = True,
        start_index: int = 0,
    ) -> list[WMLink]:
        links: list[WMLink] = []
        seen: set[tuple[int, int]] = set()

        for comment in self.wikicode.filter_comments(recursive=recursive):
            comment_code = mwparserfromhell.parse(comment.contents)
            for node in comment_code.ifilter(
                recursive=True,
                matches=lambda n: isinstance(n, (Wikilink, ExternalLink)),
            ):
                key = (id(comment), id(node))
                if key in seen:
                    continue
                seen.add(key)
                links.append(
                    WMLink(
                        node,
                        comment_code,
                        comment_code,
                        self.resolver,
                        self.source,
                        start_index + len(links),
                        in_comment=True,
                        comment_node=comment,
                    )
                )

        return links

    def filter_links(
        self,
        recursive: bool = True,
        predicate: Optional[Callable[[WMLink], bool]] = None,
        comment_links: bool = False,
        **criteria,
    ) -> list[WMLink]:
        nodes = self.wikicode.ifilter(
            recursive=recursive,
            matches=lambda n: isinstance(n, (Wikilink, ExternalLink)),
        )
        links = self._make_links(nodes, self.wikicode)

        if comment_links:
            links.extend(
                self._comment_links(
                    recursive=recursive,
                    start_index=len(links),
                )
            )

        if predicate is not None:
            links = [link for link in links if predicate(link)]
        if criteria:
            links = [link for link in links if link.matches(**criteria)]
        return links

    def filter_wikilinks(
        self,
        recursive: bool = True,
        predicate: Optional[Callable[[WMLink], bool]] = None,
        comment_links: bool = False,
        **criteria,
    ) -> list[WMLink]:
        return self._filter_kind(
            Wikilink, recursive, predicate, comment_links, criteria
        )

    def filter_external_links(
        self,
        recursive: bool = True,
        predicate: Optional[Callable[[WMLink], bool]] = None,
        comment_links: bool = False,
        **criteria,
    ) -> list[WMLink]:
        return self._filter_kind(
            ExternalLink, recursive, predicate, comment_links, criteria
        )

    def _filter_kind(
        self,
        node_type,
        recursive: bool,
        predicate: Optional[Callable[[WMLink], bool]],
        comment_links: bool,
        criteria: dict,
    ) -> list[WMLink]:
        links = [
            link
            for link in self.filter_links(
                recursive=recursive,
                comment_links=comment_links,
            )
            if isinstance(link.node, node_type)
        ]
        if predicate is not None:
            links = [link for link in links if predicate(link)]
        if criteria:
            links = [link for link in links if link.matches(**criteria)]
        return links

    def convert(
        self,
        to: str,
        recursive: bool = True,
        predicate: Optional[Callable[[WMLink], bool]] = None,
        comment_links: bool = False,
        **criteria,
    ) -> list[WMLink]:
        # pick the links first, then change only those links
        links = self.filter_links(
            recursive=recursive,
            predicate=predicate,
            comment_links=comment_links,
            **criteria,
        )
        for link in links:
            link.convert(to)
        return links

    def get_sections(self, *args, **kwargs) -> list["WMCode"]:
        return [
            WMCode(section, self.resolver, self.source, self._root)
            for section in self.wikicode.get_sections(*args, **kwargs)
        ]

    def __str__(self) -> str:
        return str(self.wikicode)

    def __repr__(self) -> str:
        return f"WMCode({str(self.wikicode)!r})"


def parse(text: str, source: Any = None, metadata: Optional[MetadataStore] = None) -> WMCode:
    if not isinstance(text, str):
        raise TypeError("wmlinksfromhell.parse() expects wikitext text as a str")
    resolver = Resolver(metadata)
    return WMCode(mwparserfromhell.parse(text), resolver, source)
