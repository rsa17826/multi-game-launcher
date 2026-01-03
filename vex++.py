import launcher
import os
import subprocess, shlex
from PySide6.QtWidgets import QVBoxLayout


def getGameLogLocation():
  return ""


def gameLaunchRequested(path, args, settings: launcher.SettingsData) -> None:
  """
  Handles the execution of the game binary when the user double-clicks a version.

  Args:
    path (str): The directory containing the specific game version.
    args (list[str]): Base command-line arguments provided by the launcher.
    settings: The current settings object containing user-defined flags.
  """
  if settings.loadSpecificMapOnStart:
    args += ["--loadMap", settings.nameOfMapToLoad]

  exe = os.path.join(path, "vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + args, cwd=path)

  exe = os.path.join(path, "windows/vex.exe")
  if os.path.isfile(exe):
    subprocess.Popen([exe] + args, cwd=path)


def getAssetName(settings: launcher.SettingsData) -> str:
  """
  Identifies which file to download from the GitHub Release assets.
  """
  return "windows.zip"


def gameVersionExists(path, settings: launcher.SettingsData) -> bool:
  """
  Validation check to see if a folder contains a valid installation.
  Used by the launcher to decide if a version is 'Local' (Run) or 'Online' (Download).
  """

  def isfile(p):
    return os.path.isfile(os.path.join(path, p))

  return (isfile("vex.exe") and isfile("vex.pck")) or (
    isfile("windows/vex.exe") and isfile("windows/vex.pck")
  )


def addCustomNodes(_self: launcher.Launcher, layout: QVBoxLayout) -> None:
  """
  Injects custom UI elements into the 'Local Settings' section of the Launcher.

  Args:
    _self: Reference to the Launcher instance to use its helper methods (newCheckbox, etc.)
    layout: The layout where these widgets will be added.
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
