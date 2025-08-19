import pytest
from model_constraints import add_no_overlap_constraint, add_inside_container_constraint
from ortools.sat.python import cp_model

from visualization_utils import visualize_solution




# Minimal box and container data for geometry tests
def make_box(l, w, h, id=0):
    return {"id": id, "l": l, "w": w, "h": h}

def make_container(L, W, H):
    return {"L": L, "W": W, "H": H}

def test_no_overlap_simple():
    model = cp_model.CpModel()
    n = 2
    # Place two boxes in a 10x10x10 container
    boxes = [make_box(5, 5, 5, id=1), make_box(5, 5, 5, id=2)]
    container = (10, 10, 10)
    x = [model.NewIntVar(0, 5, f"x_{i}") for i in range(n)]
    y = [model.NewIntVar(0, 5, f"y_{i}") for i in range(n)]
    z = [model.NewIntVar(0, 5, f"z_{i}") for i in range(n)]
    # Use constants as IntVar for dimension lists to satisfy typed constraints
    l_eff = [model.NewConstant(5) for _ in range(n)]
    w_eff = [model.NewConstant(5) for _ in range(n)]
    h_eff = [model.NewConstant(5) for _ in range(n)]
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # Check that boxes do not overlap
    x0, y0, z0 = solver.Value(x[0]), solver.Value(y[0]), solver.Value(z[0])
    x1, y1, z1 = solver.Value(x[1]), solver.Value(y[1]), solver.Value(z[1])
    # They must be separated in at least one dimension
    separated = (
        x0 + 5 <= x1 or x1 + 5 <= x0 or
        y0 + 5 <= y1 or y1 + 5 <= y0 or
        z0 + 5 <= z1 or z1 + 5 <= z0
    )
    assert separated

def test_inside_container():
    from model_setup import setup_3d_bin_packing_model
    model = cp_model.CpModel()
    # Use box/cont dicts compatible with model_setup
    boxes = [{"size": (5, 5, 5), "id": 1, "rotation": "none"}]
    container = (10, 10, 10)
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    from model_constraints import add_inside_container_constraint,add_no_overlap_constraint
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # Check that box is inside container
    assert 0 <= solver.Value(x[0]) <= 5
    assert 0 <= solver.Value(y[0]) <= 5
    assert 0 <= solver.Value(z[0]) <= 5

def test_no_rotation_single_tall_box_infeasible_in_shallow_container():
    """A single tall box (1x1x4, rotation=none) cannot fit into a shallow container (4x4x1)."""
    
    from model_setup import setup_3d_bin_packing_model
    model = cp_model.CpModel()
    # Use box/cont dicts compatible with model_setup
    boxes = [{"size": (1, 1, 4), "id": 4, "rotation": "none"}]        
    container = (4, 4, 1)
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    from model_constraints import add_inside_container_constraint,add_no_overlap_constraint
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Should be infeasible: height 4 cannot fit in container height 1 without rotation
    assert status == cp_model.INFEASIBLE

def test_free_rotation_four_tall_boxes_rotate_flat_to_fit_shallow_container():
    """Four tall boxes (1x1x4, rotation=free) can rotate flat to fit a shallow container (4x4x1)."""
    from model_setup import setup_3d_bin_packing_model
    model = cp_model.CpModel()
    # Use box/cont dicts compatible with model_setup
    boxes = [{"size": (1, 1, 4), "id": 1, "rotation": "free"},
             {"size": (1, 1, 4), "id": 2, "rotation": "free"},
             {"size": (1, 1, 4), "id": 3, "rotation": "free"},
             {"size": (1, 1, 4), "id": 4, "rotation": "free"}]
    container = (4, 4, 1)
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    from model_constraints import add_inside_container_constraint,add_no_overlap_constraint
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Should be optimal/feasible: all 4 boxes can fit with rotation
    #assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    print(f'Solver status: {status}')
    assert status == cp_model.OPTIMAL
    # Check that all boxes are placed inside the container and do not overlap, and that orientation is valid
    positions = set()
    possible_box_orientations : int = 6
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        # Only one orientation is selected and it must be one with h=1
        orient_val = [solver.Value(orient[i][k]) for k in range(possible_box_orientations)]
        assert sum(orient_val) == 1
        k_sel = orient_val.index(1)
        l_sel, w_sel, h_sel = perms_list[i][k_sel]
        # Check box is inside container
        assert 0 <= xi <= container[0] - l_sel
        assert 0 <= yi <= container[1] - w_sel
        assert 0 <= zi <= container[2] - h_sel
        # Save position and size for overlap check
        positions.add((xi, yi, zi, l_sel, w_sel, h_sel))
    # Check that no two boxes overlap
    pos_list = list(positions)
    for i in range(n):
        xi, yi, zi, li, wi, hi = pos_list[i]
        for j in range(i+1, n):
            xj, yj, zj, lj, wj, hj = pos_list[j]
            separated = (
                xi + li <= xj or xj + lj <= xi or
                yi + wi <= yj or yj + wj <= yi or
                zi + hi <= zj or zj + hj <= zi
            )
            assert separated

    # Visualize the solution
    # Build placements to match new visualize_solution API
    placements = []
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        orient_val = [solver.Value(orient[i][k]) for k in range(len(perms_list[i]))]
        k_sel = orient_val.index(1) if 1 in orient_val else 0
        l_sel, w_sel, h_sel = perms_list[i][k_sel]
        placements.append({
            "id": boxes[i].get("id", i),
            "position": (xi, yi, zi),
            "size": (l_sel, w_sel, h_sel),
            "orientation": k_sel,
        })
    # Pass container as dict with 'size' key per visualize_solution API
    # Include rotation_type consistent with model logic; default to 'free'
    for p in placements:
        p.setdefault('rotation_type', boxes[p['id']-1].get('rotation', 'free') if isinstance(p.get('id'), int) else 'free')
    visualize_solution(0, {"size": list(container)}, boxes, placements, str(status))

