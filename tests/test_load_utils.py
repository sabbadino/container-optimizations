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
    # check box fields spot-check
    assert boxes[0]['rotation'] == 'none'
    assert symmetry_mode == 'simple'
    assert max_time == 120
    assert anchormode == 'larger'
    # verify all preference weights are parsed in the expected order
    assert prefer_orientation_weight == 0
    assert prefer_surface_contact_weight == 0
    assert prefer_large_base_weight == 0
    assert prefer_floor_area_weight == 0
    assert prefer_large_base_nonlinear_weight == 0
    assert prefer_volume_lower_z_weight == 1


def _write_json(tmp_path, payload):
    p = tmp_path / "input.json"
    p.write_text(__import__('json').dumps(payload), encoding='utf-8')
    return str(p)


def test_rotation_missing_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0}  # rotation missing
        ]
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "missing required field 'rotation'" in str(e.value)


def test_rotation_invalid_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0, "rotation": "bad"}
        ]
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "invalid rotation" in str(e.value).lower()


def test_invalid_container_dims_raises(tmp_path):
    payload = {
        "container": [10, 0, 10],  # zero dim
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0, "rotation": "free"}
        ]
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "Container dimensions must be positive" in str(e.value)


def test_invalid_box_dims_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, -2, 3], "weight": 1.0, "rotation": "z"}
        ]
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "dimensions must be positive" in str(e.value)


def test_invalid_weight_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": -5, "rotation": "none"}
        ]
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "weight must be non-negative" in str(e.value)


def test_invalid_symmetry_mode_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0, "rotation": "free"}
        ],
        "symmetry_mode": "bogus"
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "Invalid symmetry_mode" in str(e.value)


def test_invalid_anchor_mode_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0, "rotation": "free"}
        ],
    "anchor_mode": "wrong",
    # required fields
    "symmetry_mode": "full",
    "solver_phase1_max_time_in_seconds": 60
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "Invalid anchor_mode" in str(e.value)


def test_negative_preference_weight_raises(tmp_path):
    payload = {
        "container": [10, 10, 10],
        "boxes": [
            {"id": 1, "size": [1, 2, 3], "weight": 1.0, "rotation": "free"}
        ],
    "prefer_total_floor_area_weight": -1,
    # required fields
    "symmetry_mode": "full",
    "solver_phase1_max_time_in_seconds": 60
    }
    path = _write_json(tmp_path, payload)
    with pytest.raises(ValueError) as e:
        load_data_from_json(path)
    assert "must be a non-negative number" in str(e.value)
