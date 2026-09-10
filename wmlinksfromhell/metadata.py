"""Wikimedia metadata discovery, caching, and source-specific interwiki maps"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import replace
from typing import Any, Iterable, Optional
from urllib.parse import unquote, urlsplit

from . import constants
from .cache import MetadataCache
from .exceptions import MetadataMissingError, SourceResolutionError
from .models import DestinationType, InterwikiEntry, InterwikiInfo, WikiInfo


_WIKIMEDIA_FOUNDATION_SUFFIXES = (".wikimedia.org", ".wikimediafoundation.org", ".wmcloud.org", ".wmflabs.org")
_INTERWIKI_CONFIG_URL = "https://noc.wikimedia.org/conf/interwiki.php.txt"
_WIKIMEDIA_FOUNDATION_ROOTS = {"wikimedia.org", "www.wikimedia.org", "wikimediafoundation.org", "www.wikimediafoundation.org", "wikimediadc.org"}
_WIKI_FAMILY_BY_CODE = {
    "wiki": "wikipedia",
    "wikipedia": "wikipedia",
    "wiktionary": "wiktionary",
    "wikinews": "wikinews",
    "wikibooks": "wikibooks",
    "wikiquote": "wikiquote",
    "wikisource": "wikisource",
    "wikiversity": "wikiversity",
    "wikivoyage": "wikivoyage",
}


def _looks_like_organization_entry(prefix: str, entry: InterwikiEntry) -> bool:
    key = prefix.casefold()
    host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
    if key in constants.CHAPTER_PREFIXES:
        return True
    if entry.destination_dbname:
        return "$1" not in entry.url
    if not key.startswith("wm"):
        return False
    if "$1" not in entry.url:
        return host.casefold() == "meta.wikimedia.org"
    # chapter/affiliate sites are generally outside wikimedia's .org wiki-host space
    return "wikimedia" in host.casefold() and not host.casefold().endswith(".wikimedia.org")


class InterwikiMap:
    """a source wiki's interwiki entries, plus a small bootstrap fallback"""

    def __init__(self, entries: Optional[dict[str, InterwikiEntry]] = None):
        self.entries = {k.casefold(): v for k, v in (entries or {}).items()}
        self.family_prefixes: dict[str, str] = {}
        self.single_wiki_prefixes: dict[str, str] = {}
        self.service_prefixes: dict[str, dict] = {}
        self.chapter_prefixes: dict[str, str] = {}
        self.organization_entries: dict[str, InterwikiEntry] = {}
        for prefix, value in constants.FAMILY_PREFIXES.items():
            self.family_prefixes[prefix.casefold()] = value
        for prefix, value in constants.SINGLE_WIKI_PREFIXES.items():
            self.single_wiki_prefixes[prefix.casefold()] = value
        self.service_prefixes.update({k.casefold(): v for k, v in constants.SERVICE_PREFIXES.items()})
        self.chapter_prefixes.update({k.casefold(): v for k, v in constants.CHAPTER_PREFIXES.items()})
        for entry in self.entries.values():
            self._classify_entry(entry)

    def _classify_entry(self, entry: InterwikiEntry) -> None:
        prefix = entry.prefix.casefold()
        if entry.destination_type is DestinationType.ORGANIZATION or _looks_like_organization_entry(prefix, entry):
            self.organization_entries[prefix] = entry
            self.single_wiki_prefixes.pop(prefix, None)
            self.service_prefixes.pop(prefix, None)
        elif entry.destination_type is DestinationType.WIKI and entry.destination_dbname and "$1" in entry.url:
            self.single_wiki_prefixes[prefix] = entry.destination_dbname
            self.service_prefixes.pop(prefix, None)
            self.chapter_prefixes.pop(prefix, None)
        elif entry.destination_dbname and "$1" in entry.url:
            self.single_wiki_prefixes[prefix] = entry.destination_dbname
        if entry.destination_type is DestinationType.SERVICE:
            self.service_prefixes[prefix] = {
                "hostname": urlsplit(entry.url.replace("$1", "x")).hostname or "",
                "name": entry.sitename or entry.prefix,
                "url": entry.url,
                "destination_type": "service",
            }
        elif entry.destination_type is DestinationType.TOOL:
            self.service_prefixes[prefix] = {
                "hostname": urlsplit(entry.url.replace("$1", "x")).hostname or "",
                "name": entry.sitename or entry.prefix,
                "url": entry.url,
                "destination_type": "tool",
            }
        elif entry.language and not entry.destination_dbname:
            # explicit language entries beat assumptions about iso-ish prefixes
            self.entries[prefix] = entry

    def get(self, prefix: str) -> Optional[InterwikiEntry]:
        return self.entries.get(prefix.casefold())

    def __contains__(self, prefix: str) -> bool:
        key = prefix.casefold()
        return key in self.entries or key in self.family_prefixes or key in self.single_wiki_prefixes or key in self.service_prefixes or key in self.chapter_prefixes


def _normalized_wiki_info(wiki: WikiInfo) -> WikiInfo:
    """repair stable wiki identity fields that may be stale in an older cache."""
    family = wiki.family.casefold()
    data = constants.MULTILINGUAL_FAMILIES.get(family)
    if (
        data
        and wiki.dbname not in constants.SINGLE_WIKIS
        and wiki.site_code == data["site_code"]
        and wiki.is_standard_project is not True
    ):
        wiki = replace(
            wiki,
            is_standard_project=True,
            project=data["project"],
            family=family,
        )

    if wiki.dbname in {"simplewiki", "simplewiktionary"} and wiki.language.casefold() != "simple":
        wiki = replace(wiki, language="simple")

    return wiki


