
from ortools.sat.python import cp_model
import sys
from typing import List, Tuple, Dict, Any

# --- Factored out: position variables setup ---
def create_position_variables(
    model: cp_model.CpModel,
    container: Tuple[int, int, int],
    boxes: List[Dict[str, Any]]
) -> Tuple[List[cp_model.IntVar], List[cp_model.IntVar], List[cp_model.IntVar]]:
    """
    Create position variables (x, y, z) for n boxes in a container.
    Args:
        model: OR-Tools CpModel instance
        container: (L, W, H) tuple for container size
        boxes: list of box dicts
    Returns:
        x, y, z: lists of IntVar for each box's lower-left-bottom corner
    """
    n: int = len(boxes)
    x: List[cp_model.IntVar] = [model.NewIntVar(0, container[0], f'x_{i}') for i in range(n)]
    y: List[cp_model.IntVar] = [model.NewIntVar(0, container[1], f'y_{i}') for i in range(n)]
    z: List[cp_model.IntVar] = [model.NewIntVar(0, container[2], f'z_{i}') for i in range(n)]
    return x, y, z

def setup_3d_bin_packing_model(
    model: cp_model.CpModel,
    container: Tuple[int, int, int],
    boxes: List[Dict[str, Any]]
) -> Tuple[int, List[cp_model.IntVar], List[cp_model.IntVar], List[cp_model.IntVar], List[List[Tuple[int, int, int]]], List[List[cp_model.BoolVarT]], List[cp_model.IntVar], List[cp_model.IntVar], List[cp_model.IntVar]]:
    """
    Sets up the 3D bin packing model with rotation and anchoring logic.
    Returns:
        n: number of boxes
        x, y, z: position variables
        perms_list: list of allowed orientations for each box
        orient: orientation variables
        l_eff, w_eff, h_eff: effective dimension variables
    """
    x: List[cp_model.IntVar]
    y: List[cp_model.IntVar]
    z: List[cp_model.IntVar]
    x, y, z = create_position_variables(model, container, boxes)
    n: int = len(boxes)
    perms_list: List[List[Tuple[int, int, int]]]
    orient: List[List[cp_model.BoolVarT]]
    l_eff: List[cp_model.IntVar]
    w_eff: List[cp_model.IntVar]
    h_eff: List[cp_model.IntVar]
    perms_list, orient, l_eff, w_eff, h_eff = create_orientation_and_dimension_variables(model, container, boxes)
    return n, x, y, z, perms_list, orient, l_eff, w_eff, h_eff

# --- Factored out: orientation and effective dimension logic ---
def create_orientation_and_dimension_variables(
    model: cp_model.CpModel,
    container: Tuple[int, int, int],
    boxes: List[Dict[str, Any]]
) -> Tuple[List[List[Tuple[int, int, int]]], List[List[cp_model.BoolVarT]], List[cp_model.IntVar], List[cp_model.IntVar], List[cp_model.IntVar]]:
    """
    For each box, determine allowed orientations, create orientation variables, and link to effective dimensions.
    Args:
        model: OR-Tools CpModel instance
        container: (L, W, H) tuple for container size
        boxes: list of box dicts
    Returns:
        perms_list: list of allowed orientations for each box
        orient: list of lists of BoolVar for each box's orientation
        l_eff, w_eff, h_eff: lists of IntVar for effective dimensions
    """
    n: int = len(boxes)
    perms_list: List[List[Tuple[int, int, int]]] = []
    orient: List[List[cp_model.BoolVarT]] = []
    for i, box in enumerate(boxes):
        l0: int
        w0: int
        h0: int
        l0, w0, h0 = box['size']
        rot: str = box.get('rotation', 'free')
        perms: List[Tuple[int, int, int]]
        if rot == 'free':
            perms = [
                (l0, w0, h0), (l0, h0, w0), (w0, l0, h0),
                (w0, h0, l0), (h0, l0, w0), (h0, w0, l0)
            ]
        elif rot == 'z':
            perms = [
                (l0, w0, h0), (w0, l0, h0)
            ]
        else:  # 'none' or unspecified
            perms = [(l0, w0, h0)]
        perms_list.append(perms)
        orient.append([model.NewBoolVar(f'orient_{i}_{k}') for k in range(len(perms))])
        model.Add(sum(orient[-1]) == 1)

    l_eff: List[cp_model.IntVar] = [model.NewIntVar(0, container[0], f'l_eff_{i}') for i in range(n)]
    w_eff: List[cp_model.IntVar] = [model.NewIntVar(0, container[1], f'w_eff_{i}') for i in range(n)]
    h_eff: List[cp_model.IntVar] = [model.NewIntVar(0, container[2], f'h_eff_{i}') for i in range(n)]

    for i in range(n):
        for k, (l, w, h) in enumerate(perms_list[i]):
            l: int
            w: int
            h: int
            model.Add(l_eff[i] == l).OnlyEnforceIf(orient[i][k])
            model.Add(w_eff[i] == w).OnlyEnforceIf(orient[i][k])
            model.Add(h_eff[i] == h).OnlyEnforceIf(orient[i][k])

    return perms_list, orient, l_eff, w_eff, h_eff


