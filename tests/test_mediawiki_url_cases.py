import pytest

from wmlinksfromhell.exceptions import ConversionError
from wmlinksfromhell.models import DestinationType, ResolutionStatus
from wmlinksfromhell.resolver import Resolver
from wmlinksfromhell.url import build_url, parse_url


def test_meta_wikipedia_alias(metadata):
    result = Resolver(metadata).resolve_url("https://meta.wikipedia.org/wiki/Help:Links")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "metawiki"
    assert result.title == "Links"


def test_protocol_relative_wikimedia_url(metadata):
    result = Resolver(metadata).resolve_url("//en.wikipedia.org/wiki/Apple")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.dbname == "enwiki"
    assert result.url == "https://en.wikipedia.org/wiki/Apple"


def test_protocol_relative_external_url(metadata):
    result = Resolver(metadata).resolve_url("//example.com/thing")
    assert result.status is ResolutionStatus.EXTERNAL
    assert result.url == "//example.com/thing"


def test_ftp_and_mailto_are_external(metadata):
    resolver = Resolver(metadata)
    for value in ("ftp://example.com/file.txt", "mailto:info@example.org"):
        result = resolver.resolve(value)
        assert result.status is ResolutionStatus.EXTERNAL
        assert result.destination is not None
        assert result.destination.destination_type is DestinationType.EXTERNAL


def test_unknown_external_http_host_remains_external_at_resolver_level(metadata):
    result = Resolver(metadata).resolve_url("https://example.com/page")
    assert result.status is ResolutionStatus.EXTERNAL


