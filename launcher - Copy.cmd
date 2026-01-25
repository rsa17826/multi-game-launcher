@echo off
if exist ./.venv (
  call ./.venv/scripts/activate
  python ./base/launcher/__init__.py offline launcherName vex++
) else (
  py -3.13 -m venv .venv
  call ./.venv/scripts/activate
  pip install -e ./base
  pip install -r ./base/requirements.txt
  python ./base/launcher/__init__.py
)