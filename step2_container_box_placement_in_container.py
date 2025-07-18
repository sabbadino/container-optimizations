import json
import sys
from ortools.sat.python import cp_model
from load_utils import load_data_from_json

def run_phase_2(container_id, container, boxes, settingsfile, verbose=True, visualize=True):
    # Load settings from the JSON file
    with open(settingsfile, 'r') as f:
        data = json.load(f)

    symmetry_mode = data.get('symmetry_mode', 'full')
    max_time_in_seconds = data.get('max_time_in_seconds', 60)
    anchor_mode = data.get('anchor_mode', None)
    prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight = data.get('prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight', 0)
    prefer_maximize_surface_contact_weight = data.get('prefer_maximize_surface_contact_weight', 0)
    prefer_large_base_lower_weight = data.get('prefer_large_base_lower_weight', 0)
    prefer_total_floor_area_weight = data.get('prefer_total_floor_area_weight', 0)  # default 0 for backward compatibility
    prefer_large_base_lower_non_linear_weight = data.get('prefer_large_base_lower_non_linear_weight', 0)  # default 0
    prefer_put_boxes_by_volume_lower_z_weight = data.get('prefer_put_boxes_by_volume_lower_z_weight', 0)  # default 0

    status, placements, vis_data = run_inner(
        container_id, container, boxes, symmetry_mode, max_time_in_seconds, anchor_mode,
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,
        prefer_maximize_surface_contact_weight,
        prefer_large_base_lower_weight,
        prefer_total_floor_area_weight,
        prefer_large_base_lower_non_linear_weight,
        prefer_put_boxes_by_volume_lower_z_weight,
        verbose,
        visualize)
    return status, placements, vis_data

def run_inner(container_id,container, boxes, symmetry_mode, max_time, anchor_mode, \
    prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight, \
    prefer_maximize_surface_contact_weight, \
    prefer_large_base_lower_weight, \
    prefer_total_floor_area_weight, \
    prefer_large_base_lower_non_linear_weight, \
    prefer_put_boxes_by_volume_lower_z_weight,verbose=True, visualize=True ):

    if verbose:
        print(f'symmetry_mode:  {symmetry_mode}')
        print(f'anchormode: {anchor_mode}')
        print(f'prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight: {prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight}')
        print(f'prefer_maximize_surface_contact_weight: {prefer_maximize_surface_contact_weight}')
        print(f'prefer_total_floor_area_weight: {prefer_total_floor_area_weight}')
        print(f'prefer_large_base_lower_weight: {prefer_large_base_lower_weight}')
        print(f'prefer_large_base_lower_non_linear_weight: {prefer_large_base_lower_non_linear_weight}')
        print(f'prefer_put_boxes_by_volume_lower_z_weight: {prefer_put_boxes_by_volume_lower_z_weight}')

    # override rotation if box is a cube
    for i, item in enumerate(boxes):
        if item['size'][0] == item['size'][1] == item['size'][2] and item.get('rotation') != 'fixed' :
            if verbose:
                print(f"\033[90mItem {i} is a cube, setting rotation from {item['rotation']} to 'fixed'\033[0m")
            item['rotation'] = 'fixed'


    model = cp_model.CpModel()
    from model_setup import setup_3d_bin_packing_model
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    import time
    solver = cp_model.CpSolver()





    from model_constraints import add_no_overlap_constraint, apply_anchor_logic
   
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)


    from model_constraints import add_inside_container_constraint
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)


    # Anchor logic based on anchormode
    apply_anchor_logic(model, anchor_mode, boxes, x, y, z)


    from model_optimizations import prefer_put_boxes_by_volume_lower_z, add_symmetry_breaking_for_identical_boxes,prefer_put_boxes_lower_z, prefer_put_boxes_lower_z_non_linear, get_total_floor_area_covered, prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom, prefer_maximize_surface_contact

    # Symmetry breaking for identical boxes (same size and allowed rotations)
    add_symmetry_breaking_for_identical_boxes(model, boxes, x, y, z, symmetry_mode, container)

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
        preferred_orient_vars = prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom(perms_list, orient, boxes)
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
            placements.append({
                'id': boxes[i].get('id'),
                'position': pos,
                'orientation': orient_idx,
                'size': (l, w, h),
                'rotation_type': boxes[i].get('rotation', 'free')
            })
            print(f'BoxId {boxes[i].get("id")}: pos={pos}, size=({l}, {w}, {h}), orientation={orient_idx}, rotation_type={boxes[i].get("rotation", "free")})')

        if visualize:
            from visualization_utils import visualize_solution
            plt = visualize_solution(elapsed_time, container, boxes, perms_list, placements, n, status_str, container_id)
            plt.show(block=False)
    else:
        print('No solution found.')

    # Always return visualization info as a dict
    vis_data = {
        'elapsed_time': elapsed_time,
        'container': container,
        'boxes': boxes,
        'perms_list': perms_list,
        'placements': placements,
        'n': n,
        'status_str': status_str,
        'container_id': container_id
    }
    return status_str, placements, vis_data





if __name__ == "__main__": 
    input_file = sys.argv[1]
    # Usage: python step2_container_bin_packing_rotation_allowed.py <input_json_file>
    if len(sys.argv) < 2:
        print("Usage: python step2_container_bin_packing_rotation_allowed.py <input_json_file>")
        sys.exit(1)

    container, boxes, symmetry_mode, max_time, anchormode, \
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight, \
        prefer_maximize_surface_contact_weight, \
        prefer_put_boxes_lower_z_weight, \
        prefer_total_floor_area_weight, \
        prefer_put_boxes_lower_z_non_linear_weight,\
        prefer_put_boxes_by_volume_lower_z_weight = load_data_from_json(input_file)
    run_inner(1,container, boxes, symmetry_mode, max_time, anchormode,
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,
        prefer_maximize_surface_contact_weight,
        prefer_put_boxes_lower_z_weight,
        prefer_total_floor_area_weight,
        prefer_put_boxes_lower_z_non_linear_weight,
        prefer_put_boxes_by_volume_lower_z_weight)
    
    input("Press Enter to exit...")  # Keep the window open until user input
    