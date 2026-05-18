@echo off
if exist ./.venv (
  call ./.venv/scripts/activate
) else (
  py -3.13 --version >nul 2>&1 && (py -3.13 -m venv .venv) || (py install 3.13 && py -3.13 -m venv .venv || exit)
  call ./.venv/scripts/activate
  pip install -e ./base
  pip install -r ./base/requirements.txt
  rmdir /S /Q "./base/launcher.egg-info"
)
python ./base/launcher/__init__.py %*