import math
from pathlib import Path

import pytest

from alns_loop import run_alns_with_library
from container_loading_state import ContainerLoadingState


def small_good_instance():
    """
    Build a tiny, quickly-solvable instance for ALNS E2E testing.
    - One container 6x6x6 with generous weight.
    - 5 small boxes that comfortably fit.
    """
    container = {"size": [6, 6, 6], "weight": 10_000}
    boxes = [
        {"id": 1, "size": [2, 2, 2], "weight": 10, "rotation": "free"},
        {"id": 2, "size": [2, 2, 2], "weight": 10, "rotation": "free"},
        {"id": 3, "size": [2, 2, 2], "weight": 10, "rotation": "free"},
        {"id": 4, "size": [2, 2, 1], "weight": 5, "rotation": "free"},
        {"id": 5, "size": [1, 2, 2], "weight": 5, "rotation": "z"},
    ]
    initial_assignment = [{"id": 1, "size": container["size"], "boxes": boxes}]
    return container, initial_assignment

def small_bad_instance():
    """
    Build a tiny, quickly- non solvable instance for ALNS E2E testing.
    - One container 6x6x6 with generous weight.
    - 5 small boxes that comfortably fit.
    """
    container = {"size": [6, 6, 6], "weight": 10_000}
    boxes = [
        {"id": 1, "size": [7, 2, 2], "weight": 10, "rotation": "free"},
        {"id": 5, "size": [1, 2, 2], "weight": 5, "rotation": "z"},
    ]
    initial_assignment = [{"id": 1, "size": container["size"], "boxes": boxes}]
    return container, initial_assignment



def settings_path():
    # Keep phase2 fast for tests
    return str(Path("tests/inputs/step2_settings_test.json"))


@pytest.mark.timeout(20)
def test_alns_e2e_runs_and_preserves_items():
    container, initial_assignment = small_good_instance()

    best = run_alns_with_library(
        initial_assignment=initial_assignment,
        container=container,
        step2_settings_file=settings_path(),
        num_iterations=10,
        num_remove=1,
        time_limit=2,
        max_no_improve=5,
        phase1_time_limit=1,
        seed=123,
        verbose=False,
    )

    assert isinstance(best, ContainerLoadingState)

    # Best score should be a finite float
    best_score = best.objective()
    assert isinstance(best_score, float)
    assert math.isfinite(best_score)

    # Item count preserved by repair (each item assigned exactly once)
    orig = sum(len(c["boxes"]) for c in initial_assignment)
    now = sum(len(c["boxes"]) for c in best.assignment)
    assert now == orig

    # Statuses present and valid
    assert len(best.statuses) == len(best.assignment)
    valid_status = {"OPTIMAL"}
    for s in best.statuses:
        assert s in valid_status


@pytest.mark.timeout(20)
def test_alns_best_not_worse_than_initial():
    container, initial_assignment = small_good_instance()

    # Evaluate the initial state to get its baseline score
    init_state = ContainerLoadingState(initial_assignment, container, settings_path(), verbose=False)
    init_score = init_state.objective()

    best = run_alns_with_library(
        initial_assignment=initial_assignment,
        container=container,
        step2_settings_file=settings_path(),
        num_iterations=8,
        num_remove=1,
        time_limit=2,
        max_no_improve=4,
        phase1_time_limit=1,
        seed=123,
        verbose=False,
    )

    best_score = best.objective()
    # Our acceptance either improves the score or (rarely) accepts by chance.
    # The global best tracked by the iterator should never be worse than the initial.
    assert best_score <= init_score


@pytest.mark.timeout(20)
def test_alns_positions_are_non_negative_when_placed():
    container, initial_assignment = small_good_instance()

    best = run_alns_with_library(
        initial_assignment=initial_assignment,
        container=container,
        step2_settings_file=settings_path(),
        num_iterations=6,
        num_remove=1,
        time_limit=2,
        max_no_improve=3,
        phase1_time_limit=1,
        seed=321,
        verbose=False,
    )

    assert isinstance(best, ContainerLoadingState)

    # For containers that solved, boxes should have a final_position tuple with non-negative coords
    for cont_idx, cont in enumerate(best.assignment):
        status = best.statuses[cont_idx]
        if status in {"OPTIMAL", "FEASIBLE"}:
            for box in cont["boxes"]:
                pos = box.get("final_position")
                if pos is not None:
                    assert isinstance(pos, tuple) and len(pos) == 3
                    assert all(isinstance(v, int) for v in pos)
                    assert all(v >= 0 for v in pos)


@pytest.mark.timeout(20)
def test_alns_infeasible_on_bad_instance():
    """
    Using a deliberately bad instance (one box too large to fit), ALNS should
    yield at least one container with status 'INFEASIBLE'.
    """
    container, initial_assignment = small_bad_instance()

    best = run_alns_with_library(
        initial_assignment=initial_assignment,
        container=container,
        step2_settings_file=settings_path(),
        num_iterations=4,
        num_remove=1,
        time_limit=2,
        max_no_improve=2,
        phase1_time_limit=1,
        seed=42,
        verbose=False,
    )

    assert isinstance(best, ContainerLoadingState)
    # Expect at least one infeasible container due to the 7-length box
    assert any(s == "INFEASIBLE" for s in best.statuses)
