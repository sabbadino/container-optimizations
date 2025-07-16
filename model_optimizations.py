def prefer_put_boxes_lower_z_non_linear(model, n, z, l_eff, w_eff, container):
    from ortools.sat.python.cp_model import CpModel, IntVar
    from typing import List, Tuple, Any
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
    weighted_terms: List[IntVar] = []
    max_base_area: int = container[0] * container[1]
    max_height: int = container[2]
    for i in range(n):
        base_area: IntVar = model.NewIntVar(0, max_base_area, f'base_area_{i}_ex')
        model.AddMultiplicationEquality(base_area, [l_eff[i], w_eff[i]])

        height_from_bottom: IntVar = model.NewIntVar(0, max_height, f'height_from_bottom_{i}_ex')
        model.Add(height_from_bottom == max_height - z[i])

        height_from_bottom_sq: IntVar = model.NewIntVar(0, max_height * max_height, f'height_from_bottom_sq_{i}_ex')
        model.AddMultiplicationEquality(height_from_bottom_sq, [height_from_bottom, height_from_bottom])

        weighted: IntVar = model.NewIntVar(0, max_base_area * max_height * max_height, f'weighted_{i}_ex')
        model.AddMultiplicationEquality(weighted, [base_area, height_from_bottom_sq])

        weighted_terms.append(weighted)
    return weighted_terms

def prefer_put_boxes_lower_z(model, n, z, l_eff, w_eff, container):
    from ortools.sat.python.cp_model import CpModel, IntVar
    from typing import List, Tuple, Any
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
    weighted_terms: List[IntVar] = []
    for i in range(n):
        base_area: IntVar = model.NewIntVar(0, container[0] * container[1], f'base_area_{i}')
        model.AddMultiplicationEquality(base_area, [l_eff[i], w_eff[i]])

        height_from_bottom: IntVar = model.NewIntVar(0, container[2], f'height_from_bottom_{i}')
        model.Add(height_from_bottom == container[2] - z[i])

        weighted: IntVar = model.NewIntVar(0, container[0] * container[1] * container[2], f'weighted_{i}')
        model.AddMultiplicationEquality(weighted, [base_area, height_from_bottom])

        weighted_terms.append(weighted)
    return weighted_terms

