"""
Utility functions for conditional printing.
"""

def create_print_if_verbose(verbose):
    """
    Creates a print function that only prints if verbose is True.
    
    Args:
        verbose (bool): Whether to enable printing
        
    Returns:
        function: A print function that respects the verbose flag
        
    Example:
        print_if_verbose = create_print_if_verbose(True)
        print_if_verbose("This will print")
        
        print_if_verbose = create_print_if_verbose(False)
        print_if_verbose("This will not print")
    """
    def print_if_verbose(*args, **kwargs):
        """Helper function to print only if verbose is True"""
        if verbose:
            print(*args, **kwargs)
    
    return print_if_verbose


def print_if_verbose_factory(verbose):
    """
    Alternative factory function name for creating conditional print functions.
    This is an alias for create_print_if_verbose.
    """
    return create_print_if_verbose(verbose)


def dump_phase1_results(
    solver, status, x, y, group_in_containers, group_ids, group_to_items,
    items, container_size, container_weight, verbose=False):
    """
    Print and write markdown summary of phase 1 assignment model results.
    
    Args:
        solver: OR-Tools CP-SAT solver instance
        status: Solver status
        x: Assignment variables (item -> container)
        y: Container usage variables
        group_in_containers: Group assignment variables
        group_ids: List of group IDs
        group_to_items: Mapping from group ID to item indices
        items: List of item dictionaries
        container_size: [L, W, H] container dimensions
        container_weight: Maximum weight per container
        verbose: Whether to print detailed output
    """
    print_if_verbose = create_print_if_verbose(verbose)
    
    num_items = len(items)
    item_ids = [item.get('id', i+1) for i, item in enumerate(items)]
    item_weights = [item['weight'] for item in items]
    item_volumes = [item['size'][0] * item['size'][1] * item['size'][2] for item in items]
    item_group_ids = [item.get('group_id') for item in items]
    container_volume = container_size[0] * container_size[1] * container_size[2]
    if container_volume <= 0:
        raise ValueError(f"Invalid container volume: {container_volume}. Container dimensions: {container_size}")
    if container_weight <= 0:
        raise ValueError(f"Invalid container weight: {container_weight}")
    max_containers = len(y)
    
    # Import here to avoid circular dependencies
    from ortools.sat.python import cp_model
    status_dict = {
        cp_model.OPTIMAL: 'OPTIMAL',
        cp_model.FEASIBLE: 'FEASIBLE',
        cp_model.INFEASIBLE: 'INFEASIBLE',
        cp_model.MODEL_INVALID: 'MODEL_INVALID',
        cp_model.UNKNOWN: 'UNKNOWN',
    }
 
    print('')
    print(f'******** PHASE 1 OUTPUT ********')
    print(f'Step 1 Solver status: {status_dict.get(status, status)}')
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        min_containers = int(sum(solver.Value(y[j]) for j in range(max_containers)))
        group_splits = {g: solver.Value(group_in_containers[g]) - 1 for g in group_ids}
        total_group_splits = sum(group_splits.values())
        print(f'Minimum containers used: {min_containers}')
        print(f'Total group splits (penalized): {total_group_splits}')
        used_container_indices = [j for j in range(max_containers) if solver.Value(y[j])]
        container_rebase = {old_idx: new_idx+1 for new_idx, old_idx in enumerate(used_container_indices)}
 
        total_boxes_weight_check = sum(item_weights[i] for j in used_container_indices for i in range(num_items) if solver.Value(x[i, j]))  
        total_boxes_volume_check = sum(item_volumes[i] for j in used_container_indices for i in range(num_items) if solver.Value(x[i, j]))
        total_container_boxes = 0
 
        for old_j in used_container_indices:
            new_j = container_rebase[old_j]
            items_in_container = [i for i in range(num_items) if solver.Value(x[i, old_j])]
            total_weight = sum(item_weights[i] for i in items_in_container)
            total_volume = sum(item_volumes[i] for i in items_in_container)
            container_boxes = [items[i] for i in items_in_container]
            total_container_boxes += len(container_boxes)
            pct_weight = 100 * total_weight / container_weight if container_weight > 0 else 0
            pct_volume = 100 * total_volume / container_volume if container_volume > 0 else 0
            print_if_verbose('')
            print_if_verbose(f'### Container {new_j}')
            print_if_verbose('| Item id | Weight | Volume | Group id |')
            
            for i in items_in_container:
                print_if_verbose(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_group_ids[i]} |')
            print_if_verbose(f'**Total for container {new_j}: weight = {total_weight} ({pct_weight:.1f}% of max), volume = {total_volume} ({pct_volume:.1f}% of max)**')
        
        print(f'Total boxes weight check: {total_boxes_weight_check}')
        print(f'Total boxes volume check: {total_boxes_volume_check}')    
        print(f'Total container boxes: {total_container_boxes}')            
        
        if group_ids:
            print_if_verbose('')
            print_if_verbose('### Group Splits')
            print_if_verbose('| Group id | Containers used | Splits (penalized) | Container numbers |')
            print_if_verbose('|----------|----------------|--------------------|-------------------|')
            for g in group_ids:
                containers_for_group = []
                for old_j in used_container_indices:
                    if any(solver.Value(x[i, old_j]) for i in group_to_items[g]):
                        containers_for_group.append(str(container_rebase[old_j]))
                containers_str = ', '.join(containers_for_group)
                print_if_verbose(f'| {g} | {solver.Value(group_in_containers[g])} | {group_splits[g]} | {containers_str} |')
            print('')
    else:
        print('No solution found.')
    print(f'********************************')
