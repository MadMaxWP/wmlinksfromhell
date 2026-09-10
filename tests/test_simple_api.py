import wmlinksfromhell as wm
from wmlinksfromhell.models import WikiInfo


def test_wiki_and_interwiki_convenience_api():
    metadata = wm.Metadata()
    metadata._wikis["astwiki"] = WikiInfo(
        "astwiki", "wikipedia", "wikipedia", "ast", "Asturian",
        "ast.wikipedia.org", is_standard_project=True,
    )
    metadata._reindex()

    wiki = wm.wiki("astwiki", metadata=metadata)
    assert wiki.dbname == "astwiki"
    assert wiki.family == "wikipedia"
    assert wiki.project == "wikipedia"
    assert wiki.language == "ast"
    assert wiki.interwiki("Apple", metadata=metadata) == "w:ast:Apple"


def test_interwiki_info_has_named_project_and_language():
    metadata = wm.Metadata()
    metadata._wikis["astwiki"] = WikiInfo(
        "astwiki", "wikipedia", "wikipedia", "ast", "Asturian",
        "ast.wikipedia.org", is_standard_project=True,
    )
    metadata._reindex()

    for dbname, prefix, project, language in (
        ("astwiki", "w:ast", "w", "ast"),
        ("dewiktionary", "wikt:de", "wikt", "de"),
        ("dewikibooks", "b:de", "b", "de"),
        ("itwikivoyage", "voy:it", "voy", "it"),
        ("betawikiversity", "betawikiversity", "betawikiversity", None),
        ("mediawikiwiki", "mw", "mw", None),
        ("commonswiki", "c", "c", None),
        ("wikidatawiki", "d", "d", None),
    ):
        info = wm.interwiki(dbname, metadata=metadata)
        assert info.prefix == prefix
        assert info.project == project
        assert info.language == language
        assert info.dbname == dbname


def test_convenience_rendering_functions():
    assert wm.url("enwiki", "Apple") == "https://en.wikipedia.org/wiki/Apple"
    assert wm.link("enwiki", "Apple") == "[[w:en:Apple]]"
    assert wm.link("enwiki", "Apple", "the fruit") == "[[w:en:Apple|the fruit]]"


def test_wiki_convenience_urls():
    wiki = wm.wiki("dewiktionary")
    assert wiki.page_url("Apfel") == "https://de.wiktionary.org/wiki/Apfel"
    assert wiki.main_page_url() == "https://de.wiktionary.org/wiki/Main_Page"
    assert wiki.link("Apfel", "Apfel") == "[[wikt:de:Apfel|Apfel]]"


def test_wiki_convenience_special_wikis():
    assert wm.wiki("commonswiki").interwiki("File:Example.jpg") == "c:File:Example.jpg"
    assert wm.wiki("wikidatawiki").interwiki("Q42") == "d:Q42"
    assert wm.wiki("betawikiversity").interwiki("Main Page") == "betawikiversity:Main Page"


def test_link_convenience_properties():
    code = wm.parse(
        "[[w:en:Apple]] https://en.wikipedia.org/wiki/Apple [[phab:T123]]",
        source="metawiki",
    )

    links = code.filter_links()

    assert links[0].is_wiki
    assert not links[0].is_external
    assert links[0].has_title
    assert not links[0].has_revision
    assert not links[0].has_diff
    assert links[0].wiki.dbname == "enwiki"

    assert links[1].is_url
    assert links[1].is_wiki
    assert not links[1].is_interwiki

    assert links[2].is_service
    assert links[2].is_wikimedia


def test_empty_project_prefixes_still_resolve_to_main_page():
    for value, dbname in (
        ("w:", "enwiki"),
        ("en:", "enwiki"),
        ("c:", "commonswiki"),
        ("Wikipedia:", "enwiki"),
        ("Wikibooks:", "enwikibooks"),
    ):
        result = wm.resolve_interwiki(value, source="metawiki")
        assert result.destination is not None
        assert result.dbname == dbname
        assert result.title == "Main Page"


def test_link_kind_helpers_distinguish_syntax_from_destination():
    code = wm.parse(
        "[[w:en:Apple]] https://en.wikipedia.org/wiki/Apple "
        "[https://example.org Example] https://example.org/plain",
        source="metawiki",
    )

    interwiki_link, wiki_url, bracketed_external, bare_external = code.filter_links()

    assert interwiki_link.is_interwiki
    assert interwiki_link.is_wiki
    assert not interwiki_link.is_url

    assert wiki_url.is_wiki
    assert wiki_url.is_url
    assert wiki_url.is_url
    assert wiki_url.is_wiki

    assert bracketed_external.is_url
    assert not bracketed_external.is_wiki

    assert bare_external.is_url
    assert not bare_external.is_wiki


def test_legacy_link_properties_remain_available():
    code = wm.parse(
        'https://en.wikipedia.org/wiki/Apple https://example.org/Apple',
        source='metawiki',
    )
    wiki_url, external_url = code.filter_links()

    assert wiki_url.is_external is True
    assert wiki_url.is_external_link is True
    assert wiki_url.is_bare_url is True
    assert wiki_url.is_wiki_url is True
    assert wiki_url.is_external_url is False

    assert external_url.is_external is True
    assert external_url.is_external_link is True
    assert external_url.is_bare_url is True
    assert external_url.is_wiki_url is False
    assert external_url.is_external_url is True


def test_wiki_only_filter_excludes_services_and_tools():
    code = wm.parse(
        "[[w:en:Apple]] [[phab:T123]] [[toolforge:example]] https://example.org/Apple",
        source="metawiki",
    )

    assert [link.original for link in code.filter_links(wiki_only=True)] == [
        "[[w:en:Apple]]"
    ]
