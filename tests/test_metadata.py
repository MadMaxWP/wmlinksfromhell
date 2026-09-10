from pathlib import Path
import pytest

from wmlinksfromhell.metadata import MetadataStore
from wmlinksfromhell.exceptions import ConversionError
from wmlinksfromhell.models import DestinationType, InterwikiEntry, WikiInfo
from wmlinksfromhell.destination import Destination


def test_standard_wikimedia_hosts_can_be_derived_without_one_entry_per_wiki(metadata):
    for language, family, dbname in (
        ("en", "wikipedia", "enwiki"),
        ("az", "wikipedia", "azwiki"),
        ("ru", "wikipedia", "ruwiki"),
        ("uk", "wikipedia", "ukwiki"),
        ("fa", "wikipedia", "fawiki"),
        ("az", "wikisource", "azwikisource"),
    ):
        wiki = metadata.resolve_wikimedia_hostname(f"{language}.{family}.org")
        assert wiki is not None
        assert wiki.dbname == dbname
        assert wiki.family == family
        assert wiki.language == language


def test_unknown_language_on_standard_wikimedia_family_is_related_but_not_guessed(metadata):
    assert metadata.resolve_wikimedia_hostname("zzzz.wikipedia.org") is None
    assert metadata.is_wikimedia_hostname("zzzz.wikipedia.org")
    assert metadata.related_destination_type("zzzz.wikipedia.org") is DestinationType.UNKNOWN


def test_ordinary_external_host_is_not_wikimedia(metadata):
    assert not metadata.is_wikimedia_hostname("example.com")
    assert metadata.related_destination_type("example.com") is None


def test_special_wikis_have_exact_metadata(metadata):
    assert metadata.wiki_by_hostname("commons.wikimedia.org").dbname == "commonswiki"
    assert metadata.wiki_by_hostname("www.wikidata.org").dbname == "wikidatawiki"
    assert metadata.wiki_by_hostname("meta.wikimedia.org").dbname == "metawiki"
    assert metadata.wiki_by_hostname("www.mediawiki.org").dbname == "mediawikiwiki"


def test_dbname_family_mapping_does_not_misclassify_special_wikis(metadata):
    assert metadata._family_from_dbname("wikidatawiki") == "wikidata"
    assert metadata._family_from_dbname("commonswiki") == "commons"
    assert metadata._family_from_dbname("metawiki") == "meta"
    assert metadata._family_from_dbname("enwiki") == "wikipedia"


def test_sitematrix_parser_discovers_regular_and_special_sites(metadata):
    data = {
        "sitematrix": {
            "count": 2,
            "0": {
                "code": "en",
                "name": "English",
                "site": [
                    {"code": "wiki", "dbname": "enwiki", "lang": "en", "sitename": "English Wikipedia", "url": "https://en.wikipedia.org"},
                    {"code": "wiktionary", "dbname": "enwiktionary", "lang": "en", "sitename": "English Wiktionary", "url": "https://en.wiktionary.org"},
                ],
            },
            "specials": [
                {"code": "wikidatawiki", "dbname": "wikidatawiki", "lang": "mul", "sitename": "Wikidata", "url": "https://www.wikidata.org"},
            ],
        }
    }
    wikis, languages = metadata._parse_sitematrix(data)
    assert languages["en"] == "English"
    assert wikis["enwiki"].family == "wikipedia"
    assert wikis["enwiktionary"].family == "wiktionary"
    assert wikis["wikidatawiki"].family == "wikidata"


def test_interwiki_entry_parser_classifies_known_wiki_target(metadata):
    entries = metadata._parse_interwiki_entries([
        {"prefix": "foo", "url": "https://en.wikipedia.org/wiki/$1", "local": True},
        {"prefix": "phab", "url": "https://phabricator.wikimedia.org/$1"},
    ])
    assert entries["foo"].destination_dbname == "enwiki"
    assert entries["foo"].destination_type is DestinationType.WIKI
    assert entries["phab"].destination_type is DestinationType.SERVICE


