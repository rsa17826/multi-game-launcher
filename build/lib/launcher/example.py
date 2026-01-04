# @regex settings \(launcher\.SettingsData\): _description_
# @replace settings (launcher.SettingsData): The current settings object containing user-defined flags
# @endregex

import launcher
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


def addCustomNodes(_self: launcher.Launcher, layout: QVBoxLayout) -> None:
  return


launcher.run(
  launcher.Config(
    WINDOW_TITLE="You've Ran the Wrong File",
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
