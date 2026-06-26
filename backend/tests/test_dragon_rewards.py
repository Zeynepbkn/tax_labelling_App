from __future__ import annotations

import pytest

from app.services.labeling_service import _earned_daily_dragon_count


@pytest.mark.parametrize(
    ("completed_count", "expected_dragons"),
    [
        (0, 0),
        (24, 0),
        (25, 1),
        (49, 1),
        (50, 2),
        (74, 2),
        (75, 3),
    ],
)
def test_daily_dragon_is_earned_for_each_25_documents(
    completed_count: int,
    expected_dragons: int,
) -> None:
    assert _earned_daily_dragon_count(completed_count) == expected_dragons
