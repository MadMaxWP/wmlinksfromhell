import pytest

from wmlinksfromhell.exceptions import ConversionError
from wmlinksfromhell.models import DestinationType


def test_url_to_interwiki(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Page_name")
    text = resolver.to_interwiki(result.destination)
    assert text == "w:en:Page name"


def test_url_to_interwiki_with_fragment(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Page_name#Section")
    text = resolver.to_interwiki(result.destination)
    assert text == "w:en:Page name#Section"


def test_url_to_interwiki_with_long_project_prefix(resolver):
    result = resolver.resolve_url("https://hi.wikipedia.org/wiki/Apple")
    assert resolver.to_interwiki(result.destination, long_project_prefix=True) == "wikipedia:hi:Apple"
    assert resolver.resolve_url("https://hi.wikipedia.org/wiki/Apple", long_project_prefix=True).canonical_interwiki == "wikipedia:hi:Apple"


def test_long_project_language_interwiki_resolves_and_converts(resolver):
    result = resolver.resolve_interwiki("wikipedia:hi:Apple")
    assert result.destination.dbname == "hiwiki"
    assert result.canonical_prefix == "w:hi"
    assert result.canonical_interwiki == "w:hi:Apple"
    assert resolver.to_interwiki(result.destination) == "w:hi:Apple"
    assert resolver.to_interwiki(result.destination, long_project_prefix=True) == "wikipedia:hi:Apple"


def test_commons_url_to_interwiki(resolver):
    result = resolver.resolve_url("https://commons.wikimedia.org/wiki/File:Example.jpg")
    text = resolver.to_interwiki(result.destination)
    assert text == "c:File:Example.jpg"


def test_wikidata_url_to_interwiki(resolver):
    result = resolver.resolve_url("https://www.wikidata.org/wiki/Q42")
    text = resolver.to_interwiki(result.destination)
    assert text == "d:Q42"


def test_interwiki_to_url(resolver):
    result = resolver.resolve_interwiki(":w:en:Page name")
    url = resolver.to_url(result.destination)
    assert url == "https://en.wikipedia.org/wiki/Page_name"


def test_url_to_local_when_on_source_wiki(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Apple")
    local = resolver.to_local(result.destination, source="enwiki")
    assert local == "Apple"


def test_url_to_local_fails_off_source_wiki(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Apple")
    with pytest.raises(ConversionError):
        resolver.to_local(result.destination, source="dewiki")


def test_interwiki_to_local_when_source_matches(resolver):
    result = resolver.resolve_interwiki(":w:en:Apple")
    local = resolver.to_local(result.destination, source="enwiki")
    assert local == "Apple"


def test_revision_url_conversion_preserves_oldid(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/w/index.php?title=Foo&oldid=123456")
    url = resolver.to_url(result.destination)
    assert "oldid=123456" in url
    assert "Foo" in url


def test_cannot_convert_unresolved_destination_to_url(resolver):
    result = resolver.resolve_interwiki(":en:Apple")  # context_required, no destination
    assert result.destination is None


def test_chapter_destination_renders_back_to_its_prefix(resolver):
    result = resolver.resolve_interwiki("wmin")
    text = resolver.to_interwiki(result.destination)
    assert text == "wmin"


def test_service_destination_renders_back_to_its_prefix(resolver):
    result = resolver.resolve_interwiki("phab:T12345")
    text = resolver.to_interwiki(result.destination)
    assert text == "phab:T12345"


def test_url_to_interwiki_writes_permanent_link_for_oldid(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/w/index.php?title=Foo&oldid=123456")
    assert result.canonical_interwiki == "w:en:Special:PermanentLink/123456"


def test_url_to_interwiki_writes_special_diff_for_symbolic_diff(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/w/index.php?title=Foo&diff=prev&oldid=123456")
    assert result.canonical_interwiki == "w:en:Special:Diff/123456/prev"


def test_url_to_url_roundtrip_preserves_symbolic_diff(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/w/index.php?title=Foo&diff=prev&oldid=123456")
    url = resolver.to_url(result.destination)
    assert "diff=prev" in url
    assert "oldid=123456" in url


def test_direct_url_result_exposes_canonical_interwiki(resolver):
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Apple")
    assert result.canonical_interwiki == "w:en:Apple"


def test_special_wiki_does_not_fall_back_to_family_prefix(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis["boardwiki"] = WikiInfo(
        dbname="boardwiki", family="special", project="boardwiki", language="en",
        language_name="English", hostname="board.wikimedia.org", is_standard_project=False,
    )
    destination = resolver.resolve_url("https://board.wikimedia.org/wiki/Foo").destination
    assert destination is not None
    with pytest.raises(ConversionError):
        resolver.to_interwiki(destination, source="metawiki")


def test_special_wiki_uses_real_source_interwiki_prefix(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo, DestinationType

    metadata._wikis["arbcom_zhwiki"] = WikiInfo(
        dbname="arbcom_zhwiki", family="special", project="arbcom_zhwiki", language="zh",
        language_name="Chinese", hostname="wikipedia-zh-arbcom.wikimedia.org", is_standard_project=False,
    )
    metadata._reindex()
    metadata._interwiki_maps["metawiki"] = {
        "arbcom-zh": InterwikiEntry(
            prefix="Arbcom-zh",
            url="https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1",
            destination_dbname="arbcom_zhwiki",
            destination_type=DestinationType.WIKI,
        )
    }
    destination = resolver.resolve_url("https://wikipedia-zh-arbcom.wikimedia.org/wiki/Foo").destination
    assert destination is not None
    assert resolver.to_interwiki(destination, source="metawiki") == "Arbcom-zh:Foo"


def test_beta_wikiversity_is_a_wiki_and_uses_its_real_prefix(resolver):
    result = resolver.resolve_url("https://beta.wikiversity.org/wiki/Foo")
    assert result.destination is not None
    assert result.destination.destination_type is DestinationType.WIKI
    assert resolver.to_interwiki(result.destination, source="metawiki") == "betawikiversity:Foo"


def test_special_and_beta_wikis_use_real_global_prefixes(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo

    metadata._wikis.update({
        "arbcom_zhwiki": WikiInfo(
            dbname="arbcom_zhwiki", family="special", project="arbcom_zhwiki", language="zh",
            language_name="Chinese", hostname="wikipedia-zh-arbcom.wikimedia.org", is_standard_project=False,
        ),
        "betawikiversity": WikiInfo(
            dbname="betawikiversity", family="wikiversity", project="wikiversity", language="en",
            language_name="English", hostname="beta.wikiversity.org", is_standard_project=False,
        ),
    })
    metadata._reindex()
    metadata._global_interwikis.update({
        "arbcom-zh": InterwikiEntry(
            prefix="Arbcom-zh", url="https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1",
            destination_dbname="arbcom_zhwiki", destination_type=DestinationType.WIKI,
        ),
        "betawikiversity": InterwikiEntry(
            prefix="betawikiversity", url="https://beta.wikiversity.org/wiki/$1",
            destination_dbname="betawikiversity", destination_type=DestinationType.WIKI,
        ),
    })
    for url, expected in (
        ("https://wikipedia-zh-arbcom.wikimedia.org/wiki/Foo", "Arbcom-zh:Foo"),
        ("https://beta.wikiversity.org/wiki/Foo", "betawikiversity:Foo"),
    ):
        destination = resolver.resolve_url(url).destination
        assert resolver.to_interwiki(destination, source="metawiki") == expected


def test_special_wiki_prefixes_are_taken_from_global_metadata(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo, InterwikiEntry

    for dbname, family, project, lang, host, prefix in (
        ("abstractwiki", "wikipedia", "wikipedia", "en", "abstract.wikipedia.org", "abstract"),
        ("wikimania2016wiki", "wikimania", "wikimania2016", "en", "wikimania2016.wikimedia.org", "wm2016"),
        ("wikimaniawiki", "wikimania", "wikimania", "en", "wikimania.wikimedia.org", "wmania"),
        ("foundationwiki", "foundation", "foundation", "en", "foundation.wikimedia.org", "wmf"),
    ):
        metadata._wikis[dbname] = WikiInfo(dbname, family, project, lang, "English", host, is_standard_project=False)
        metadata._global_interwikis[prefix] = InterwikiEntry(prefix, f"https://{host}/wiki/$1", destination_dbname=dbname, destination_type=DestinationType.WIKI)
    metadata._reindex()

    for dbname, prefix in (("abstractwiki", "abstract"), ("wikimania2016wiki", "wm2016"), ("wikimaniawiki", "wmania"), ("foundationwiki", "wmf")):
        destination = resolver.resolve_url(f"https://{metadata._wikis[dbname].hostname}/wiki/Foo").destination
        assert destination is not None
        assert resolver.to_interwiki(destination) == f"{prefix}:Foo"


def test_wikimania_global_prefixes_override_service_bootstrap(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo, InterwikiEntry

    for dbname, family, project, host, prefix in (
        ("wikimaniawiki", "wikimania", "wikimania", "wikimania.wikimedia.org", "wmania"),
        ("wikimania2016wiki", "wikimania", "wikimania2016", "wikimania2016.wikimedia.org", "wm2016"),
    ):
        metadata._wikis[dbname] = WikiInfo(dbname, family, project, "en", "English", host, is_standard_project=False)
        metadata._global_interwikis[prefix] = InterwikiEntry(prefix, f"https://{host}/wiki/$1", destination_dbname=dbname, destination_type=DestinationType.WIKI)
    metadata._reindex()

    for dbname, prefix in (("wikimaniawiki", "wmania"), ("wikimania2016wiki", "wm2016")):
        result = resolver.resolve_interwiki(prefix + ":Foo")
        assert result.destination.dbname == dbname
        assert result.destination.destination_type is DestinationType.WIKI
        assert result.canonical_interwiki == f"{prefix}:Foo"


def test_global_organization_template_is_used_for_url_rendering(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry

    metadata._global_interwikis["wmde"] = InterwikiEntry(
        prefix="wmde",
        url="https://wikimedia.de/$1",
        destination_type=DestinationType.ORGANIZATION,
    )
    result = resolver.resolve_interwiki("wmde:Foo")
    assert resolver.to_url(result.destination) == "https://wikimedia.de/Foo"


def test_global_tool_prefix_url_template_is_used_for_rendering(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry

    metadata._global_interwikis["gs"] = InterwikiEntry(
        prefix="gs",
        url="https://global-search.toolforge.org/?q=$1",
        destination_type=DestinationType.TOOL,
    )
    result = resolver.resolve_interwiki("gs:MediaWiki:Gadget:Xtools.js")
    assert result.destination.destination_type is DestinationType.TOOL
    assert resolver.to_url(result.destination) == "https://global-search.toolforge.org/?q=MediaWiki:Gadget:Xtools.js"


def test_fixed_noc_chapter_alias_beats_meta_service_alias(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, DestinationType

    metadata._global_interwikis["wmin"] = InterwikiEntry(
        prefix="wmin",
        url="https://meta.wikimedia.org/wiki/Wikimedia_India",
        destination_dbname="metawiki",
        destination_type=DestinationType.ORGANIZATION,
    )
    destination = resolver.resolve_url("https://meta.wikimedia.org/wiki/Wikimedia_India").destination
    assert destination is not None
    assert resolver.to_interwiki(destination, source="metawiki") == "wmin"


def test_more_noc_special_wikis_use_real_prefixes(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo, DestinationType

    entries = {
        "wikimaniateamwiki": ("wikimaniateam.wikimedia.org", "wmania:Foo"),
        "nostalgiawiki": ("nostalgia.wikipedia.org", "nostalgia:Foo"),
        "tenwiki": ("ten.wikipedia.org", "tenwiki:Foo"),
        "test2wiki": ("test2.wikipedia.org", "test2wiki:Foo"),
        "testcommonswiki": ("test-commons.wikimedia.org", "testcommons:Foo"),
        "testwikidatawiki": ("test.wikidata.org", "testwikidata:Foo"),
    }
    for dbname, (host, expected) in entries.items():
        metadata._wikis[dbname] = WikiInfo(dbname, "special", dbname, "en", "English", host, is_standard_project=False)
        prefix = expected.split(":", 1)[0]
        metadata._global_interwikis[prefix] = InterwikiEntry(
            prefix=prefix,
            url=f"https://{host}/wiki/$1",
            destination_dbname=dbname,
            destination_type=DestinationType.WIKI,
        )
    metadata._reindex()

    for dbname, (host, expected) in entries.items():
        destination = resolver.resolve_url(f"https://{host}/wiki/Foo").destination
        assert destination is not None
        assert resolver.to_interwiki(destination, source="metawiki") == expected
