# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a container optimization research project that implements bin packing algorithms using Google OR-Tools. The project focuses on optimizing the placement of boxes/items in containers while considering weight, volume, rotation constraints, and group affinity preferences.

## Core Architecture

The project uses a two-phase optimization approach:

1. **Phase 1 - Assignment Model** (`assignment_model.py`): Uses CP-SAT to assign items to containers, minimizing container count while penalizing group splits
2. **Phase 2 - 3D Placement** (`step2_container_box_placement_in_container.py`): Uses CP-SAT to determine exact 3D coordinates for items within each container

### Key Components

- **ALNS Implementation** (`alns_container_loading.py`): Adaptive Large Neighborhood Search metaheuristic for repair/destroy operations
- **Model Setup** (`model_setup.py`): Creates position variables and constraints for 3D bin packing
- **Model Constraints** (`model_constraints.py`): Non-overlap, boundary, and geometric constraints
- **Model Optimizations** (`model_optimizations.py`): Objective functions and preference weights
- **Load Utilities** (`load_utils.py`): JSON data loading and validation
- **Visualization** (`visualization_utils.py`): Plotting and 3D visualization tools

### Execution Flow

1. `step1_box_partition_in_containers.py` - Main entry point for assignment optimization
2. `step2_container_box_placement_in_container.py` - Called per container for 3D placement

## Development Commands

### Environment Setup
The project uses a Python virtual environment in `ortools/`:
```bash
ortools\Scripts\activate  # Windows
# or
source ortools/bin/activate  # Unix
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest
# or with verbose output:
pytest -vv
```

### Input/Output Structure

- **Input files**: JSON format in `inputs/` directory
- **Output files**: Results saved to `outputs/` as both JSON and Markdown reports
- **Settings**: Step 2 optimization parameters in JSON files (e.g., `inputs/step2_settings_a.json`)

### Data Format

Items must have: `id`, `size` [L,W,H], `weight`, `rotation` (free/fixed), optional `group_id`
Containers have: `size` [L,W,H], `weight` capacity

### .NET Implementation

A parallel C# implementation exists in `net/` using OR-Tools .NET bindings:
- Build with Visual Studio or `dotnet build net/ortoolsnet/ortoolsnet.sln`
- Console app entry point: `net/NetConsoleApp/Program.cs`

## Key Algorithms

- **CP-SAT**: Google OR-Tools constraint programming solver
- **ALNS**: Adaptive Large Neighborhood Search for metaheuristic optimization
- **3D Non-overlap**: Geometric constraints ensuring boxes don't overlap
- **Group penalties**: Soft constraints to keep items with same group_id together