def test_source_resolution_accepts_host_url_and_dbname(metadata):
    assert metadata.resolve_source("enwiki").dbname == "enwiki"
    assert metadata.resolve_source("en.wikipedia.org").dbname == "enwiki"
    assert metadata.resolve_source("https://en.wikipedia.org/wiki/Foo").dbname == "enwiki"


def test_sitematrix_update_is_cached_and_unchanged_response_is_not_reprocessed(tmp_path, monkeypatch):
    from wmlinksfromhell.cache import MetadataCache

    cache = MetadataCache(tmp_path / "metadata.json")
    store = MetadataStore(cache=cache)
    payload = {
        "sitematrix": {
            "count": 1,
            "0": {"code": "xx", "name": "Test", "site": [
                {"code": "wiki", "dbname": "xxwiki", "lang": "xx", "sitename": "Test Wikipedia", "url": "https://xx.wikipedia.org"},
            ]},
        }
    }
    calls = {"count": 0}

    def fake_fetch(url, meta, timeout, force, retries):
        calls["count"] += 1
        return payload, {"ETag": '"one"'}, True

    monkeypatch.setattr(store, "_fetch_json", fake_fetch)
    assert store.update_sitematrix()
    assert store.wiki_by_dbname("xxwiki") is not None
    assert calls["count"] == 1

    calls["count"] = 0

    def unchanged(url, meta, timeout, force, retries):
        calls["count"] += 1
        return {}, {"ETag": '"one"'}, False

    monkeypatch.setattr(store, "_fetch_json", unchanged)
    assert not store.update_sitematrix()
    assert store.wiki_by_dbname("xxwiki") is not None
    assert calls["count"] == 1


def test_failed_refresh_keeps_existing_cache(tmp_path, monkeypatch):
    from wmlinksfromhell.cache import MetadataCache
    from wmlinksfromhell.exceptions import MetadataMissingError

    cache = MetadataCache(tmp_path / "metadata.json")
    store = MetadataStore(cache=cache)
    before = cache.empty()
    before["wikis"]["xxwiki"] = {
        "dbname": "xxwiki", "family": "wikipedia", "project": "wikipedia", "language": "xx",
        "language_name": "Test", "hostname": "xx.wikipedia.org", "article_path": "/wiki/$1",
        "script_path": "/w/index.php", "wikiid": "xxwiki", "sitename": "Test", "api_url": "https://xx.wikipedia.org/w/api.php",
        "metadata_source": "live", "site_code": "wiki", "is_multilingual": False,
    }
    cache.save(before)
    store = MetadataStore(cache=cache)

    def fail(*args, **kwargs):
        raise MetadataMissingError("network down")

    monkeypatch.setattr(store, "_fetch_json", fail)
    try:
        store.update_sitematrix()
    except MetadataMissingError:
        pass
    else:
        raise AssertionError("refresh should fail")

    assert cache.load()["wikis"]["xxwiki"]["dbname"] == "xxwiki"


def test_metadata_short_update_alias(monkeypatch, metadata):
    called = {}

    def fake_refresh(**kwargs):
        called.update(kwargs)
        return True

    monkeypatch.setattr(metadata, "refresh", fake_refresh)
    assert metadata.update("metawiki", max_age=3600, force=True, retries=1)
    assert called == {
        "dbname": "metawiki",
        "timeout": 10.0,
        "max_age": 3600,
        "force": True,
        "retries": 1,
    }


def test_sitematrix_special_sites_are_not_classified_as_language_projects(metadata):
    data = {
        "sitematrix": {
            "specials": [
                {"code": "wiki", "dbname": "arbcom_enwiki", "lang": "en", "sitename": "English Arbitration Committee", "url": "https://arbcom-en.wikipedia.org"},
                {"code": "wiki", "dbname": "boardwiki", "lang": "en", "sitename": "Wikimedia Board", "url": "https://board.wikimedia.org"},
                {"code": "wikiversity", "dbname": "betawikiversity", "lang": "en", "sitename": "Beta Wikiversity", "url": "https://beta.wikiversity.org"},
                {"code": "wiki", "dbname": "abstractwiki", "lang": "en", "sitename": "Abstract Wikipedia", "url": "https://abstract.wikipedia.org"},
            ]
        }
    }
    wikis, _ = metadata._parse_sitematrix(data)
    for dbname in ("arbcom_enwiki", "boardwiki", "betawikiversity", "abstractwiki"):
        assert wikis[dbname].is_standard_project is False


