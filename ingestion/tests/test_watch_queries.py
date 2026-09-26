"""Tests for watching multiple products in one flyer discovery run."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

from lidl_tracker import cli_watch


def test_run_queries_searches_each_query_and_reuses_extracted_cards(
    monkeypatch, tmp_path
):
    flyer = SimpleNamespace(
        id="flyer-1",
        name="Weekly flyer",
        offer_start_date="2026-09-28",
        offer_end_date="2026-10-04",
        flyer_url="https://example.invalid/flyer",
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def discover(self):
            return [flyer]

        def download_pdf(self, _flyer, _raw_dir):
            return tmp_path / "flyer.pdf", False

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(cli_watch, "STATE_PATH", state_path)
    monkeypatch.setattr(cli_watch, "LidlLeafletClient", FakeClient)
    extract = Mock(return_value=[{"name": "product"}])
    monkeypatch.setattr(cli_watch, "extract_cards_cached", extract)
    monkeypatch.setattr(
        cli_watch,
        "search_cards",
        lambda _cards, query: [{"name": query, "price": "1.00"}],
    )
    notify = Mock(return_value=True)
    monkeypatch.setattr(cli_watch, "send_email", notify)

    queries = ["queso en salmuera", "Queso Cottage"]
    assert cli_watch.run_queries(queries, "watcher@example.invalid") == 0

    assert extract.call_count == 1
    assert [call.args[1] for call in notify.call_args_list] == [
        f"Lidl: '{query}' is in this week's flyer" for query in queries
    ]
    assert json.loads(state_path.read_text(encoding="utf-8"))["notified"] == [
        ["flyer-1", "queso en salmuera"],
        ["flyer-1", "queso cottage"],
    ]

    notify.reset_mock()
    assert cli_watch.run_queries(queries, "watcher@example.invalid") == 0
    notify.assert_not_called()
    assert extract.call_count == 1
