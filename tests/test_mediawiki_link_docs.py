import pytest

from wmlinksfromhell.exceptions import ConversionError
from wmlinksfromhell.models import DestinationType, ResolutionStatus
from wmlinksfromhell.resolver import Resolver
from wmlinksfromhell.url import parse_url


class FakePage:
    def __init__(self, dbname="enwiki", title="Help:Links"):
        self._dbname = dbname
        self._title = title

    def dbName(self):
        return self._dbname

    def title(self):
        return self._title


def test_http_wikimedia_url_resolves(metadata):
    result = Resolver(metadata).resolve_url("http://en.wikipedia.org/wiki/Apple")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"
    assert result.title == "Apple"


def test_www_wikipedia_is_the_portal_not_english_wikipedia(metadata):
    result = Resolver(metadata).resolve_url("https://www.wikipedia.org/")
    assert result.status is ResolutionStatus.EXTERNAL
    assert result.destination.destination_type is DestinationType.EXTERNAL
    assert result.destination.is_wikimedia_project is True


def test_mediawiki_root_alias_resolves(metadata):
    result = Resolver(metadata).resolve_url("https://mediawiki.org/wiki/Help:Links")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "mediawikiwiki"
    assert result.title == "Links"


def test_invalid_percent_encoding_is_rejected(metadata):
    dest, reason = parse_url("https://en.wikipedia.org/wiki/%ZZ", metadata)
    assert dest is None
    assert "percent-encoding" in reason


def test_reserved_percent_encoded_title_characters_decode_once(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/wiki/Foo%3ABar", metadata)
    assert dest is not None
    assert dest.title == "Foo:Bar"


def test_oldid_without_title_is_revision_identity(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url("https://en.wikipedia.org/w/index.php?oldid=53587")
    assert result.revision == 53587
    assert result.title is None
    assert resolver.to_interwiki(result.destination) == "w:en:Special:PermanentLink/53587"


def test_oldid_dominates_page_identity_when_title_differs(metadata):
    resolver = Resolver(metadata)
    a = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Help:Links&oldid=53587"
    ).destination
    b = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Completely_Wrong&oldid=53587"
    ).destination
    assert a.same_page_as(b)
    assert a == b


def test_diff_forms(metadata):
    resolver = Resolver(metadata)
    cases = [
        ("https://en.wikipedia.org/w/index.php?diff=1242287", None, 1242287, "w:en:Special:Diff/1242287"),
        ("https://en.wikipedia.org/w/index.php?oldid=1242286&diff=1242287", 1242286, 1242287, "w:en:Special:Diff/1242286/1242287"),
        ("https://en.wikipedia.org/w/index.php?oldid=1242287&diff=prev", 1242287, "prev", "w:en:Special:Diff/1242287/prev"),
        ("https://en.wikipedia.org/w/index.php?oldid=1242287&diff=next", 1242287, "next", "w:en:Special:Diff/1242287/next"),
        ("https://en.wikipedia.org/w/index.php?oldid=1242287&diff=cur", 1242287, "cur", "w:en:Special:Diff/1242287/cur"),
    ]
    for url, revision, diff, expected in cases:
        result = resolver.resolve_url(url)
        assert result.revision == revision
        assert result.diff == diff
        assert resolver.to_interwiki(result.destination) == expected


def test_symbolic_diff_without_oldid_falls_back_to_page_interwiki(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=prev"
    )
    assert resolver.to_interwiki(result.destination) == "w:en:Apple"


def test_namespaced_special_edit_target_keeps_namespace(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/wiki/Special:Edit/MediaWiki:Gadget:Xtools.js"
    )
    assert result.status is ResolutionStatus.RESOLVED
    assert result.action == "edit"
    assert result.namespace == "MediaWiki"
    assert result.title == "Gadget:Xtools.js"
    assert resolver.to_interwiki(result.destination) == "w:en:Special:Edit/MediaWiki:Gadget:Xtools.js"


def test_edit_section_and_new_are_preserved_with_page_interwiki_fallback(metadata):
    resolver = Resolver(metadata)
    for section in ("5", "new"):
        result = resolver.resolve_url(
            f"https://en.wikipedia.org/w/index.php?title=Apple&action=edit&section={section}"
        )
        assert result.action == "edit"
        assert ("section", section) in result.destination.query_parameters
        assert "section=" + section in result.url
        assert resolver.to_interwiki(result.destination) == "w:en:Apple"


def test_purge_raw_history_and_other_documented_actions_are_preserved(metadata):
    resolver = Resolver(metadata)
    for action in (
        "purge", "raw", "view", "watch", "unwatch", "delete",
        "revert", "rollback", "unprotect", "info", "markpatrolled",
        "validate", "render", "deletetrackback", "history",
    ):
        result = resolver.resolve_url(
            f"https://en.wikipedia.org/w/index.php?title=Apple&action={action}"
        )
        assert result.status is ResolutionStatus.RESOLVED
        assert result.action == action
        assert f"action={action}" in result.url


