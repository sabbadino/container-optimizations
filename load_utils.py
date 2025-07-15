import json

def load_data_from_json(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    container = tuple(data['container'])
    boxes = data['boxes']
    return container, boxes
