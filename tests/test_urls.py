import pytest

from wmlinksfromhell.destination import Destination
from wmlinksfromhell.exceptions import ConversionError
from wmlinksfromhell.models import DestinationType, ResolutionStatus
from wmlinksfromhell.url import build_url, parse_url


def test_basic_wiki_url(metadata):
    dest, reason = parse_url("https://en.wikipedia.org/wiki/Apple", metadata)
    assert dest.dbname == "enwiki"
    assert dest.title == "Apple"
    assert dest.fragment is None


def test_underscore_and_percent_encoding_are_equivalent(metadata):
    a, _ = parse_url("https://en.wikipedia.org/wiki/Page_name", metadata)
    b, _ = parse_url("https://en.wikipedia.org/wiki/Page%20name", metadata)
    assert a.title == b.title == "Page name"


def test_namespace_qualified_title(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/wiki/Help:Page_name", metadata)
    assert dest.namespace == "Help"
    assert dest.title == "Page name"


def test_fragment_is_decoded(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/wiki/Page_name#History", metadata)
    assert dest.title == "Page name"
    assert dest.fragment == "History"


def test_index_php_title_query(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/w/index.php?title=Foo", metadata)
    assert dest.dbname == "enwiki"
    assert dest.title == "Foo"


def test_index_php_oldid(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/w/index.php?title=Foo&oldid=123456", metadata)
    assert dest.revision == 123456
    assert dest.title == "Foo"


def test_index_php_diff(metadata):
    dest, _ = parse_url(
        "https://en.wikipedia.org/w/index.php?title=Foo&diff=124&oldid=123", metadata
    )
    assert dest.diff == 124
    assert dest.revision == 123


def test_index_php_action_edit(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/w/index.php?title=Foo&action=edit", metadata)
    assert dest.action == "edit"
    assert dest.title == "Foo"


def test_unknown_hostname_is_not_a_wiki_destination(metadata):
    dest, reason = parse_url("https://example.com/page", metadata)
    assert dest is None
    assert "not a known Wikimedia-related site" in reason


def test_malformed_percent_encoding(metadata):
    # %ff is not a valid UTF-8 start byte on its own
    dest, reason = parse_url("https://en.wikipedia.org/wiki/%ff", metadata)
    assert dest is None


def test_commons_file_url(metadata):
    dest, _ = parse_url("https://commons.wikimedia.org/wiki/File:Example.jpg", metadata)
    assert dest.dbname == "commonswiki"
    assert dest.namespace == "File"
    assert dest.title == "Example.jpg"


def test_legacy_image_namespace_normalizes_to_file(metadata):
    image, _ = parse_url("https://en.wikipedia.org/wiki/Image:Example.png", metadata)
    file, _ = parse_url("https://en.wikipedia.org/wiki/File:Example.png", metadata)
    assert image.namespace == file.namespace == "File"


def test_wikidata_item_url(metadata):
    dest, _ = parse_url("https://www.wikidata.org/wiki/Q42", metadata)
    assert dest.dbname == "wikidatawiki"
    assert dest.title == "Q42"


def test_build_url_from_destination(metadata):
    dest = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Page name",
                        fragment="History")
    url = build_url(dest, metadata)
    assert url == "https://en.wikipedia.org/wiki/Page_name#History"


def test_build_url_with_revision_uses_index_php(metadata):
    dest = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Foo", revision=123456)
    url = build_url(dest, metadata)
    assert "index.php" in url
    assert "oldid=123456" in url


def test_build_url_requires_dbname(metadata):
    dest = Destination(destination_type=DestinationType.WIKI, title="Foo")
    with pytest.raises(ConversionError):
        build_url(dest, metadata)


def test_build_url_rejects_external_destination(metadata):
    dest = Destination(destination_type=DestinationType.EXTERNAL, hostname="example.com")
    with pytest.raises(ConversionError):
        build_url(dest, metadata)


def test_index_php_and_article_url_have_same_semantic_destination(metadata):
    a, _ = parse_url("https://en.wikipedia.org/wiki/Apple", metadata)
    b, _ = parse_url("https://en.wikipedia.org/w/index.php?title=Apple", metadata)
    assert a == b
    assert a.same_page_as(b)


def test_symbolic_diff_is_preserved(metadata):
    dest, _ = parse_url(
        "https://en.wikipedia.org/w/index.php?title=Foo&diff=prev&oldid=123456",
        metadata,
    )
    assert dest.diff == "prev"
    assert dest.revision == 123456


def test_extra_query_parameters_are_preserved_without_breaking_equivalence(metadata):
    dest, _ = parse_url(
        "https://en.wikipedia.org/w/index.php?title=Foo&redirect=no&action=edit",
        metadata,
    )
    assert dest.action == "edit"
    assert ("redirect", "no") in dest.query_parameters


def test_unknown_wikimedia_host_is_not_an_ordinary_external_destination(metadata):
    dest, reason = parse_url("https://example.wikimedia.org/foo", metadata)
    assert dest is not None
    assert dest.destination_type is DestinationType.UNKNOWN
    assert dest.is_wikimedia_project is True
    assert "metadata" in reason.lower()


def test_fragment_does_not_apply_title_normalization(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/wiki/Apple#Section_With_Underscores", metadata)
    assert dest.fragment == "Section_With_Underscores"


def test_special_wiki_url_preserves_standard_project_flag(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis["betawikiversity"] = WikiInfo(
        dbname="betawikiversity", family="wikiversity", project="wikiversity", language="en",
        language_name="English", hostname="beta.wikiversity.org", is_standard_project=False,
    )
    metadata._reindex()
    result = resolver.resolve_url("https://beta.wikiversity.org/wiki/Foo")
    assert result.destination is not None
    assert result.destination.is_standard_project is False


def test_dynamic_noc_chapter_url_gets_organization_metadata(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, DestinationType

    metadata._global_interwikis["wmde"] = InterwikiEntry(
        prefix="wmde",
        url="https://wikimedia.de/$1",
        destination_type=DestinationType.ORGANIZATION,
    )
    dest = resolver.resolve_url("https://wikimedia.de/Foo").destination
    assert dest is not None
    assert dest.destination_type is DestinationType.ORGANIZATION
    assert dest.organization_name == "wmde"
    assert dest.title == "Foo"


def test_noc_global_org_url_is_resolved_from_global_prefix(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, DestinationType

    metadata._global_interwikis["wmde"] = InterwikiEntry(
        prefix="wmde",
        url="https://wikimedia.de/$1",
        destination_type=DestinationType.ORGANIZATION,
    )
    result = resolver.resolve_url("https://wikimedia.de/Foo")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.organization_name == "wmde"
    assert result.destination.title == "Foo"


def test_special_edit_url_becomes_edit_destination(metadata):
    dest, _ = parse_url("https://en.wikipedia.org/wiki/Special:Edit/Apple", metadata)
    assert dest.action == "edit"
    assert dest.title == "Apple"
    assert dest.namespace is None


def test_index_php_action_edit_keeps_extra_query_parameters(metadata):
    dest, _ = parse_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&action=edit&section=1",
        metadata,
    )
    assert dest.action == "edit"
    assert dest.title == "Apple"
    assert ("section", "1") in dest.query_parameters
