import wmlinksfromhell as wm


def test_parse_returns_wmcode(metadata):
    code = wm.parse("[[Foo]]", metadata=metadata)
    assert isinstance(code, wm.WMCode)
    assert str(code) == "[[Foo]]"


def test_filter_links_finds_wikilinks_and_external_links(metadata):
    text = "[[Foo]] and [https://example.com label] and https://example.org/bare"
    code = wm.parse(text, metadata=metadata)
    links = code.filter_links()
    assert len(links) == 3
    assert links[0].is_wikilink
    assert links[1].is_external_link
    assert links[2].is_external_link


def test_filter_links_recurses_into_templates(metadata):
    text = "{{cite web|url=https://en.wikipedia.org/wiki/Apple}}"
    code = wm.parse(text, source="enwiki", metadata=metadata)
    links = code.filter_links()
    assert len(links) == 1
    assert links[0].dbname == "enwiki"


def test_str_roundtrips_unrelated_content(metadata):
    text = "Some {{template|a=1}} text with a <!-- comment --> and a table\n{| \n|a\n|}"
    code = wm.parse(text, metadata=metadata)
    assert str(code) == text


def test_filter_wikilinks_and_external_links_separately(metadata):
    text = "[[Foo]] [https://example.com x]"
    code = wm.parse(text, metadata=metadata)
    assert len(code.filter_wikilinks()) == 1
    assert len(code.filter_external_links()) == 1


def test_parser_accepts_plain_text_from_any_source(metadata):
    text = "before [[w:en:Apple]] after https://en.wikipedia.org/wiki/Berlin"
    code = wm.parse(text, source="metawiki", metadata=metadata)
    assert [link.dbname for link in code.filter_links()] == ["enwiki", "enwiki"]


def test_section_wrappers_share_root_for_transformations(metadata):
    text = "== One ==\n[[w:en:Apple]]\n== Two ==\n[[w:de:Berlin]]"
    code = wm.parse(text, source="enwiki", metadata=metadata)
    section = code.get_sections()[1]
    link = section.filter_links()[0]
    link.set_local()
    assert "[[Apple]]" in str(code)
    assert "[[w:de:Berlin]]" in str(code)


def test_short_public_names_are_available():
    import wmlinksfromhell as wm

    assert wm.Code is wm.WMCode
    assert wm.Link is wm.WMLink
    assert wm.Wiki is wm.WikiInfo
    assert wm.Metadata is wm.MetadataStore
    assert wm.Result is wm.ResolutionResult