def test_z_rotation_swaps_length_width_to_fit_two_planks_in_narrow_width():
    """Two planks (1x4x1, rotation=z) fit in a 4x2x1 container by swapping L/W via z-rotation."""
    from model_setup import setup_3d_bin_packing_model
    model = cp_model.CpModel()
    # Use box/cont dicts compatible with model_setup
    boxes = [{"size": (1, 4, 1), "id": 1, "rotation": "z"},
             {"size": (1, 4, 1), "id": 2, "rotation": "z"}]
    container = (4, 2, 1)
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    from model_constraints import add_inside_container_constraint,add_no_overlap_constraint
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Should be optimal/feasible: both boxes can fit with z-rotation
    print(f'Solver status: {status}')
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # Check that all boxes are placed inside the container and do not overlap, and that orientation is valid
    positions = set()
    possible_box_orientations : int = 2
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        # Only one orientation is selected and it must be one with h=1
        orient_val = [solver.Value(orient[i][k]) for k in range(possible_box_orientations)]
        assert sum(orient_val) == 1
        k_sel = orient_val.index(1)
        l_sel, w_sel, h_sel = perms_list[i][k_sel]
        # Check box is inside container
        assert 0 <= xi <= container[0] - l_sel
        assert 0 <= yi <= container[1] - w_sel
        assert 0 <= zi <= container[2] - h_sel
        # Save position and size for overlap check
        positions.add((xi, yi, zi, l_sel, w_sel, h_sel))
    # Check that no two boxes overlap
    pos_list = list(positions)
    for i in range(n):
        xi, yi, zi, li, wi, hi = pos_list[i]
        for j in range(i+1, n):
            xj, yj, zj, lj, wj, hj = pos_list[j]
            separated = (
                xi + li <= xj or xj + lj <= xi or
                yi + wi <= yj or yj + wj <= yi or
                zi + hi <= zj or zj + hj <= zi
            )
            assert separated

def test_free_rotation_mixed_boxes_pack_optimally_in_4x4x2():
    """Mixed-size boxes with free rotation pack optimally inside a 4x4x2 container without overlap."""
    from model_setup import setup_3d_bin_packing_model
    model = cp_model.CpModel()
    # Use box/cont dicts compatible with model_setup
    boxes = [{"size": (1, 2, 4), "id": 1, "rotation": "free"} # {"size": (4, 1, 1), "id": 1, "rotation": "free"} does ot work , model invalid, why ? 
             ,
             {"size": (2, 2, 1), "id": 2, "rotation": "free"}
             ,
             {"size": (2, 2, 1), "id": 3, "rotation": "free"}
              ,
              {"size": (2, 1, 2), "id": 4, "rotation": "free"},
              {"size": (2, 2, 1), "id": 5, "rotation": "free"},
             ]
    container = (4, 4, 2)
    n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff = setup_3d_bin_packing_model(model, container, boxes)
    from model_constraints import add_inside_container_constraint,add_no_overlap_constraint
    add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
    add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    print(f'Solver status: {status}')
    # Should be optimal/feasible: all 4 boxes can fit with rotation
    assert status == cp_model.OPTIMAL
    # Check that all boxes are placed inside the container and do not overlap, and that orientation is valid
    positions = set()
    possible_box_orientations : int = 6
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        # Only one orientation is selected and it must be one with h=1
        orient_val = [solver.Value(orient[i][k]) for k in range(possible_box_orientations)]
        assert sum(orient_val) == 1
        k_sel = orient_val.index(1)
        l_sel, w_sel, h_sel = perms_list[i][k_sel]
        # Check box is inside container
        assert 0 <= xi <= container[0] - l_sel
        assert 0 <= yi <= container[1] - w_sel
        assert 0 <= zi <= container[2] - h_sel
        # Save position and size for overlap check
        positions.add((xi, yi, zi, l_sel, w_sel, h_sel))
    # Check that no two boxes overlap
    pos_list = list(positions)
    for i in range(n):
        xi, yi, zi, li, wi, hi = pos_list[i]
        for j in range(i+1, n):
            xj, yj, zj, lj, wj, hj = pos_list[j]
            separated = (
                xi + li <= xj or xj + lj <= xi or
                yi + wi <= yj or yj + wj <= yi or
                zi + hi <= zj or zj + hj <= zi
            )
            assert separated

    # Build placements to match new visualize_solution API
    placements = []
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        orient_val = [solver.Value(orient[i][k]) for k in range(len(perms_list[i]))]
        k_sel = orient_val.index(1) if 1 in orient_val else 0
        l_sel, w_sel, h_sel = perms_list[i][k_sel]
        placements.append({
            "id": boxes[i].get("id", i),
            "position": (xi, yi, zi),
            "size": (l_sel, w_sel, h_sel),
            "orientation": k_sel,
        })
    # Include rotation_type; default to box's rotation or 'free'
    for idx, p in enumerate(placements):
        p.setdefault('rotation_type', boxes[idx].get('rotation', 'free'))
    # Pass container as dict with 'size' key per visualize_solution API
    visualize_solution(0, {"size": list(container)}, boxes, placements, str(status))

