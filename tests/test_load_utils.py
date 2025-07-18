import pytest
from load_utils import load_data_from_json


def test_load_data_from_json():
    path = 'tests/inputs/step2_sample_packing_data_with_rotation.json'
    (container, boxes, symmetry_mode, max_time, anchormode, 
     prefer_orientation_weight, prefer_surface_contact_weight, 
     prefer_large_base_weight, prefer_floor_area_weight, 
     prefer_large_base_nonlinear_weight, prefer_volume_lower_z_weight) = load_data_from_json(path)
    assert container == (10, 10, 10)
    assert isinstance(boxes, list)
    assert len(boxes) == 15
    assert boxes[0]['id'] == 1
    assert symmetry_mode == 'simple'
    assert max_time == 120
    assert anchormode == 'larger'
