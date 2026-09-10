from wmlinksfromhell.destination import Destination, normalize_title
from wmlinksfromhell.models import DestinationType


def test_normalize_title_collapses_underscores_and_whitespace():
    assert normalize_title("Page_name") == "Page name"
    assert normalize_title("Page   name") == "Page name"
    assert normalize_title("  Page_name  ") == "Page name"


def test_full_title_combines_namespace_and_title():
    dest = Destination(destination_type=DestinationType.WIKI, title="Contents", namespace="Help")
    assert dest.full_title == "Help:Contents"


def test_full_title_without_namespace():
    dest = Destination(destination_type=DestinationType.WIKI, title="Apple")
    assert dest.full_title == "Apple"


def test_equal_destinations_from_different_syntax_compare_equal():
    a = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple")
    b = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple")
    assert a == b
    assert a.same_page_as(b)


def test_fragment_difference_still_same_page():
    a = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple", fragment="History")
    b = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple")
    assert a != b  # fragments are a distinct property (spec section 37)
    assert a.same_page_as(b)  # but it's still the same page


def test_underscore_vs_space_title_same_page():
    a = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Page_name")
    b = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Page name")
    assert a.same_page_as(b)


def test_different_dbname_is_a_different_page():
    a = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple")
    b = Destination(destination_type=DestinationType.WIKI, dbname="dewiki", title="Apple")
    assert not a.same_page_as(b)


def test_as_dict_and_as_json_roundtrip_shape():
    dest = Destination(destination_type=DestinationType.WIKI, dbname="enwiki", title="Apple")
    data = dest.as_dict()
    assert data["destination_type"] == "wiki"
    assert data["dbname"] == "enwiki"
    assert isinstance(dest.as_json(), str)