class MetadataStore:
    """single metadata source used by parsing, URL handling, and conversion"""

    def __init__(self, cache: Optional[MetadataCache] = None):
        self.cache = cache or MetadataCache()
        self._wikis: dict[str, WikiInfo] = dict(constants.WIKIS)
        self._languages: dict[str, str] = dict(constants.LANGUAGES)
        self._interwiki_maps: dict[str, dict[str, InterwikiEntry]] = {}
        self._global_interwikis: dict[str, InterwikiEntry] = {
            prefix: InterwikiEntry(
                prefix=prefix,
                url=url,
                destination_dbname=dbname,
                destination_type=DestinationType.WIKI,
            )
            for prefix, (url, dbname) in constants.WIKIMEDIA_GLOBAL_WIKI_PREFIXES.items()
        }
        self._global_prefix_lists: dict[str, tuple[str, ...]] = {}
        self._family_language_aliases: dict[tuple[str, str], str] = {}
        self._family_language_prefixes: dict[tuple[str, str], str] = {}
        self._family_language_prefix_score: dict[tuple[str, str], int] = {}
        self._namespaces: dict[str, frozenset[str]] = {}
        self._namespace_aliases: dict[str, dict[str, str]] = {}
        self._http_meta: dict[str, dict] = {}
        self._load_cached_overrides()
        self._reindex()

    def _reindex(self) -> None:
        for dbname, wiki in tuple(self._wikis.items()):
            self._wikis[dbname] = _normalized_wiki_info(wiki)
        self._hostname_index = {w.hostname.casefold().rstrip("."): dbname for dbname, w in self._wikis.items()}
        for dbname, hosts in constants.SINGLE_WIKI_HOST_ALIASES.items():
            if dbname in self._wikis:
                for host in hosts:
                    self._hostname_index[host.casefold().rstrip(".")] = dbname

    def wiki_by_dbname(self, dbname: str) -> Optional[WikiInfo]:
        wiki = self._wikis.get(dbname)
        if wiki is not None:
            normalized = _normalized_wiki_info(wiki)
            if normalized is not wiki:
                self._wikis[dbname] = normalized
            return normalized
        value = dbname.casefold()
        for family, data in constants.MULTILINGUAL_FAMILIES.items():
            suffix = data["suffix"]
            if not value.endswith(suffix):
                continue
            lang = value[:-len(suffix)]
            if lang and lang in self._languages:
                wiki = self.resolve_wikimedia_hostname(f"{lang}.{family}.org")
                if wiki is not None:
                    return wiki
        for entry in self._global_interwikis.values():
            if entry.destination_dbname != dbname:
                continue
            hostname = urlsplit(entry.url.replace("$1", "x")).hostname
            if not hostname:
                continue
            return WikiInfo(
                dbname=dbname,
                family=self._family_from_dbname(dbname) or "special",
                project=self._family_from_dbname(dbname) or dbname,
                language=entry.language or "en",
                language_name=self._languages.get(entry.language or "en", entry.language or "en"),
                hostname=hostname,
                sitename=entry.sitename or entry.prefix,
                metadata_source="bootstrap",
                is_standard_project=False,
            )
        return None

    def wiki_by_hostname(self, hostname: str) -> Optional[WikiInfo]:
        dbname = self._hostname_index.get(hostname.casefold().rstrip("."), "")
        if not dbname:
            return None
        wiki = self._wikis.get(dbname)
        if wiki is None:
            return None
        normalized = _normalized_wiki_info(wiki)
        if normalized is not wiki:
            self._wikis[dbname] = normalized
        return normalized

    def known_wiki_hosts(self) -> frozenset[str]:
        return frozenset(self._hostname_index)

    def language_name(self, code: str) -> Optional[str]:
        return self._languages.get(code.casefold())

    def is_known_language(self, code: str) -> bool:
        key = code.casefold()
        return key in self._languages or any(alias == key for _family, alias in self._family_language_aliases)

    def wiki_for_family_language(self, family: str, language: str) -> Optional[WikiInfo]:
        family = family.casefold()
        language = language.casefold()

        # SiteMatrix is authoritative when it explicitly identifies a wiki by
        # family and language. Interwiki.php aliases are only fallbacks because
        # a generic alias can otherwise point at a different wiki in the same
        # family (for example an old or closed project).
        for wiki in self._wikis.values():
            if wiki.family.casefold() == family and wiki.language.casefold() == language:
                return wiki

        alias_dbname = self._family_language_aliases.get((family, language)) or constants.FAMILY_LANGUAGE_ALIASES.get((family, language))
        if alias_dbname:
            wiki = self.wiki_by_dbname(alias_dbname)
            if wiki is not None:
                return wiki

        data = constants.MULTILINGUAL_FAMILIES.get(family)
        if data and language in constants.BOOTSTRAP_LANGS_BY_FAMILY.get(family, ()):
            return self.resolve_wikimedia_hostname(f"{language}.{family}.org")
        return None

    def _family_language_alias(self, family: str, language: str) -> Optional[WikiInfo]:
        """return a wiki only when the prefix is an explicit family-language alias."""
        key = (family.casefold(), language.casefold())
        dbname = self._family_language_aliases.get(key) or constants.FAMILY_LANGUAGE_ALIASES.get(key)
        return self.wiki_by_dbname(dbname) if dbname else None

    def namespace_names(self, dbname: Optional[str]) -> frozenset[str]:
        if dbname and dbname in self._namespaces:
            return self._namespaces[dbname]
        return constants.COMMON_NAMESPACE_NAMES

    def namespace_aliases(self, dbname: Optional[str]) -> dict[str, str]:
        return self._namespace_aliases.get(dbname or "", constants.NAMESPACE_ALIASES)

    def is_namespace(self, text: str, source: Optional[WikiInfo]) -> bool:
        return text.casefold() in self.namespace_names(source.dbname if source else None)

    def interwiki_map(self, source: Any = None) -> InterwikiMap:
        source_wiki = source if isinstance(source, WikiInfo) else self.resolve_source(source) if source is not None else None
        entries: dict[str, InterwikiEntry] = dict(self._global_interwikis)
        if source_wiki:
            for prefix in self._global_prefix_lists.get(source_wiki.dbname, ()):
                entry = self._global_interwikis.get(prefix.casefold())
                if entry is not None:
                    entries.setdefault(prefix.casefold(), entry)
            entries.update(self._interwiki_maps.get(source_wiki.dbname, {}))
        return InterwikiMap(entries)

    def is_wikimedia_hostname(self, hostname: str) -> bool:
        host = hostname.casefold().rstrip(".")
        if self.wiki_by_hostname(host):
            return True
        if host in _WIKIMEDIA_FOUNDATION_ROOTS or host.endswith(_WIKIMEDIA_FOUNDATION_SUFFIXES):
            return True
        if host.endswith(constants.COMMON_WIKIMEDIA_HOST_SUFFIXES):
            return True
        if "wikimedia" in host.split(".")[-3:]:
            return True
        if host in constants.CHAPTER_HOSTS.values():
            return True
        return any(host == info["hostname"] for info in constants.SERVICE_PREFIXES.values())

    def organization_prefix_for_hostname(self, hostname: str) -> Optional[str]:
        host = hostname.casefold().rstrip(".")
        candidates = []
        for prefix, entry in self._global_interwikis.items():
            if not _looks_like_organization_entry(prefix, entry):
                continue
            entry_host = urlsplit(entry.url.replace("$1", "x")).hostname
            if entry_host and entry_host.casefold().rstrip(".") == host:
                candidates.append((prefix, entry))
        for prefix, host_value in constants.CHAPTER_HOSTS.items():
            if host_value.casefold().rstrip(".") == host:
                return prefix
        if not candidates:
            return None
        candidates.sort(key=lambda item: (len(item[0]), item[0].casefold()))
        return candidates[0][0]

    def global_interwiki_entry(self, prefix: str) -> Optional[InterwikiEntry]:
        return self._global_interwikis.get(prefix.casefold())

    def related_destination_type(self, hostname: str) -> Optional[DestinationType]:
        host = hostname.casefold().rstrip(".")
        if self.wiki_by_hostname(host):
            return DestinationType.WIKI
        if any(host == h.casefold() for h in constants.CHAPTER_HOSTS.values()):
            return DestinationType.ORGANIZATION
        for info in constants.SERVICE_PREFIXES.values():
            if host == info["hostname"].casefold():
                return DestinationType(info.get("destination_type", "service"))
        for entry in self._global_interwikis.values():
            entry_host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
            if entry_host.casefold().rstrip(".") == host and entry.destination_type in {DestinationType.ORGANIZATION, DestinationType.SERVICE, DestinationType.TOOL}:
                return entry.destination_type
        if host.endswith(".toolforge.org") or host == "toolforge.org":
            return DestinationType.TOOL
        if host in _WIKIMEDIA_FOUNDATION_ROOTS or host.endswith(_WIKIMEDIA_FOUNDATION_SUFFIXES) or host.endswith(constants.COMMON_WIKIMEDIA_HOST_SUFFIXES) or "wikimedia" in host.split(".")[-3:]:
            return DestinationType.UNKNOWN
        return None

    def resolve_wikimedia_hostname(self, hostname: str) -> Optional[WikiInfo]:
        """return exact/cached metadata, or safely derive common language-family hosts

        the derived path is only used for the standard multilingual project domains.
        an arbitrary Wikimedia host never becomes a guessed wiki record.
        """
        exact = self.wiki_by_hostname(hostname)
        if exact:
            return exact
        host = hostname.casefold().rstrip(".")
        for entry in self._global_interwikis.values():
            entry_host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
            if entry_host.casefold().rstrip(".") != host or entry.destination_type is not DestinationType.WIKI:
                continue
            if entry.destination_dbname:
                wiki = self.wiki_by_dbname(entry.destination_dbname)
                if wiki is not None:
                    return wiki
        for family, data in constants.MULTILINGUAL_FAMILIES.items():
            suffix = f".{family}.org"
            if not host.endswith(suffix):
                continue
            lang = host[: -len(suffix)]
            if not lang or "." in lang or not re.fullmatch(r"[a-z0-9-]{2,32}", lang):
                return None
            if lang not in constants.BOOTSTRAP_LANGS_BY_FAMILY.get(family, ()) and host not in self._hostname_index:
                return None
            return WikiInfo(
                dbname=f"{lang}{data['suffix']}",
                family=family,
                project=data["project"],
                language=lang,
                language_name=self._languages.get(lang, lang),
                hostname=host,
                metadata_source="derived",
                site_code=data["site_code"],
                is_standard_project=True,
            )
        return None

    def resolve_source(self, source: Any) -> Optional[WikiInfo]:
        if source is None:
            return None
        if isinstance(source, WikiInfo):
            return source
        if isinstance(source, str):
            value = source.strip()
            if value.startswith(("http://", "https://")):
                hostname = urlsplit(value).hostname
                if not hostname:
                    raise SourceResolutionError(f"{source!r} is not a valid Wikimedia URL")
                return self.resolve_source(hostname)
            wiki = self.wiki_by_dbname(value) or self.wiki_by_hostname(value)
            if wiki:
                return wiki
            raise SourceResolutionError(f"{source!r} doesn't match known Wikimedia metadata")
        db_name_method = getattr(source, "dbName", None)
        if callable(db_name_method):
            dbname = db_name_method()
            wiki = self.wiki_by_dbname(dbname)
            if wiki:
                return wiki
            raise MetadataMissingError(f"no metadata cached for source dbname {dbname!r}")

        # Pywikibot Page objects expose their Site as `site` while the Site
        # object itself exposes `dbName()`. Resolve the page through its Site
        # so callers keep page-title context without requiring special cases
        # in Resolver/WMCode.
        page_site = getattr(source, "site", None)
        if page_site is not None:
            if callable(page_site):
                page_site = page_site()
            if page_site is not source:
                dbname_method = getattr(page_site, "dbName", None)
                if callable(dbname_method):
                    dbname = dbname_method()
                    wiki = self.wiki_by_dbname(dbname)
                    if wiki:
                        return wiki
                    raise MetadataMissingError(f"no metadata cached for source dbname {dbname!r}")

        family_attr = getattr(source, "family", None)
        lang_attr = getattr(source, "lang", None)
        if family_attr is not None and lang_attr is not None:
            family = getattr(family_attr, "name", family_attr)
            wiki = self.wiki_for_family_language(str(family), str(lang_attr))
            if wiki:
                return wiki
        raise SourceResolutionError(f"don't know how to resolve source of type {type(source)!r}")

    def wiki(self, dbname: str) -> Optional[WikiInfo]:
        return self.wiki_by_dbname(dbname)

    def interwiki(self, dbname: str, source: Any = None) -> Optional[InterwikiInfo]:
        """return the canonical interwiki identity for a dbname."""
        wiki = self.wiki_by_dbname(dbname)
        if wiki is None:
            return None

        from .constants import PREFERRED_FAMILY_PREFIX, PREFERRED_SINGLE_WIKI_PREFIX

        if wiki.is_standard_project:
            project = PREFERRED_FAMILY_PREFIX.get(wiki.family.casefold(), wiki.family)
            language = self.interwiki_language_for_wiki(wiki)
            prefix = f"{project}:{language}"
        elif wiki.dbname in PREFERRED_SINGLE_WIKI_PREFIX:
            project = PREFERRED_SINGLE_WIKI_PREFIX[wiki.dbname]
            language = None
            prefix = project
        else:
            from .destination import Destination
            destination = Destination(
                DestinationType.WIKI,
                family=wiki.family,
                project=wiki.project,
                language=wiki.language,
                dbname=wiki.dbname,
                wikiid=wiki.wikiid,
                hostname=wiki.hostname,
                title="Main Page",
                is_wikimedia_project=True,
                is_standard_project=wiki.is_standard_project,
                is_multilingual=wiki.is_multilingual,
                metadata_source=wiki.metadata_source,
            )
            prefix = self.interwiki_prefix_for_destination(
                destination,
                source=source,
            )
            if prefix is None:
                return None
            project = prefix
            language = None

        return InterwikiInfo(
            prefix=prefix,
            project=project,
            language=language,
            dbname=wiki.dbname,
            wiki=wiki,
        )

    def all_wikis(self) -> tuple[WikiInfo, ...]:
        normalized = []
        for dbname, wiki in self._wikis.items():
            wiki = _normalized_wiki_info(wiki)
            if self._wikis[dbname] is not wiki:
                self._wikis[dbname] = wiki
            normalized.append(wiki)
        return tuple(normalized)

    def interwiki_language_for_wiki(self, wiki: WikiInfo) -> str:
        return self._family_language_prefixes.get((wiki.family.casefold(), wiki.dbname), wiki.language)

    def interwiki_prefix_for_destination(self, destination, source=None) -> Optional[str]:
        """return the best real prefix for a destination, never inventing one."""
        if not destination.hostname:
            return None
        host = destination.hostname.casefold().rstrip(".")
        active = self.interwiki_map(source)
        candidates: list[tuple[int, str]] = []

        for prefix, entry in active.entries.items():
            entry_host = urlsplit(entry.url.replace("$1", "x")).hostname
            if not entry_host or entry_host.casefold().rstrip(".") != host:
                continue
            entry_url = entry.url
            if "$1" not in entry_url:
                # fixed prefixes are aliases for one exact destination. they must
                # never become a generic hostname match.
                entry_parts = urlsplit(entry_url.rstrip("/"))
                destination_path = (destination.full_title or "").replace(" ", "_")
                wiki = self.wiki_by_dbname(destination.dbname) if destination.dbname else None
                if wiki is not None:
                    destination_prefix = wiki.article_path.split("$1", 1)[0]
                    destination_path = (destination_prefix + destination_path).rstrip("/")
                if (
                    entry_parts.hostname and entry_parts.hostname.casefold().rstrip(".") == host
                    and unquote(entry_parts.path).replace("_", " ").rstrip("/").casefold()
                    == unquote(destination_path).replace("_", " ").rstrip("/").casefold()
                    and entry_parts.query == ""
                ):
                    candidates.append((1000, entry.prefix))
                continue
            if entry.destination_type in {DestinationType.SERVICE, DestinationType.TOOL}:
                continue
            if entry.destination_type is DestinationType.ORGANIZATION and destination.destination_type is not DestinationType.WIKI:
                continue
            score = 100
            if entry.destination_dbname == destination.dbname:
                score += 100
            if entry.language and destination.language and entry.language.casefold() == destination.language.casefold():
                score += 10
            candidates.append((score, entry.prefix))

        for prefix, dbname in active.single_wiki_prefixes.items():
            target = self.wiki_by_dbname(dbname)
            if target and target.hostname.casefold().rstrip(".") == host:
                candidates.append((80, prefix))

        if destination.destination_type is not DestinationType.WIKI:
            for prefix, info in active.service_prefixes.items():
                if info.get("hostname", "").casefold().rstrip(".") == host:
                    candidates.append((90, prefix))

        if destination.destination_type is DestinationType.WIKI and destination.family == "special":
            for prefix, host_value in constants.CHAPTER_HOSTS.items():
                if host_value.casefold().rstrip(".") == host:
                    candidates.append((70, prefix))
        elif destination.destination_type is not DestinationType.WIKI:
            for prefix, host_value in constants.CHAPTER_HOSTS.items():
                if host_value.casefold().rstrip(".") == host:
                    candidates.append((70, prefix))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[0], len(item[1]), item[1].casefold()))
        return candidates[0][1]

    def refresh(
        self,
        dbname: str = "metawiki",
        timeout: float = 10.0,
        max_age: Optional[float] = None,
        force: bool = False,
        retries: int = 2,
    ) -> bool:
        """refresh SiteMatrix and the source wiki metadata explicitly."""
        cached = self.cache.load()
        before = cached.get("http", {})
        ready = bool(cached.get("wikis")) and bool(cached.get("global_interwikis")) and "interwiki-config" in before and dbname in self._wikis
        if max_age is not None and not force and ready and not self.cache.is_expired(max_age):
            return False
        self.update_sitematrix(timeout=timeout, force=force, retries=retries)
        self.update_interwiki_config(timeout=timeout, force=force, retries=retries)
        self.update_wiki_metadata(dbname, timeout=timeout, force=force, retries=retries)
        after = self.cache.load().get("http", {})
        return after != before

    def update(
        self,
        dbname: str = "metawiki",
        timeout: float = 10.0,
        max_age: Optional[float] = None,
        force: bool = False,
        retries: int = 2,
    ) -> bool:
        """refresh Wikimedia metadata explicitly."""
        return self.refresh(
            dbname=dbname, timeout=timeout, max_age=max_age, force=force, retries=retries
        )

    def update_from_network(
        self,
        dbname: str = "metawiki",
        timeout: float = 10.0,
        max_age: Optional[float] = None,
        force: bool = False,
        retries: int = 2,
    ) -> bool:
        """deprecated alias for update(); kept for compatibility"""
        return self.update(dbname=dbname, timeout=timeout, max_age=max_age, force=force, retries=retries)

    def refresh_all(
        self,
        dbname: str = "metawiki",
        timeout: float = 10.0,
        max_age: Optional[float] = None,
        force: bool = False,
        retries: int = 2,
    ) -> bool:
        """deprecated alias for update(); kept for compatibility"""
        return self.update(dbname=dbname, timeout=timeout, max_age=max_age, force=force, retries=retries)

    def load_sitematrix(self, data: dict) -> int:
        """load a SiteMatrix API response into memory without network or disk I/O."""
        discovered, languages = self._parse_sitematrix(data)
        self._wikis.update(discovered)
        self._languages.update(languages)
        self._reindex()
        self._enrich_global_interwikis()
        return len(discovered)

    def load_interwiki_config(self, text: str) -> int:
        """load global interwiki configuration text into memory without network or disk I/O."""
        entries, prefix_lists = self._parse_interwiki_config(text)
        family_aliases, family_prefixes = self._parse_family_language_entries(text)
        self._global_interwikis.update(entries)
        self._global_prefix_lists.update(prefix_lists)
        self._family_language_aliases.update(family_aliases)
        self._family_language_prefixes.update(family_prefixes)
        self._global_interwikis = dict(self._global_interwikis)
        self._enrich_global_interwikis()
        self._reindex()
        return len(entries)

    def update_sitematrix(self, timeout: float = 10.0, force: bool = False, retries: int = 2) -> bool:
        url = (
            "https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json&formatversion=2"
            "&smstate=all&smlimit=5000&smsiteprop=url%7Cdbname%7Ccode%7Csitename%7Clang"
        )
        meta = self._http_meta.get("sitematrix", {})
        if not isinstance(meta, dict):
            meta = {}
            self._http_meta["sitematrix"] = meta
        data, headers, changed = self._fetch_json(url, meta, timeout, force, retries)
        if not changed:
            return False
        discovered, languages = self._parse_sitematrix(data)
        merged = self.cache.load()
        merged["wikis"] = {**merged.get("wikis", {}), **{k: v.as_dict() for k, v in discovered.items()}}
        merged["languages"] = {**merged.get("languages", {}), **languages}
        merged.setdefault("http", {})["sitematrix"] = {
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "content_hash": hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "checked_at": time.time(),
        }
        self.cache.save(merged)
        self._load_cached_overrides()
        self._reindex()
        return True

    def update_interwiki_config(self, timeout: float = 10.0, force: bool = False, retries: int = 2) -> bool:
        meta = self._http_meta.get("interwiki-config", {})
        if not isinstance(meta, dict):
            meta = {}
            self._http_meta["interwiki-config"] = meta
        data, headers, changed = self._fetch_text(_INTERWIKI_CONFIG_URL, meta, timeout, force, retries)
        if not changed:
            return False
        entries, prefix_lists = self._parse_interwiki_config(data)
        family_aliases, family_prefixes = self._parse_family_language_entries(data)
        merged = self.cache.load()
        merged["global_interwikis"] = {k: v.as_dict() for k, v in entries.items()}
        merged["global_interwiki_lists"] = {k: list(v) for k, v in prefix_lists.items()}
        merged["family_language_aliases"] = {f"{family}:{alias}": dbname for (family, alias), dbname in family_aliases.items()}
        merged["family_language_prefixes"] = {f"{family}:{dbname}": prefix for (family, dbname), prefix in family_prefixes.items()}
        merged.setdefault("http", {})["interwiki-config"] = {
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "content_hash": hashlib.sha256(data.encode("utf-8")).hexdigest(),
            "checked_at": time.time(),
        }
        self.cache.save(merged)
        self._load_cached_overrides()
        self._reindex()
        return True

    def _fetch_text(self, url: str, meta: dict, timeout: float, force: bool, retries: int) -> tuple[str, dict, bool]:
        headers = {"User-Agent": "wmlinksfromhell/0.1.1 (Wikimedia link resolver)"}
        if not isinstance(meta, dict):
            meta = {}
        if not force:
            if meta.get("etag"):
                headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                headers["If-Modified-Since"] = meta["last_modified"]
        last_error = None
        for attempt in range(max(1, retries + 1)):
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read()
                    response_headers = dict(response.headers.items())
                    return body.decode("utf-8"), response_headers, True
            except urllib.error.HTTPError as exc:
                if exc.code == 304:
                    return "", dict(exc.headers.items()), False
                last_error = exc
            except (OSError, UnicodeDecodeError) as exc:
                last_error = exc
            if attempt < retries:
                time.sleep(min(2.0 ** attempt, 4.0))
        raise MetadataMissingError(f"Wikimedia metadata update failed for {url}: {last_error}") from last_error

    def _parse_interwiki_config(self, text: str) -> tuple[dict[str, InterwikiEntry], dict[str, tuple[str, ...]]]:
        entries: dict[str, InterwikiEntry] = {}
        prefix_lists: dict[str, tuple[str, ...]] = {}
        global_pattern = re.compile(r"^\s*'__global:((?:[^'\\]|\\.)*)'\s*=>\s*'([01])\s+(.+?)',\s*$", re.MULTILINE)
        list_pattern = re.compile(r"^\s*'__list:([^']+)'\s*=>\s*'([^']*)',\s*$", re.MULTILINE)

        for raw_prefix, local_flag, template in global_pattern.findall(text):
            prefix = raw_prefix.replace("\\'", "'").replace("\\\\", "\\")
            url = template.replace("\\'", "'")
            if not self._is_wikimedia_related_interwiki_url(url):
                continue
            host = urlsplit(url.replace("$1", "x")).hostname or ""
            target = self.resolve_wikimedia_hostname(host)
            probe = InterwikiEntry(prefix=prefix, url=url, destination_dbname=target.dbname if target else None)
            if _looks_like_organization_entry(prefix, probe):
                dtype = DestinationType.ORGANIZATION
            elif target is not None:
                dtype = DestinationType.WIKI
            else:
                dtype = self.related_destination_type(host)
                if dtype is None and self._is_wikimedia_related_interwiki_url(url):
                    dtype = DestinationType.SERVICE
            entries[prefix.casefold()] = InterwikiEntry(
                prefix=prefix,
                url=url,
                local=bool(int(local_flag)),
                destination_dbname=target.dbname if target else None,
                destination_type=dtype,
            )

        for name, values in list_pattern.findall(text):
            prefix_lists[name] = tuple(values.split())
        return entries, prefix_lists

    def _parse_family_language_entries(self, text: str) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
        aliases: dict[tuple[str, str], str] = {}
        prefixes: dict[tuple[str, str], str] = {}
        pattern = re.compile(r"^\s*'_(wiki|wiktionary|wikinews|wikibooks|wikiquote|wikisource|wikiversity):([^']+)'\s*=>\s*'1\s+(.+?)',\s*$", re.MULTILINE)
        family_names = {
            "wiki": "wikipedia",
            "wiktionary": "wiktionary",
            "wikinews": "wikinews",
            "wikibooks": "wikibooks",
            "wikiquote": "wikiquote",
            "wikisource": "wikisource",
            "wikiversity": "wikiversity",
        }
        for family_code, alias, template in pattern.findall(text):
            host = urlsplit(template.replace("$1", "x")).hostname or ""
            wiki = self.resolve_wikimedia_hostname(host)
            if wiki is None:
                continue
            family = family_names[family_code]
            aliases[(family, alias.casefold())] = wiki.dbname
            current_language = wiki.language.casefold()
            host_prefix = host.casefold().split(".", 1)[0]
            score = 0
            if current_language == alias.casefold():
                score += 100
            if host_prefix == alias.casefold():
                score += 50
            key = (family, wiki.dbname)
            old = prefixes.get(key)
            if old is None or score > self._family_language_prefix_score.get((family, wiki.dbname), -1):
                prefixes[key] = alias
                self._family_language_prefix_score[(family, wiki.dbname)] = score
        return aliases, prefixes

    def _is_wikimedia_related_interwiki_url(self, url: str) -> bool:
        host = (urlsplit(url.replace("$1", "x")).hostname or "").casefold().rstrip(".")
        if not host:
            return False
        if self.wiki_by_hostname(host):
            return True
        if host in _WIKIMEDIA_FOUNDATION_ROOTS or host.endswith(_WIKIMEDIA_FOUNDATION_SUFFIXES):
            return True
        if host.endswith(constants.COMMON_WIKIMEDIA_HOST_SUFFIXES):
            return True
        if any(host == value.casefold() for value in constants.CHAPTER_HOSTS.values()):
            return True
        return any(host == info["hostname"].casefold() for info in constants.SERVICE_PREFIXES.values()) or host.endswith(".toolforge.org") or host == "toolforge.org"

    def update_wiki_metadata(self, dbname: str, timeout: float = 10.0, force: bool = False, retries: int = 2) -> bool:
        wiki = self.wiki_by_dbname(dbname)
        if wiki is None:
            raise MetadataMissingError(f"no known Wikimedia wiki {dbname!r}")
        api_url = wiki.api_url or f"{wiki.url}/w/api.php"
        url = (
            f"{api_url}?action=query&meta=siteinfo"
            "&siprop=general%7Cinterwikimap%7Cnamespaces%7Cnamespacealiases&format=json&formatversion=2"
        )
        meta = self._http_meta.get(f"siteinfo:{dbname}", {})
        if not isinstance(meta, dict):
            meta = {}
            self._http_meta[f"siteinfo:{dbname}"] = meta
        data, headers, changed = self._fetch_json(url, meta, timeout, force, retries)
        if not changed:
            return False
        query = data.get("query")
        if not isinstance(query, dict):
            raise MetadataMissingError(
                f"Wikimedia siteinfo endpoint returned an invalid query object for {dbname!r}"
            )
        general = query.get("general", {})
        if not isinstance(general, dict):
            raise MetadataMissingError(
                f"Wikimedia siteinfo endpoint returned an invalid general object for {dbname!r}"
            )
        updated_wiki = replace(
            wiki,
            article_path=general.get("articlepath", wiki.article_path),
            script_path=general.get("scriptpath", wiki.script_path),
            sitename=general.get("sitename", wiki.sitename),
            api_url=general.get("server", wiki.url).rstrip("/") + "/w/api.php" if general.get("server") else wiki.api_url,
            metadata_source="live",
        )
        entries = self._parse_interwiki_entries(query.get("interwikimap", []))
        namespace_names, namespace_aliases = self._parse_namespaces(query)
        merged = self.cache.load()
        merged.setdefault("wikis", {})[dbname] = updated_wiki.as_dict()
        merged.setdefault("interwiki_maps", {})[dbname] = {k: v.as_dict() for k, v in entries.items()}
        merged.setdefault("namespaces", {})[dbname] = {
            "namespaces": sorted(namespace_names),
            "aliases": namespace_aliases,
        }
        merged.setdefault("http", {})[f"siteinfo:{dbname}"] = {
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "content_hash": hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "checked_at": time.time(),
        }
        self.cache.save(merged)
        self._load_cached_overrides()
        self._reindex()
        return True

    def _fetch_json(self, url: str, meta: dict, timeout: float, force: bool, retries: int) -> tuple[dict, dict, bool]:
        headers = {"User-Agent": "wmlinksfromhell/0.1.1 (Wikimedia link resolver)"}
        if not isinstance(meta, dict):
            meta = {}
        if not force:
            if meta.get("etag"):
                headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                headers["If-Modified-Since"] = meta["last_modified"]
        last_error = None
        for attempt in range(max(1, retries + 1)):
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read()
                    response_headers = dict(response.headers.items())
                    text = body.decode("utf-8")
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError as exc:
                        content_type = response_headers.get("Content-Type", "unknown")
                        preview = " ".join(text.split())[:200]
                        raise MetadataMissingError(
                            f"Wikimedia metadata endpoint returned non-JSON "
                            f"content from {url} (Content-Type: {content_type}); "
                            f"response starts with {preview!r}"
                        ) from exc
                    if not isinstance(data, dict):
                        raise MetadataMissingError(
                            f"Wikimedia metadata endpoint returned JSON "
                            f"that is not an object from {url}"
                        )
                    if "error" in data:
                        error_info = data.get("error")
                        if isinstance(error_info, dict):
                            message = error_info.get("info") or error_info.get("code") or "unknown API error"
                        else:
                            message = str(error_info)
                        raise MetadataMissingError(
                            f"Wikimedia metadata endpoint returned an API error from {url}: {message}"
                        )
                    return data, response_headers, True
            except urllib.error.HTTPError as exc:
                if exc.code == 304:
                    return {}, dict(exc.headers.items()), False
                last_error = exc
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                last_error = exc
            if attempt < retries:
                time.sleep(min(2.0 ** attempt, 4.0))
        raise MetadataMissingError(f"Wikimedia metadata update failed for {url}: {last_error}") from last_error

    def _parse_sitematrix(self, data: dict) -> tuple[dict[str, WikiInfo], dict[str, str]]:
        sm = data.get("sitematrix", {})
        wikis: dict[str, WikiInfo] = {}
        languages: dict[str, str] = {}
        if not isinstance(sm, dict):
            raise MetadataMissingError("invalid SiteMatrix response")
        for key, group in sm.items():
            if key in {"count", "specials"}:
                continue
            if not isinstance(group, dict):
                continue
            lang = str(group.get("code") or key).casefold()
            languages[lang] = group.get("name") or group.get("localname") or lang
            sites = group.get("site", [])
            if isinstance(sites, dict):
                sites = [sites]
            if not isinstance(sites, list):
                continue
            for site in sites:
                if not isinstance(site, dict):
                    continue
                wiki = self._wiki_from_sitematrix_site(site, lang)
                if wiki:
                    wikis[wiki.dbname] = wiki
        specials = sm.get("specials", [])
        if isinstance(specials, dict):
            specials = [specials]
        if isinstance(specials, list):
            for site in specials:
                if not isinstance(site, dict):
                    continue
                wiki = self._wiki_from_special_site(site)
                if wiki:
                    wikis[wiki.dbname] = wiki
        return wikis, languages

    def _wiki_from_sitematrix_site(self, site: dict, lang: str) -> Optional[WikiInfo]:
        dbname = site.get("dbname")
        hostname = urlsplit(site.get("url", "")).hostname if site.get("url") else None
        code = str(site.get("code") or "")
        if not dbname or not hostname:
            return None
        family = _WIKI_FAMILY_BY_CODE.get(code)
        if not family:
            family = self._family_from_dbname(dbname) or code or "unknown"
        project = family
        is_standard_project = code in _WIKI_FAMILY_BY_CODE and family in constants.MULTILINGUAL_FAMILIES
        language = str(site.get("lang") or lang).casefold()
        if dbname in {"simplewiki", "simplewiktionary"} or hostname in {"simple.wikipedia.org", "simple.wiktionary.org"}:
            language = "simple"
        return WikiInfo(
            dbname=dbname,
            family=family,
            project=project,
            language=language,
            language_name=self._languages.get(lang, lang),
            hostname=hostname,
            sitename=site.get("sitename"),
            site_code=code,
            metadata_source="sitematrix",
            is_standard_project=is_standard_project,
        )

    def _wiki_from_special_site(self, site: dict) -> Optional[WikiInfo]:
        dbname = site.get("dbname")
        hostname = urlsplit(site.get("url", "")).hostname if site.get("url") else None
        code = str(site.get("code") or "")
        if not dbname or not hostname:
            return None
        if dbname in constants.SINGLE_WIKIS:
            family = constants.SINGLE_WIKIS[dbname]["family"]
            project = constants.SINGLE_WIKIS[dbname]["project"]
        else:
            family = "special"
            project = dbname
        language = str(site.get("lang") or ("mul" if family in {"commons", "wikidata", "wikifunctions", "wikispecies", "incubator"} else "en"))
        return WikiInfo(
            dbname=dbname,
            family=family,
            project=project,
            language=language,
            language_name=self._languages.get(language, language),
            hostname=hostname,
            sitename=site.get("sitename"),
            site_code=code,
            metadata_source="live",
            is_multilingual=language == "mul",
            is_standard_project=False,
        )

    @staticmethod
    def _family_from_dbname(dbname: str) -> Optional[str]:
        value = dbname.casefold()
        for suffix, family in (
            ("wikidatawiki", "wikidata"), ("commonswiki", "commons"), ("metawiki", "meta"),
            ("mediawikiwiki", "mediawiki"), ("specieswiki", "wikispecies"), ("incubatorwiki", "incubator"),
            ("wikifunctionswiki", "wikifunctions"), ("wikitechwiki", "wikitech"),
            ("foundationwiki", "foundation"), ("strategywiki", "strategy"),
            ("wiktionary", "wiktionary"), ("wikinews", "wikinews"), ("wikibooks", "wikibooks"),
            ("wikiquote", "wikiquote"), ("wikisource", "wikisource"), ("wikiversity", "wikiversity"),
            ("wikivoyage", "wikivoyage"), ("wiki", "wikipedia"),
        ):
            if value.endswith(suffix):
                return family
        return None

    def _parse_interwiki_entries(self, rows: Iterable[dict]) -> dict[str, InterwikiEntry]:
        entries = {}
        if isinstance(rows, dict):
            rows = rows.values()
        if not isinstance(rows, (list, tuple)):
            return entries
        for row in rows:
            if not isinstance(row, dict):
                continue
            prefix = row.get("prefix")
            url = row.get("url")
            if not prefix or not url:
                continue
            host = urlsplit(url.replace("$1", "x")).hostname or ""
            target = self.resolve_wikimedia_hostname(host)
            probe = InterwikiEntry(prefix=prefix, url=url, destination_dbname=target.dbname if target else None)
            if _looks_like_organization_entry(prefix, probe):
                dtype = DestinationType.ORGANIZATION
            elif target is not None:
                dtype = DestinationType.WIKI
            else:
                dtype = self.related_destination_type(host)
                if dtype is None and self._is_wikimedia_related_interwiki_url(url):
                    dtype = DestinationType.SERVICE
            entries[prefix.casefold()] = InterwikiEntry(
                prefix=prefix,
                url=url,
                local=bool(row.get("local")),
                trans=bool(row.get("trans")),
                language=row.get("language"),
                localinterwiki=bool(row.get("localinterwiki")),
                extralanglink=bool(row.get("extralanglink")),
                linktext=row.get("linktext"),
                sitename=row.get("sitename"),
                wikiid=row.get("wikiid"),
                api=row.get("api"),
                destination_dbname=target.dbname if target else None,
                destination_type=dtype,
            )
        return entries

    @staticmethod
    def _parse_namespaces(query: dict) -> tuple[frozenset[str], dict[str, str]]:
        names = {"media", "special"}
        aliases: dict[str, str] = {}
        if not isinstance(query, dict):
            return frozenset(names | set(constants.COMMON_NAMESPACE_NAMES)), aliases

        namespaces = query.get("namespaces", [])
        if isinstance(namespaces, dict):
            namespaces = tuple(namespaces.values())
        elif not isinstance(namespaces, (list, tuple)):
            namespaces = ()

        valid_namespaces = []
        for namespace in namespaces:
            if not isinstance(namespace, dict):
                continue
            valid_namespaces.append(namespace)
            name = namespace.get("canonical") or namespace.get("name")
            if name:
                names.add(str(name).casefold())

        namespacealiases = query.get("namespacealiases", [])
        if isinstance(namespacealiases, dict):
            namespacealiases = tuple(namespacealiases.values())
        elif not isinstance(namespacealiases, (list, tuple)):
            namespacealiases = ()

        for alias in namespacealiases:
            if not isinstance(alias, dict):
                continue
            alias_name = alias.get("alias")
            ns_id = alias.get("id")
            target = next(
                (
                    namespace.get("canonical") or namespace.get("name")
                    for namespace in valid_namespaces
                    if namespace.get("id") == ns_id
                ),
                None,
            )
            if alias_name and target:
                aliases[str(alias_name).casefold()] = str(target)
                names.add(str(alias_name).casefold())

        return frozenset(names | set(constants.COMMON_NAMESPACE_NAMES)), aliases

    def _enrich_global_interwikis(self) -> None:
        """attach SiteMatrix wiki targets to cached NOC prefixes when possible."""
        for prefix, entry in tuple(self._global_interwikis.items()):
            host = urlsplit(entry.url.replace("$1", "x")).hostname or ""
            target = self.wiki_by_hostname(host)
            if target is None:
                continue
            probe = replace(entry, destination_dbname=target.dbname, destination_type=DestinationType.WIKI)
            if _looks_like_organization_entry(prefix, probe):
                probe = replace(probe, destination_type=DestinationType.ORGANIZATION)
            self._global_interwikis[prefix] = probe

    def _load_cached_overrides(self) -> None:
        data = self.cache.load()
        for dbname, row in data.get("wikis", {}).items():
            try:
                self._wikis[dbname] = _normalized_wiki_info(WikiInfo(**row))
            except TypeError:
                continue
        languages = data.get("languages", {})
        if isinstance(languages, dict):
            self._languages.update(languages)
        cached_global = {}
        for prefix, row in data.get("global_interwikis", {}).items():
            try:
                row = dict(row)
                dtype = row.get("destination_type")
                if dtype:
                    row["destination_type"] = DestinationType(dtype)
                cached_global[prefix] = InterwikiEntry(**row)
            except TypeError:
                continue
        self._global_interwikis = {
            **{
                prefix: InterwikiEntry(
                    prefix=prefix,
                    url=url,
                    destination_dbname=dbname,
                    destination_type=DestinationType.WIKI,
                )
                for prefix, (url, dbname) in constants.WIKIMEDIA_GLOBAL_WIKI_PREFIXES.items()
            },
            **cached_global,
        }
        global_lists = data.get("global_interwiki_lists", {})
        if not isinstance(global_lists, dict):
            global_lists = {}
        self._global_prefix_lists = {
            str(dbname): tuple(str(prefix) for prefix in prefixes)
            for dbname, prefixes in global_lists.items()
            if isinstance(prefixes, (list, tuple))
        }
        self._family_language_aliases = {}
        for key, dbname in data.get("family_language_aliases", {}).items():
            family, sep, alias = str(key).partition(":")
            if sep:
                self._family_language_aliases[(family, alias)] = str(dbname)
        self._family_language_prefixes = {}
        self._family_language_prefix_score = {}
        for key, prefix in data.get("family_language_prefixes", {}).items():
            family, sep, dbname = str(key).partition(":")
            if sep:
                self._family_language_prefixes[(family, dbname)] = str(prefix)
        self._interwiki_maps = {}
        for dbname, rows in data.get("interwiki_maps", {}).items():
            if dbname == "_global":
                continue
            entries = {}
            for prefix, row in rows.items():
                try:
                    dtype = row.get("destination_type")
                    if dtype:
                        row = dict(row)
                        row["destination_type"] = DestinationType(dtype)
                    entries[prefix] = InterwikiEntry(**row)
                except TypeError:
                    continue
            self._interwiki_maps[dbname] = entries
        self._namespaces = {}
        self._namespace_aliases = {}
        namespaces_data = data.get("namespaces", {})
        if not isinstance(namespaces_data, dict):
            namespaces_data = {}
        for dbname, row in namespaces_data.items():
            if not isinstance(row, dict):
                continue
            names = row.get("namespaces", [])
            aliases = row.get("aliases", {})
            if not isinstance(names, (list, tuple, set)):
                names = []
            if not isinstance(aliases, dict):
                aliases = {}
            self._namespaces[dbname] = frozenset(str(x).casefold() for x in names)
            self._namespace_aliases[dbname] = {str(k).casefold(): str(v) for k, v in aliases.items()}
        self._http_meta = data.get("http", {})
        if not isinstance(self._http_meta, dict):
            self._http_meta = {}
        self._reindex()
        self._enrich_global_interwikis()
