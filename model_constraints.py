def get_weighted_sum_base_area_times_height_from_bottom_ex(model, n, z, l_eff, w_eff, container):
    """
    Returns a list of terms, one for each box, representing (base area) * (height from bottom)^2,
    where base area is the area of the lower face of the box in its current orientation, and
    height from bottom is the distance from the bottom of the container to the lower face of the box.

    This is a non-linear (quadratic) version: it strongly rewards placing large-base boxes lower in the container.
    For boxes with free rotation, the base area is determined by the chosen orientation (l_eff[i], w_eff[i]).

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        z: List of IntVar, z[i] is the z-coordinate of the lower face of box i.
        l_eff, w_eff: Lists of IntVar, effective length and width of box i (depends on orientation).
        container: Tuple/list of container dimensions (length, width, height).

    Returns:
        weighted_terms: List of IntVar, each representing (l_eff[i] * w_eff[i]) * (container[2] - z[i]) ** 2
    """
    weighted_terms = []
    max_base_area = container[0] * container[1]
    max_height = container[2]
    for i in range(n):
        # Compute the base area of the box in its current orientation
        base_area = model.NewIntVar(0, max_base_area, f'base_area_{i}_ex')
        model.AddMultiplicationEquality(base_area, [l_eff[i], w_eff[i]])

        # Compute the height from the bottom of the container to the lower face of the box
        height_from_bottom = model.NewIntVar(0, max_height, f'height_from_bottom_{i}_ex')
        model.Add(height_from_bottom == max_height - z[i])

        # Quadratic term: (height_from_bottom)^2
        height_from_bottom_sq = model.NewIntVar(0, max_height * max_height, f'height_from_bottom_sq_{i}_ex')
        model.AddMultiplicationEquality(height_from_bottom_sq, [height_from_bottom, height_from_bottom])

        # The weighted term is base_area * (height_from_bottom)^2
        weighted = model.NewIntVar(0, max_base_area * max_height * max_height, f'weighted_{i}_ex')
        model.AddMultiplicationEquality(weighted, [base_area, height_from_bottom_sq])

        # Add to the list of terms
        weighted_terms.append(weighted)
    return weighted_terms

def get_weighted_sum_base_area_times_height_from_bottom(model, n, z, l_eff, w_eff, container):
    """
    Returns a list of terms, one for each box, representing (base area) * (height from bottom),
    where base area is the area of the lower face of the box in its current orientation, and
    height from bottom is the distance from the bottom of the container to the lower face of the box.

    This is used as a soft constraint to encourage boxes with larger lower surfaces to be placed lower
    in the container, improving stability. For boxes with free rotation, the base area is determined
    by the chosen orientation (l_eff[i], w_eff[i]).

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        z: List of IntVar, z[i] is the z-coordinate of the lower face of box i.
        l_eff, w_eff: Lists of IntVar, effective length and width of box i (depends on orientation).
        container: Tuple/list of container dimensions (length, width, height).

    Returns:
        weighted_terms: List of IntVar, each representing (l_eff[i] * w_eff[i]) * (container[2] - z[i])
    """
    weighted_terms = []
    for i in range(n):
        # Compute the base area of the box in its current orientation
        base_area = model.NewIntVar(0, container[0] * container[1], f'base_area_{i}')
        model.AddMultiplicationEquality(base_area, [l_eff[i], w_eff[i]])

        # Compute the height from the bottom of the container to the lower face of the box
        height_from_bottom = model.NewIntVar(0, container[2], f'height_from_bottom_{i}')
        model.Add(height_from_bottom == container[2] - z[i])

        # The weighted term is base_area * height_from_bottom
        weighted = model.NewIntVar(0, container[0] * container[1] * container[2], f'weighted_{i}')
        model.AddMultiplicationEquality(weighted, [base_area, height_from_bottom])

        # Add to the list of terms
        weighted_terms.append(weighted)
    return weighted_terms

