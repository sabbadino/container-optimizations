import json
import sys
from ortools.sat.python import cp_model
from load_utils import load_data_from_json

def run_phase_2(container, boxes, settingsfile, verbose=True, visualize=True):
    """Run phase 2: place boxes inside a single container using CP-SAT.

    This function loads solver/heuristic settings from a JSON file and
    delegates to the internal CP-SAT model builder/solver to compute
    placements of the given boxes within the given container, optionally
    applying soft preferences (e.g., maximize floor coverage, prefer lower Z,
    orientation preferences) and visualization.

    Args:
        container: Dict with keys: 'id' and 'size' = [L, W, H].
            Note: list/tuple input is no longer supported.
        boxes: List[dict] describing items to place. Each item should include at
            least an "id" and a "size" triple [l, w, h]. Optional fields like
            "rotation" control allowed orientations.
        settingsfile: Path to a JSON file containing solver and preference
            parameters (e.g., symmetry_mode, max_time_in_seconds, anchor_mode,
            and preference weights).
        verbose: If True, print diagnostic information.
        visualize: If True, create a 3D visualization of the solution.

    Returns:
        Tuple[str, dict]:
            - status_str: Solver status string (one of
                {"OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID", "UNKNOWN"}).
            - step2_results: Dict with information to reproduce visualization and
                analysis (elapsed_time, perms_list, placements, status_str).
              Note: placements are included inside step2_results to avoid duplication.
    """
    # Load settings from the JSON file
    with open(settingsfile, 'r') as f:
        data = json.load(f)

    # Validate and normalize container input (must be dict with size)
    if not isinstance(container, dict):
        raise TypeError("container must be a dict with keys 'id' and 'size' = [L, W, H]")
    if container.get('size') is None:
        raise ValueError("container dict must contain 'size' key with [L, W, H]")
    container_size = container['size']

    symmetry_mode = data.get('symmetry_mode', 'full')
    max_time_in_seconds = data.get('max_time_in_seconds', 60)
    anchor_mode = data.get('anchor_mode', None)
    prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight = data.get('prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight', 0)
    prefer_maximize_surface_contact_weight = data.get('prefer_maximize_surface_contact_weight', 0)
    prefer_large_base_lower_weight = data.get('prefer_large_base_lower_weight', 0)
    prefer_total_floor_area_weight = data.get('prefer_total_floor_area_weight', 0)  # default 0 for backward compatibility
    prefer_large_base_lower_non_linear_weight = data.get('prefer_large_base_lower_non_linear_weight', 0)  # default 0
    prefer_put_boxes_by_volume_lower_z_weight = data.get('prefer_put_boxes_by_volume_lower_z_weight', 0)  # default 0
    status_str, step2_results = run_inner(
        container_size, boxes, symmetry_mode, max_time_in_seconds, anchor_mode,
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,
        prefer_maximize_surface_contact_weight,
        prefer_large_base_lower_weight,
        prefer_total_floor_area_weight,
        prefer_large_base_lower_non_linear_weight,
        prefer_put_boxes_by_volume_lower_z_weight,
        verbose,
        visualize)
    return status_str, step2_results

