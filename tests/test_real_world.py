from pathlib import Path

import pytest

import wmlinksfromhell


FIXTURE = Path(__file__).parent / "fixtures" / "meta_update_a_common_gadget.txt"


def test_meta_fixture_has_mixed_realistic_link_forms(metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis["dvwiktionary"] = WikiInfo(
        "dvwiktionary", "wiktionary", "wiktionary", "dv", "Divehi", "dv.wiktionary.org",
    )
    metadata._reindex()
    text = FIXTURE.read_text(encoding="utf-8")
    code = wmlinksfromhell.parse(text, source="metawiki", metadata=metadata)
    links = code.filter_links()

    assert links
    assert any(link.is_wikilink and link.dbname == "metawiki" for link in links)
    assert any(link.dbname == "enwiki" for link in links)
    assert any(link.dbname == "dvwiktionary" for link in links)
    assert any(link.destination_type == "service" and link.service_name == "Phabricator" for link in links)
    assert any(link.destination_type == "external" for link in links)


def test_meta_fixture_structural_selection_can_be_scoped_to_a_section(metadata):
    text = FIXTURE.read_text(encoding="utf-8")
    code = wmlinksfromhell.parse(text, source="metawiki", metadata=metadata)
    sections = code.get_sections()
    target = next(section for section in sections if any("Update a common gadget" in str(h.title) for h in section.wikicode.filter_headings()))
    links = target.filter_links()
    assert any(link.dbname == "enwiki" for link in links)
    assert any(link.destination_type == "service" for link in links)


@pytest.mark.live
def test_live_meta_update_a_common_gadget():
    pywikibot = pytest.importorskip("pywikibot")
    site = pywikibot.Site("meta", "meta")
    page = pywikibot.Page(site, "Steward requests/Miscellaneous")
    code = wmlinksfromhell.parse(page.text, source=site)
    sections = code.get_sections()
    target = next(section for section in sections if any(str(h.title).strip() == "Update a common gadget" for h in section.wikicode.filter_headings()))
    links = target.filter_links()
    assert links
    assert any(link.dbname == "enwiki" for link in links)
