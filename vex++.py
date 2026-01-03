import os
import subprocess, shlex


def getGameLogLocation():
  return ""


def gameLaunchRequested(path, args):
  """called when the user tries to launch a version of the game
  this should open the game when called
  Args:
    path (str): the path to the game dir
    args (list[str]): the command-line arguments in list format
  """
  exe = os.path.join(path, "vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + args, cwd=path)
  exe = os.path.join(path, "windows/vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + shlex.split(args), cwd=path)


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

  def isfile(p):
    return os.path.isfile(os.path.join(path, p))

  return (isfile("vex.exe") and isfile("vex.pck")) or (
    isfile("windows/vex.exe") and isfile("win dows/vex.pck")
  )


from PySide6.QtWidgets import QWidget


def addCustomNodes(_self, layout) -> dict[str, QWidget]:
  """
  Args:
    _self: The Launcher instance (to register widgets for saving)
    layout: The QVBoxLayout of the Local Settings section
  """

  levelNameInput = _self.newLineEdit(
    "Enter level name (e.g. Level_01)", "inputLevelName"
  )
  layout.addWidget(
    _self.newCheckbox(
      "Load Specific Level on Start",
      False,
      "loadCustomLevel",
      onChange=levelNameInput.setEnabled,
    )
  )
  levelNameInput.setEnabled(_self.settings.loadCustomLevel)
  layout.addWidget(levelNameInput)

  return {}


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
