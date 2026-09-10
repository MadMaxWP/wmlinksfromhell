import wmlinksfromhell as wm


def test_public_api_is_available_from_top_level():
    for name in (
        "parse",
        "resolve",
        "resolve_url",
        "resolve_interwiki",
        "to_url",
        "to_interwiki",
        "to_local",
        "wiki",
        "interwiki",
        "url",
        "link",
        "MetadataStore",
        "Metadata",
        "Resolver",
        "Destination",
        "DestinationType",
        "ConversionError",
    ):
        assert hasattr(wm, name), name


def test_edit_url_round_trips_through_interwiki():
    resolver = wm.Resolver()
    result = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&action=edit"
    )
    assert result.destination is not None
    assert result.destination.action == "edit"
    assert resolver.to_interwiki(result.destination) == "w:en:Special:Edit/Apple"

    roundtrip = resolver.resolve_interwiki("w:en:Special:Edit/Apple")
    assert roundtrip.destination is not None
    assert roundtrip.destination.action == "edit"
    assert roundtrip.destination.title == "Apple"
    assert roundtrip.destination == result.destination


def test_edit_page_url_round_trips_through_special_url():
    resolver = wm.Resolver()
    result = resolver.resolve_url("https://en.wikipedia.org/wiki/Special:Edit/Apple")
    assert result.destination is not None
    assert result.destination.action == "edit"
    assert result.destination.title == "Apple"
    assert resolver.to_interwiki(result.destination) == "w:en:Special:Edit/Apple"


def test_permanent_link_round_trip_preserves_revision_identity():
    resolver = wm.Resolver()
    original = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&oldid=123456"
    )
    converted = resolver.to_interwiki(original.destination)
    assert converted == "w:en:Special:PermanentLink/123456"

    roundtrip = resolver.resolve_interwiki(converted)
    assert roundtrip.destination is not None
    assert roundtrip.destination.revision == 123456
    assert roundtrip.destination == original.destination


def test_diff_round_trip_preserves_diff_identity():
    resolver = wm.Resolver()
    original = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=123456"
    )
    converted = resolver.to_interwiki(original.destination)
    assert converted == "w:en:Special:Diff/123456"

    roundtrip = resolver.resolve_interwiki(converted)
    assert roundtrip.destination is not None
    assert roundtrip.destination.diff == 123456
    assert roundtrip.destination == original.destination


def test_diff_with_oldid_round_trip_preserves_both_revisions():
    resolver = wm.Resolver()
    original = resolver.resolve_url(
        "https://en.wikipedia.org/w/index.php?title=Apple&diff=124&oldid=123"
    )
    converted = resolver.to_interwiki(original.destination)
    assert converted == "w:en:Special:Diff/123/124"

    roundtrip = resolver.resolve_interwiki(converted)
    assert roundtrip.destination is not None
    assert roundtrip.destination.revision == 123
    assert roundtrip.destination.diff == 124
    assert roundtrip.destination == original.destination


def test_interwiki_underscore_and_url_space_are_the_same_destination():
    resolver = wm.Resolver()
    underscore = resolver.resolve_interwiki("w:en:Foo_bar")
    url = resolver.resolve_url("https://en.wikipedia.org/wiki/Foo_bar")
    assert underscore.destination is not None
    assert url.destination is not None
    assert underscore.destination.title == "Foo bar"
    assert underscore.destination == url.destination


def test_bootstrap_special_wiki_prefixes_are_used_after_sitematrix_load():
    metadata = wm.MetadataStore()
    metadata.load_sitematrix({
        "sitematrix": {
            "specials": [
                {"code": "wiki", "dbname": "abstractwiki", "lang": "en", "url": "https://abstract.wikipedia.org", "sitename": "Abstract Wikipedia"},
                {"code": "wiki", "dbname": "wikimaniateamwiki", "lang": "en", "url": "https://wikimaniateam.wikimedia.org", "sitename": "Wikimania Team"},
                {"code": "wiki", "dbname": "wikimaniawiki", "lang": "en", "url": "https://wikimania.wikimedia.org", "sitename": "Wikimania"},
                {"code": "wiki", "dbname": "wikimania2016wiki", "lang": "en", "url": "https://wikimania2016.wikimedia.org", "sitename": "Wikimania 2016"},
            ]
        }
    })
    resolver = wm.Resolver(metadata)

    for dbname, prefix in (
        ("abstractwiki", "abstract"),
        ("wikimaniateamwiki", "wmteam"),
        ("wikimaniawiki", "wmania"),
        ("wikimania2016wiki", "wm2016"),
    ):
        wiki = metadata.wiki_by_dbname(dbname)
        destination = wm.Destination(
            wm.DestinationType.WIKI,
            wiki.family,
            wiki.project,
            wiki.language,
            wiki.dbname,
            wiki.wikiid,
            wiki.hostname,
            "MediaWiki:Gadget:Xtools.js",
            is_wikimedia_project=True,
            is_standard_project=False,
        )
        assert resolver.to_interwiki(destination, source="metawiki") == f"{prefix}:MediaWiki:Gadget:Xtools.js"


def test_special_prefixes_resolve_without_explicit_noc_loading():
    resolver = wm.Resolver()
    for value, dbname in (
        ("abstract:Foo", "abstractwiki"),
        ("wmania:Foo", "wikimaniawiki"),
        ("wm2016:Foo", "wikimania2016wiki"),
        ("wmteam:Foo", "wikimaniateamwiki"),
    ):
        result = resolver.resolve_interwiki(value, source="metawiki")
        assert result.destination is not None
        assert result.destination.dbname == dbname


def test_parse_page_uses_page_site_as_source(metadata):
    import wmlinksfromhell as wm

    class FakeSite:
        def dbName(self):
            return "enwiki"

    class FakePage:
        site = FakeSite()
        text = "[[w:en:Apple]]"

        def title(self):
            return "Apple"

    code = wm.parse_page(FakePage(), metadata=metadata)
    link = code.filter_links()[0]
    assert link.dbname == "enwiki"
    assert link.title == "Apple"


def test_parse_page_uses_site_property_as_source(metadata):
    import wmlinksfromhell as wm

    class FakeSite:
        def dbName(self):
            return "enwiki"

    class FakePage:
        site = FakeSite()
        text = "[[w:en:Apple]]"

    code = wm.parse_page(FakePage(), metadata=metadata)
    link = code.filter_links()[0]
    assert link.dbname == "enwiki"
    assert link.title == "Apple"


def test_parse_page_keeps_page_as_source(metadata):
    import wmlinksfromhell as wm

    class FakeSite:
        def dbName(self):
            return "enwiki"

    class FakePage:
        site = FakeSite()
        text = "[[w:en:Apple]]"

        def title(self):
            return "Example"

    code = wm.parse_page(FakePage(), metadata=metadata)
    assert code.source.title() == "Example"
    assert code.filter_links()[0].dbname == "enwiki"


def test_link_line_number_and_text_use_the_actual_node():
    code = wm.parse("[[Foo]] first\nmiddle\n[[Foo]] second")
    links = code.filter_links()

    assert links[0].line_number == 1
    assert links[0].line_text == "[[Foo]] first"
    assert links[1].line_number == 3
    assert links[1].line_text == "[[Foo]] second"


def test_link_line_number_handles_nested_nodes():
    code = wm.parse("{{box|value=[[Foo]]}}\n[[Foo]]")
    links = code.filter_wikilinks()

    assert links[0].line_number == 1
    assert links[0].line_text == "{{box|value=[[Foo]]}}"
    assert links[1].line_number == 2
    assert links[1].line_text == "[[Foo]]"
