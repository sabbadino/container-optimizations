import json

def load_data_from_json(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    container = tuple(data['container'])
    boxes = data['boxes']
    symmetry_mode = data.get('symmetry_breaking', 'full')
    max_time = data.get('max_time_in_seconds', 60)
    return container, boxes, symmetry_mode, max_time