def prefer_maximize_surface_contact(model, n, x, y, z, l_eff, w_eff, h_eff,container):
    from ortools.sat.python.cp_model import CpModel, IntVar, BoolVarT
    from typing import List
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
        container: Tuple/list of container dimensions (length, width, height).

    Returns:
        contact_area_vars: List of IntVar, each representing the total contact area of box i with boxes below.
    """
    contact_area_vars: List[IntVar] = []
    max_area: int = container[0] * container[1]
    for i in range(n):
        contact_with_any: List[IntVar] = []
        for j in range(n):
            if i == j:
                continue
            is_on_j: BoolVarT = model.NewBoolVar(f'is_on_{i}_on_{j}')
            model.Add(z[i] == z[j] + h_eff[j]).OnlyEnforceIf(is_on_j)
            model.Add(x[i] < x[j] + l_eff[j]).OnlyEnforceIf(is_on_j)
            model.Add(x[i] + l_eff[i] > x[j]).OnlyEnforceIf(is_on_j)
            model.Add(y[i] < y[j] + w_eff[j]).OnlyEnforceIf(is_on_j)
            model.Add(y[i] + w_eff[i] > y[j]).OnlyEnforceIf(is_on_j)
            area_ij: IntVar = model.NewIntVar(0, max_area, f'contact_area_{i}_on_{j}')
            tmp_area: IntVar = model.NewIntVar(0, max_area, f'tmp_contact_area_{i}_on_{j}')
            model.AddMultiplicationEquality(tmp_area, [l_eff[i], w_eff[i]])
            model.AddMultiplicationEquality(area_ij, [is_on_j, tmp_area])
            contact_with_any.append(area_ij)
        if contact_with_any:
            contact_area_i: IntVar = model.NewIntVar(0, max_area, f'contact_area_{i}')
            model.Add(contact_area_i == sum(contact_with_any))
            contact_area_vars.append(contact_area_i)
        else:
            contact_area_vars.append(model.NewIntVar(0, 0, f'contact_area_{i}_none'))
    return contact_area_vars
def add_symmetry_breaking_for_identical_boxes(model, boxes, x, y, z, symmetry_mode, container):
    from ortools.sat.python.cp_model import CpModel, IntVar, BoolVarT
    from typing import List, Dict, Any
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
    n: int = len(boxes)
    axis_names: List[str] = ['x', 'y', 'z']
    axis_vars: List[List[IntVar]] = [x, y, z]
    max_axis: int = max(enumerate(container), key=lambda t: t[1])[0]  # 0=x, 1=y, 2=z
    for i in range(n):
        for j in range(i + 1, n):
            if (
                boxes[i]['size'] == boxes[j]['size']
                and boxes[i].get('rotation', 'free') == boxes[j].get('rotation', 'free')
            ):
                if symmetry_mode == 'simple':
                    model.Add(axis_vars[max_axis][i] <= axis_vars[max_axis][j])
                else:
                    b_xless: BoolVar = model.NewBoolVar(f'sb_xless_{i}_{j}')
                    b_xeq: BoolVar = model.NewBoolVar(f'sb_xeq_{i}_{j}')
                    b_yless: BoolVar = model.NewBoolVar(f'sb_yless_{i}_{j}')
                    b_yeq: BoolVar = model.NewBoolVar(f'sb_yeq_{i}_{j}')
                    model.Add(x[i] < x[j]).OnlyEnforceIf(b_xless)
                    model.Add(x[i] >= x[j]).OnlyEnforceIf(b_xless.Not())
                    model.Add(x[i] == x[j]).OnlyEnforceIf(b_xeq)
                    model.Add(x[i] != x[j]).OnlyEnforceIf(b_xeq.Not())
                    model.Add(y[i] < y[j]).OnlyEnforceIf(b_yless)
                    model.Add(y[i] >= y[j]).OnlyEnforceIf(b_yless.Not())
                    model.Add(y[i] == y[j]).OnlyEnforceIf(b_yeq)
                    model.Add(y[i] != y[j]).OnlyEnforceIf(b_yeq.Not())
                    b_xy_eq: BoolVar = model.NewBoolVar(f'sb_xyeq_{i}_{j}')
                    model.AddBoolAnd([b_xeq, b_yeq]).OnlyEnforceIf(b_xy_eq)
                    model.AddBoolOr([b_xeq.Not(), b_yeq.Not()]).OnlyEnforceIf(b_xy_eq.Not())
                    model.Add(z[i] <= z[j]).OnlyEnforceIf(b_xy_eq)
                    b_xeq_and_yless: BoolVar = model.NewBoolVar(f'sb_xeq_yless_{i}_{j}')
                    model.AddBoolAnd([b_xeq, b_yless]).OnlyEnforceIf(b_xeq_and_yless)
                    model.AddBoolOr([b_xeq.Not(), b_yless.Not()]).OnlyEnforceIf(b_xeq_and_yless.Not())
                    model.AddBoolOr([b_xless, b_xeq_and_yless, b_xy_eq])

def get_total_floor_area_covered(model, n, on_floor_vars, l_eff, w_eff, container):
    from ortools.sat.python.cp_model import CpModel, IntVar, BoolVar
    from typing import List
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
    max_area: int = container[0] * container[1]
    area_vars: List[IntVar] = []
    for i in range(n):
        area_i: IntVar = model.NewIntVar(0, max_area, f'area_on_floor_{i}')
        tmp: IntVar = model.NewIntVar(0, max_area, f'tmp_{i}')
        model.AddMultiplicationEquality(tmp, [l_eff[i], w_eff[i]])
        model.AddMultiplicationEquality(area_i, [on_floor_vars[i], tmp])
        area_vars.append(area_i)
    return area_vars


def prefer_side_with_biggest_surface_at_the_bottom(perms_list, orient, boxes):
    from ortools.sat.python.cp_model import BoolVarT
    from typing import List, Tuple, Dict, Any
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
    preferred_orient_vars: List[BoolVarT] = []
    for i, perms in enumerate(perms_list):
        if boxes[i].get('rotation', 'free') != 'free':
            continue
        bottom_areas: List[int] = [l * w for (l, w, h) in perms]
        max_area: int = max(bottom_areas)
        for k, area in enumerate(bottom_areas):
            if area == max_area:
                preferred_orient_vars.append(orient[i][k])
    return preferred_orient_vars
