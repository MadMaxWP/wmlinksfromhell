from wmlinksfromhell.models import DestinationType, ResolutionStatus, SyntaxType


def test_resolve_auto_detects_url(resolver):
    result = resolver.resolve("https://en.wikipedia.org/wiki/Apple")
    assert result.syntax_type is SyntaxType.BARE_URL
    assert result.status is ResolutionStatus.RESOLVED


def test_resolve_auto_detects_wikilink_target(resolver):
    result = resolver.resolve(":w:en:Apple")
    assert result.syntax_type is SyntaxType.INTERWIKI_WIKILINK
    assert result.status is ResolutionStatus.RESOLVED


def test_url_and_interwiki_resolve_to_the_same_destination(resolver):
    from_url = resolver.resolve("https://en.wikipedia.org/wiki/Apple")
    from_interwiki = resolver.resolve(":w:en:Apple")
    assert from_url.destination == from_interwiki.destination


def test_external_url_resolution(resolver):
    result = resolver.resolve("https://example.com/page")
    assert result.status is ResolutionStatus.EXTERNAL
    assert result.destination.destination_type is DestinationType.EXTERNAL


def test_confidence_is_high_when_resolved_and_zero_when_not(resolver):
    resolved = resolver.resolve(":w:en:Apple")
    unresolved = resolver.resolve(":en:Apple")  # no source -> context_required
    assert resolved.confidence == 1.0
    assert unresolved.confidence == 0.0


def test_local_link_syntax_type_detected(resolver):
    result = resolver.resolve("Apple", source="enwiki")
    assert result.syntax_type is SyntaxType.LOCAL_WIKILINK


def test_interwiki_to_local_is_recognized_as_local_when_on_source(resolver):
    result = resolver.resolve(":w:en:Apple", source="enwiki")
    assert result.syntax_type is SyntaxType.LOCAL_WIKILINK
    result2 = resolver.resolve(":w:en:Apple", source="dewiki")
    assert result2.syntax_type is SyntaxType.INTERWIKI_WIKILINK


def test_as_dict_is_json_serializable_shape(resolver):
    import json
    result = resolver.resolve(":w:en:Apple", source="enwiki")
    payload = result.as_dict()
    json.dumps(payload)  # should not raise
    assert payload["status"] == "resolved"
    assert payload["destination"]["dbname"] == "enwiki"


def test_resolution_does_not_make_network_requests(resolver, monkeypatch):
    import urllib.request

    def fail(*args, **kwargs):
        raise AssertionError("normal resolution must not access the network")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    assert resolver.resolve(":w:en:Apple").destination.dbname == "enwiki"
    assert resolver.resolve("https://en.wikipedia.org/wiki/Apple").destination.dbname == "enwiki"


def test_known_wikimedia_host_with_unrecognized_route_is_not_ordinary_external(resolver):
    result = resolver.resolve("https://en.wikipedia.org/not-a-wiki-route")
    assert result.status is ResolutionStatus.UNSUPPORTED
    assert result.destination.destination_type is DestinationType.UNKNOWN
    assert result.destination.is_wikimedia_project is True


def test_resolution_result_as_json_matches_as_dict_json(resolver):
    import json

    result = resolver.resolve(":w:en:Apple")

    assert result.as_json() == json.dumps(result.as_dict(), sort_keys=True, ensure_ascii=False)


def test_resolve_many_matches_individual_resolution(resolver):
    values = [":w:en:Apple", ":w:de:Berlin"]

    results = resolver.resolve_many(values)

    assert [result.destination for result in results] == [resolver.resolve(value).destination for value in values]


def test_resolve_many_passes_source_to_each_resolution(resolver):
    results = resolver.resolve_many(["Apple", "Banana"], source="enwiki")

    assert [result.dbname for result in results] == ["enwiki", "enwiki"]