def test_special_wiki_without_prefix_is_not_rendered_as_w_family(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis["arbcom_enwiki"] = WikiInfo(
        dbname="arbcom_enwiki", family="special", project="arbcom_enwiki", language="en",
        language_name="English", hostname="arbcom-en.wikipedia.org", is_standard_project=False,
    )
    destination = resolver.resolve_url("https://arbcom-en.wikipedia.org/wiki/Foo").destination
    assert destination is not None
    with pytest.raises(ConversionError):
        resolver.to_interwiki(destination, source="metawiki")


def test_beta_wikiversity_is_bootstrapped_as_a_special_wiki(metadata):
    wiki = metadata.wiki_by_dbname("betawikiversity")
    assert wiki is not None
    assert wiki.family == "wikiversity"
    assert wiki.language == "en"
    assert wiki.is_standard_project is False
    assert wiki.hostname == "beta.wikiversity.org"


def test_global_interwiki_config_discovers_special_wikis_and_chapters(metadata):
    text = """
    <?php
    return [
        '__global:arbcom-zh' => '1 https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1',
        '__global:betawikiversity' => '1 https://beta.wikiversity.org/wiki/$1',
        '__global:wmde' => '0 https://wikimedia.de/$1',
        '__global:wmin' => '1 https://meta.wikimedia.org/wiki/Wikimedia_India',
        '__global:wm2016' => '1 https://wikimania2016.wikimedia.org/wiki/$1',
        '__global:github' => '0 https://github.com/$1',
        '__list:arbcom_enwiki' => 'w wikt q b n s chapter v voy',
    ];
    """
    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo(
            dbname="arbcom_zhwiki", family="special", project="arbcom_zhwiki", language="zh",
            language_name="Chinese", hostname="wikipedia-zh-arbcom.wikimedia.org", is_standard_project=False,
        ),
        "betawikiversity": WikiInfo(
            dbname="betawikiversity", family="wikiversity", project="wikiversity", language="en",
            language_name="English", hostname="beta.wikiversity.org", is_standard_project=False,
        ),
        "wikimania2016wiki": WikiInfo(
            dbname="wikimania2016wiki", family="wikimania", project="wikimania2016", language="en",
            language_name="English", hostname="wikimania2016.wikimedia.org", is_standard_project=False,
        ),
    })
    metadata._reindex()
    entries, lists = metadata._parse_interwiki_config(text)
    assert entries["arbcom-zh"].destination_dbname == "arbcom_zhwiki"
    assert entries["betawikiversity"].destination_dbname == "betawikiversity"
    assert entries["wmde"].destination_type is DestinationType.ORGANIZATION
    assert entries["wmin"].destination_type is DestinationType.ORGANIZATION
    assert entries["wm2016"].destination_dbname == "wikimania2016wiki"
    assert "github" not in entries
    assert lists["arbcom_enwiki"] == ("w", "wikt", "q", "b", "n", "s", "chapter", "v", "voy")