def test_curid_is_preserved(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/w/index.php?curid=9906", metadata)
    assert dest is not None
    assert dest.page_id == 9906
    assert dest.title is None
    assert build_url(dest, metadata) == "https://en.wikipedia.org/w/index.php?curid=9906"


def test_curid_with_title_is_preserved(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/w/index.php?title=Foo&curid=9906", metadata)
    assert dest.page_id == 9906
    assert dest.title == "Foo"
    assert "curid=9906" in build_url(dest, metadata)


def test_uselang_is_preserved_and_falls_back_to_page_interwiki(metadata):
    resolver = Resolver(metadata)
    dest, _ = parse_url(
        "https://commons.wikimedia.org/w/index.php?title=Glavna_stran&uselang=sl",
        metadata,
    )
    assert dest.query_parameters == (("uselang", "sl"),)
    assert "uselang=sl" in build_url(dest, metadata)
    assert resolver.to_interwiki(dest) == "c:Glavna stran"


def test_generic_actions_are_preserved_in_url(metadata):
    resolver = Resolver(metadata)
    for action in ("purge", "raw", "history", "view", "watch", "unwatch", "info", "render"):
        result = resolver.resolve_url(
            f"https://en.wikipedia.org/w/index.php?title=Apple&action={action}"
        )
        assert result.status is ResolutionStatus.RESOLVED
        assert result.action == action
        assert f"action={action}" in result.url


def test_edit_section_is_preserved_and_falls_back_to_page_interwiki(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&action=edit&section=5"
    )
    assert result.action == "edit"
    assert ("section", "5") in result.destination.query_parameters
    assert resolver.to_interwiki(result.destination, source="metawiki") == "w:en:Apple"


def test_symbolic_diff_without_oldid_falls_back_to_page_interwiki(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=prev"
    )
    assert result.status is ResolutionStatus.RESOLVED
    assert resolver.to_interwiki(result.destination, source="metawiki") == "w:en:Apple"

def test_symbolic_diff_without_oldid_falls_back_to_local_page_link(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=cur"
    )
    assert resolver.to_local(result.destination, source="enwiki") == "Apple"


def test_local_special_pages_are_not_treated_as_ordinary_special_namespace_titles(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki(
        "Special:PermanentLink/123456",
        source="enwiki",
    )
    assert result.revision == 123456
    assert result.special_page == "PermanentLink"
    assert result.title is None
    assert resolver.to_url(result.destination) == "https://en.wikipedia.org/w/index.php?oldid=123456"
    assert resolver.to_interwiki(result.destination, source="metawiki") == "w:en:Special:PermanentLink/123456"


def test_local_special_diff_forms_are_semantic_and_roundtrip(metadata):
    resolver = Resolver(metadata)
    for value, revision, diff in (
        ("Special:Diff/123456", None, 123456),
        ("Special:Diff/123456/prev", 123456, "prev"),
        ("Special:Diff/123456/next", 123456, "next"),
        ("Special:Diff/123456/cur", 123456, "cur"),
        ("Special:Diff/123/124", 123, 124),
    ):
        result = resolver.resolve_interwiki(value, source="enwiki")
        assert result.special_page == "Diff"
        assert result.revision == revision
        assert result.diff == diff
        assert resolver.to_interwiki(result.destination, source="metawiki") == "w:en:" + value


def test_relative_links_need_page_context(metadata):
    resolver = Resolver(metadata)
    for value in ("/example", "../example", "#section"):
        result = resolver.resolve_interwiki(value, source="enwiki")
        assert result.status is ResolutionStatus.CONTEXT_REQUIRED

def test_string_source_is_never_treated_as_a_page_title(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki("/example", source="enwiki")
    assert result.status is ResolutionStatus.CONTEXT_REQUIRED
    assert result.destination is None


def test_symbolic_diff_with_oldid_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=prev&oldid=123456"
    )
    interwiki = resolver.to_interwiki(result.destination, source="metawiki")
    roundtrip = resolver.resolve_interwiki(interwiki, source="metawiki")
    assert interwiki == "w:en:Special:Diff/123456/prev"
    assert roundtrip.destination == result.destination


def test_numeric_diff_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=123456"
    )
    interwiki = resolver.to_interwiki(result.destination, source="metawiki")
    assert interwiki == "w:en:Special:Diff/123456"
    assert resolver.resolve_interwiki(interwiki, source="metawiki").destination == result.destination


def test_diff_between_two_revisions_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=1242287&oldid=1242286"
    )
    interwiki = resolver.to_interwiki(result.destination, source="metawiki")
    assert interwiki == "w:en:Special:Diff/1242286/1242287"
    assert resolver.resolve_interwiki(interwiki, source="metawiki").destination == result.destination


def test_permanent_link_without_title_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?oldid=123456"
    )
    interwiki = resolver.to_interwiki(result.destination, source="metawiki")
    roundtrip = resolver.resolve_interwiki(interwiki, source="metawiki")
    assert interwiki == "w:en:Special:PermanentLink/123456"
    assert roundtrip.destination == result.destination


def test_edit_special_page_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki(
        "w:en:Special:Edit/Apple",
        source="metawiki",
    )
    assert result.action == "edit"
    assert result.destination == resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&action=edit"
    ).destination


def test_meta_project_prefix_is_canonical(metadata):
    resolver = Resolver(metadata)
    for source in ("metawiki", "enwiki", "dewiki", "commonswiki"):
        result = resolver.resolve_interwiki(
            "w:Apple",
            source=source,
        )
        assert result.dbname == "enwiki"
        assert result.interwiki == "w:en:Apple"


