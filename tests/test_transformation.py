import pytest

import wmlinksfromhell as wm
from wmlinksfromhell.exceptions import ConversionError


def test_bulk_convert_only_matching_links(metadata):
    text = (
        "[[w:en:Apple]]\n"
        "https://en.wikipedia.org/wiki/Banana\n"
        "https://de.wikipedia.org/wiki/Berlin\n"
        "https://example.com/page\n"
        "[[mw:Some page]]\n"
    )
    code = wm.parse(text, source="enwiki", metadata=metadata)
    for link in code.filter_links():
        if link.matches(dbname="enwiki"):
            link.set_interwiki()
    result = str(code)
    assert "[[:w:en:Apple]]" in result
    assert "[[:w:en:Banana]]" in result
    assert "https://de.wikipedia.org/wiki/Berlin" in result
    assert "https://example.com/page" in result
    assert "[[mw:Some page]]" in result


def test_label_is_preserved_when_converting(metadata):
    code = wm.parse("[[w:en:Apple|this article]]", metadata=metadata)
    link = code.filter_links()[0]
    link.set_url()
    assert str(code) == "[https://en.wikipedia.org/wiki/Apple this article]"


def test_surrounding_text_and_templates_untouched(metadata):
    text = "Before {{cite|x=1}} [[w:en:Apple]] after <!-- comment --> {| \n|a\n|}"
    code = wm.parse(text, source="enwiki", metadata=metadata)
    link = code.filter_links()[0]
    link.set_local()
    result = str(code)
    assert result.startswith("Before {{cite|x=1}} [[Apple]] after <!-- comment -->")
    assert "{| \n|a\n|}" in result


def test_url_to_local_conversion(metadata):
    code = wm.parse("See https://en.wikipedia.org/wiki/Apple for details", source="enwiki",
                     metadata=metadata)
    link = code.filter_links()[0]
    link.set_local()
    assert str(code) == "See [[Apple]] for details"


def test_url_to_local_off_source_wiki_raises(metadata):
    code = wm.parse("https://en.wikipedia.org/wiki/Apple", source="dewiki", metadata=metadata)
    link = code.filter_links()[0]
    with pytest.raises(ConversionError):
        link.set_local()


def test_interwiki_to_local_conversion(metadata):
    code = wm.parse("[[:w:en:Apple]]", source="enwiki", metadata=metadata)
    link = code.filter_links()[0]
    link.set_local()
    assert str(code) == "[[Apple]]"


def test_bare_external_link_conversion_has_no_brackets(metadata):
    code = wm.parse("https://en.wikipedia.org/wiki/Apple", metadata=metadata)
    link = code.filter_links()[0]
    link.set_interwiki()
    assert str(code) == "[[:w:en:Apple]]"


def test_bracketed_external_link_with_label_becomes_bracketed_interwiki(metadata):
    code = wm.parse("[https://en.wikipedia.org/wiki/Apple fruit]", metadata=metadata)
    link = code.filter_links()[0]
    link.set_interwiki()
    assert str(code) == "[[:w:en:Apple|fruit]]"


def test_url_to_long_project_interwiki_conversion(metadata):
    code = wm.parse("https://hi.wikipedia.org/wiki/Apple", metadata=metadata)
    link = code.filter_links()[0]
    link.set_interwiki(long_project_prefix=True)
    assert str(code) == "[[:wikipedia:hi:Apple]]"


def test_unresolved_link_cannot_be_transformed(metadata):
    code = wm.parse("[[:en:Apple]]", metadata=metadata)  # no source, ambiguous
    link = code.filter_links()[0]
    with pytest.raises(ConversionError):
        link.set_interwiki()


def test_many_links_bulk_processing(metadata):
    lines = [f"https://en.wikipedia.org/wiki/Page_{i}" for i in range(200)]
    lines.append("https://de.wikipedia.org/wiki/Berlin")
    text = "\n".join(lines)
    code = wm.parse(text, source="enwiki", metadata=metadata)
    links = code.filter_links()
    assert len(links) == 201
    converted = 0
    for link in links:
        if link.matches(dbname="enwiki"):
            link.set_local()
            converted += 1
    assert converted == 200
    assert "[[Page_0]]" not in str(code)  # underscores get normalized to spaces
    assert "[[Page 0]]" in str(code)
    assert "https://de.wikipedia.org/wiki/Berlin" in str(code)