def test_global_noc_entries_classify_special_and_organization_targets(metadata):
    text = """<?php
    return [
        '__global:arbcom-zh' => '1 https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1',
        '__global:betawikiversity' => '1 https://beta.wikiversity.org/wiki/$1',
        '__global:abstract' => '1 https://abstract.wikipedia.org/wiki/$1',
        '__global:wmf' => '1 https://foundation.wikimedia.org/wiki/$1',
        '__global:wm2016' => '1 https://wikimania2016.wikimedia.org/wiki/$1',
        '__global:wmania' => '1 https://wikimania.wikimedia.org/wiki/$1',
        '__global:wmde' => '0 https://wikimedia.de/$1',
        '__global:wmin' => '1 https://meta.wikimedia.org/wiki/Wikimedia_India',
        '__global:wmhk' => '1 https://meta.wikimedia.org/wiki/Wikimedia_Hong_Kong',
    ];
    """
    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo("arbcom_zhwiki", "special", "arbcom_zhwiki", "zh", "Chinese", "wikipedia-zh-arbcom.wikimedia.org"),
        "betawikiversity": WikiInfo("betawikiversity", "wikiversity", "wikiversity", "en", "English", "beta.wikiversity.org"),
        "abstractwiki": WikiInfo("abstractwiki", "wikipedia", "wikipedia", "en", "English", "abstract.wikipedia.org"),
        "foundationwiki": WikiInfo("foundationwiki", "foundation", "foundation", "en", "English", "foundation.wikimedia.org"),
        "wikimania2016wiki": WikiInfo("wikimania2016wiki", "wikimania", "wikimania2016", "en", "English", "wikimania2016.wikimedia.org"),
        "wikimaniawiki": WikiInfo("wikimaniawiki", "wikimania", "wikimania", "en", "English", "wikimania.wikimedia.org"),
    })
    metadata._reindex()
    entries, _ = metadata._parse_interwiki_config(text)
    assert entries["arbcom-zh"].destination_type is DestinationType.WIKI
    assert entries["betawikiversity"].destination_type is DestinationType.WIKI
    assert entries["abstract"].destination_type is DestinationType.WIKI
    assert entries["wmf"].destination_type is DestinationType.WIKI
    assert entries["wm2016"].destination_type is DestinationType.WIKI
    assert entries["wmania"].destination_type is DestinationType.WIKI
    assert entries["wmde"].destination_type is DestinationType.ORGANIZATION
    assert entries["wmin"].destination_type is DestinationType.ORGANIZATION
    assert entries["wmhk"].destination_type is DestinationType.ORGANIZATION


def test_sitematrix_language_group_sites_are_marked_standard_projects(metadata):
    data = {
        "sitematrix": {
            "0": {"code": "en", "name": "English", "site": [
                {"code": "wiki", "dbname": "enwiki", "lang": "en", "url": "https://en.wikipedia.org", "sitename": "English Wikipedia"},
                {"code": "wiktionary", "dbname": "enwiktionary", "lang": "en", "url": "https://en.wiktionary.org", "sitename": "English Wiktionary"},
            ]},
            "specials": [],
        }
    }
    wikis, _ = metadata._parse_sitematrix(data)
    assert wikis["enwiki"].is_standard_project is True
    assert wikis["enwiktionary"].is_standard_project is True


def test_real_noc_config_exposes_family_language_aliases(metadata):
    text = """
    '_wiki:simple' => '1 https://simple.wikipedia.org/wiki/$1',
    '_wiki:en-simple' => '1 https://simple.wikipedia.org/wiki/$1',
    '_wiktionary:simple' => '1 https://simple.wiktionary.org/wiki/$1',
    '_wikiversity:mul' => '1 https://beta.wikiversity.org/wiki/$1',
    """
    metadata._wikis.update({
        "simplewiki": WikiInfo("simplewiki", "wikipedia", "wikipedia", "en", "Simple English", "simple.wikipedia.org"),
        "simplewiktionary": WikiInfo("simplewiktionary", "wiktionary", "wiktionary", "en", "Simple English", "simple.wiktionary.org"),
        "betawikiversity": WikiInfo("betawikiversity", "wikiversity", "wikiversity", "en", "English", "beta.wikiversity.org"),
    })
    metadata._reindex()
    aliases, prefixes = metadata._parse_family_language_entries(text)
    assert aliases[("wikipedia", "simple")] == "simplewiki"
    assert aliases[("wikipedia", "en-simple")] == "simplewiki"
    assert aliases[("wiktionary", "simple")] == "simplewiktionary"
    assert aliases[("wikiversity", "mul")] == "betawikiversity"
    assert prefixes[("wikipedia", "simplewiki")] == "simple"


def test_wikimedia_chapter_domain_family_is_recognized(metadata):
    assert metadata.is_wikimedia_hostname("www.wikimedia.ch")
    assert metadata.is_wikimedia_hostname("wikimedia.de")
    assert metadata.is_wikimedia_hostname("wikimediadc.org")
    assert not metadata.is_wikimedia_hostname("wikimedia-example.com")