def test_uselang_is_preserved_with_page_interwiki_fallback(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://commons.wikimedia.org/w/index.php?title=Glavna_stran&uselang=sl"
    )
    assert result.destination.query_parameters == (("uselang", "sl"),)
    assert "uselang=sl" in result.url
    assert resolver.to_interwiki(result.destination) == "c:Glavna stran"


def test_protocol_relative_wikimedia_url(metadata):
    result = Resolver(metadata).resolve("//en.wikipedia.org/wiki/Apple")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"


def test_ftp_mailto_and_custom_uri_are_external(metadata):
    resolver = Resolver(metadata)
    for value in (
        "ftp://example.org/file.txt",
        "mailto:info@example.org",
        "mailto:info@example.org?subject=Hello&body=World",
        "skype:echo123",
    ):
        result = resolver.resolve(value)
        assert result.status is ResolutionStatus.EXTERNAL
        assert result.destination.destination_type is DestinationType.EXTERNAL
        assert resolver.to_url(result.destination) == value


def test_special_edit_permanentlink_and_diff_forms(metadata):
    resolver = Resolver(metadata)
    cases = [
        ("w:en:Special:Edit/Apple", "edit", None, None),
        ("w:en:Special:PermanentLink/123456", None, 123456, None),
        ("w:en:Special:Diff/123456", None, None, 123456),
        ("w:en:Special:Diff/123/124", None, 123, 124),
        ("w:en:Special:Diff/123/prev", None, 123, "prev"),
    ]
    for value, action, revision, diff in cases:
        result = resolver.resolve_interwiki(value)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.action == action
        assert result.revision == revision
        assert result.diff == diff
        assert resolver.to_interwiki(result.destination) == value


def test_local_anchor_uses_source_page_context(metadata):
    resolver = Resolver(metadata)
    page = FakePage(title="Help:Links")
    result = resolver.resolve_interwiki("#Piped_links", source=page)
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"
    assert result.title == "Links"
    assert result.fragment == "Piped_links"


def test_relative_subpage_links_use_source_page_context(metadata):
    resolver = Resolver(metadata)
    page = FakePage(title="Help:Links/example")

    result = resolver.resolve_interwiki("../example2", source=page)
    assert result.status is ResolutionStatus.RESOLVED
    assert result.title == "Links/example2"
    assert result.namespace == "Help"

    result = resolver.resolve_interwiki("/child", source=page)
    assert result.status is ResolutionStatus.RESOLVED
    assert result.title == "Links/example/child"

    page = FakePage(title="Help:Links/example/foo")
    result = resolver.resolve_interwiki("../../s", source=page)
    assert result.status is ResolutionStatus.RESOLVED
    assert result.title == "Links/s"


