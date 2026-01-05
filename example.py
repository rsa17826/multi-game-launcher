# @regex settings \(launcher\.SettingsData\): _description_
# @replace settings (launcher.SettingsData): The current settings object containing user-defined flags
# @endregex

import launcher as launcher
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
  return


def getAssetName(settings: launcher.SettingsData) -> str:
  return ""


def gameVersionExists(
  path, settings: launcher.SettingsData, selectedOs: supportedOs
) -> bool:
  return False


import os


def addCustomNodes(_self: launcher.Launcher, layout: QVBoxLayout) -> None:
  layout.addWidget(
    _self.newButton(
      "open example file location",
      lambda: _self.openFile(os.path.dirname(__file__)),
    )
  )


launcher.loadConfig(
  launcher.Config(
    WINDOW_TITLE="Example File",
    CAN_USE_CENTRAL_GAME_DATA_FOLDER=False,
    GH_USERNAME="",
    GH_REPO="",
    getGameLogLocation=getGameLogLocation,
    gameLaunchRequested=gameLaunchRequested,
    getAssetName=getAssetName,
    gameVersionExists=gameVersionExists,
    addCustomNodes=addCustomNodes,
    supportedOs=supportedOs,
  )
)
