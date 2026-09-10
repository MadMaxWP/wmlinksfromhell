import pytest

from wmlinksfromhell.metadata import MetadataStore
from wmlinksfromhell.resolver import Resolver


@pytest.fixture
def metadata() -> MetadataStore:
    return MetadataStore(cache=_NullCache())


@pytest.fixture
def resolver(metadata) -> Resolver:
    return Resolver(metadata)


class _NullCache:
    """a cache stand-in that never has anything on disk, so tests are
    isolated from whatever a real ~/.cache happens to contain"""

    def load(self) -> dict:
        return {"schema_version": 1, "updated_at": None, "wikis": {}, "interwiki_maps": {}}

    def save(self, data):  # pragma: no cover - not exercised unless a test opts in
        raise AssertionError("tests should not write to the real cache")

    def is_expired(self, max_age_seconds):
        return True

    def clear(self):
        pass
