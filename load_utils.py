import json

def load_data_from_json(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    container = tuple(data['container'])
    boxes = data['boxes']
    symmetry_mode = data.get('symmetry_mode', data.get('symmetry_breaking', 'full'))
    max_time_in_seconds = data.get('max_time_in_seconds', 60)
    anchor_mode = data.get('anchor_mode', None)
    prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight = data.get('prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight', 0)
    prefer_maximize_surface_contact_weight = data.get('prefer_maximize_surface_contact_weight', 0)
    prefer_put_boxes_lower_z_weight = data.get('prefer_put_boxes_lower_z_weight', 0)
    prefer_total_floor_area_weight = data.get('prefer_total_floor_area_weight', 0)  # default 0 for backward compatibility
    prefer_put_boxes_lower_z_non_linear_weight = data.get('prefer_put_boxes_lower_z_non_linear_weight', 0)  # default 0
    prefer_put_boxes_by_volume_lower_z_weight = data.get('prefer_put_boxes_by_volume_lower_z_weight', 0)  # default 0
    return (container, boxes, symmetry_mode, max_time_in_seconds, anchor_mode,
            prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,
            prefer_maximize_surface_contact_weight,
            prefer_put_boxes_lower_z_weight,
            prefer_total_floor_area_weight,
            prefer_put_boxes_lower_z_non_linear_weight,
            prefer_put_boxes_by_volume_lower_z_weight)
