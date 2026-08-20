from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
from pathlib import Path
import runpy
from threading import Thread
from unittest.mock import patch

import pytest

import discovery


@contextmanager
def _serve(body: str, *, age: str = "0", response_date: str | None = None):
    received_headers: dict[str, str] = {}
    received_paths: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        if response_date is not None:
            def date_time_string(self, _timestamp=None):
                return response_date

        def do_GET(self):
            received_headers.update(self.headers.items())
            received_paths.append(self.path)
            payload = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Age", age)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield (
            f"http://127.0.0.1:{server.server_port}/",
            received_headers,
            received_paths,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_fetch_fresh_page_bypasses_intermediary_caches():
    assert callable(getattr(discovery, "fetch_fresh_page", None))

    with _serve("<h1>Weekly Wisereads</h1>") as (url, received_headers, received_paths):
        page = discovery.fetch_fresh_page(url)

    assert page.body == "<h1>Weekly Wisereads</h1>"
    assert received_headers["Cache-Control"] == "no-cache, no-store, max-age=0"
    assert received_headers["Pragma"] == "no-cache"
    assert received_paths[0].startswith("/?_wisereads_fresh=")


def test_fetch_fresh_page_rejects_a_stale_cached_response():
    assert hasattr(discovery, "StalePageError")

    with _serve("<h1>Weekly Wisereads</h1>", age="3600") as (url, _, _):
        with pytest.raises(discovery.StalePageError, match="HTTP Age"):
            discovery.fetch_fresh_page(url, max_http_age_seconds=60)


def test_fetch_fresh_page_rejects_an_old_origin_response_date():
    now = datetime(2026, 8, 19, 2, 0, tzinfo=timezone.utc)
    with _serve(
        "<h1>Weekly Wisereads</h1>",
        response_date="Mon, 17 Aug 2026 02:00:00 GMT",
    ) as (url, _, _):
        with pytest.raises(discovery.StalePageError, match="response Date"):
            discovery.fetch_fresh_page(
                url,
                now=now,
                max_response_clock_skew_seconds=300,
            )


def test_fetch_fresh_page_rejects_negative_cache_age():
    with _serve("<h1>Weekly Wisereads</h1>", age="-1") as (url, _, _):
        with pytest.raises(discovery.StalePageError, match="Invalid HTTP Age"):
            discovery.fetch_fresh_page(url)


def test_live_discovery_fetches_the_origin_homepage_then_confirms_the_detail():
    assert callable(getattr(discovery, "discover_live_issue", None))

    homepage = """
    <h1>Weekly Wisereads</h1><ul>
      <li><a href="/issues/wisereads-vol-156/">Wisereads Vol. 156 — Latest</a></li>
      <li><a href="/issues/wisereads-vol-155/">Wisereads Vol. 155 — Cached</a></li>
    </ul>
    """
    detail = "<h1>Wisereads Vol. 156 — Latest</h1>"
    requested: list[str] = []

    def fetch_page(url: str):
        requested.append(url)
        body = homepage if url == discovery.HOMEPAGE_URL else detail
        return discovery.FetchedPage(url=url, body=body, http_age_seconds=0)

    result = discovery.discover_live_issue(fetch_page=fetch_page)

    assert result.state == "DISCOVERED"
    assert result.issue is not None
    assert result.issue.issue_key == "wisereads-vol-156"
    assert requested == [
        "https://wise.readwise.io/",
        "https://wise.readwise.io/issues/wisereads-vol-156/",
    ]


def test_live_discovery_surfaces_freshness_failure_instead_of_returning_noop():
    assert callable(getattr(discovery, "discover_live_issue", None))

    def stale_fetch(_url: str):
        raise discovery.StalePageError("HTTP Age 3600s exceeds 60s")

    result = discovery.discover_live_issue(fetch_page=stale_fetch)

    assert result.state == "BLOCKED_DISCOVERY_STALE"
    assert result.issue is None
    assert "HTTP Age" in result.failure_reason


