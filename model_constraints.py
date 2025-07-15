def add_symmetry_breaking_for_identical_boxes(model, boxes, x, y, z, symmetry_mode, container):
    """
    Adds symmetry breaking constraints for identical boxes (same size and allowed rotations).
    symmetry_mode: 'simple' or 'full'.
    For 'simple', chooses the axis with the largest container dimension.
    """
    n = len(boxes)
    # Determine axis with largest container dimension
    axis_names = ['x', 'y', 'z']
    axis_vars = [x, y, z]
    max_axis = max(enumerate(container), key=lambda t: t[1])[0]  # 0=x, 1=y, 2=z
    for i in range(n):
        for j in range(i + 1, n):
            if (
                boxes[i]['size'] == boxes[j]['size']
                and boxes[i].get('rotation', 'free') == boxes[j].get('rotation', 'free')
            ):
                if symmetry_mode == 'simple':
                    # Use the axis with the largest container dimension
                    model.Add(axis_vars[max_axis][i] <= axis_vars[max_axis][j])
                else:
                    # Full lexicographical ordering
                    b_xless = model.NewBoolVar(f'sb_xless_{i}_{j}')
                    b_xeq = model.NewBoolVar(f'sb_xeq_{i}_{j}')
                    b_yless = model.NewBoolVar(f'sb_yless_{i}_{j}')
                    b_yeq = model.NewBoolVar(f'sb_yeq_{i}_{j}')
                    # x[i] < x[j] <=> b_xless
                    model.Add(x[i] < x[j]).OnlyEnforceIf(b_xless)
                    model.Add(x[i] >= x[j]).OnlyEnforceIf(b_xless.Not())
                    # x[i] == x[j] <=> b_xeq
                    model.Add(x[i] == x[j]).OnlyEnforceIf(b_xeq)
                    model.Add(x[i] != x[j]).OnlyEnforceIf(b_xeq.Not())
                    # y[i] < y[j] <=> b_yless
                    model.Add(y[i] < y[j]).OnlyEnforceIf(b_yless)
                    model.Add(y[i] >= y[j]).OnlyEnforceIf(b_yless.Not())
                    # y[i] == y[j] <=> b_yeq
                    model.Add(y[i] == y[j]).OnlyEnforceIf(b_yeq)
                    model.Add(y[i] != y[j]).OnlyEnforceIf(b_yeq.Not())
                    # b_xy_eq = b_xeq AND b_yeq
                    b_xy_eq = model.NewBoolVar(f'sb_xyeq_{i}_{j}')
                    model.AddBoolAnd([b_xeq, b_yeq]).OnlyEnforceIf(b_xy_eq)
                    model.AddBoolOr([b_xeq.Not(), b_yeq.Not()]).OnlyEnforceIf(b_xy_eq.Not())
                    # z[i] <= z[j] if b_xy_eq
                    model.Add(z[i] <= z[j]).OnlyEnforceIf(b_xy_eq)
                    # Main lex constraint:
                    # (x[i] < x[j]) OR (x[i] == x[j] AND y[i] < y[j]) OR (x[i] == x[j] AND y[i] == y[j] AND z[i] <= z[j])
                    b_xeq_and_yless = model.NewBoolVar(f'sb_xeq_yless_{i}_{j}')
                    model.AddBoolAnd([b_xeq, b_yless]).OnlyEnforceIf(b_xeq_and_yless)
                    model.AddBoolOr([b_xeq.Not(), b_yless.Not()]).OnlyEnforceIf(b_xeq_and_yless.Not())
                    model.AddBoolOr([b_xless, b_xeq_and_yless, b_xy_eq])