def test_global_noc_prefixes_cover_special_wikis_and_chapters(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo("arbcom_zhwiki", "special", "arbcom_zhwiki", "zh", "Chinese", "wikipedia-zh-arbcom.wikimedia.org"),
        "abstractwiki": WikiInfo("abstractwiki", "wikipedia", "wikipedia", "en", "English", "abstract.wikipedia.org", is_standard_project=False),
        "wikimania2016wiki": WikiInfo("wikimania2016wiki", "wikimania", "wikimania2016", "en", "English", "wikimania2016.wikimedia.org"),
        "wikimaniawiki": WikiInfo("wikimaniawiki", "wikimania", "wikimania", "en", "English", "wikimania.wikimedia.org"),
        "betawikiversity": WikiInfo("betawikiversity", "wikiversity", "wikiversity", "en", "English", "beta.wikiversity.org", is_standard_project=False),
    })
    metadata._reindex()
    text = Path(__file__).parent.joinpath("fixtures", "noc_specials.txt").read_text(encoding="utf-8")
    entries, _ = metadata._parse_interwiki_config(text)
    metadata._global_interwikis.update(entries)

    cases = (
        ("arbcom_zhwiki", "arbcom-zh:Foo"),
        ("abstractwiki", "abstract:Foo"),
        ("wikimania2016wiki", "wm2016:Foo"),
        ("wikimaniawiki", "wmania:Foo"),
        ("betawikiversity", "betawikiversity:Foo"),
    )
    for dbname, expected in cases:
        destination = resolver.resolve_url(f"https://{metadata._wikis[dbname].hostname}/wiki/Foo").destination
        assert destination is not None
        assert resolver.to_interwiki(destination, source="metawiki") == expected


def test_fixed_global_prefix_wins_exact_url_over_meta_shortcut(resolver, metadata):
    text = Path(__file__).parent.joinpath("fixtures", "noc_specials.txt").read_text(encoding="utf-8")
    entries, _ = metadata._parse_interwiki_config(text)
    metadata._global_interwikis.update(entries)

    destination = resolver.resolve_url("https://meta.wikimedia.org/wiki/Wikimedia_India").destination
    assert destination is not None
    assert resolver.to_interwiki(destination, source="metawiki") == "wmin"


def test_noc_real_world_special_prefix_classes_are_not_collapsed(metadata, resolver):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo("arbcom_zhwiki", "special", "arbcom_zhwiki", "zh", "Chinese", "wikipedia-zh-arbcom.wikimedia.org"),
        "abstractwiki": WikiInfo("abstractwiki", "wikipedia", "wikipedia", "en", "English", "abstract.wikipedia.org", is_standard_project=False),
        "wikimaniawiki": WikiInfo("wikimaniawiki", "wikimania", "wikimania", "en", "English", "wikimania.wikimedia.org", is_standard_project=False),
        "wikimania2016wiki": WikiInfo("wikimania2016wiki", "wikimania", "wikimania2016", "en", "English", "wikimania2016.wikimedia.org", is_standard_project=False),
        "betawikiversity": WikiInfo("betawikiversity", "wikiversity", "wikiversity", "en", "English", "beta.wikiversity.org", is_standard_project=False),
    })
    metadata._reindex()
    entries, _ = metadata._parse_interwiki_config(Path(__file__).parent.joinpath("fixtures", "noc_specials.txt").read_text(encoding="utf-8"))
    metadata._global_interwikis.update(entries)

    for dbname, expected in (
        ("arbcom_zhwiki", "arbcom-zh:Foo"),
        ("abstractwiki", "abstract:Foo"),
        ("wikimaniawiki", "wmania:Foo"),
        ("wikimania2016wiki", "wm2016:Foo"),
        ("betawikiversity", "betawikiversity:Foo"),
    ):
        destination = resolver.resolve_url(f"https://{metadata._wikis[dbname].hostname}/wiki/Foo").destination
        assert destination is not None
        assert resolver.to_interwiki(destination, source="metawiki") == expected

    for dbname in ("arbcom_enwiki", "boardwiki", "checkuserwiki"):
        host = {
            "arbcom_enwiki": "wikipedia-en-arbcom.wikimedia.org",
            "boardwiki": "board.wikimedia.org",
            "checkuserwiki": "checkuser.wikimedia.org",
        }[dbname]
        metadata._wikis[dbname] = WikiInfo(dbname, "special", dbname, "en", "English", host, is_standard_project=False)
    metadata._reindex()
    for dbname in ("arbcom_enwiki", "boardwiki", "checkuserwiki"):
        destination = resolver.resolve_url(f"https://{metadata._wikis[dbname].hostname}/wiki/Foo").destination
        assert destination is not None
        with __import__("pytest").raises(Exception):
            resolver.to_interwiki(destination, source="metawiki")


