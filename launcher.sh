#!/bin/bash

# Check if the virtual environment directory exists
if [ -d "./.venv" ]; then
  # Activate the virtual environment
  source ./.venv/bin/activate
  # Run the Python script with any passed arguments
  python ./base/launcher/__init__.py "$@"
else
  # Create a virtual environment using Python 3.13 (ensure python3.13 is installed)
  python3.13 -m venv .venv
  # Activate the virtual environment
  source ./.venv/bin/activate
  # Install the base package in editable mode and requirements
  pip install -e ./base
  pip install -r ./base/requirements.txt
  # Remove egg-info directory
  rm -rf ./base/launcher.egg-info
  # Run the Python script with any passed arguments
  python ./base/launcher/__init__.py "$@"
fi
