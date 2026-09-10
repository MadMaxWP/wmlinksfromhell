from wmlinksfromhell.cache import MetadataCache


def test_cache_round_trips_and_sets_schema(tmp_path):
    cache = MetadataCache(tmp_path / "metadata.json")
    data = cache.empty()
    data["languages"]["xx"] = "Test"
    cache.save(data)

    loaded = cache.load()
    assert loaded["languages"]["xx"] == "Test"
    assert loaded["schema_version"] == data["schema_version"]
    assert loaded["updated_at"] is not None


def test_corrupt_cache_is_quarantined(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text("not json", encoding="utf-8")
    cache = MetadataCache(path)

    loaded = cache.load()

    assert loaded["wikis"] == {}
    assert not path.exists()
    assert any(p.name.startswith("metadata.json") and p.name.endswith(".corrupt") for p in tmp_path.iterdir())


def test_wrong_schema_is_quarantined(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text('{"schema_version": 999}', encoding="utf-8")
    cache = MetadataCache(path)

    loaded = cache.load()

    assert loaded["wikis"] == {}
    assert not path.exists()


def test_atomic_save_does_not_leave_tmp_file(tmp_path):
    path = tmp_path / "metadata.json"
    cache = MetadataCache(path)
    cache.save(cache.empty())

    assert path.exists()
    assert list(tmp_path.glob(".metadata-*.tmp")) == []


def test_clear_removes_cache(tmp_path):
    path = tmp_path / "metadata.json"
    cache = MetadataCache(path)
    cache.save(cache.empty())
    cache.clear()
    assert not path.exists()


def test_metadata_ignores_malformed_namespace_cache_row(tmp_path):
    from wmlinksfromhell.metadata import MetadataStore

    cache = MetadataCache(tmp_path / "metadata.json")
    data = cache.empty()
    data["namespaces"]["enwiki"] = "not-a-dict"
    cache.save(data)

    metadata = MetadataStore(cache=cache)

    assert metadata.wiki_by_dbname("enwiki") is not None
    assert "enwiki" not in metadata._namespaces
