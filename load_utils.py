import json

def load_data_from_json(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    container = tuple(data['container'])
    boxes = data['boxes']
    symmetry_mode = data.get('symmetry_breaking', 'full')
    max_time = data.get('max_time_in_seconds', 60)
    anchormode = data.get('anchormode', None)
    prefer_side_with_biggest_surface_at_the_bottom_weight = data.get('preferSideWithBiggestSurfaceAtTheBottomWeight', 0)
    prefer_maximize_surface_contact_weight = data.get('preferMaximizeSurfaceContactWeight', 0)
    prefer_large_base_lower_weight = data.get('preferLargeBaseLowerWeight', 0)
    prefer_total_floor_area_weight = data.get('preferTotalFloorAreaWeight', 0)  # default 0 for backward compatibility
    prefer_large_base_lower_non_linear_weight = data.get('preferLargeBaseLowerNonLinearWeight', 0)  # default 0
    return (container, boxes, symmetry_mode, max_time, anchormode,
            prefer_side_with_biggest_surface_at_the_bottom_weight,
            prefer_maximize_surface_contact_weight,
            prefer_large_base_lower_weight,
            prefer_total_floor_area_weight,
            prefer_large_base_lower_non_linear_weight)