def test_global_noc_targets_are_reenriched_after_site_metadata_load(metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._global_interwikis["arbcom-zh"] = InterwikiEntry(
        prefix="Arbcom-zh",
        url="https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1",
    )
    metadata._global_interwikis["wm2016"] = InterwikiEntry(
        prefix="wm2016",
        url="https://wikimania2016.wikimedia.org/wiki/$1",
    )
    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo("arbcom_zhwiki", "special", "arbcom_zhwiki", "zh", "Chinese", "wikipedia-zh-arbcom.wikimedia.org"),
        "wikimania2016wiki": WikiInfo("wikimania2016wiki", "special", "wikimania2016", "en", "English", "wikimania2016.wikimedia.org"),
    })
    metadata._reindex()
    metadata._enrich_global_interwikis()

    assert metadata.global_interwiki_entry("arbcom-zh").destination_dbname == "arbcom_zhwiki"
    assert metadata.global_interwiki_entry("arbcom-zh").destination_type is DestinationType.WIKI
    assert metadata.global_interwiki_entry("wm2016").destination_dbname == "wikimania2016wiki"
    assert metadata.global_interwiki_entry("wm2016").destination_type is DestinationType.WIKI


def test_update_does_not_skip_when_global_noc_metadata_is_missing(metadata, monkeypatch):
    calls = []
    monkeypatch.setattr(metadata.cache, "is_expired", lambda max_age: False)
    monkeypatch.setattr(metadata, "update_sitematrix", lambda **kwargs: calls.append("sitematrix") or False)
    monkeypatch.setattr(metadata, "update_interwiki_config", lambda **kwargs: calls.append("interwiki") or False)
    monkeypatch.setattr(metadata, "update_wiki_metadata", lambda dbname, **kwargs: calls.append("siteinfo") or False)

    metadata.update(max_age=3600)
    assert calls == ["sitematrix", "interwiki", "siteinfo"]


def test_stale_standard_project_flag_is_repaired(metadata):
    metadata._wikis["enwiki"] = WikiInfo(
        "enwiki", "wikipedia", "wikipedia", "en", "English", "en.wikipedia.org",
        site_code="wiki", is_standard_project=False,
    )
    assert metadata.wiki_by_dbname("enwiki").is_standard_project is True


def test_all_wikis_repairs_stale_standard_project_flag(metadata):
    metadata._wikis["enwiki"] = WikiInfo(
        "enwiki", "wikipedia", "wikipedia", "en", "English", "en.wikipedia.org",
        site_code="wiki", is_standard_project=False,
    )
    assert next(w for w in metadata.all_wikis() if w.dbname == "enwiki").is_standard_project is True


def test_wiki_destination_does_not_choose_service_prefix_for_same_hostname(metadata):
    from wmlinksfromhell.destination import Destination

    metadata.load_interwiki_config(
        (Path(__file__).parent / "fixtures" / "interwiki-config.txt").read_text(encoding="utf-8")
    )
    destination = Destination(
        DestinationType.WIKI,
        family="meta",
        project="meta",
        language="en",
        dbname="metawiki",
        wikiid="metawiki",
        hostname="meta.wikimedia.org",
        title="SomePage",
        is_wikimedia_project=True,
        is_standard_project=False,
    )
    assert metadata.interwiki_prefix_for_destination(destination, "metawiki") == "m"


