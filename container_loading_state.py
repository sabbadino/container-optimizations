import copy
from step2_box_placement_in_container import run_phase_2


class ContainerLoadingState:
    """
    State class for ALNS that represents a container loading solution.
    Implements the required objective() method for the ALNS library.
    """

    def __init__(self, assignment, container, step2_settings_file, verbose=False):
        """
        assignment: list of containers, each is a dict with 'id', 'boxes' (list of box dicts)
        container: mapping with keys 'size' ([L, W, H]) and 'weight' (max weight)
        step2_settings_file: path to settings JSON for step 2
        verbose: bool, controls solver logging
        """
        self.assignment = copy.deepcopy(assignment)
        # Store the provided container spec and unpack convenience fields
        self.container = container
        self.container_size = container["size"]
        self.container_weight = container["weight"]
        self.step2_settings_file = step2_settings_file
        self.verbose = verbose
        self.statuses = []  # 'OPTIMAL', 'FEASIBLE', 'UNFEASIBLE' per container
        self.aggregate_score = None
        self.visualization_data = []  # store visualization info per container
        self._objective_computed = False
        # Placeholder used by ALNS destroy/repair operators to pass removed items
        # between operators without mutating the original state.
        self._removed_items = []

    def objective(self) -> float:
        """
        Required method for ALNS library. Returns the objective value (lower is better).
        Since ALNS assumes minimization, we return the aggregate score directly.
        """
        if not self._objective_computed:
            self.evaluate()
        return float(self.aggregate_score) if self.aggregate_score is not None else 0.0

    def evaluate(self):
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
                self.statuses.append('UNFEASIBLE')
                self.visualization_data.append(None)
                continue

            # Run step 2 placement and get placements and visualization info
            status, step2_results = run_phase_2(
                {"id": cont['id'], "size": self.container_size}, boxes,
                self.step2_settings_file, self.verbose
            )
            print(f'Completed run of phase 2 for container {cont["id"]} with size {self.container_size}')
            self.statuses.append(status)
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

        penalty = 1000 * self.statuses.count('UNFEASIBLE') + 500 * self.statuses.count('UNKNOWN')
        optimal_bonus = 2 * self.statuses.count('OPTIMAL')
        feasible_bonus = 1 * self.statuses.count('FEASIBLE')
        self.aggregate_score = penalty - optimal_bonus - feasible_bonus

        print('')
        print(
            f'\033[94mAggregate score: {self.aggregate_score} '
            f'(penalty={penalty} - optimal_bonus={optimal_bonus} - feasible_bonus={feasible_bonus})\033[0m'
        )

        self._objective_computed = True
        return self.aggregate_score

    def is_feasible(self):
        """Check if all containers have feasible solutions."""
        if not self._objective_computed:
            self.evaluate()
        return 'UNFEASIBLE' not in self.statuses

    def copy(self):
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
