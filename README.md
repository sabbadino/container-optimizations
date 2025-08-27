# Container Loading Optimization (3D)

This repository solves practical 3D container loading: choose which boxes go into which container and where each box sits, so that nothing overlaps, everything fits, and packing is stable and efficient.

The system does this in two phases and can optionally refine the plan with an iterative improvement loop. Technical terms are explained in plain language; you don’t need prior optimization background to use this.

---

## 1) Goal and scope

- Input: a container with inner size [L, W, H] and max payload, and a list of boxes with size [l, w, h], weight, optional group id, and allowed rotation policy.
- Output: one or more packed containers, each with a 3D placement for the boxes and a packing status (feasible/optimal/etc.).
- Hard rules respected at all times:
   - Every placed box fits fully inside the container.
   - No two boxes overlap.
   - No “floating” boxes: each box sits on the floor or directly on top of another box with face contact.
   - Total container weight and volume capacity are respected in the assignment phase.
- Soft objectives you can mix and match:
   - Use fewer containers when possible.
   - Keep grouped items together (avoid splitting groups across containers).
   - Balance volume across used containers.
   - Encourage stable stacks: large/heavy/large-base boxes lower in z.
   - Cover more floor area and maximize face-to-face contact.

---

## 2) Architecture: main logic blocks

- `main.py`: End-to-end runner. Loads JSON input, runs the two phases, optional refinement, saves JSON output, and opens a visualization if available.
- `step1_model_builder.py`: Phase 1 “assignment” model. Chooses which container each item goes into, under container capacity rules and grouping preferences.
- `step2_box_placement_in_container.py`: Phase 2 “geometry” model. Places a set of boxes into a single container in 3D with non-overlap, inside, and no-floating rules plus soft preferences.
- `model_setup.py`: Low-level variable setup for Phase 2: positions (x, y, z), allowed orientations, and effective sizes driven by rotation policy.
- `model_constraints.py`: Core constraints for Phase 2: non-overlap, inside-container, no-floating; optional anchoring.
- `model_optimizations.py`: Soft-objective terms for Phase 2 (floor coverage, large-base lower, surface contact, etc.) and symmetry breaking for identical boxes.
- `alns_loop.py`, `alns_acceptance.py`, `alns_criteria.py`: Optional iterative improvement loop. It repeatedly removes and reassigns some boxes (destroy/repair), then re-packs and keeps improvements.
- `container_loading_state.py`: Holds a candidate solution, runs Phase 2 per container to evaluate quality, and stores visualization data.
- `visualization_utils.py`: Simple 3D viewer for placements (Matplotlib). See also `visualization/alns_babylon_viewer.html` for an interactive web viewer.

---

## 3) Execution flow (what runs when)

1) Load input JSON (see “Input format”).
2) Phase 1 – assignment across containers (`step1_model_builder.py`):
    - Decide for each item which container it goes into (exactly one in current code).
    - Respect per-container volume and weight limits.
    - Softly discourage splitting groups and keep container loads balanced.
    - Minimize: number of used containers + penalties (group splits, imbalance).
3) Optional refinement (`alns_loop.py`):
    - Iteratively remove a subset of items and reassign them with Phase 1 under a time limit; keep a better plan if found. This is a pragmatic “search around the current plan” method.
4) Phase 2 – 3D placement per container (`step2_box_placement_in_container.py`):
    - For each container, compute 3D positions and orientations for its items.
    - Enforce inside, non-overlap, and no-floating.
    - Apply soft preferences (floor coverage, surface contact, lower-z for large/voluminous boxes, preferred orientations).
    - Maximize a weighted sum of these soft terms.
5) Save output JSON and, if Matplotlib is available, render a 3D view.

---

## 4) Inputs and outputs

### Input JSON (top-level)

Minimal shape:

```json
{
   "container": { "size": [L, W, H], "weight": 10000 },
   "items": [
      { "id": 1, "size": [l, w, h], "weight": 12.3, "rotation": "free", "group_id": 10 },
      { "id": 2, "size": [l, w, h], "weight": 5.0,  "rotation": "z" }
   ],
   "solver_phase1_max_time_in_seconds": 60,
   "step2_settings_file": "ortools/inputs/step2_settings_a.json",
   "alns_params": { "num_iterations": 100, "num_can_be_moved_percentage": 10, "time_limit": 60, "max_no_improve": 20 }
}
```

Notes:

- `rotation` policy per item:
   - `"none"`: fixed orientation.
   - `"z"`: can swap L and W (spin around vertical axis). Height stays on Z.
   - `"free"`: any of the 6 axis permutations are allowed.