def test_live_discovery_maps_network_failure_to_machine_readable_block():
    def failed_fetch(_url: str):
        raise TimeoutError("origin timed out")

    result = discovery.discover_live_issue(fetch_page=failed_fetch)

    assert result.state == "BLOCKED_DISCOVERY"
    assert result.issue is None
    assert result.failure_reason == "origin timed out"


@pytest.mark.parametrize(
    ("homepage_final_url", "detail_final_url"),
    [
        ("https://attacker.invalid/", "https://wise.readwise.io/issues/wisereads-vol-156/"),
        ("https://wise.readwise.io/", "https://wise.readwise.io/issues/wisereads-vol-155/"),
    ],
)
def test_live_discovery_rejects_cross_origin_or_wrong_path_redirects(
    homepage_final_url: str,
    detail_final_url: str,
):
    homepage = """
    <h1>Weekly Wisereads</h1><ul>
      <li><a href="/issues/wisereads-vol-156/">Wisereads Vol. 156 — Latest</a></li>
    </ul>
    """
    detail = "<h1>Wisereads Vol. 156 — Latest</h1>"

    def fetch_page(url: str):
        if url == discovery.HOMEPAGE_URL:
            return discovery.FetchedPage(
                url=homepage_final_url,
                body=homepage,
                http_age_seconds=0,
            )
        return discovery.FetchedPage(
            url=detail_final_url,
            body=detail,
            http_age_seconds=0,
        )

    result = discovery.discover_live_issue(fetch_page=fetch_page)

    assert result.state == "BLOCKED_DISCOVERY_IDENTITY"
    assert result.issue is None
    assert "final URL" in result.failure_reason


def test_live_discovery_cli_emits_machine_readable_identity():
    assert callable(getattr(discovery, "main", None))

    homepage = """
    <h1>Weekly Wisereads</h1><ul>
      <li><a href="/issues/wisereads-vol-156/">Wisereads Vol. 156 — Latest</a></li>
    </ul>
    """
    detail = "<h1>Wisereads Vol. 156 — Latest</h1>"

    def fetch_page(url: str):
        body = homepage if url == discovery.HOMEPAGE_URL else detail
        return discovery.FetchedPage(url=url, body=body, http_age_seconds=0)

    stdout = StringIO()
    exit_code = discovery.main(fetch_page=fetch_page, stdout=stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "failure_reason": None,
        "issue": {
            "issue_key": "wisereads-vol-156",
            "issue_kind": "standard",
            "issue_label": "Vol. 156",
            "issue_number": 156,
            "source_url": "https://wise.readwise.io/issues/wisereads-vol-156/",
        },
        "state": "DISCOVERED",
    }


def test_discovery_script_executes_after_all_parser_functions_are_defined():
    homepage = """
    <h1>Weekly Wisereads</h1><ul>
      <li><a href="/issues/wisereads-vol-156/">Wisereads Vol. 156 — Latest</a></li>
    </ul>
    """.encode()
    detail = "<h1>Wisereads Vol. 156 — Latest</h1>".encode()
    payloads = iter((homepage, detail))

    class Response:
        def __init__(self, payload, final_url):
            self.payload = payload
            self.final_url = final_url
            self.headers = Message()
            self.headers["Content-Type"] = "text/html; charset=utf-8"
            self.headers["Date"] = datetime.now(timezone.utc).strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            self.headers["Age"] = "0"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.payload

        def geturl(self):
            return self.final_url

    def fake_urlopen(request, timeout):
        assert timeout == 30
        requested_url = request.full_url
        final_url = (
            "https://wise.readwise.io/issues/wisereads-vol-156/"
            if "/issues/" in requested_url
            else "https://wise.readwise.io/"
        )
        return Response(next(payloads), final_url)

    stdout = StringIO()
    script = Path(discovery.__file__)
    with patch("urllib.request.urlopen", fake_urlopen), redirect_stdout(stdout):
        with pytest.raises(SystemExit) as exited:
            runpy.run_path(script, run_name="__main__")

    assert exited.value.code == 0
    assert json.loads(stdout.getvalue())["issue"]["issue_key"] == "wisereads-vol-156"
