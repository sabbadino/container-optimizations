"""
Shared CP-SAT assignment model for container loading (step 1 and ALNS repair)
"""
from typing import Any, Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

def build_step1_model(
    items: List[Dict[str, Any]],
    container_size: List[int],
    container_weight: float,
    max_containers: int,
    group_to_items: Optional[Dict[Any, List[int]]] = None,
    fixed_assignments: Optional[Dict[int, int]] = None,
    group_penalty_lambda: float = 1.0,
    volume_balance_lambda: float = 0.1,
    dump_inputs: bool = False,
):
    """
    items: list of item dicts (must have 'id', 'size', 'weight', optional 'group_id')
    container_size: [L, W, H]
    container_weight: max weight per container
    max_containers: int, upper bound on containers
    group_to_items: dict mapping group_id to list of item indices (optional)
    fixed_assignments: dict {item_id: container_idx} for items to fix (optional)
    group_penalty_lambda: penalty weight for group splits
    volume_balance_lambda: penalty weight for volume imbalance between containers
    Returns: model, x, y, group_in_containers, group_ids
    """
    if dump_inputs:
        print('****************')
        print('INPUTS')
        print(f'Container volume capacity: {container_size[0] * container_size[1] * container_size[2]}')
        print(f'Container weight capacity: {container_weight}')
        print(f'number of items: {len(items)} total weight: {sum(item["weight"] for item in items)} total volume: {sum(item["size"][0] * item["size"][1] * item["size"][2] for item in items)}')
        print('Item details:')
        for i, item in enumerate(items):
            volume = item['size'][0] * item['size'][1] * item['size'][2]
            rotation = item.get('rotation', None)
            group_id = item.get('group_id', None)
            print(f'Counter {i} Item id {item["id"]}: weight={item["weight"]}, volume={volume}, rotation={rotation}, group_id={group_id}')
        print('****************')
    
    model: cp_model.CpModel = cp_model.CpModel()
    
    num_items: int = len(items)
    container_capacity_volume: int = container_size[0] * container_size[1] * container_size[2]
    
    # Variables
    x: Dict[Tuple[int, int], cp_model.IntVar] = {}  # BoolVar; x[i, j] = 1 if item i in container j
    for i in range(num_items):
        for j in range(max_containers):
            x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
    y: List[cp_model.IntVar] = [model.NewBoolVar(f'y_{j}') for j in range(max_containers)]
    # Constraints
    for i in range(num_items):
        if fixed_assignments and items[i]['id'] in fixed_assignments:
            # Fix item to container
            fixed_j = fixed_assignments[items[i]['id']]
            for j in range(max_containers):
                if j == fixed_j:
                    model.Add(x[i, j] == 1)
                else:
                    model.Add(x[i, j] == 0)
        else:
            model.Add(sum(x[i, j] for j in range(max_containers)) == 1)
    for j in range(max_containers):
        model.Add(sum(items[i]['size'][0]*items[i]['size'][1]*items[i]['size'][2] * x[i, j] for i in range(num_items)) <= container_size[0]*container_size[1]*container_size[2] * y[j])
        model.Add(sum(items[i]['weight'] * x[i, j] for i in range(num_items)) <= container_weight * y[j])
    for j in range(max_containers):
        for i in range(num_items):
            model.Add(x[i, j] <= y[j])
    # Soft grouping
    group_in_j: Dict[Tuple[Any, int], cp_model.IntVar] = {}  # kept for readability
    group_in_containers: Dict[Any, cp_model.IntVar] = {}
    group_ids: List[Any] = list(group_to_items.keys()) if group_to_items else []
    if group_ids:
        assert group_to_items is not None
        for g in group_ids:
            for j in range(max_containers):
                group_in_j[g, j] = model.NewBoolVar(f'group_{g}_in_{j}')
                item_vars = [x[i, j] for i in group_to_items[g]]
                model.AddMaxEquality(group_in_j[g, j], item_vars)
            group_in_containers[g] = model.NewIntVar(1, max_containers, f'group_{g}_num_containers')
            model.Add(group_in_containers[g] == sum(group_in_j[g, j] for j in range(max_containers)))
    
    # Volume balance variables and constraints (Pairwise approach)
    container_volume_used: Dict[int, cp_model.IntVar] = {}
    for j in range(max_containers):
        container_volume_used[j] = model.NewIntVar(0, container_capacity_volume, f'vol_used_{j}')
        model.Add(container_volume_used[j] == sum(
            items[i]['size'][0] * items[i]['size'][1] * items[i]['size'][2] * x[i, j] 
            for i in range(num_items)
        ))
    
    # Pairwise volume balance penalties
    pairwise_penalties: List[cp_model.IntVar] = []
    for j1 in range(max_containers):
        for j2 in range(j1 + 1, max_containers):
            diff_var = model.NewIntVar(0, container_capacity_volume, f'diff_{j1}_{j2}')
            both_used = model.NewBoolVar(f'both_used_{j1}_{j2}')
            
            # both_used is true only if both containers are used
            model.AddBoolAnd([y[j1], y[j2]]).OnlyEnforceIf(both_used)
            model.AddBoolOr([y[j1].Not(), y[j2].Not()]).OnlyEnforceIf(both_used.Not())
            
            # Calculate absolute difference only if both containers are used
            model.Add(diff_var >= container_volume_used[j1] - container_volume_used[j2]).OnlyEnforceIf(both_used)
            model.Add(diff_var >= container_volume_used[j2] - container_volume_used[j1]).OnlyEnforceIf(both_used)
            model.Add(diff_var == 0).OnlyEnforceIf(both_used.Not())
            
            pairwise_penalties.append(diff_var)
    
    # Objective
    # Objective
    group_split_penalty = sum(group_in_containers[g] - 1 for g in group_ids) if group_ids else 0
    volume_balance_penalty = sum(pairwise_penalties) if pairwise_penalties else 0
    
    model.Minimize(
        sum(y[j] for j in range(max_containers)) +  # Minimize number of containers
        group_penalty_lambda * group_split_penalty +  # Group cohesion penalty
        volume_balance_lambda * volume_balance_penalty  # Volume balance penalty
    )
    return model, x, y, group_in_containers, group_ids
