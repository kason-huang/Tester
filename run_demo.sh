#!/bin/bash
# Wrapper script to run Habitat-Sim demo with proper environment variables

# Run the Python script directly (pygame now initializes before Habitat-sim to avoid OpenGL context conflicts)
python habitat-learning/simple_demo_viewer.py "$@"