def test_special_site_prefixes_can_be_loaded_after_sitematrix(metadata):
    sitematrix = {
        "sitematrix": {
            "specials": [
                {
                    "code": "wiki",
                    "dbname": "abstractwiki",
                    "lang": "en",
                    "sitename": "Abstract Wikipedia",
                    "url": "https://abstract.wikipedia.org",
                },
                {
                    "code": "wiki",
                    "dbname": "wikimaniateamwiki",
                    "lang": "en",
                    "sitename": "Wikimania Team",
                    "url": "https://wikimaniateam.wikimedia.org",
                },
                {
                    "code": "wiki",
                    "dbname": "bdwikimedia",
                    "lang": "en",
                    "sitename": "Wikimedia Bangladesh",
                    "url": "https://bd.wikimedia.org",
                },
            ]
        }
    }
    metadata.load_sitematrix(sitematrix)
    metadata.load_interwiki_config(
        (Path(__file__).parent / "fixtures" / "noc_specials.txt").read_text(encoding="utf-8")
    )
    for dbname, prefix in (
        ("abstractwiki", "abstract"),
        ("wikimaniateamwiki", "wmteam"),
        ("bdwikimedia", "wmbd"),
    ):
        wiki = metadata.wiki_by_dbname(dbname)
        assert metadata.interwiki_prefix_for_destination(
            Destination(
                DestinationType.WIKI,
                family=wiki.family,
                project=wiki.project,
                language=wiki.language,
                dbname=wiki.dbname,
                wikiid=wiki.wikiid,
                hostname=wiki.hostname,
                title="MediaWiki:Gadget:Xtools.js",
                is_wikimedia_project=True,
                is_standard_project=wiki.is_standard_project,
            ),
            "metawiki",
        ) == prefix


def test_standard_wiki_url_rendering_survives_stale_cache(metadata):
    metadata._wikis["enwiki"] = WikiInfo(
        "enwiki", "wikipedia", "wikipedia", "en", "English", "en.wikipedia.org",
        site_code="wiki", is_standard_project=False,
    )
    metadata._reindex()
    wiki = metadata.wiki_by_hostname("en.wikipedia.org")
    assert wiki.is_standard_project is True


def test_special_wikimedia_chapter_site_uses_chapter_prefix(metadata):
    from wmlinksfromhell.models import WikiInfo
    wiki = WikiInfo(
        "bdwikimedia", "special", "bdwikimedia", "en", "English",
        "bd.wikimedia.org", is_standard_project=False,
    )
    metadata._wikis["bdwikimedia"] = wiki
    metadata._reindex()
    destination = Destination(
        DestinationType.WIKI,
        family=wiki.family,
        project=wiki.project,
        language=wiki.language,
        dbname=wiki.dbname,
        wikiid=wiki.wikiid,
        hostname=wiki.hostname,
        title="MediaWiki:Gadget:Xtools.js",
        is_wikimedia_project=True,
        is_standard_project=False,
    )
    assert metadata.interwiki_prefix_for_destination(destination, "metawiki") == "wmbd"


def test_special_sites_with_global_prefixes_resolve_after_metadata_ingest(metadata):
    metadata.load_sitematrix({
        "sitematrix": {
            "specials": [
                {"code": "wiki", "dbname": "abstractwiki", "lang": "en", "url": "https://abstract.wikipedia.org"},
                {"code": "wiki", "dbname": "wikimaniateamwiki", "lang": "en", "url": "https://wikimaniateam.wikimedia.org"},
            ]
        }
    })
    metadata.load_interwiki_config(
        (Path(__file__).parent / "fixtures" / "noc_specials.txt").read_text(encoding="utf-8")
    )
    for dbname, prefix in (("abstractwiki", "abstract"), ("wikimaniateamwiki", "wmteam")):
        wiki = metadata.wiki_by_dbname(dbname)
        destination = Destination(
            DestinationType.WIKI, wiki.family, wiki.project, wiki.language, wiki.dbname,
            wiki.wikiid, wiki.hostname, "MediaWiki:Gadget:Xtools.js",
            is_wikimedia_project=True, is_standard_project=False,
        )
        assert metadata.interwiki_prefix_for_destination(destination, "metawiki") == prefix


