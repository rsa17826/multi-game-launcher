import inspect
import sys

# Define the list of variables you require
REQUIRED_VARS = {
  "ASSET_NAME": "file to download from gh releases eg windows.zip",
  "GAME_LOG_LOCATION": "location that the game stores error logs, leave empty if the game doesn't generate logs",
  "WINDOW_TITLE": "what to set the launchers title to",
  "USE_HARD_LINKS": "if true will scan all new version downloads and check to see if any files are the same between different versions and replace the new files with hardlinks instead",
  "USE_CENTRAL_GAME_DATA_FOLDER": "if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location",
  "API_URL": "github api url eg https://api.github.com/repos/rsa17826/vex-plus-plus/releases",
}


def check_requirements():
  # Look at the module that imported this file
  frame = inspect.stack()[1]
  caller_globals = frame.frame.f_globals
  caller_name = caller_globals.get("__name__")

  # We don't want to error out if we are running hints.py directly
  if caller_name == "__main__":
    return

  missing = []
  for var in REQUIRED_VARS:
    if var not in caller_globals:
      missing.append(var)

  if missing:
    print("\n" + "!" * 50)
    print(f"CONFIGURATION ERROR in '{frame.filename}':")
    for var in missing:
      print(f" -> Variable '{var}' must be defined before importing hints.")
    print("!" * 50 + "\n")
    sys.exit(1)  # Stop the program immediately


# Run the check automatically on import
check_requirements()