- `solver_phase1_max_time_in_seconds` limits the time budget for the assignment model (also used by the refinement repair step).
- `step2_settings_file` tunes Phase 2 behavior (see below).

### Phase 2 settings JSON (`step2_settings_file`)

Keys recognized in `step2_box_placement_in_container.py`:

- `symmetry_mode` (default `"full"`): symmetry breaking for identical boxes: `"full"` uses lexicographic ordering on (x,y,z); `"simple"` orders along the longest container axis; anything else disables it.
- `solver_phase2_max_time_in_seconds` (default 60): time limit per container for 3D placement.
- `anchor_mode`: optional hard anchor at the origin for a specific box:
   - `"larger"`: anchor the largest-volume box at (0,0,0).
   - `"heavierWithinMostRecurringSimilar"`: among the most frequent size, anchor the heaviest at (0,0,0).
- Soft-preference weights (integers ≥ 0). Each weight scales a term that the model maximizes:
   - `prefer_total_floor_area_weight`: favor more floor area covered.
   - `prefer_maximize_surface_contact_weight`: favor larger face-to-face contact between stacked boxes.
   - `prefer_large_base_lower_weight`: favor larger base area at lower z (linear).
   - `prefer_large_base_lower_non_linear_weight`: stronger quadratic variant of the previous.
   - `prefer_put_boxes_by_volume_lower_z_weight`: favor larger-volume boxes lower in z.
   - `prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight`: favor orientations that put the largest face on the floor (for items with `rotation = "free"`).

### Output JSON

`main.py` saves an array of containers with placements and status. Example:

```json
[
   {
      "id": 1,
      "size": [L, W, H],
      "placements": [
         { "id": 1, "position": [x, y, z], "orientation": 2, "size": [l, w, h], "rotation_type": "free" }
      ],
      "status": "FEASIBLE"
   }
]
```

Orientation index → axis order (for `rotation_type = "free"`):

- 0 → [L, W, H]
- 1 → [L, H, W]
- 2 → [W, L, H]
- 3 → [W, H, L]
- 4 → [H, L, W]
- 5 → [H, W, L]

---

## 5) Phase 1 details: assignment across containers

File: `step1_model_builder.py`

Decision variables (conceptually):

- For each item i and container j: x[i,j] ∈ {0,1} (item i goes in container j).
- For each container j: y[j] ∈ {0,1} (container j is used).

Hard rules:

- Every item is assigned to exactly one container (current code has equality; change to ≤ 1 if some items can be left out).
- Per container j:
   - Sum of item volumes in j ≤ container volume × y[j].
   - Sum of item weights in j ≤ container weight × y[j].

Soft terms and objective:

- Group cohesion: for each group g, estimate how many containers it spans and penalize splits. The code builds `group_in_containers[g]` and adds `(group_in_containers[g] - 1)` to the penalty.
- Volume balance: pairwise imbalance between used containers is penalized.
- Objective minimized:
   - number of used containers (Σ y[j])
   - plus λ_group × group-split penalty
   - plus λ_balance × volume-imbalance penalty

Tuning knobs in this phase:

- `group_penalty_lambda` and `volume_balance_lambda` in `build_step1_model` control the trade-offs.
- `solver_phase1_max_time_in_seconds` in the input JSON limits solve time.

---

## 6) Phase 2 details: 3D placement in a container

Files: `step2_box_placement_in_container.py`, `model_setup.py`, `model_constraints.py`, `model_optimizations.py`

Variables (per item i):

- Position integers x[i], y[i], z[i] (lower-left-bottom corner).
- Orientation choice among allowed permutations (driven by `rotation`). Effective size (l_eff[i], w_eff[i], h_eff[i]) is linked to the chosen orientation.

Hard rules enforced:

- Inside bounds: x[i] + l_eff[i] ≤ L; y[i] + w_eff[i] ≤ W; z[i] + h_eff[i] ≤ H.
- Non-overlap: for every pair (i, j), at least one must be true: i is left/right/in front/behind/below/above j. The code implements this with six boolean conditions and requires at least one to hold.
- No-floating: each box either sits on the floor (z = 0) or exactly on top of another box, and their projections overlap in x and y.

Search-space reductions and anchors:

- Symmetry breaking for identical boxes (same size and rotation policy):
   - `symmetry_mode = "simple"`: order boxes along the longest container axis.
   - `symmetry_mode = "full"`: order lexicographically on (x, y, z).
- Optional anchor (`anchor_mode`) pins one selected box at (0,0,0) to stabilize the layout.

Soft preferences (you control weights in settings):

- Total floor area covered (more is better).
- Maximize surface contact between stacked faces.
- Prefer orientations with the largest face on the floor (for freely rotatable items).
- Prefer large-base boxes lower in z (linear and stronger quadratic variant).
- Prefer larger-volume boxes lower in z.

