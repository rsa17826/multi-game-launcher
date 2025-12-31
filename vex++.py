import os
import subprocess


def getGameLogLocation():
  return ""


def gameLaunchRequested(path):
  """called when the user tries to launch a version of the game
  this should open the game when called
  Args:
    path (str): the path to the game dir
  """
  exe = os.path.join(path, "vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe], cwd=path)


def getAssetName():
  """file to download from gh releases eg windows.zip
  Returns:
    str
  """
  return "windows.zip"


def gameVersionExists(path):
  """return true if the dir has a valid game version in it
  Args:
    path (str): path to dir to check
  Returns:
    bool: true if the given dir has a valid game in it
  """
  return os.path.isfile(os.path.join(path, "vex.pck"))

from PySide6.QtWidgets import QCheckBox, QLineEdit, QWidget

def addCustomNodes(_self, layout) -> dict[str, QWidget]:
  """
  Args:
    _self: The Launcher instance (to register widgets for saving)
    layout: The QVBoxLayout of the Local Settings section
  """

  # 1. Create the Checkbox
  load_level_cb = QCheckBox("Load Specific Level on Start")
  layout.addWidget(load_level_cb)

  # 2. Create the Input Box
  level_name_input = QLineEdit()
  level_name_input.setPlaceholderText("Enter level name (e.g. Level_01)")

  # Start greyed out (disabled)
  level_name_input.setEnabled(False)
  layout.addWidget(level_name_input)

  # 3. Logic: Automatically grey/un-grey the input based on the checkbox
  # When checkbox is checked (True), setEnabled(True) is called.
  # When unchecked (False), it becomes greyed out.
  load_level_cb.toggled.connect(level_name_input.setEnabled)

  return {"cb_load_custom_level":load_level_cb, "input_level_name":level_name_input}


import launcher

launcher.run(
  launcher.Config(
    WINDOW_TITLE="Vex++ Launcher",
    USE_HARD_LINKS=True,
    CAN_USE_CENTRAL_GAME_DATA_FOLDER=True,
    GH_USERNAME="rsa17826",
    GH_REPO="vex-plus-plus",
    getGameLogLocation=getGameLogLocation,
    gameLaunchRequested=gameLaunchRequested,
    getAssetName=getAssetName,
    gameVersionExists=gameVersionExists,
    addCustomNodes=addCustomNodes,
  )
)
