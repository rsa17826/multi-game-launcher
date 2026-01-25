#!/bin/bash

# Check if the virtual environment directory exists
if [ -d "./.venv" ]; then
  # Activate the virtual environment (Unix-based systems use 'source' instead of 'call')
  source ./.venv/bin/activate
  python ./base/launcher/__init__.py
else
  # Create a virtual environment using Python 3.13 (ensure python3.13 is installed)
  python3.13 -m venv .venv
  # Activate the virtual environment
  source ./.venv/bin/activate
  # Install the base package in editable mode and requirements
  pip install -e ./base
  pip install -r ./base/requirements.txt
  # Run the Python script
  python ./base/launcher/__init__.py
fi
