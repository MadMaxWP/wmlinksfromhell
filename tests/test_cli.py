import json
import subprocess
import sys


def test_cli_resolve_json():
    result = subprocess.run(
        [sys.executable, "-m", "wmlinksfromhell", "resolve", "w:en:Apple", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "resolved"
    assert payload["destination"]["dbname"] == "enwiki"


def test_cli_resolve_accepts_source():
    result = subprocess.run(
        [sys.executable, "-m", "wmlinksfromhell", "resolve", "Apple", "--source", "enwiki", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout)["destination"]["dbname"] == "enwiki"
