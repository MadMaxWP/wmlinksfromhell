import wmlinksfromhell as wm


def test_bootstrap_arbcom_prefix_resolves_where_a_real_prefix_is_known():
    result = wm.resolve_interwiki(
        "arbcom-zh:Foo",
        source="metawiki",
    )
    assert result.destination is not None
    assert result.destination.dbname == "arbcom_zhwiki"


def test_other_special_arbcom_wikis_stay_distinct_without_a_known_prefix():
    metadata = wm.Metadata()
    for dbname in (
        "arbcom_cswiki",
        "arbcom_dewiki",
        "arbcom_enwiki",
        "arbcom_fiwiki",
        "arbcom_itwiki",
        "arbcom_nlwiki",
        "arbcom_plwiki",
        "arbcom_ruwiki",
    ):
        wiki = metadata.wiki_by_dbname(dbname)
        assert wiki is not None
        assert wiki.is_standard_project is False


def test_bootstrap_special_wiki_url_can_resolve():
    result = wm.resolve_url(
        "https://board.wikimedia.org/wiki/MediaWiki:Gadget:Xtools.js"
    )

    assert result.destination is not None
    assert result.destination.dbname == "boardwiki"
    assert result.destination.is_wikimedia_project is True
