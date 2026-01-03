import os
import subprocess, shlex


def getGameLogLocation():
  return ""


def gameLaunchRequested(path, args, settings) -> None:
  """called when the user tries to launch a version of the game
  this should open the game when called
  Args:
    path (str): the path to the game dir
    args (list[str]): the command-line arguments in list format
  """
  if settings.loadSpecificMapOnStart:
    args += ["--loadMap", settings.nameOfMapToLoad]
  exe = os.path.join(path, "vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + args, cwd=path)
  exe = os.path.join(path, "windows/vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + shlex.split(args), cwd=path)


def getAssetName(settings) -> str:
  """file to download from gh releases eg windows.zip
  Returns:
    str
  """
  return "windows.zip"


def gameVersionExists(path, settings) -> bool:
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


from PySide6.QtWidgets import QVBoxLayout


def addCustomNodes(_self, layout: QVBoxLayout) -> None:
  """
  Args:
    _self: The Launcher instance (to register widgets for saving)
    layout: The QVBoxLayout of the Local Settings section
  """

  mapNameInput = _self.newLineEdit('Enter map name or "NEWEST"', "nameOfMapToLoad")
  layout.addWidget(
    _self.newCheckbox(
      "Load Specific Map on Start",
      False,
      "loadSpecificMapOnStart",
      onChange=mapNameInput.setEnabled,
    )
  )
  mapNameInput.setEnabled(_self.settings.loadSpecificMapOnStart)
  layout.addWidget(mapNameInput)


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
