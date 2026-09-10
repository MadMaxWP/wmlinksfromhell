import wmlinksfromhell as wm


def _links(text, source=None, metadata=None):
    code = wm.parse(text, source=source, metadata=metadata)
    return code.filter_links()


def test_match_by_dbname(metadata):
    links = _links("[[w:en:Apple]] [[w:de:Beispiel]]", metadata=metadata)
    matched = [l for l in links if l.dbname == "enwiki"]
    assert len(matched) == 1
    assert matched[0].title == "Apple"


def test_matches_helper_single_kwarg(metadata):
    links = _links("[[w:en:Apple]] [[w:de:Beispiel]]", metadata=metadata)
    matched = [l for l in links if l.matches(dbname="dewiki")]
    assert len(matched) == 1
    assert matched[0].title == "Beispiel"


def test_matches_helper_multiple_kwargs(metadata):
    links = _links("[[w:de:Beispiel]] [[q:de:Beispiel]]", metadata=metadata)
    matched = [l for l in links if l.matches(family="wikipedia", language="de")]
    assert len(matched) == 1


def test_matches_by_destination_equality(metadata):
    links = _links(
        "[[w:en:Apple]] https://en.wikipedia.org/wiki/Apple https://de.wikipedia.org/wiki/Berlin",
        metadata=metadata,
    )
    target = links[0].destination
    matched = [l for l in links if l.destination == target]
    assert len(matched) == 2


def test_wikimedia_only_flag(metadata):
    links = _links("[[w:en:Apple]] https://example.com/page", metadata=metadata)
    wikimedia = [l for l in links if l.matches(wikimedia_only=True)]
    external = [l for l in links if l.matches(external_only=True)]
    assert len(wikimedia) == 1
    assert len(external) == 1


def test_local_only_and_interwiki_only_flags(metadata):
    # [[w:en:Apple]] on enwiki points at enwiki itself, so it's local too (spec section 43);
    # [[w:de:Beispiel]] on enwiki points elsewhere, so it's a genuine interwiki link
    links = _links("[[Apple]] [[w:en:Apple]] [[w:de:Beispiel]]", source="enwiki", metadata=metadata)
    local = [l for l in links if l.matches(local_only=True)]
    interwiki = [l for l in links if l.matches(interwiki_only=True)]
    assert len(local) == 2
    assert len(interwiki) == 1
    assert interwiki[0].dbname == "dewiki"


def test_unrelated_links_are_not_matched(metadata):
    links = _links(
        "[[w:en:Apple]] https://de.wikipedia.org/wiki/Berlin https://example.com/page",
        metadata=metadata,
    )
    matched = [l for l in links if l.matches(dbname="enwiki")]
    assert len(matched) == 1


def test_url_and_interwiki_forms_match_by_semantic_destination(metadata):
    links = _links("[[w:en:Apple]] https://en.wikipedia.org/w/index.php?title=Apple", metadata=metadata)
    target = links[0].destination
    assert all(link.matches(destination=target) for link in links)


def test_match_same_page_ignores_fragment(metadata):
    links = _links("[[w:en:Apple#History]] [[w:en:Apple]]", metadata=metadata)
    assert links[0].matches(same_page_as=links[1].destination)
    assert not links[0].matches(destination=links[1].destination)