def add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff):
    """
    Adds no-overlap constraints for all pairs of boxes in 3D using effective dimensions.
    """
    for i in range(n):
        for j in range(i + 1, n):
            no_overlap = []
            no_overlap.append(model.NewBoolVar(f'i{i}_left_of_j{j}'))
            model.Add(x[i] + l_eff[i] <= x[j]).OnlyEnforceIf(no_overlap[-1])
            no_overlap.append(model.NewBoolVar(f'i{i}_right_of_j{j}'))
            model.Add(x[j] + l_eff[j] <= x[i]).OnlyEnforceIf(no_overlap[-1])
            no_overlap.append(model.NewBoolVar(f'i{i}_front_of_j{j}'))
            model.Add(y[i] + w_eff[i] <= y[j]).OnlyEnforceIf(no_overlap[-1])
            no_overlap.append(model.NewBoolVar(f'i{i}_behind_of_j{j}'))
            model.Add(y[j] + w_eff[j] <= y[i]).OnlyEnforceIf(no_overlap[-1])
            no_overlap.append(model.NewBoolVar(f'i{i}_below_j{j}'))
            model.Add(z[i] + h_eff[i] <= z[j]).OnlyEnforceIf(no_overlap[-1])
            no_overlap.append(model.NewBoolVar(f'i{i}_above_j{j}'))
            model.Add(z[j] + h_eff[j] <= z[i]).OnlyEnforceIf(no_overlap[-1])
            model.AddBoolOr(no_overlap)
def add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container):
    """
    Adds constraints to ensure each box is fully inside the container using effective dimensions.
    """
    for i in range(n):
        model.Add(x[i] + l_eff[i] <= container[0])
        model.Add(y[i] + w_eff[i] <= container[1])
        model.Add(z[i] + h_eff[i] <= container[2])
def add_no_floating_constraint(model, n, x, y, z, l_eff, w_eff, h_eff):
    """
    Adds the 'no floating' constraint: each box is on the floor or on top of another box.
    Returns a list of on_floor_vars for use in the objective.
    """
    on_floor_vars = []
    for i in range(n):
        on_floor = model.NewBoolVar(f'on_floor_{i}')
        on_floor_vars.append(on_floor)
        model.Add(z[i] == 0).OnlyEnforceIf(on_floor)
        on_another = []
        for j in range(n):
            if i == j:
                continue
            above = model.NewBoolVar(f'above_{i}_{j}')
            model.Add(z[i] == z[j] + h_eff[j]).OnlyEnforceIf(above)
            # Must overlap in x and y
            model.Add(x[i] < x[j] + l_eff[j]).OnlyEnforceIf(above)
            model.Add(x[i] + l_eff[i] > x[j]).OnlyEnforceIf(above)
            model.Add(y[i] < y[j] + w_eff[j]).OnlyEnforceIf(above)
            model.Add(y[i] + w_eff[i] > y[j]).OnlyEnforceIf(above)
            on_another.append(above)
        model.AddBoolOr([on_floor] + on_another)
    return on_floor_vars

def get_total_floor_area_covered(model, n, on_floor_vars, l_eff, w_eff, container):
    """
    Returns a list of area variables for each box: on_floor[i] * l_eff[i] * w_eff[i].
    These can be summed for the total covered floor area.
    container: tuple/list with container dimensions (length, width, height)
    """
    max_area = container[0] * container[1]
    area_vars = []
    for i in range(n):
        area_i = model.NewIntVar(0, max_area, f'area_on_floor_{i}')
        tmp = model.NewIntVar(0, max_area, f'tmp_{i}')
        model.AddMultiplicationEquality(tmp, [l_eff[i], w_eff[i]])
        model.AddMultiplicationEquality(area_i, [on_floor_vars[i], tmp])
        area_vars.append(area_i)
    return area_vars


def get_preferred_orientation_vars_for_largest_bottom_face(perms_list, orient, boxes):
    """
    Returns a list of orientation variables where the largest face is on the bottom for each box,
    but only for boxes with free rotation.
    perms_list: list of lists of (l, w, h) tuples for each box's allowed orientations.
    orient: list of lists of BoolVar, orient[i][k] is 1 if box i uses orientation k.
    boxes: list of box dicts (to check rotation type)
    """
    preferred_orient_vars = []
    for i, perms in enumerate(perms_list):
        if boxes[i].get('rotation', 'free') != 'free':
            continue
        bottom_areas = [l * w for (l, w, h) in perms]
        max_area = max(bottom_areas)
        for k, area in enumerate(bottom_areas):
            if area == max_area:
                preferred_orient_vars.append(orient[i][k])
    return preferred_orient_vars
