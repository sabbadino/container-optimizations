import copy
from typing import Any, Dict, List, Optional, Tuple, Literal, TypedDict, cast

from step2_box_placement_in_container import run_phase_2


# --- Type definitions for clarity and Pylance friendliness ---
class BaseBox(TypedDict):
    id: int
    size: List[int]  # [L, W, H]
    weight: float
    rotation: Literal['none', 'z', 'free']


class Box(BaseBox, total=False):
    group_id: int | str | None
    final_position: List[int] | Tuple[int, int, int]
    final_orientation: int
    final_orientation_desc: str


class ContainerEntry(TypedDict):
    id: int
    size: List[int]  # [L, W, H]
    boxes: List[Box]


class ContainerSpec(TypedDict):
    size: List[int]
    weight: float


Status = Literal['OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'UNKNOWN']
Assignment = List[ContainerEntry]


class ContainerLoadingState:
    """
    State class for ALNS that represents a container loading solution.
    Implements the required objective() method for the ALNS library.
    """

    def __init__(
        self,
        assignment: Assignment,
        container: ContainerSpec,
        step2_settings_file: str,
        verbose: bool = False,
    ) -> None:
        """
        assignment: list of containers, each is a dict with 'id', 'boxes' (list of box dicts)
        container: mapping with keys 'size' ([L, W, H]) and 'weight' (max weight)
        step2_settings_file: path to settings JSON for step 2
        verbose: bool, controls solver logging
        """
        self.assignment = copy.deepcopy(assignment)  # type: Assignment
        # Store the provided container spec and unpack convenience fields
        self.container = container  # type: ContainerSpec
        self.container_size = container["size"]  # type: List[int]
        self.container_weight = container["weight"]  # type: float
        self.step2_settings_file = step2_settings_file  # type: str
        self.verbose = verbose  # type: bool
        self.statuses = []  # type: List[Status]
        self.aggregate_score = None  # type: Optional[float]
        # Store visualization info per container (solver timing, placements, status, etc.)
        self.visualization_data = []  # type: List[Optional[Dict[str, Any]]]
        self._objective_computed = False  # type: bool
        # Placeholder used by ALNS destroy/repair operators to pass removed items
        # between operators without mutating the original state.
        self._removed_items = []  # type: List[Box]

    def objective(self) -> float:
        """
        Required method for ALNS library. Returns the objective value (lower is better).
        Since ALNS assumes minimization, we return the aggregate score directly.
        """
        if not self._objective_computed:
            self.evaluate()
        return float(self.aggregate_score) if self.aggregate_score is not None else 0.0

    def evaluate(self) -> float:
        """
        For each container, run step 2 and collect status and soft objective score.
        Also update each box in the assignment with its actual orientation and position.
        Store visualization info for each container.
        """
        self.statuses = []
        self.visualization_data = []
        container_volume = self.container_size[0] * self.container_size[1] * self.container_size[2]
        if container_volume <= 0:
            raise ValueError(
                f"Invalid container volume: {container_volume}. Container dimensions: {self.container_size}"
            )

        for cont in self.assignment:
            print(f'**** Running phase 2 for container {cont["id"]} with size {self.container_size}')
            boxes = cont.get('boxes', [])
            if not boxes:
                self.statuses.append('INFEASIBLE')
                self.visualization_data.append(None)
                continue

            # Run step 2 placement and get placements and visualization info
            status, step2_results = run_phase_2(
                {"id": cont['id'], "size": self.container_size}, boxes,
                self.step2_settings_file, self.verbose
            )
            print(f'Completed run of phase 2 for container {cont["id"]} with size {self.container_size}')
            self.statuses.append(cast(Status, status))
            self.visualization_data.append(step2_results)

            placements = step2_results.get('placements', []) if isinstance(step2_results, dict) else []
            placement_map = {p['id']: p for p in placements}
            for box in boxes:
                p = placement_map.get(box['id'])
                if p is not None:
                    box['final_position'] = p['position']
                    box['final_orientation'] = p['orientation']

            print(
                f'Container {cont["id"]}: status={status}, n_boxes={len(boxes)}, '
                f'n_placements={len(placements) if placements else 0}'
            )

        penalty = 1000 * self.statuses.count('INFEASIBLE') + 500 * self.statuses.count('UNKNOWN')
        optimal_bonus = 2 * self.statuses.count('OPTIMAL')
        feasible_bonus = 1 * self.statuses.count('FEASIBLE')
        self.aggregate_score = penalty - optimal_bonus - feasible_bonus

        print('')
        print(
            f'\033[94mAggregate score: {self.aggregate_score} '
            f'(penalty={penalty} - optimal_bonus={optimal_bonus} - feasible_bonus={feasible_bonus})\033[0m'
        )

        self._objective_computed = True
        # aggregate_score is set above
        return float(self.aggregate_score) if self.aggregate_score is not None else 0.0

    def is_feasible(self) -> bool:
        """Check if all containers have feasible solutions."""
        if not self._objective_computed:
            self.evaluate()
        return 'INFEASIBLE' not in self.statuses

    def copy(self) -> "ContainerLoadingState":
        """Create a deep copy of this state."""
        new_state = ContainerLoadingState(
            self.assignment, self.container,
            self.step2_settings_file, self.verbose
        )
        new_state.statuses = self.statuses.copy()
        new_state.aggregate_score = self.aggregate_score
        new_state.visualization_data = copy.deepcopy(self.visualization_data)
        new_state._objective_computed = self._objective_computed
        new_state._removed_items = copy.deepcopy(self._removed_items)
        return new_state