def test_simple_wiktionary_keeps_simple_language(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki(
        "wikt:simple:uppercase",
        source="metawiki",
    )
    assert result.dbname == "simplewiktionary"
    assert result.language == "simple"
    assert result.interwiki == "wikt:simple:uppercase"


def test_special_wiki_prefixes_are_wiki_destinations(metadata):
    resolver = Resolver(metadata)
    for value, dbname in (
        ("abstract:Foo", "abstractwiki"),
        ("wmania:Foo", "wikimaniawiki"),
        ("wm2016:Foo", "wikimania2016wiki"),
        ("wmteam:Foo", "wikimaniateamwiki"),
    ):
        result = resolver.resolve_interwiki(value, source="metawiki")
        assert result.destination is not None
        assert result.destination.dbname == dbname
        assert result.destination.destination_type is DestinationType.WIKI


def test_special_wiki_prefixes_render_back(metadata):
    resolver = Resolver(metadata)
    for value, expected in (
        ("abstract:Foo", "abstract:Foo"),
        ("wmania:Foo", "wmania:Foo"),
        ("wm2016:Foo", "wm2016:Foo"),
        ("wmteam:Foo", "wmteam:Foo"),
    ):
        result = resolver.resolve_interwiki(value, source="metawiki")
        assert resolver.to_interwiki(result.destination, source="metawiki") == expected


def test_local_special_operations_are_parsed_semantically(metadata):
    resolver = Resolver(metadata)
    cases = (
        ("Special:PermanentLink/123456", None, 123456, None),
        ("Special:Diff/123456", None, None, 123456),
        ("Special:Diff/123456/prev", None, 123456, "prev"),
        ("Special:Diff/123456/next", None, 123456, "next"),
        ("Special:Diff/123456/cur", None, 123456, "cur"),
        ("Special:Diff/123/124", None, 123, 124),
    )
    for value, action, revision, diff in cases:
        result = resolver.resolve_interwiki(value, source="enwiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.action == action
        assert result.revision == revision
        assert result.diff == diff
        assert result.destination.special_page in {"PermanentLink", "Diff"}


def test_nonrepresentable_page_operations_fall_back_to_normal_interwiki(metadata):
    resolver = Resolver(metadata)
    for url in (
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=prev",
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=next",
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=cur",
        "https://en.wikipedia.org/w/index.php?title=Apple&action=edit&section=5",
        "https://en.wikipedia.org/w/index.php?title=Apple&action=purge",
        "https://en.wikipedia.org/w/index.php?title=Apple&uselang=de",
        "https://en.wikipedia.org/w/index.php?title=Apple&foo=bar",
    ):
        result = resolver.resolve_url(url)
        assert resolver.to_interwiki(result.destination) == "w:en:Apple"

def test_local_special_operations_resolve_and_roundtrip(metadata):
    resolver = Resolver(metadata)
    cases = (
        ("Special:PermanentLink/123456", 123456, None),
        ("Special:Diff/123456", None, 123456),
        ("Special:Diff/123456/prev", 123456, "prev"),
        ("Special:Diff/123456/next", 123456, "next"),
        ("Special:Diff/123456/cur", 123456, "cur"),
        ("Special:Diff/123/124", 123, 124),
    )
    for value, revision, diff in cases:
        result = resolver.resolve_interwiki(value, source="enwiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.revision == revision
        assert result.diff == diff
        assert result.destination.special_page in {"PermanentLink", "Diff"}
        assert resolver.to_interwiki(result.destination, source="enwiki") == f"w:en:{value}"


def test_local_special_edit_resolves_and_roundtrips(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_interwiki(
        "Special:Edit/Apple",
        source="enwiki",
    )
    assert result.status is ResolutionStatus.RESOLVED
    assert result.action == "edit"
    assert result.title == "Apple"
    assert resolver.to_interwiki(result.destination, source="enwiki") == "w:en:Special:Edit/Apple"


def test_curid_only_destination_cannot_be_falsely_rendered_as_interwiki(metadata):
    resolver = Resolver(metadata)
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?curid=9906"
    )
    with pytest.raises(ConversionError):
        resolver.to_interwiki(result.destination)


def test_diff_is_not_same_page_as_permanent_link_with_same_revision(metadata):
    resolver = Resolver(metadata)
    diff = resolver.resolve_interwiki(
        "w:en:Special:Diff/123456",
        source="metawiki",
    ).destination
    revision = resolver.resolve_interwiki(
        "w:en:Special:PermanentLink/123456",
        source="metawiki",
    ).destination
    assert diff != revision
    assert not diff.same_page_as(revision)

