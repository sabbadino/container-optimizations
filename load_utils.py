import json
import os

def load_data_from_json(input_file):
    """
    Load container optimization data from JSON file with proper error handling.
    
    Args:
        input_file (str): Path to the JSON input file
        
    Returns:
        tuple: Container data and configuration parameters
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the JSON is malformed or missing required fields
        PermissionError: If unable to read the file due to permissions
    """
    # Validate input file path
    if not input_file:
        raise ValueError("Input file path cannot be empty")
    
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    try:
        # Handle file reading errors
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {input_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in {input_file}: {e}")
    except UnicodeDecodeError:
        raise ValueError(f"File encoding error in {input_file}. Expected UTF-8.")
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading {input_file}: {e}")
    
    # Validate required fields exist (core structural fields only)
    required_fields = ['container', 'boxes']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields in JSON: {missing_fields}")
    
    try:
        # Validate and extract container data
        container_data = data['container']
        if not isinstance(container_data, (list, tuple)) or len(container_data) != 3:
            raise ValueError("Container must be a list/tuple of 3 dimensions [L, W, H]")
        
        container = tuple(float(dim) for dim in container_data)
        if any(dim <= 0 for dim in container):
            raise ValueError("Container dimensions must be positive numbers")
        
        # Validate boxes data
        boxes = data['boxes']
        if not isinstance(boxes, list) or len(boxes) == 0:
            raise ValueError("Boxes must be a non-empty list")
        
        # Validate each box has required fields
        for i, box in enumerate(boxes):
            if not isinstance(box, dict):
                raise ValueError(f"Box {i} must be a dictionary")
            
            required_box_fields = ['id', 'size', 'weight']
            missing_box_fields = [field for field in required_box_fields if field not in box]
            if missing_box_fields:
                raise ValueError(f"Box {i} missing required fields: {missing_box_fields}")
            
            # Validate box dimensions
            if not isinstance(box['size'], (list, tuple)) or len(box['size']) != 3:
                raise ValueError(f"Box {i} size must be [L, W, H]")
            
            if any(dim <= 0 for dim in box['size']):
                raise ValueError(f"Box {i} dimensions must be positive")
            
            # Validate weight
            if not isinstance(box['weight'], (int, float)) or box['weight'] < 0:
                raise ValueError(f"Box {i} weight must be non-negative number")

            # Validate rotation (required)
            if 'rotation' not in box:
                raise ValueError(f"Box {i} missing required field 'rotation'")
            rot = box['rotation']
            if rot not in ('none', 'z', 'free'):
                raise ValueError(f"Box {i} invalid rotation '{rot}'. Must be one of ['none','z','free']")
        
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid data format: {e}")
    
    # Extract optional parameters with validation
    try:
        # symmetry_mode is required (no default). Accept legacy/test value 'simple' too
        if 'symmetry_mode' not in data:
            raise ValueError("Missing required field in JSON: 'symmetry_mode'")
        symmetry_mode = data['symmetry_mode']
        valid_symmetry_modes = ['full', 'partial', 'none', 'simple']
        if symmetry_mode not in valid_symmetry_modes:
            raise ValueError(f"Invalid symmetry_mode: {symmetry_mode}. Must be one of {valid_symmetry_modes}")

        # solver_phase1_max_time_in_seconds is required (no default).
        if 'solver_phase1_max_time_in_seconds' in data:
            solver_phase1_max_time_in_seconds = data['solver_phase1_max_time_in_seconds']
        else:
            raise ValueError("Missing required field in JSON: 'solver_phase1_max_time_in_seconds'")
        if not isinstance(solver_phase1_max_time_in_seconds, (int, float)) or solver_phase1_max_time_in_seconds <= 0:
            raise ValueError("solver_phase1_max_time_in_seconds must be a positive number")
        
        anchor_mode = data.get('anchor_mode', None)
        if anchor_mode is not None:
            # Accept additional mode 'larger' used in tests/configs
            valid_anchor_modes = ['volume', 'weight', 'surface_area', 'larger']
            if anchor_mode not in valid_anchor_modes:
                raise ValueError(f"Invalid anchor_mode: {anchor_mode}. Must be one of {valid_anchor_modes}")
        
        # Validate weight parameters are non-negative numbers
        weight_params = [
            'prefer_orientation_where_side_with_biggest_surface_is_at_the_bottom_weight',
            'prefer_maximize_surface_contact_weight', 
            'prefer_large_base_lower_weight',
            'prefer_total_floor_area_weight',
            'prefer_large_base_lower_non_linear_weight',
            'prefer_put_boxes_by_volume_lower_z_weight'
        ]
        
        extracted_weights = []
        for param in weight_params:
            value = data.get(param, 0)
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{param} must be a non-negative number")
            extracted_weights.append(value)
        
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid configuration parameter: {e}")
    
    return (container, boxes, symmetry_mode, solver_phase1_max_time_in_seconds, anchor_mode, *extracted_weights)