def test_update_wiki_metadata_uses_api_endpoint(tmp_path, monkeypatch):
    from wmlinksfromhell.cache import MetadataCache
    from wmlinksfromhell.models import WikiInfo

    metadata = MetadataStore(cache=MetadataCache(tmp_path / "metadata.json"))
    metadata._wikis["xxwiki"] = WikiInfo(
        "xxwiki", "wikipedia", "wikipedia", "xx", "Test", "xx.wikipedia.org",
    )
    metadata._reindex()
    captured = {}

    def fake_fetch(url, meta, timeout, force, retries):
        captured["url"] = url
        return {
            "query": {
                "general": {
                    "articlepath": "/wiki/$1",
                    "scriptpath": "/w/index.php",
                    "sitename": "Test Wikipedia",
                    "server": "https://xx.wikipedia.org",
                },
                "interwikimap": [],
                "namespaces": {},
                "namespacealiases": [],
            }
        }, {}, True

    monkeypatch.setattr(metadata, "_fetch_json", fake_fetch)
    assert metadata.update_wiki_metadata("xxwiki")
    assert captured["url"].startswith("https://xx.wikipedia.org/w/api.php?")


def test_resolve_source_supports_page_like_site_property(metadata):
    class FakeSite:
        def dbName(self):
            return "enwiki"

    class FakePage:
        site = FakeSite()

        def title(self):
            return "Example/Subpage"

    assert metadata.resolve_source(FakePage()).dbname == "enwiki"


def test_resolve_source_supports_page_like_site_method(metadata):
    class FakeSite:
        def dbName(self):
            return "enwiki"

    class FakePage:
        def site(self):
            return FakeSite()

        def title(self):
            return "Example/Subpage"

    assert metadata.resolve_source(FakePage()).dbname == "enwiki"


def test_sitematrix_parser_ignores_malformed_collection_members(metadata):
    data = {
        "sitematrix": {
            "0": {
                "code": "en",
                "name": "English",
                "site": [
                    "unexpected-string",
                    {
                        "code": "wiki",
                        "dbname": "enwiki",
                        "lang": "en",
                        "sitename": "English Wikipedia",
                        "url": "https://en.wikipedia.org",
                    },
                ],
            },
            "specials": [
                "unexpected-string",
                {
                    "code": "wikidatawiki",
                    "dbname": "wikidatawiki",
                    "lang": "mul",
                    "sitename": "Wikidata",
                    "url": "https://www.wikidata.org",
                },
            ],
        }
    }

    wikis, _ = metadata._parse_sitematrix(data)
    assert set(wikis) == {"enwiki", "wikidatawiki"}


def test_update_wiki_metadata_rejects_malformed_query(tmp_path, monkeypatch):
    from wmlinksfromhell.cache import MetadataCache

    metadata = MetadataStore(cache=MetadataCache(tmp_path / "metadata.json"))
    metadata._wikis["xxwiki"] = WikiInfo(
        "xxwiki", "wikipedia", "wikipedia", "xx", "Test", "xx.wikipedia.org",
    )
    metadata._reindex()

    monkeypatch.setattr(
        metadata,
        "_fetch_json",
        lambda *args, **kwargs: ({"query": "bad"}, {}, True),
    )

    with pytest.raises(Exception) as exc:
        metadata.update_wiki_metadata("xxwiki")

    assert isinstance(exc.value, Exception)
    assert "invalid query object" in str(exc.value)


def test_parse_namespaces_accepts_mapping_form(metadata):
    names, aliases = metadata._parse_namespaces({
        "namespaces": {
            "0": {"id": 0, "canonical": ""},
            "2": {"id": 2, "name": "User"},
        },
        "namespacealiases": {
            "0": {"id": 2, "alias": "Benutzer"},
        },
    })
    assert "user" in names
    assert aliases["benutzer"] == "User"


def test_metadata_parsers_ignore_malformed_rows(metadata):
    entries = metadata._parse_interwiki_entries([
        "bad",
        {"prefix": "w", "url": "https://en.wikipedia.org/wiki/$1"},
    ])
    assert entries["w"].prefix == "w"

    names, aliases = metadata._parse_namespaces({
        "namespaces": ["bad", {"id": 0, "canonical": ""}, {"id": 2, "name": "User"}],
        "namespacealiases": ["bad", {"id": 2, "alias": "Benutzer"}],
    })
    assert "user" in names
    assert aliases["benutzer"] == "User"
