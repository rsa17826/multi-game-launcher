# @regex settings \(launcher\.SettingsData\): _description_
# @replace settings (launcher.SettingsData): The current settings object containing user-defined flags
# @endregex

import launcher
import os
import subprocess
from PySide6.QtWidgets import QVBoxLayout
from enum import Enum


class supportedOs(Enum):
  windows = 0
  linux = 1


def getGameLogLocation(selectedOs: supportedOs, gameId: str):
  return ""


def gameLaunchRequested(
  path, args, settings: launcher.SettingsData, selectedOs: supportedOs
) -> None:
  if settings.loadSpecificMapOnStart:
    args += ["--loadMap", settings.nameOfMapToLoad]

  match selectedOs:
    case supportedOs.windows:
      exe = os.path.join(path, "vex.exe")
      if os.path.isfile(exe):
        subprocess.Popen([exe] + args, cwd=path)

      exe = os.path.join(path, "windows/vex.exe")
      if os.path.isfile(exe):
        subprocess.Popen([exe] + args, cwd=path)
    case supportedOs.linux:
      exe = os.path.join(path, "vex.sh")
      if os.path.isfile(exe):
        subprocess.Popen([exe] + args, cwd=path)


def getAssetName(settings: launcher.SettingsData) -> str:
  return "windows.zip"


def gameVersionExists(
  path, settings: launcher.SettingsData, selectedOs: supportedOs
) -> bool:
  def isfile(p):
    return os.path.isfile(os.path.join(path, p))

  match selectedOs:
    case supportedOs.windows:
      return (isfile("vex.exe") and isfile("vex.pck")) or (
        isfile("windows/vex.exe") and isfile("windows/vex.pck")
      )
    case supportedOs.linux:
      return isfile("vex.sh") and isfile("vex.pck")


def addCustomNodes(_self: launcher.Launcher, layout: QVBoxLayout) -> None:
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
    supportedOs=supportedOs,
  )
)
