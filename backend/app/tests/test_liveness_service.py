from app.services.liveness_service import (
    _YAW_INCREASING_MEANS,
    detect_blink,
    detect_head_movement,
    head_turned_direction,
)


def test_detect_blink_requires_dip_and_recovery():
    open_only = [0.30, 0.31, 0.29, 0.30]
    real_blink = [0.30, 0.29, 0.15, 0.14, 0.28, 0.30]
    stays_closed_to_end = [0.30, 0.29, 0.10, 0.09, 0.08]  # occlusion, not a blink

    assert detect_blink(open_only, threshold=0.23) is False
    assert detect_blink(real_blink, threshold=0.23) is True
    assert detect_blink(stays_closed_to_end, threshold=0.23) is False


def test_detect_head_movement_requires_sufficient_range():
    still = [1.0, 1.2, 0.8, 1.1]
    moved = [1.0, 3.0, 8.0, 2.0]

    assert detect_head_movement(still, min_range_degrees=5.0) is False
    assert detect_head_movement(moved, min_range_degrees=5.0) is True


def test_detect_head_movement_ignores_none_values():
    # yaw_from_landmarks returns None when solvePnP fails on a given frame;
    # detect_head_movement must not crash on a sequence containing them.
    sequence = [1.0, None, None, 1.5]
    assert detect_head_movement(sequence, min_range_degrees=5.0) is False


def test_detect_head_movement_needs_at_least_two_valid_readings():
    assert detect_head_movement([5.0], min_range_degrees=1.0) is False
    assert detect_head_movement([], min_range_degrees=1.0) is False


def test_head_turned_direction_matches_configured_sign_convention():
    increasing = [0.0, 2.0, 6.0, 10.0]
    decreasing = [0.0, -2.0, -6.0, -10.0]

    expected_for_increasing = _YAW_INCREASING_MEANS
    expected_for_decreasing = "left" if _YAW_INCREASING_MEANS == "right" else "right"

    assert head_turned_direction(increasing, min_range_degrees=5.0) == expected_for_increasing
    assert head_turned_direction(decreasing, min_range_degrees=5.0) == expected_for_decreasing


def test_head_turned_direction_none_when_movement_too_small():
    assert head_turned_direction([0.0, 1.0, 2.0], min_range_degrees=5.0) is None