def run_inner(container, boxes, symmetry_mode, max_time, anchor_mode,     prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,     prefer_maximize_surface_contact_weight,     prefer_large_base_lower_weight,     prefer_total_floor_area_weight,     prefer_large_base_lower_non_linear_weight,     prefer_put_boxes_by_volume_lower_z_weight,     verbose=False, visualize=True ):
    """Builds and solves the 3D box placement CP-SAT model for one container.

    Sets up decision variables, hard constraints (inside container, no overlap,
    no floating), optional anchoring, and symmetry breaking. Adds soft-objective
    terms based on the provided preference weights, then solves under a time
    limit. Optionally visualizes the resulting placement.

    Note:
        For cubic boxes (l == w == h), rotation is forced to 'fixed' on an
        internal deep copy of the input boxes to reduce symmetry. The input
        list is not mutated.

    Args:
        container: Container size triple [L, W, H] consumed by the model setup.
    boxes: List of dicts with at least 'id' and 'size' = [l, w, h]. May
            include 'rotation' to control allowed orientations.
        symmetry_mode: Symmetry breaking mode for identical boxes (e.g., 'full'
            or other supported modes).
        max_time: Solver time limit in seconds.
        anchor_mode: Optional anchoring strategy applied to some boxes
            (implementation-dependent, can be None).
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight:
            Weight for preferring orientations where the largest face lies on
            the floor.
        prefer_maximize_surface_contact_weight: Weight for maximizing contact
            area among touching faces.
        prefer_large_base_lower_weight: Linear weight to prefer lower z for
            boxes with larger base.
        prefer_total_floor_area_weight: Weight to maximize total covered floor
            area by boxes that touch the floor.
        prefer_large_base_lower_non_linear_weight: Non-linear variant of the
            lower-z preference for large-base boxes.
        prefer_put_boxes_by_volume_lower_z_weight: Weight to prefer larger
            volume boxes at lower z.
        verbose: If True, prints diagnostic information.
        visualize: If True, renders a 3D visualization of the solution.

        Returns:
                Tuple[str, dict]:
                        - status_str: One of {"OPTIMAL", "FEASIBLE", "INFEASIBLE",
                            "MODEL_INVALID", "UNKNOWN"}.
                        - step2_results: Dict with visualization/analysis inputs
                            {elapsed_time, perms_list, placements, status_str}.
                          Note: placements are included inside step2_results.
    """

    if verbose:
        print(f'symmetry_mode:  {symmetry_mode}')
        print(f'anchormode: {anchor_mode}')
        print(f'prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight: {prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight}')
        print(f'prefer_maximize_surface_contact_weight: {prefer_maximize_surface_contact_weight}')
        print(f'prefer_total_floor_area_weight: {prefer_total_floor_area_weight}')
        print(f'prefer_large_base_lower_weight: {prefer_large_base_lower_weight}')
        print(f'prefer_large_base_lower_non_linear_weight: {prefer_large_base_lower_non_linear_weight}')
        print(f'prefer_put_boxes_by_volume_lower_z_weight: {prefer_put_boxes_by_volume_lower_z_weight}')

    # Work on a local deep copy of boxes: override rotation for cubes without mutating input
    import copy as _copy
    boxes_local = _copy.deepcopy(boxes)
    for i, item in enumerate(boxes_local):
        if item['size'][0] == item['size'][1] == item['size'][2] and item.get('rotation') != 'fixed':
            item['rotation'] = 'fixed'


    model = cp_model.CpModel()
    from model_setup import setup_3d_bin_packing_model
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes_local)
    import time
    solver = cp_model.CpSolver()
    #if verbose:
     #   solver.parameters.log_search_progress = True




    from model_constraints import add_no_overlap_constraint, apply_anchor_logic
   
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)


    from model_constraints import add_inside_container_constraint
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)


    # Anchor logic based on anchormode
    apply_anchor_logic(model, anchor_mode, boxes_local, x, y, z)


    from model_optimizations import prefer_put_boxes_by_volume_lower_z, add_symmetry_breaking_for_identical_boxes,prefer_put_boxes_lower_z, prefer_put_boxes_lower_z_non_linear, get_total_floor_area_covered, prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom, prefer_maximize_surface_contact

    # Symmetry breaking for identical boxes (same size and allowed rotations)
    add_symmetry_breaking_for_identical_boxes(model, boxes_local, x, y, z, symmetry_mode, container)

    # Add no floating constraint
    from model_constraints import add_no_floating_constraint
    on_floor_vars = add_no_floating_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)


    # Soft constraints
    terms = []

    

    if prefer_total_floor_area_weight:
        # Maximize total covered floor area (as a soft constraint with weight)
        area_vars = get_total_floor_area_covered(model, n, on_floor_vars, l_eff, w_eff, container)
        terms.append(prefer_total_floor_area_weight * sum(area_vars))
        
    if prefer_maximize_surface_contact_weight:
        contact_area_vars = prefer_maximize_surface_contact(model, n, x, y, z, l_eff, w_eff, h_eff,container)
        gamma = prefer_maximize_surface_contact_weight
        terms.append(gamma * sum(contact_area_vars))    

    if prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight:
        preferred_orient_vars = prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom(perms_list, orient, boxes_local)
        beta = prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight
        terms.append(beta * sum(preferred_orient_vars))
    
    if prefer_large_base_lower_weight:
        weighted_terms = prefer_put_boxes_lower_z(model, n, z, l_eff, w_eff, container)
        delta = prefer_large_base_lower_weight
        terms.append(delta * sum(weighted_terms))
    if prefer_large_base_lower_non_linear_weight:
        weighted_terms_nl = prefer_put_boxes_lower_z_non_linear(model, n, z, l_eff, w_eff, container)
        delta_nl = prefer_large_base_lower_non_linear_weight
        terms.append(delta_nl * sum(weighted_terms_nl))
    if prefer_put_boxes_by_volume_lower_z_weight:
        weighted_terms_vol = prefer_put_boxes_by_volume_lower_z(model, n, z, l_eff, w_eff, h_eff, container)
        delta_vol = prefer_put_boxes_by_volume_lower_z_weight
        terms.append(delta_vol * sum(weighted_terms_vol))
    model.Maximize(sum(terms))


    # Solve
    print(f'run inner max_time_in_seconds {max_time}');
    solver.parameters.max_time_in_seconds = max_time
    print(f'Solver max_time_in_seconds: {max_time}')
    start_time = time.time()
    status = solver.Solve(model)
    elapsed_time = time.time() - start_time

    # Print model status
    status_dict = {
        cp_model.OPTIMAL: 'OPTIMAL',
        cp_model.FEASIBLE: 'FEASIBLE',
        cp_model.INFEASIBLE: 'INFEASIBLE',
        cp_model.MODEL_INVALID: 'MODEL_INVALID',
        cp_model.UNKNOWN: 'UNKNOWN',
    }

    status_str = status_dict.get(status, str(status))
    color_map = {
        'OPTIMAL': '\033[92m',      # Green
        'FEASIBLE': '\033[94m',     # Blue
        'INFEASIBLE': '\033[91m',   # Red
        'MODEL_INVALID': '\033[95m',# Magenta
        'UNKNOWN': '\033[93m',     # Yellow
    }
    color = color_map.get(status_str, '\033[0m')
    endc = '\033[0m'
    print(f'Step 2 Solver status: {color}{status_str}{endc}')  
    print(f'Solver time: {elapsed_time:.3f} seconds')


    placements = []
    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        for i in range(n):
            # Find which orientation is selected
            orient_val = [solver.Value(orient[i][k]) for k in range(len(orient[i]))]
            orient_idx = orient_val.index(1) if 1 in orient_val else None
            l, w, h = perms_list[i][orient_idx] if orient_idx is not None else (None, None, None)
            pos = (solver.Value(x[i]), solver.Value(y[i]), solver.Value(z[i])) if orient_idx is not None else (None, None, None)
            
            # Get effective rotation policy used by the model (from local copy)
            current_rotation = boxes_local[i].get('rotation', 'free')
            
            placements.append({
                'id': boxes[i].get('id'),
                'position': pos,
                'orientation': orient_idx,
                'size': (l, w, h),
                'rotation_type': current_rotation
            })
            print(f'BoxId {boxes[i].get("id")}: pos={pos}, size=({l}, {w}, {h}), orientation={orient_idx}, rotation_type={current_rotation}')

        if visualize:
            from visualization_utils import visualize_solution
            # Use original boxes (unmodified) for visualization labels and original sizes
            # container may be size triple; ID (if needed) is inferred when a dict is passed
            plt = visualize_solution(elapsed_time, container, boxes, perms_list, placements, status_str)
            plt.show(block=False)
    else:
        print('No solution found.')

    # Always return visualization info as a dict
    step2_results = {
        'elapsed_time': elapsed_time,
        'perms_list': perms_list,
        'placements': placements,
    # 'n' deprecated; viewers infer from placements length
        'status_str': status_str,
    }
    return status_str, step2_results






