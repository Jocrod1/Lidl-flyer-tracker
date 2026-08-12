"""Tests for watch-state idempotency (no network/PDF involved)."""

from __future__ import annotations

from lidl_tracker.cli_watch import already_notified, mark_notified


class TestWatchState:
    def test_fresh_state_has_no_notifications(self):
        state = {"notified": []}
        assert not already_notified(state, "flyer-1", "queso en salmuera")

    def test_marking_then_checking(self):
        state = {"notified": []}
        mark_notified(state, "flyer-1", "queso en salmuera")
        assert already_notified(state, "flyer-1", "queso en salmuera")

    def test_different_flyer_is_independent(self):
        state = {"notified": []}
        mark_notified(state, "flyer-1", "queso en salmuera")
        assert not already_notified(state, "flyer-2", "queso en salmuera")

    def test_different_query_on_same_flyer_is_independent(self):
        state = {"notified": []}
        mark_notified(state, "flyer-1", "queso en salmuera")
        assert not already_notified(state, "flyer-1", "air fryer")
