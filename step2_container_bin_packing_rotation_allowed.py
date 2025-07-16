





import sys
from ortools.sat.python import cp_model
from load_utils import load_data_from_json

# Usage: python step2_container_bin_packing_rotation_allowed.py <input_json_file>
if len(sys.argv) < 2:
    print("Usage: python step2_container_bin_packing_rotation_allowed.py <input_json_file>")
    sys.exit(1)





input_file = sys.argv[1]
container, boxes, symmetry_mode, max_time, anchormode, \
    prefer_side_with_biggest_surface_at_the_bottom_weight, \
    prefer_maximize_surface_contact_weight, \
    prefer_put_boxes_lower_z_weight, \
    prefer_total_floor_area_weight, \
    prefer_put_boxes_lower_z_non_linear_weight = load_data_from_json(input_file)
print(f'symmetry_mode:  {symmetry_mode}')
print(f'anchormode: {anchormode}')
print(f'prefer_side_with_biggest_surface_at_the_bottom_weight: {prefer_side_with_biggest_surface_at_the_bottom_weight}')
print(f'prefer_maximize_surface_contact_weight: {prefer_maximize_surface_contact_weight}')
print(f'prefer_large_base_lower_weight: {prefer_put_boxes_lower_z_weight}')
print(f'prefer_total_floor_area_weight: {prefer_total_floor_area_weight}')
print(f'prefer_large_base_lower_non_linear_weight: {prefer_put_boxes_lower_z_non_linear_weight}')

model = cp_model.CpModel()
from model_setup import setup_3d_bin_packing_model
n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
import time
solver = cp_model.CpSolver()





from model_constraints import add_no_overlap_constraint, apply_anchor_logic
 # Anchor logic based on anchormode
apply_anchor_logic(model, anchormode, boxes, x, y, z)

add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)


from model_constraints import add_inside_container_constraint
add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)




from model_optimizations import add_symmetry_breaking_for_identical_boxes,prefer_put_boxes_lower_z_non_linear, get_total_floor_area_covered, prefer_side_with_biggest_surface_at_the_bottom, prefer_maximize_surface_contact, prefer_put_boxes_lower_z

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
if prefer_side_with_biggest_surface_at_the_bottom_weight:
    preferred_orient_vars = prefer_side_with_biggest_surface_at_the_bottom(perms_list, orient, boxes)
    beta = prefer_side_with_biggest_surface_at_the_bottom_weight
    terms.append(beta * sum(preferred_orient_vars))
if prefer_maximize_surface_contact_weight:
    contact_area_vars = prefer_maximize_surface_contact(model, n, x, y, z, l_eff, w_eff, h_eff,container)
    gamma = prefer_maximize_surface_contact_weight
    terms.append(gamma * sum(contact_area_vars))
if prefer_put_boxes_lower_z_weight:
    weighted_terms = prefer_put_boxes_lower_z(model, n, z, l_eff, w_eff, container)
    delta = prefer_put_boxes_lower_z_weight
    terms.append(delta * sum(weighted_terms))
if prefer_put_boxes_lower_z_non_linear_weight:
    weighted_terms_nl = prefer_put_boxes_lower_z_non_linear(model, n, z, l_eff, w_eff, container)
    delta_nl = prefer_put_boxes_lower_z_non_linear_weight
    terms.append(delta_nl * sum(weighted_terms_nl))
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

print(f'Solver status: {status_dict.get(status, status)}')
print(f'Solver time: {elapsed_time:.3f} seconds')

if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    for i in range(n):
        # Find which orientation is selected
        orient_val = [solver.Value(orient[i][k]) for k in range(len(orient[i]))]
        orient_idx = orient_val.index(1)
        l, w, h = perms_list[i][orient_idx]
        print(f'BoxId {boxes[i].get("id")}: pos=({solver.Value(x[i])}, {solver.Value(y[i])}, {solver.Value(z[i])}), size=({l}, {w}, {h}), orientation={orient_idx}, rotation_type={boxes[i].get("rotation", "free")}')

    from visualization_utils import visualize_solution
    visualize_solution(container, boxes, perms_list, orient, x, y, z, solver, n)
else:
    print('No solution found.')
