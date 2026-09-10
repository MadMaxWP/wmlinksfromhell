import wmlinksfromhell as wm


def test_comments_are_ignored_by_default():
    code = wm.parse(
        "<!-- [[w:en:Hidden]] [https://en.wikipedia.org/wiki/Hidden] --> [[w:en:Visible]]",
        source="metawiki",
    )

    assert [link.title for link in code.filter_links()] == ["Visible"]


def test_comment_links_can_be_included_through_the_main_filter():
    code = wm.parse(
        "<!-- [[w:en:Hidden]] [https://en.wikipedia.org/wiki/Hidden2] --> [[w:en:Visible]]",
        source="metawiki",
    )

    links = code.filter_links(comment_links=True)

    assert [link.title for link in links[:1]] == ["Visible"]
    assert {link.title for link in links if link.in_comment} == {"Hidden", "Hidden2"}
    assert all(link.in_comment is False for link in links[:1])


def test_comment_only_selection_uses_the_same_filter_api():
    code = wm.parse(
        "[[w:en:Visible]] <!-- [[w:en:Hidden]] -->",
        source="metawiki",
    )

    links = code.filter_links(comment_links=True, in_comment=True)

    assert [link.title for link in links] == ["Hidden"]


def test_comment_wikilinks_and_urls_can_be_filtered_separately():
    code = wm.parse(
        "<!-- [[w:en:Hidden]] [https://en.wikipedia.org/wiki/Hidden2 Hidden] -->",
        source="metawiki",
    )

    assert [link.title for link in code.filter_wikilinks(comment_links=True)] == [
        "Hidden"
    ]
    assert [link.title for link in code.filter_external_links(comment_links=True)] == [
        "Hidden2"
    ]


def test_comment_links_can_be_converted_in_place():
    code = wm.parse(
        "<!-- [[w:en:Hidden]] --> [[w:en:Visible]]",
        source="metawiki",
    )

    code.convert(
        "url",
        comment_links=True,
        in_comment=True,
    )

    assert "https://en.wikipedia.org/wiki/Hidden" in str(code)
    assert "[[w:en:Visible]]" in str(code)


def test_link_has_a_single_simple_convert_entry_point():
    code = wm.parse("[[w:en:Apple]]", source="metawiki")
    link = code.filter_links()[0]

    returned = link.convert("url")

    assert returned is link
    assert "https://en.wikipedia.org/wiki/Apple" in str(code)


def test_top_level_short_names_are_available():
    assert wm.Code is wm.WMCode
    assert wm.Link is wm.WMLink
    assert wm.Wiki is wm.WikiInfo
    assert wm.Metadata is wm.MetadataStore
    assert wm.Result is wm.ResolutionResult
    assert wm.Error is wm.WMLinksFromHellError


def test_comment_links_can_be_converted_and_written_back_to_the_comment():
    code = wm.parse(
        "<!-- [[w:en:Hidden]] --> [[w:en:Visible]]",
        source="metawiki",
    )

    comment_links = code.filter_links(comment_links=True, in_comment=True)
    assert len(comment_links) == 1

    comment_links[0].convert("url")

    assert "<!-- [https://en.wikipedia.org/wiki/Hidden] -->" in str(code)
    assert "[[w:en:Visible]]" in str(code)

def test_category_and_file_transclusions_are_not_converted_as_normal_links():
    code = wm.parse(
        "[[Category:Help]] [[File:Example.jpg]] [[:Category:Help]] [[:File:Example.jpg]]",
        source="enwiki",
    )

    links = code.filter_links()
    assert [link.link_type for link in links] == ["category", "file", "wikilink", "wikilink"]
    assert links[0].is_category_link
    assert links[1].is_file_link
    assert not links[2].is_category_link
    assert not links[3].is_file_link