Objective in Phase 2:

- Maximize the weighted sum of the chosen soft terms. All hard rules above are always enforced; weights only steer among compliant layouts.

Time limit:

- `solver_phase2_max_time_in_seconds` bounds the computation per container.

---

## 7) Optional refinement loop (destroy/repair search)

Files: `alns_loop.py`, `alns_acceptance.py`, `alns_criteria.py`, `container_loading_state.py`

Plain-language idea:

- Start from the Phase 1 plan. Repeatedly “shake” it by removing a handful of items and then repairing the plan by reassigning those items. Keep the new plan if it’s better. Stop after a time or no further improvement.

What happens each iteration:

1) Destroy: randomly select up to N items and unassign them.
2) Repair: run the Phase 1 assignment solver on “removed + fixed” items (fixed keep their containers) with a time limit to reassign.
3) Evaluate: for each container in the plan, run Phase 2 placement to get a quality score. Score includes penalties for infeasible/unknown placements and small bonuses for feasible/optimal ones.
4) Accept/Reject: keep strictly better solutions, and occasionally accept a non-improving one (small probability) to escape local traps.
5) Stop: after max iterations, max no-improvement, or a global time limit.

Tuning knobs:

- `alns_params` in the input JSON: number of iterations, fraction of items to remove, loop time limit, and patience (max no-improve).
- Repair time budget uses `solver_phase1_max_time_in_seconds`.

---

## 8) How to run

Prerequisites:

- Python 3.11+ recommended. Install dependencies from `requirements.txt` (includes OR-Tools and ALNS).

Install and run:

```bash
# 1) Install deps
python -m pip install -r requirements.txt

# 2) Run end-to-end
python main.py --input inputs/your_case.json --output outputs/solution.json

# Optional: skip the refinement loop
python main.py --input inputs/your_case.json --output outputs/solution.json --no-alns
```

Run tests (if you use VS Code tasks, a task named "pytest -q" is provided):

```bash
python -m pytest -q
```

---

## 9) Practical tips and troubleshooting

- If Phase 1 fails, check container limits vs. total demand. You may need more containers or to relax “every item must be assigned”.
- If Phase 2 is slow, reduce weights so fewer soft terms compete, enable symmetry breaking (`"full"`), and increase time limits gradually.
- Use `anchor_mode` to seed a stable layout in tight instances.
- Groups: large group-split penalties will push items of the same group into the same container; set to 0 to ignore grouping.
- For heavy skew (very large items), try `prefer_put_boxes_by_volume_lower_z_weight` and/or the quadratic lower-z term for stability.

---

## 10) File-by-file map (quick reference)

- `main.py`: CLI entry; glues everything; saves output; optional Matplotlib visualization.
- `step1_model_builder.py`: container assignment with capacities, groups, and balance.
- `step2_box_placement_in_container.py`: per-container 3D placement with inside/non-overlap/no-floating and soft preferences.
- `model_setup.py`: variables and orientation linking (effective sizes from rotation policy).
- `model_constraints.py`: non-overlap, inside, no-floating, and anchoring helpers.
- `model_optimizations.py`: soft-objective terms and symmetry breaking.
- `alns_loop.py`: refinement loop; destroy/repair and evaluation.
- `alns_acceptance.py`, `alns_criteria.py`: acceptance and stopping criteria used by the loop.
- `container_loading_state.py`: holds a plan; runs Phase 2 to evaluate.
- `visualization_utils.py`: 3D Matplotlib plotter; also see `visualization/alns_babylon_viewer.html`.
- `tests/`: quick unit tests for utilities and loop scaffolding.

---

## 11) Glossary (plain language)

- Constraint solver: a tool that finds values for variables (like positions or yes/no assignments) that satisfy all rules you give it. We add an objective to prefer some valid solutions over others.
- Iterative improvement (destroy/repair): repeatedly perturb the current solution and fix it, keeping improvements; a practical way to explore nearby alternatives on bigger problems.

---

## 12) Extending the project

- To require that some items must not be placed together, add for each container j a rule like “not both i and k in j” in Phase 1, and optionally prevent adjacency in Phase 2.
- To prioritize specific SKUs, add a bonus term in Phase 2 (e.g., reward placing priority boxes on the floor) or a penalty in Phase 1 for assigning them to extra containers.
- To allow unassigned items, change the per-item assignment from `== 1` to `<= 1` in `build_step1_model` and add a value-based objective.

If you’d like this README to include a concrete example (with the sample inputs in `ortools/inputs/`), say which file you use and how you want it visualized, and we’ll wire it up.