def test_category_and_file_targets_are_still_semantic_wiki_destinations(metadata):
    resolver = Resolver(metadata)
    for value, namespace, title in (
        ("Category:Help", "Category", "Help"),
        ("File:Example.jpg", "File", "Example.jpg"),
        ("Media:Example.jpg", "Media", "Example.jpg"),
    ):
        result = resolver.resolve_interwiki(value, source="enwiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination_type is DestinationType.WIKI
        assert result.namespace == namespace
        assert result.title == title


def test_fragment_roundtrip_preserves_anchor_exactly(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/wiki/Help:Links#Some_Anchor"
    )
    assert result.fragment == "Some_Anchor"
    assert resolver.to_interwiki(result.destination) == "w:en:Help:Links#Some_Anchor"


def test_curid_and_query_parameters_roundtrip(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Foo&curid=9906&uselang=sl"
    )
    assert result.destination.page_id == 9906
    assert ("uselang", "sl") in result.destination.query_parameters
    rebuilt = resolver.to_url(result.destination)
    assert "curid=9906" in rebuilt
    assert "uselang=sl" in rebuilt

def test_documented_special_diff_forms_roundtrip_with_fragments(metadata):
    resolver = Resolver(metadata)
    for value in (
        "w:en:Special:Diff/1242287",
        "w:en:Special:Diff/1242287/prev",
        "w:en:Special:Diff/1242287/next",
        "w:en:Special:Diff/1242287/cur",
        "w:en:Special:Diff/1242286/1242287",
        "w:en:Special:Diff/1242286/1242287#History",
    ):
        result = resolver.resolve_interwiki(value)
        assert resolver.to_interwiki(result.destination) == value


def test_documented_page_id_is_url_only_without_page_name(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?curid=9906"
    )
    assert result.destination.page_id == 9906
    with pytest.raises(ConversionError):
        resolver.to_interwiki(result.destination)



def test_short_project_prefix_inherits_source_language_across_families(metadata):
    resolver = Resolver(metadata)

    cases = [
        ("dewiki", "b:Main Page", "dewikibooks"),
        ("dewiki", "q:Main Page", "dewikiquote"),
        ("itwiki", "b:Main Page", "itwikibooks"),
        ("frwiki", "wikt:Main Page", "frwiktionary"),
        ("simplewiki", "b:Main Page", "simplewikibooks"),
    ]

    for source, value, expected_dbname in cases:
        result = resolver.resolve_interwiki(value, source=source)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.dbname == expected_dbname


def test_short_project_prefix_from_multilingual_source_uses_english(metadata):
    resolver = Resolver(metadata)

    for value, expected_dbname in (
        ("b:Main Page", "enwikibooks"),
        ("q:Main Page", "enwikiquote"),
        ("w:Main Page", "enwiki"),
    ):
        result = resolver.resolve_interwiki(value, source="metawiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.dbname == expected_dbname


def test_long_project_prefix_is_fixed_english(metadata):
    resolver = Resolver(metadata)

    for value, expected_dbname in (
        ("wikipedia:Main Page", "enwiki"),
        ("wiktionary:Main Page", "enwiktionary"),
        ("wikibooks:Main Page", "enwikibooks"),
        ("wikiquote:Main Page", "enwikiquote"),
        ("wikinews:Main Page", "enwikinews"),
        ("wikisource:Main Page", "enwikisource"),
        ("wikiversity:Main Page", "enwikiversity"),
        ("wikivoyage:Main Page", "enwikivoyage"),
    ):
        result = resolver.resolve_interwiki(value, source="dewiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.dbname == expected_dbname


def test_leading_colon_keeps_the_same_interlanguage_destination(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki(":en:Apple", source="dewiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"
    assert result.title == "Apple"


def test_language_target_without_leading_colon_is_interlanguage(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki("en:Apple", source="dewiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"
    assert result.title == "Apple"


def test_leading_colon_does_not_break_explicit_language_project_chain(metadata):
    resolver = Resolver(metadata)

    result = resolver.resolve_interwiki(":de:q:Hauptseite", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "dewikiquote"
    assert result.title == "Hauptseite"


def test_documented_left_to_right_meta_chains(metadata):
    resolver = Resolver(metadata)

    result = resolver.resolve_interwiki(":m:en:About", source="metawiki")
    assert result.dbname == "enwiki"
    assert result.title == "About"

    result = resolver.resolve_interwiki(":pl:w:2006", source="metawiki")
    assert result.dbname == "enwiki"
    assert result.title == "2006"

    result = resolver.resolve_interwiki(":w:it:b:Wiskunde", source="metawiki")
    assert result.dbname == "itwikibooks"
    assert result.title == "Wiskunde"

    result = resolver.resolve_interwiki(":ja:ja:2006", source="metawiki")
    assert result.dbname == "jawiki"
    assert result.title == "2006"


def test_meta_project_namespace_can_override_long_interwiki_name(metadata):
    metadata._namespaces["metawiki"] = frozenset({"meta"})
    resolver = Resolver(metadata)

    result = resolver.resolve_interwiki("meta:About", source="metawiki")

    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "metawiki"
    assert result.destination.namespace == "meta"
    assert result.title == "About"


def test_fixed_wikimedia_global_prefixes_keep_their_fixed_targets(metadata):
    resolver = Resolver(metadata)

    cases = [
        ("wikipedia:Apple", "enwiki"),
        ("wiktionary:Apple", "enwiktionary"),
        ("wikibooks:Apple", "enwikibooks"),
        ("wikiquote:Apple", "enwikiquote"),
        ("wikisource:Apple", "enwikisource"),
        ("wikiversity:Apple", "enwikiversity"),
        ("wikivoyage:Apple", "enwikivoyage"),
        ("oldwikisource:Apple", "mulwikisource"),
    ]

    for value, expected_dbname in cases:
        result = resolver.resolve_interwiki(value, source="dewiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.dbname == expected_dbname


def test_documented_leading_colon_and_interlanguage_behavior_in_parsed_wikitext(metadata):
    from wmlinksfromhell import parse

    code = parse(
        "[[:en:Apple]] [[en:Apple]]",
        source="dewiki",
        metadata=metadata,
    )
    links = code.filter_links()

    assert len(links) == 2
    assert links[0].dbname == "enwiki"
    assert links[0].title == "Apple"
    assert links[0].is_interwiki
    assert links[0].leading_colon
    assert links[1].dbname == "enwiki"
    assert links[1].title == "Apple"
    assert links[1].is_interwiki
    assert not links[1].leading_colon
    assert links[0].destination == links[1].destination


def test_documented_universal_meta_interwiki_chain(metadata):
    resolver = Resolver(metadata)

    result = resolver.resolve_interwiki(
        "m:b:nl:Wiskunde",
        source="dewiki",
    )
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "nlwikibooks"
    assert result.title == "Wiskunde"


def test_documented_meta_language_chain_on_multilingual_source(metadata):
    resolver = Resolver(metadata)

    for value, expected_dbname in (
        (":pl:2006", "plwiki"),
        (":ja:2006", "jawiki"),
        (":ja:ja:2006", "jawiki"),
    ):
        result = resolver.resolve_interwiki(value, source="metawiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.dbname == expected_dbname
