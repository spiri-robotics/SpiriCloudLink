"""Tests for link.py: the env file it accepts, the addresses it links to, and
linking against a fake cloud."""

import json
from types import SimpleNamespace

import link
import pytest


@pytest.mark.parametrize(
    ("text", "env"),
    [
        ("", {}),
        ("# a comment\n\nA='1'\nB_2=''\n", {"A": "1", "B_2": ""}),
        ("URL='https://x.example/a b'\n", {"URL": "https://x.example/a b"}),
    ],
)
def test_parse_env_reads_the_format(text, env):
    assert link.parse_env(text) == env


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("A='1'", "newline"),
        ("A=1\n", "line 1"),
        ("a='1'\n", "line 1"),
        ("A='it''s'\n", "line 1"),
        ("A='1'\nA='2'\n", "twice"),
    ],
)
def test_parse_env_refuses_anything_else(text, error):
    with pytest.raises(ValueError, match=error):
        link.parse_env(text)


@pytest.mark.parametrize(
    ("typed", "url"),
    [
        ("example.spiri.ca", "https://example.spiri.ca"),
        (" https://drones.example.spiri.ca/ ", "https://drones.example.spiri.ca"),
        ("http://localhost:8000", "http://localhost:8000"),
    ],
)
def test_normalize_url(typed, url):
    assert link.normalize_url(typed) == url


@pytest.mark.parametrize("typed", ["ftp://example.spiri.ca", "https://:443", "exa mple.ca"])
def test_normalize_url_refuses_what_isnt_a_web_address(typed):
    with pytest.raises(ValueError):
        link.normalize_url(typed)


def test_drones_candidates_try_the_subdomain_of_a_bare_address():
    assert link.drones_candidates("https://example.spiri.ca") == [
        "https://example.spiri.ca",
        "https://drones.example.spiri.ca",
    ]


@pytest.mark.parametrize("url", ["https://drones.example.spiri.ca", "https://example.spiri.ca/drones"])
def test_drones_candidates_take_an_explicit_address_as_is(url):
    assert link.drones_candidates(url) == [url]


DEVICE = {
    "device_code": "dev-code",
    "user_code": "ABCD-EFGH",
    "verification_uri": "https://drones.example.spiri.ca/link",
    "expires_in": 600,
    "interval": 5,
}


@pytest.fixture
def cloud(tmp_path, monkeypatch):
    """A Link with its files in tmp_path and no threads, against a fake cloud
    whose Drones app answers only at the addresses in `cloud.drones`."""
    monkeypatch.setattr(link, "LINK", tmp_path / "link.json")
    monkeypatch.setattr(link, "PREFS", tmp_path / "prefs.json")
    monkeypatch.setattr(link.Link, "fetch_loop", lambda self: None)
    monkeypatch.setattr(link.Link, "poll", lambda self, attempt, pending: None)

    cloud = SimpleNamespace(drones=set(), asked=[])

    def request(method, url, fields=None, token=None, etag=None):
        cloud.asked.append(url)
        if any(url == f"{d}/oauth/device_authorization" for d in cloud.drones):
            return 200, {}, json.dumps(DEVICE).encode()
        return 404, {}, b""

    monkeypatch.setattr(link, "request", request)
    cloud.link = link.Link()
    return cloud


def test_linking_finds_the_drones_app_from_the_clouds_own_address(cloud, tmp_path):
    cloud.drones = {"https://drones.example.spiri.ca"}
    cloud.link.start("example.spiri.ca", "mu-1")
    assert cloud.link.pending["url"] == "https://drones.example.spiri.ca"
    assert cloud.link.pending["user_code"] == "ABCD-EFGH"
    # The address that answered is the one kept, to link again.
    assert json.loads((tmp_path / "prefs.json").read_text())["url"] == "https://drones.example.spiri.ca"


def test_linking_reports_the_address_as_typed_when_nothing_answers(cloud):
    with pytest.raises(ValueError, match=r"^https://example.spiri.ca didn't give a link code \(404\)"):
        cloud.link.start("example.spiri.ca", "mu-1")
    assert cloud.asked == [
        "https://example.spiri.ca/oauth/device_authorization",
        "https://drones.example.spiri.ca/oauth/device_authorization",
    ]
