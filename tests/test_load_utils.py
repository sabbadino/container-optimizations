import pytest
from load_utils import load_data_from_json


def test_load_data_from_json():
    path = 'inputs/step2_sample_packing_data_with_rotation.json'
    container, boxes, symmetry_mode, max_time, anchormode = load_data_from_json(path)
    assert container == (10, 10, 10)
    assert isinstance(boxes, list)
    assert len(boxes) == 15
    assert boxes[0]['id'] == 1
    assert symmetry_mode == 'simple'
    assert max_time == 120
    assert anchormode == 'heavierWithinMostRecurringSimilar'
