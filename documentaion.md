# Container Loading Optimization – Architecture & Execution Guide

This document explains the solution’s goal, end-to-end execution flow, data contracts, and the roles of the key modules and functions so a new developer can become productive quickly.

## 1) Overall goal

Solve 3‑D container loading with a two-phase CP‑SAT approach and an optional ALNS refinement:

- Phase 1 (Assignment): Decide which items go into which container(s) under weight/volume limits, while minimizing the number of used containers and soft-penalizing group splits and imbalance.
- Phase 2 (3D Placement): For each used container, place the assigned boxes in 3D with rotation and non‑overlap, maximizing soft preferences (e.g., low Z for large bases, floor coverage), subject to hard constraints.
- Optional ALNS: Iteratively improve the assignment by destroying/repairing parts of the solution; the repair uses CP‑SAT.

CP‑SAT reference: Google OR‑Tools Python CP‑SAT API (cp_model) [developers.google.com/optimization/reference/python/sat/python/cp_model](https://developers.google.com/optimization/reference/python/sat/python/cp_model)


## 2) Execution flow (main entry point)

File: `main.py`

1. Load inputs (JSON): container (size, weight), items (id, size, weight, rotation, group_id), and optional ALNS/Step2 settings.
2. Phase 1 assignment (multiple‑knapsack style) with `assignment_model.build_step1_assignment_model`:
   - Variables: x[i,j] item→container, y[j] container used.
   - Constraints: item assignment (=1), per‑container weight/volume ≤ capacity.
   - Objective: minimize used containers + group split penalty + volume imbalance penalty.
3. Optional ALNS (`--no-alns` to skip): `alns_loop.run_alns_with_library` runs destroy/repair; repair builds a CP‑SAT assignment model with fixed items.
4. Phase 2 3D placement for each container:
   - If ALNS ran: placement already evaluated within ALNS state; results propagated to output.
  - If ALNS skipped: call `step2_box_placement_in_container.run_phase_2` per container.
5. Save final JSON (containers with placements). Optionally visualize via `visualization_utils.visualize_solution`.


## Architecture at a glance

```text
        +----------------+
        |  inputs/*.json |
        +--------+-------+
             |
             v
         +-----------+
         |  main.py  |
         +-----------+
            |
    Phase 1 (CP-SAT)  |  build_step1_assignment_model()
            v
     +-------------------------------+
     | initial assignment (containers)|
     +---------------+---------------+
             |
        (optional) | ALNS loop
             v
    +-------------------------------------------+
    |    alns_loop.py                           |
    |  - destroy: remove some items             |
    |  - repair: CP-SAT assignment w/ fixes     |
    |  - state.objective(): run Phase 2 per ctr |
    +--------------------+----------------------+
               |
               v
      Phase 2 (per container, CP-SAT)
      setup_3d_bin_packing_model()
      + constraints + soft objectives
               |
               v
      placements (x,y,z, orientation)
               |
    +------------------+------------------+
    | visualization_utils.visualize_solution |
    +------------------+------------------+
               |
               v
             outputs/*.json
```

Key building blocks:

- Model setup: `model_setup.py` creates position, orientation, and effective-dimension variables.
- Hard constraints: `model_constraints.py` enforces inside-container, no-overlap, no-floating, optional anchoring.
- Soft objectives and symmetry: `model_optimizations.py` provides preference terms and symmetry breaking.
- ALNS state: `container_loading_state.py` runs Phase 2 to score assignments during ALNS.


## 3) Data model and inputs

- Container: `{ "size": [L, W, H], "weight": <max_kg> }`
- Item/Box: `{ "id": int, "size": [l, w, h], "weight": number, "rotation": "none"|"z"|"free", "group_id": optional }`
- Main input file (see examples in `inputs/`): must contain `container` and `items`. Optional: `step2_settings_file`, `alns_params` with `{ num_iterations, num_can_be_moved_percentage, time_limit, max_no_improve }` and `solver_phase1_max_time_in_seconds` for Phase 1.
- Step2 settings file: JSON with weights and options, e.g.
  - `symmetry_mode` ('simple'|'full'|'partial'|'none') — prefer 'simple' for performance; 'full' can make the CP‑SAT model heavier and slower,
  - `max_time_in_seconds`,
  - `anchor_mode` ('larger'|'heavierWithinMostRecurringSimilar'|None),
  - Soft objective weights: `prefer_total_floor_area_weight`, `prefer_large_base_lower_weight`, `prefer_large_base_lower_non_linear_weight`, `prefer_maximize_surface_contact_weight`, `prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight`, `prefer_put_boxes_by_volume_lower_z_weight`.


## 4) Phase 1 – Assignment model (step-1)

File: `assignment_model.py` → `build_step1_assignment_model(items, container_size, container_weight, max_containers, ...)`

- Variables
  - x[i,j] ∈ {0,1}: item i assigned to container j.
  - y[j] ∈ {0,1}: container j used.
  - Optional group tracking: `group_in_j[g,j]` and `group_in_containers[g]`.
  - Volume used per container: `vol_used_j`.
- Constraints
  - Item assignment: each i must be assigned exactly once (or fixed by `fixed_assignments`).
  - Capacity by weight/volume: Σ_i weight_i·x[i,j] ≤ weight_cap·y[j]; Σ_i vol_i·x[i,j] ≤ vol_cap·y[j].
  - Linking: x[i,j] ≤ y[j].
- Soft terms
  - Group split penalty: number of containers a group touches minus 1.
  - Pairwise volume balance penalty between used containers.
- Objective (Minimize)
  - Σ_j y[j] + λ_group·(group split) + λ_balance·(volume imbalance).

Outputs consumed by `main.py`: model, x, y, group_in_containers, group_ids. Solution is converted to `assignment` list: `[ { id, size, boxes:[...] }, ... ]`.


## 5) Phase 2 – 3D placement per container

Files: `model_setup.py`, `model_constraints.py`, `model_optimizations.py`, `step2_box_placement_in_container.py`

### Variables and rotation handling (model_setup.py)

- `create_position_variables`: x[i], y[i], z[i] ∈ [0, container_dim].
- `create_orientation_and_dimension_variables`:
  - For each box i, allowed orientation permutations (`perms_list[i]`) depend on `rotation`:
    - 'none': [(l, w, h)]
    - 'z': [(l, w, h), (w, l, h)]
    - 'free': 6 permutations of (l, w, h)
  - Orientation booleans per box, with exactly one orientation active.
  - Effective dimensions `l_eff[i], w_eff[i], h_eff[i]` channel to the selected permutation using `OnlyEnforceIf`.
- `setup_3d_bin_packing_model` returns (n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff).

### Hard constraints (model_constraints.py)

- `add_inside_container_constraint`: x[i]+l_eff[i] ≤ L, y[i]+w_eff[i] ≤ W, z[i]+h_eff[i] ≤ H.
- `add_no_overlap_constraint`: for each pair (i,j), at least one separating literal holds along X/Y/Z.
- `add_no_floating_constraint`: each box is on the floor (z=0) or exactly on top of another box while overlapping in X/Y.
- Optional anchoring: `apply_anchor_logic(anchormode=...)` can fix one representative box at (0,0,0) based on size/weight/frequency.

### Symmetry breaking and soft objectives (model_optimizations.py)

- Symmetry:
  - `add_symmetry_breaking_for_identical_boxes(mode)`: order identical boxes on the largest axis ('simple') or lexicographically ('full').
- Soft objective term generators (return IntVar lists to be summed with weights):
  - `get_total_floor_area_covered`: area on floor per box.
  - `prefer_put_boxes_lower_z` (linear) and `prefer_put_boxes_lower_z_non_linear` (quadratic): larger base area → lower z.
  - `prefer_put_boxes_by_volume_lower_z`: larger volume → lower z.
  - `prefer_maximize_surface_contact`: encourages stacked contact area when a box is exactly on top of another.
  - `prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom`: favors orientation(s) with largest bottom face (for 'free' rotation).

### Phase 2 solver wrapper (step2_box_placement_in_container.py)

- `run_phase_2(container_dict, boxes, settingsfile, verbose)` loads settings and calls `run_inner`.
- `run_inner(...)` builds the CP‑SAT model using the above helpers, sets `model.Maximize(sum(weighted_terms))`, solves with a time limit, and returns:
  - `status_str` ∈ {OPTIMAL, FEASIBLE, INFEASIBLE, MODEL_INVALID, UNKNOWN}
  - `step2_results = { elapsed_time, perms_list, placements, status_str }`
- Placement records: `{ id, position: (x,y,z), orientation: k, size: (l,w,h), rotation_type }`.


## Quick start (example)

1. Create a minimal input file (e.g., `inputs/min_example.json`):

```json
{
  "container": { "size": [4, 4, 2], "weight": 1000 },
  "items": [
    { "id": 1, "size": [1, 1, 4], "weight": 10, "rotation": "free" },
    { "id": 2, "size": [2, 2, 1], "weight": 5,  "rotation": "free" }
  ],
  "step2_settings_file": "inputs/step2_settings_a.json",
  "alns_params": { "num_iterations": 50, "num_can_be_moved_percentage": 20, "time_limit": 60, "max_no_improve": 15 },
  "solver_phase1_max_time_in_seconds": 30
}
```

1. Create a simple Step 2 settings file (e.g., `inputs/step2_settings_a.json`):

```json
{
  "symmetry_mode": "simple",
  "max_time_in_seconds": 10,
  "anchor_mode": null,
  "prefer_total_floor_area_weight": 1,
  "prefer_large_base_lower_weight": 1,
  "prefer_large_base_lower_non_linear_weight": 0,
  "prefer_maximize_surface_contact_weight": 0,
  "prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight": 0,
  "prefer_put_boxes_by_volume_lower_z_weight": 0
}
```

1. Run end-to-end to produce placements (adjust paths as needed):

```bash
python main.py --input inputs/min_example.json --output outputs/min_out.json
```

1. To skip ALNS and run Phase 2 directly on Phase 1’s assignment:

```bash
python main.py --input inputs/min_example.json --output outputs/min_out.json --no-alns
```


## 6) ALNS refinement (optional)

Files: `alns_loop.py`, `container_loading_state.py`, `alns_acceptance.py`, `alns_criteria.py`

- State: `ContainerLoadingState` stores the assignment and container spec; `objective()` runs Phase 2 for each container (via `evaluate()`), caches `aggregate_score = penalties − bonuses`, and returns it to the ALNS engine.
- Operators:
  - Destroy: `create_destroy_random_items(num_remove)` removes a random subset of items from the assignment.
  - Repair: `create_repair_cpsat(max_time_in_seconds)` rebuilds a CP‑SAT assignment for removed+fixed items (uses the same step‑1 model with fixed assignments and groups), then reconstructs the assignment.
- Acceptance: `CustomContainerAcceptance` accepts a candidate if feasible and better than best (or with a small random chance).
- Stopping: `StoppingCriterionWithProgress(max_iterations, max_no_improve)` prints progress and stops on limits.
- Entry: `run_alns_with_library(initial_assignment, container, step2_settings_file, ...)` wires everything and returns the best state.

### ALNS loop, in detail (what happens each iteration and why)

This section clarifies the data/control flow inside the ALNS iterate loop and how each function participates.

1. Initialization (outside the loop)

- `run_alns_with_library(...)`
  - Wraps the Step‑1 assignment in a `ContainerLoadingState` (deep copy) with the container spec and Step‑2 settings.
  - Calls `ContainerLoadingState.objective()` once to get a baseline score. Internally this calls `evaluate()` which runs Phase‑2 placement per container via `run_phase_2(...)` and sets `aggregate_score` and `statuses`.
  - Builds the ALNS engine, registers operators, and configures selection (`RouletteWheel([1,0,0,0])` with one destroy/repair), acceptance (`CustomContainerAcceptance`), and stopping (`StoppingCriterionWithProgress`).

1. One ALNS iteration (driven by `alns.iterate(...)`)

- Selection
  - With a single destroy and repair operator registered, `RouletteWheel` deterministically picks that pair. The reward vector `[1,0,0,0]` means only “new global best” events update operator weights; with one pair, this has no effect on choice but keeps compatibility with the library API.

- Destroy: make a partial solution
  - `create_destroy_random_items(num_remove)` returns `destroy_random_items(current, rng)`.
  - It calls `current.copy()` to satisfy ALNS’s requirement that operators are pure. Copy preserves `assignment`, `container`, and the cached objective flags.
  - It flattens all `(container_index, box_index)` pairs, samples `num_remove`, and removes those boxes from their containers.
  - It records removed items on the state as `state._removed_items` and invalidates the cached objective (`_objective_computed=False`). Output is a partial state with some items unassigned.

- Repair: close the solution via CP‑SAT
  - `create_repair_cpsat(phase1_time_limit)` returns `repair_cpsat(destroyed, rng)`.
  - It builds an item list combining:
    - removed items (free to assign), and
    - fixed items from the partial assignment (forced to their current container).
  - It constructs `fixed_assignments` and a `group_to_items` map. It sets `max_containers = current_used + removed_count` to allow opening new bins if needed.
  - Calls `build_step1_assignment_model(...)` to create the Step‑1 CP‑SAT with weight/volume capacities, group split penalty, and x≤y linking; fixed items are channeled to their containers.
  - Solves with a time limit via `cp_model.CpSolver.parameters.max_time_in_seconds = phase1_time_limit` and rebuilds a fresh `assignment` from the solution using the set of used `y[j]` indices.
  - Returns a new `ContainerLoadingState` wrapping this repaired full assignment.

- Evaluation (objective of the candidate)
  - ALNS queries `candidate.objective()`. If the cached flag is false, `ContainerLoadingState.evaluate()` runs Phase‑2 per container by calling `run_phase_2(container_dict, boxes, step2_settings_file, verbose)`.
  - For each container, it records `status_str` and placements; it copies back `final_position` and `final_orientation` to each box, then computes
    `aggregate_score = 1000 * count('UNFEASIBLE') + 500 * count('UNKNOWN') - 2 * count('OPTIMAL') - 1 * count('FEASIBLE')`.
  - Since the ALNS library expects minimization, lower `aggregate_score` is better.

- Acceptance decision
  - `CustomContainerAcceptance.__call__(rng, best, current, candidate)` rejects immediately if `candidate.is_feasible()` is false (i.e., any container has status `'UNFEASIBLE'`).
  - Otherwise accept if `candidate.objective() < best.objective()` (strict improvement) or with 5% random chance. This enables occasional uphill moves.

- Book‑keeping and stopping
  - If accepted and better than best, ALNS updates `best_state`.
  - `StoppingCriterionWithProgress.__call__` increments iteration counters, prints: `Iteration k/N | No improvement a/b`, and stops when either limit is hit.

1. Results

- `alns.iterate(...)` returns a `result` object with `best_state`. `run_alns_with_library(...)` returns `(best_state, result)`.
- The best state already contains Phase‑2 placements and statuses for every container, ready to serialize or visualize.

1. Contracts and shapes (quick reference)

- State input/output
  - `assignment`: `[ { id: int, size: [L,W,H], boxes: [ { id,size,weight,rotation,group_id?, final_position?, final_orientation? }, ... ] }, ... ]`
  - Container spec: `{ size: [L,W,H], weight: number }`
  - Step‑2 settings: path to JSON with soft weights and options.
- Destroy/Repair
  - Destroy mutates only a copy; it adds `state._removed_items` for the repair.
  - Repair uses Step‑1 CP‑SAT (`build_step1_assignment_model`) with `fixed_assignments` and `group_to_items`; solve time is bounded by `phase1_time_limit`.
- Objective/feasibility
  - `objective()` calls `evaluate()` and caches `aggregate_score`; `is_feasible()` is `statuses` ∉ {'UNFEASIBLE'}.

References

- ALNS library: [https://alns.readthedocs.io](https://alns.readthedocs.io)
- OR‑Tools CP‑SAT (Python): [https://developers.google.com/optimization/reference/python/sat/python/cp_model](https://developers.google.com/optimization/reference/python/sat/python/cp_model)

  ### ALNS loop — sequence diagram

  ```mermaid
  sequenceDiagram
    autonumber
    participant main as run_alns_with_library
    participant alns as ALNS Engine
    participant destroy as Destroy (remove items)
    participant repair as Repair (CP-SAT Step‑1)
    participant state as ContainerLoadingState
    participant step2 as Phase‑2 Solver

    main->>state: Build initial state (copy assignment, container, settings)
    main->>state: objective() baseline
    state->>step2: run_phase_2 per used container
    step2-->>state: placements, statuses, aggregate_score
    main->>alns: iterate(state, select, accept, stop)

    loop Iteration k
      alns->>destroy: apply(current_state)
      destroy-->>alns: partial_state with _removed_items

      alns->>repair: apply(partial_state)
      repair->>repair: build Step‑1 model (fixed_assignments, groups)
      repair->>repair: solve CP‑SAT (time_limit)
      repair-->>alns: repaired_state (full assignment)

      alns->>state: candidate.objective()
      state->>step2: run_phase_2 per used container
      step2-->>state: placements, statuses, aggregate_score

      alns->>alns: acceptance (feasible + better or 5% chance)
      alt accepted
        alns->>alns: update current (and maybe best)
      else rejected
        alns->>alns: keep current
      end

      alns->>alns: stopping check (max iterations / max no‑improve)
    end
  ```

### Legend / scoring

- Feasibility statuses used by ALNS scoring:
  - OPTIMAL, FEASIBLE: counted as bonuses
  - UNFEASIBLE: heavy penalty (any UNFEASIBLE makes the candidate rejected by acceptance)
  - UNKNOWN: moderate penalty
- Aggregate score (minimized by ALNS):
  - score = 1000 · count(UNFEASIBLE) + 500 · count(UNKNOWN) − 2 · count(OPTIMAL) − 1 · count(FEASIBLE)
  - Lower is better. A strictly lower score is required for deterministic acceptance (5% random chance can accept otherwise).
- Practical note: Phase‑2 may return various strings; ALNS logic specifically checks for 'UNFEASIBLE' to define infeasibility.


## 7) Visualization

File: `visualization_utils.py` → `visualize_solution(time_taken, container, boxes, placements, status_str)` draws the container wireframe and boxes as colored cuboids, with orientation arrows (original axes colors: x=red, y=green, z=blue). Safe under pytest (Agg backend).


## 8) Key modules and functions (map)

- `main.py`
  - Orchestrates input → Phase 1 → (ALNS?) → Phase 2 → output (+ visualization)
- `assignment_model.py`
  - `build_step1_assignment_model(...)` – CP‑SAT assignment, capacities, groups, balance, minimize containers
- `model_setup.py`
  - `create_position_variables`, `create_orientation_and_dimension_variables`, `setup_3d_bin_packing_model`
- `model_constraints.py`
  - `add_inside_container_constraint`, `add_no_overlap_constraint`, `add_no_floating_constraint`, `apply_anchor_logic`
- `model_optimizations.py`
  - Symmetry breaking + soft objective term builders described above
- `step2_box_placement_in_container.py`
  - `run_phase_2`, `run_inner` – build/solve per‑container 3D model, produce placements
- `alns_loop.py`
  - `run_alns_with_library`, destroy/repair factories
- `container_loading_state.py`
  - `ContainerLoadingState` – ALNS state, calls Phase 2 to score solutions
- `visualization_utils.py`
  - `visualize_solution` – 3D plot builder
- Tests: `tests/test_geometry.py` – validates geometry constraints (inside container, no overlap, rotation behavior)


## 9) Running and testing

- Environment: repo includes a local venv at `ortools/` with Python and packages. Requirements in `requirements.txt` (ensure OR‑Tools and ALNS installed in your env).
- Run main:
  - Example: `python main.py --input inputs/alns_input_data_50_items_1.json --output outputs/alns_out.json`
  - Flags: `--no-alns` to skip ALNS, `--verbose` for extra logs.
- Run tests:
  - Use the provided VS Code task "pytest -q" or run `pytest -q` in the active environment.


## 10) Modeling notes and tips

- Rotation policy is strictly respected per box: 'none' (fixed), 'z' (swap L/W only), 'free' (all 6 permutations).
- Symmetry breaking helps prune equivalent solutions; prefer 'simple' in practice. The 'full' lexicographical ordering often inflates model size and constraints, making CP‑SAT significantly slower on larger instances.
- Soft objectives are additive; scale weights to reflect priorities. Since placement objective is maximization, larger weights strengthen that preference.
- For large instances, use time limits (`max_time_in_seconds`) and consider ALNS to escape local optima by re‑assigning items with CP‑SAT repair.
- When debugging feasibility:
  - Check capacities in Phase 1,
  - Validate rotation permissions and container size in Phase 2,
  - Use `tests/test_geometry.py` patterns to isolate geometry issues.
