"""Unit tests for the ingest CLI."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from lidl_tracker import cli_ingest


def test_cli_parses_comma_separated_slugs():
    with (
        patch("lidl_tracker.cli_ingest.db.apply_migrations") as mock_migrate,
        patch("lidl_tracker.cli_ingest.run_ingestion", return_value=[]) as mock_run,
    ):
        exit_code = cli_ingest.main(["--slug", "folleto-a, folleto-b", "--migrate"])

    assert exit_code == 0
    mock_migrate.assert_called_once()
    mock_run.assert_called_once_with(["folleto-a", "folleto-b"])


def test_cli_reports_per_flyer_pipeline_details(capsys):
    result = SimpleNamespace(
        flyer_meta=SimpleNamespace(name="Folleto", slug="folleto-abc"),
        status="STORED",
        skipped=False,
        storage_key="flyers/2026/08/hash.pdf",
        content_hash="abc123",
        flyer_existing=True,
        pdf_existing=False,
        extracted_cards=12,
        persisted_cards=12,
        extraction_key="flyers/2026/08/hash.cards.json",
    )
    with (
        patch("lidl_tracker.cli_ingest.db.apply_migrations"),
        patch("lidl_tracker.cli_ingest.run_ingestion", return_value=[result]),
    ):
        exit_code = cli_ingest.main(["--migrate"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "slug=folleto-abc" in out
    assert "pdf_sha256=abc123" in out
    assert "flyer=existing" in out
    assert "pdf=new" in out
    assert "extracted_cards=12" in out
    assert "persisted_upserted_cards=12" in out
    assert "extraction_json_key=flyers/2026/08/hash.cards.json" in out
