
import sys
from ortools.sat.python import cp_model
from typing import List, Tuple, Any, Optional


def add_no_overlap_constraint(
    model: cp_model.CpModel,
    n: int,
    x: List[cp_model.IntVar],
    y: List[cp_model.IntVar],
    z: List[cp_model.IntVar],
    l_eff: List[cp_model.IntVar],
    w_eff: List[cp_model.IntVar],
    h_eff: List[cp_model.IntVar]
) -> None:
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
            no_overlap: List[cp_model.BoolVarT] = []
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
def add_inside_container_constraint(
    model: cp_model.CpModel,
    n: int,
    x: List[cp_model.IntVar],
    y: List[cp_model.IntVar],
    z: List[cp_model.IntVar],
    l_eff: List[cp_model.IntVar],
    w_eff: List[cp_model.IntVar],
    h_eff: List[cp_model.IntVar],
    container: Tuple[int, int, int]
) -> None:
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
def add_no_floating_constraint(
    model: cp_model.CpModel,
    n: int,
    x: List[cp_model.IntVar],
    y: List[cp_model.IntVar],
    z: List[cp_model.IntVar],
    l_eff: List[cp_model.IntVar],
    w_eff: List[cp_model.IntVar],
    h_eff: List[cp_model.IntVar]
) -> List[cp_model.BoolVarT]:
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
    on_floor_vars: List[cp_model.BoolVarT] = []
    for i in range(n):
        on_floor: cp_model.BoolVarT = model.NewBoolVar(f'on_floor_{i}')
        on_floor_vars.append(on_floor)
        model.Add(z[i] == 0).OnlyEnforceIf(on_floor)
        on_another: List[cp_model.BoolVarT] = []
        for j in range(n):
            if i == j:
                continue
            above: cp_model.BoolVarT = model.NewBoolVar(f'above_{i}_{j}')
            model.Add(z[i] == z[j] + h_eff[j]).OnlyEnforceIf(above)
            # Must overlap in x and y
            model.Add(x[i] < x[j] + l_eff[j]).OnlyEnforceIf(above)
            model.Add(x[i] + l_eff[i] > x[j]).OnlyEnforceIf(above)
            model.Add(y[i] < y[j] + w_eff[j]).OnlyEnforceIf(above)
            model.Add(y[i] + w_eff[i] > y[j]).OnlyEnforceIf(above)
            on_another.append(above)
        model.AddBoolOr([on_floor] + on_another)
    return on_floor_vars

def apply_anchor_logic(
    model: cp_model.CpModel,
    anchormode: Optional[str],
    boxes: List[Any],
    x: List[cp_model.IntVar],
    y: List[cp_model.IntVar],
    z: List[cp_model.IntVar]
) -> None:
    """
    Apply anchoring constraints to the model based on anchormode.
    Args:
        model: OR-Tools CpModel instance
        anchormode: anchoring strategy (str or None)
        boxes: list of box dicts
        x, y, z: position variables for each box
    """
    n: int = len(boxes)
    if anchormode is not None:
        if anchormode == 'larger':
            largest_idx: int = max(range(n), key=lambda i: boxes[i]['size'][0] * boxes[i]['size'][1] * boxes[i]['size'][2])
            print(f"Anchoring box {largest_idx} with size {boxes[largest_idx]['size']}")
            model.Add(x[largest_idx] == 0)
            model.Add(y[largest_idx] == 0)
            model.Add(z[largest_idx] == 0)
        elif anchormode == 'heavierWithinMostRecurringSimilar':
            from collections import Counter
            size_tuples: List[Tuple[int, int, int]] = [tuple(box['size']) for box in boxes]
            freq: Any = Counter(size_tuples)
            most_common_size, _ = freq.most_common(1)[0]
            indices: List[int] = [i for i, box in enumerate(boxes) if tuple(box['size']) == most_common_size]
            heaviest_idx: int = max(indices, key=lambda i: boxes[i].get('weight', 0))
            print(f"Anchoring box {heaviest_idx} with size {boxes[heaviest_idx]['size']} and weight {boxes[heaviest_idx].get('weight', 0)}")
            model.Add(x[heaviest_idx] == 0)
            model.Add(y[heaviest_idx] == 0)
            model.Add(z[heaviest_idx] == 0)
        else:
            raise ValueError(f"Error: Unknown anchormode '{anchormode}'. Supported: 'larger', 'heavierWithinMostRecurringSimilar'. Exiting.")
