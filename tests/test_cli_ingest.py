"""Unit tests for the ingest CLI."""

from __future__ import annotations

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