def get_total_contact_area_on_bottom_surface(model, n, x, y, z, l_eff, w_eff, h_eff):
    """
    Returns a list of contact area variables for each box (except those on the floor):
    the area of the lower x-y surface in contact with the box below (if any).
    The area is l_eff[i] * w_eff[i] if the box is exactly on top of another and overlaps in x/y, else 0.

    This function is used as a soft constraint to encourage boxes to maximize their contact area with boxes below,
    improving stability. For each box i, it sums the contact area with all possible supporting boxes j (j != i),
    where box i is directly on top of box j (z[i] == z[j] + h_eff[j]) and their projections in x and y overlap.
    The contact area is only counted if these conditions are met.

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        x, y, z: Lists of IntVar, coordinates of the lower corner of each box.
        l_eff, w_eff, h_eff: Lists of IntVar, effective dimensions of each box (depends on orientation).

    Returns:
        contact_area_vars: List of IntVar, each representing the total contact area of box i with boxes below.
    """
    contact_area_vars = []
    for i in range(n):
        # For each box, sum contact with all possible boxes below
        contact_with_any = []
        for j in range(n):
            if i == j:
                continue
            # Create a bool var: is_on_j
            is_on_j = model.NewBoolVar(f'is_on_{i}_on_{j}')
            # z[i] == z[j] + h_eff[j]
            model.Add(z[i] == z[j] + h_eff[j]).OnlyEnforceIf(is_on_j)
            # Overlap in x
            model.Add(x[i] < x[j] + l_eff[j]).OnlyEnforceIf(is_on_j)
            model.Add(x[i] + l_eff[i] > x[j]).OnlyEnforceIf(is_on_j)
            # Overlap in y
            model.Add(y[i] < y[j] + w_eff[j]).OnlyEnforceIf(is_on_j)
            model.Add(y[i] + w_eff[i] > y[j]).OnlyEnforceIf(is_on_j)
            # Area = l_eff[i] * w_eff[i] if is_on_j else 0
            max_area = model.Proto().domain[1] if hasattr(model.Proto(), 'domain') else 1000000000
            area_ij = model.NewIntVar(0, max_area, f'contact_area_{i}_on_{j}')
            tmp_area = model.NewIntVar(0, max_area, f'tmp_contact_area_{i}_on_{j}')
            model.AddMultiplicationEquality(tmp_area, [l_eff[i], w_eff[i]])
            model.AddMultiplicationEquality(area_ij, [is_on_j, tmp_area])
            contact_with_any.append(area_ij)
        # Sum contact area with all boxes directly below (can be more than one)
        if contact_with_any:
            contact_area_i = model.NewIntVar(0, max_area, f'contact_area_{i}')
            model.Add(contact_area_i == sum(contact_with_any))
            contact_area_vars.append(contact_area_i)
        else:
            # No possible box below
            contact_area_vars.append(model.NewIntVar(0, 0, f'contact_area_{i}_none'))
    return contact_area_vars
def add_symmetry_breaking_for_identical_boxes(model, boxes, x, y, z, symmetry_mode, container):
    """
    Adds symmetry breaking constraints for identical boxes (same size and allowed rotations).

    This function helps reduce the search space by enforcing an ordering among identical boxes, so that
    equivalent solutions are not explored multiple times. Two modes are supported:
    - 'simple': Orders boxes along the axis with the largest container dimension.
    - 'full': Enforces full lexicographical ordering on (x, y, z) coordinates.

    Args:
        model: The CpModel instance.
        boxes: List of box dicts, each with 'size' and 'rotation' keys.
        x, y, z: Lists of IntVar, coordinates of the lower corner of each box.
        symmetry_mode: 'simple' or 'full'.
        container: Tuple/list of container dimensions (length, width, height).
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

    For each pair of boxes (i, j), ensures that they do not overlap in any of the three axes.
    This is done by enforcing that at least one of the following holds:
    - i is to the left of j
    - i is to the right of j
    - i is in front of j
    - i is behind j
    - i is below j
    - i is above j
    The effective dimensions (l_eff, w_eff, h_eff) account for box orientation.

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        x, y, z: Lists of IntVar, coordinates of the lower corner of each box.
        l_eff, w_eff, h_eff: Lists of IntVar, effective dimensions of each box (depends on orientation).
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

    For each box, ensures that its upper corner does not exceed the container boundaries in any axis.
    The effective dimensions (l_eff, w_eff, h_eff) account for box orientation.

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        x, y, z: Lists of IntVar, coordinates of the lower corner of each box.
        l_eff, w_eff, h_eff: Lists of IntVar, effective dimensions of each box (depends on orientation).
        container: Tuple/list of container dimensions (length, width, height).
    """
    for i in range(n):
        model.Add(x[i] + l_eff[i] <= container[0])
        model.Add(y[i] + w_eff[i] <= container[1])
        model.Add(z[i] + h_eff[i] <= container[2])
def add_no_floating_constraint(model, n, x, y, z, l_eff, w_eff, h_eff):
    """
    Adds the 'no floating' constraint: each box is on the floor or on top of another box.

    For each box, enforces that it is either:
    - On the floor (z[i] == 0), or
    - Directly on top of another box (z[i] == z[j] + h_eff[j]) and overlapping in x and y.
    Returns a list of Boolean variables indicating whether each box is on the floor.

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        x, y, z: Lists of IntVar, coordinates of the lower corner of each box.
        l_eff, w_eff, h_eff: Lists of IntVar, effective dimensions of each box (depends on orientation).

    Returns:
        on_floor_vars: List of BoolVar, each is 1 if box i is on the floor, 0 otherwise.
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

    For each box, computes the area of its lower face if it is on the floor (on_floor[i] == 1),
    otherwise 0. These can be summed for the total covered floor area.

    Args:
        model: The CpModel instance.
        n: Number of boxes.
        on_floor_vars: List of BoolVar, 1 if box i is on the floor, 0 otherwise.
        l_eff, w_eff: Lists of IntVar, effective length and width of each box (depends on orientation).
        container: Tuple/list of container dimensions (length, width, height).

    Returns:
        area_vars: List of IntVar, each representing the area of box i on the floor (0 if not on floor).
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

    For each box with free rotation, identifies the orientation(s) where the bottom face (l, w)
    has the largest possible area. Returns the corresponding orientation variables, which can be
    used in a soft constraint to encourage these orientations.

    Args:
        perms_list: List of lists of (l, w, h) tuples for each box's allowed orientations.
        orient: List of lists of BoolVar, orient[i][k] is 1 if box i uses orientation k.
        boxes: List of box dicts (to check rotation type).

    Returns:
        preferred_orient_vars: List of BoolVar, one for each preferred orientation (largest face down).
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
