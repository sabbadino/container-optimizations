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
