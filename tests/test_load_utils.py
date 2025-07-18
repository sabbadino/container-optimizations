import pytest
from load_utils import load_data_from_json


def test_load_data_from_json():
    path = 'inputs/step2_sample_packing_data_with_rotation.json'
    (
        container,
        boxes,
        symmetry_mode,
        max_time,
        anchormode,
        prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight,
        prefer_maximize_surface_contact_weight,
        prefer_put_boxes_lower_z_weight,
        prefer_total_floor_area_weight,
        prefer_put_boxes_lower_z_non_linear_weight,
        prefer_put_boxes_by_volume_lower_z_weight,
    ) = load_data_from_json(path)
    assert container == (10, 10, 10)
    assert isinstance(boxes, list)
    assert len(boxes) == 15
    assert boxes[0]['id'] == 1
    assert symmetry_mode == 'simple'
    assert max_time == 120
    assert anchormode == 'larger'
