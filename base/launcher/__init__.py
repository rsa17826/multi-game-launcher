# @name a
# @regex (?<=[^\s])  #
# @replace  #
# @endregex
from _hashlib import HASH
from ast import TypeAlias
from inspect import FrameInfo
from os import stat_result
from re import Match
from types import ModuleType
from requests.models import Response
from subprocess import CompletedProcess
from typing import Any, Never, Literal, cast
import shutil
import inspect
from dataclasses import dataclass
from typing import Callable
from functools import partial as bind
from itertools import islice
import sys
import time
import random
import requests
import shlex
from enum import Enum, EnumMeta
import json
from PySide6.QtGui import (
  QAction,
  QCloseEvent,
  QDesktopServices,
  QPainter,
  QPixmap,
  QIcon,
)
from PySide6.QtCore import QCoreApplication, QEvent, QRect, QRectF, QUrl, Signal
from PySide6.QtWidgets import (
  QApplication,
  QWidget,
  QListWidget,
  QPushButton,
  QVBoxLayout,
  QHBoxLayout,
  QCheckBox,
  QLineEdit,
  QLabel,
  QListWidgetItem,
  QSpinBox,
  QDialog,
  QGroupBox,
  QComboBox,
  QMenu,
  QMessageBox,
)
from PySide6.QtCore import QThread
from PySide6.QtGui import (
  QLinearGradient,
  QColor,
)
from PySide6.QtCore import QTimer
import os
import zipfile
import py7zr
import re
from pathlib import Path
from PySide6.QtCore import Qt
import math

import hashlib

from typing_extensions import override # pyright: ignore[reportMissingModuleSource]
from collections.abc import Iterator

type ReleaseType = dict[str, object]
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))


class EnumComboBox(QComboBox):
  usesEnum: bool = False
  usedEnum: type[Enum] | None = None


@dataclass
class ArgumentData:
  key: str | list[str]
  afterCount: int
  default: object = None

  def __post_init__(self):
    if self.afterCount == 0:
      self.default = False
    if isinstance(self.key, str):
      self.key = self.key.lstrip("-")
    else:
      self.key = [*map(lambda x: x.lstrip("-"), self.key)]


LAST_USED_ARGS = []


def checkArgs(*argData: ArgumentData, useArgs: list[str] | None = None) -> list[object]:
  if not useArgs:
    args: list[str] = sys.argv[1:] # Ignore the script name, only check arguments
    if "--" in args:
      beforeDashArgs = args[: args.index("--")]
    else:
      beforeDashArgs = args
    argsBeingUsed = beforeDashArgs
  else:
    argsBeingUsed = useArgs.copy()
  global LAST_USED_ARGS
  LAST_USED_ARGS = argsBeingUsed.copy() # pyright: ignore[reportConstantRedefinition]
  # print(beforeDashArgs, args)
  # Initialize results with the default values from argData
  results: list[object] = [data.default for data in argData]

  i = 0
  while i < len(argsBeingUsed):
    nextArg: str = argsBeingUsed[i].lstrip("-")
    foundKey: ArgumentData | None = None
    for testData in argData:
      if testData.key is str:
        if testData.key == nextArg:
          foundKey = testData
          break
      else:
        if nextArg in testData.key:
          foundKey = testData
          break

    if foundKey:
      afterCount: int = foundKey.afterCount
      idx: int | None = next(
        (
          index
          for index, e in enumerate(argData)
          if (
            e.key == nextArg if isinstance(e.key, str) else nextArg in e.key
          )
        ),
        None,
      )
      if idx is None:
        _ = argsBeingUsed.pop(i)
        continue
      if afterCount == 0:
        # If afterCount is 0, consume the key (do not use its value)
        _ = argsBeingUsed.pop(i)
        results[idx] = True # True for a valid flag

      elif afterCount == 1:
        # If afterCount is 1, consume the next argument as the value for the key
        if i + 1 < len(argsBeingUsed):
          value = argsBeingUsed[i + 1]
          _ = argsBeingUsed.pop(i)
          _ = argsBeingUsed.pop(i)
          results[idx] = value # Then the value
        else:
          # If no argument follows the key, use the default
          _ = argsBeingUsed.pop(i)
          print(
            "err",
            nextArg,
            "requires",
            afterCount,
            "args",
            "but received",
            len(argsBeingUsed),
            "args",
          )
          results[idx] = foundKey.default

      elif afterCount > 1:
        available_values = len(argsBeingUsed) - i - 1 # exclude the key itself
        if available_values >= afterCount:
          values = argsBeingUsed[i + 1 : i + 1 + afterCount]
          argsBeingUsed = (
            argsBeingUsed[:i] + argsBeingUsed[i + 1 + afterCount :]
          )
          results[idx] = values
        else:
          print(
            "err",
            nextArg,
            "requires",
            afterCount,
            "args",
            "but received",
            available_values, # ← was len(argsBeingUsed), which included the key
            "args",
          )
          argsBeingUsed = []

    else:
      # If the key is invalid, just skip it and move to the next argument
      _ = argsBeingUsed.pop(i)
      continue # Skip to the next argument

    # Skip over the processed argument
    continue

  # print(results)
  return results


selectorConfig = None

LAUNCHER_START_PATH = os.path.abspath(os.path.dirname(__file__))


def get_app_data_path():
  app_name = "launcher"

  if sys.platform == "win32":
    # Windows standard: ~/AppData/Local
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
  elif sys.platform == "darwin":
    # macOS standard: ~/Library/Application Support
    base = os.path.expanduser("~/Library/Application Support")
  else:
    # Linux/Unix XDG standard
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

  return os.path.abspath(os.path.join(base, app_name))


APP_DATA_PATH = get_app_data_path()
os.makedirs(APP_DATA_PATH, exist_ok=True)

# import os
# import sys

# def get_paths(app_name: str):
#     if sys.platform == "win32":
#         # Windows: Config goes to 'Roaming', Data goes to 'Local'
#         config_base = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
#         data_base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
#     elif sys.platform == "darwin":
#         # macOS: Both usually live in Application Support
#         config_base = data_base = os.path.expanduser("~/Library/Application Support")
#     else:
#         # Linux/Unix: Standard XDG paths
#         config_base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
#         data_base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

#     return {
#         "config": os.path.join(config_base, app_name),
#         "data": os.path.join(data_base, app_name)
#     }

# paths = get_paths("launcher")
# APP_CONFIG_PATH = paths["config"]
# APP_DATA_PATH = paths["data"]

ALL_ARG_DATA = (
  ArgumentData(key="offline", afterCount=0),
  ArgumentData(key=["launcherName", "startLauncher"], afterCount=1),
  ArgumentData(key="tryupdate", afterCount=0),
  ArgumentData(key=["silent", "headless"], afterCount=0),
  ArgumentData(key="version", afterCount=1),
  ArgumentData(key="registerProtocols", afterCount=0),
  ArgumentData(key="downloadLauncher", afterCount=4),
)

os.makedirs(os.path.join(APP_DATA_PATH, "launcherData"), exist_ok=True)


def buildArgs(*argData: ArgumentData, useArgs: list[str]) -> list[str]:
  # This will hold the final argument list
  result_args: list[str] = []

  # Start building the argument list based on useArgs
  for i in range(0, len(useArgs)):
    current_arg = useArgs[i]

    # Find matching ArgumentData for the current argument
    matching_data = None
    for data in argData:
      if isinstance(data.key, str):
        # If the key is a string, check if it matches the current_arg
        if data.key == current_arg:
          matching_data = data
          break
      else:
        # elif isinstance(data.key, list):
        # If the key is a list, check if object key matches the current_arg
        if current_arg in data.key:
          matching_data = data
          break

    # If a matching ArgumentData is found, handle accordingly
    if matching_data:
      # Add the argument key to the result
      result_args.append(f"--{current_arg}")

      # If afterCount > 0, we need to add the corresponding values
      afterCount = matching_data.afterCount
      if afterCount > 0:
        # Ensure there are enough arguments for the afterCount
        if i + 1 + afterCount <= len(useArgs):
          result_args.extend(useArgs[i + 1 : i + 1 + afterCount])
          # Skip the processed arguments (key + values)
          i += afterCount
        else:
          print(
            f"Error: Not enough arguments after {current_arg}. Expected {afterCount} but got {len(useArgs) - i - 1}."
          )
          break
    else:
      print(f"Warning: Unknown argument {current_arg}, skipping.")

  return result_args


OFFLINE: object = False
LAUNCHER_TO_LAUNCH: object = None
TRY_UPDATE: object = False
HEADLESS: object = False
VERSION: object = None
REGISTER_PROTOCOLS: object = False
DOWNLOAD_LAUNCHER: object = False


# asdadsas
def updateArgs(useArgs: list[str] | None = None):
  global OFFLINE, LAUNCHER_TO_LAUNCH, TRY_UPDATE, HEADLESS, VERSION, REGISTER_PROTOCOLS, DOWNLOAD_LAUNCHER
  (
    OFFLINE, # pyright: ignore[reportConstantRedefinition]
    LAUNCHER_TO_LAUNCH, # pyright: ignore[reportConstantRedefinition]
    TRY_UPDATE, # pyright: ignore[reportConstantRedefinition]
    HEADLESS, # pyright: ignore[reportConstantRedefinition]
    VERSION, # pyright: ignore[reportConstantRedefinition]
    REGISTER_PROTOCOLS, # pyright: ignore[reportConstantRedefinition]
    DOWNLOAD_LAUNCHER, # pyright: ignore[reportConstantRedefinition]
  ) = checkArgs(
    *ALL_ARG_DATA,
    useArgs=useArgs,
  )


updateArgs()


from base.launcher.PROTO import PROTO


def protoCalled(msg: str): # type: ignore # pyright: ignore[reportRedeclaration]
  msg: list[str] = msg.split("/")
  updateArgs(msg)
  global REGISTER_PROTOCOLS
  REGISTER_PROTOCOLS = False # pyright: ignore[reportConstantRedefinition]
  # match msg[0]:
  #   case "downloadLauncher":
  #     print(msg)
  #   case _:
  #     print("failed to find valid match", msg)


if PROTO.isSelf("multi-game-launcher") or REGISTER_PROTOCOLS: # type: ignore
  _ = PROTO.add("multi-game-launcher", protoCalled, True)

# print(HEADLESS)
LOCAL_COLOR = Qt.GlobalColor.green
ERROR_COLOR = Qt.GlobalColor.darkRed
LOCAL_ONLY_COLOR = Qt.GlobalColor.yellow
ONLINE_COLOR = Qt.GlobalColor.cyan
MISSING_COLOR = Qt.GlobalColor.gray

MAIN_LOADING_COLOR: tuple[int, int, int] = (0, 210, 255)
UNKNOWN_TIME_LOADING_COLOR: tuple[Literal[255], Literal[108], Literal[0]] = (
  255,
  108,
  0,
)

launcherUpdateAlreadyChecked = False


class Statuses(Enum):
  local = 0
  online = 1
  gameSelector = 2
  loadingInfo = 3
  localOnly = 4


# downloading = 2
# waitingForDownload = 3


@dataclass
class listData:
  path: str | None
  release: ReleaseType | None
  status: Statuses
  version: str


@dataclass
class Config:
  supportedOs: type[Enum]
  GH_USERNAME: str
  """github username eg rsa17826"""
  GH_REPO: str
  """github repo name eg vex-plus-plus"""
  LAUNCHER_GH_USERNAME: str = ""
  """github username for launcher updates - only set if launcher updates should use a separate repo"""
  LAUNCHER_GH_REPO: str = ""
  """github repo name for launcher updates - only set if launcher updates should use a separate repo"""
  LAUNCHER_ASSET_NAME: str = ""
  """Identifies which file to download from the GitHub Release assets for updating the launcher"""
  getImage: Callable[..., str] = lambda *a: ""
  """
returns the path to the image that should be shown

Args:
  version: the game version or the name of the python file.
"""
  addContextMenuOptions: Callable[..., None] = lambda *a: None
  """
Injects custom actions into the right-click menu of a version item.

Args:
  _self: Reference to the Launcher instance.
  menu: The QMenu object being constructed.
  data: The metadata dictionary of the selected version (version, status, path, etc.).
"""
  getGameLogLocation: Callable[..., str] = lambda *a: ""
  gameLaunchRequested: Callable[..., None] = lambda *a: None
  """
Handles the execution of the game binary when the user double-clicks a version.

Args:
  path (str): The directory containing the specific game version.
  args (list[str]): Base command-line arguments provided by the launcher.
  settings: The current settings object containing user-defined flags.
"""
  getAssetName: Callable[..., str] = lambda *a: ""
  """Identifies which file to download from the GitHub Release assets.
Args:
  settings (launcher.SettingsData): The current settings object containing user-defined flags
Returns:
  str: the name of the asset to download from gh
"""
  onGameVersionDownloadComplete: Callable[..., None] = lambda *a: None
  gameVersionExists: Callable[..., bool] = lambda *a: False
  """
Validation check to see if a folder contains a valid installation.
Used by the launcher to decide if a version is 'Local' (Run) or 'Online' (Download).

Args:
  path (str): path to check
  settings (launcher.SettingsData): The current settings object containing user-defined flags

Returns:
  bool: return true if the path has a game in it
"""
  addCustomNodes: Callable[..., None] = lambda *a: None
  """
Injects custom UI elements into the 'Local Settings' section of the Launcher.

Args:
  _self: Reference to the Launcher instance to use its helper methods (newCheckbox, etc.)
  layout: The layout where these widgets will be added.
"""
  WINDOW_TITLE: str = "No Window Title Has Been Set"
  """what to set the launchers title to"""
  SHOULD_USE_HARD_LINKS: bool = False
  """will set default state of setting replaceDuplicateGameFilesWithHardlinks which if true will scan all new version downloads and check to see if object files are the same between different versions and replace the new files with hardlinks instead"""
  CAN_USE_CENTRAL_GAME_DATA_FOLDER: bool = False
  """if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location"""
  configs: dict[str, Config] | None = None # pyright: ignore[reportUndefinedVariable]
  """if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location"""
  hadErrorLoading: bool = False
  errorText: str = ""


class f:
  @staticmethod
  def read(
    file: int | str | bytes | os.PathLike[str] | os.PathLike[bytes],
    default: str = "",
    asbinary: bool = False,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
  ):
    if os.path.exists(file):
      with open(
        file,
        "r" + ("b" if asbinary else ""),
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
      ) as f:
        text: str | bytes | None = f.read() # pyright: ignore[reportAny]
      if text:
        return text
      return default
    else:
      with open(
        file,
        "w" + ("b" if asbinary else ""),
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
      ) as f:
        _ = f.write(default)
      return default

  @staticmethod
  def write(
    file: int | str | bytes | os.PathLike[str] | os.PathLike[bytes],
    text: str | bytes,
    asbinary: bool = False,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
  ) -> str | bytes:
    with open(
      file,
      "w" + ("b" if asbinary else ""),
      buffering=buffering,
      encoding=encoding,
      errors=errors,
      newline=newline,
      closefd=closefd,
      opener=opener,
    ) as f:
      _ = f.write(text)
    return text


class AssetDownloadThread(QThread):
  progress: Signal = Signal(int)
  onfinished: Signal = Signal(str)
  error: Signal = Signal(str)

  def __init__(self, url: str, dest: str) -> None:
    super().__init__()
    self.url: str = url
    self.dest: str = dest

  @override
  def run(self) -> None:
    try:
      with requests.get(self.url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0

        with open(self.dest, "wb") as f:
          for chunk in cast(Iterator[bytes], r.iter_content(chunk_size=8192)):
            if chunk:
              _ = f.write(chunk)
              downloaded += len(chunk)
              if total:
                percent = int(downloaded / total * 100)
                self.progress.emit(percent)

      self.onfinished.emit(self.dest)
    except Exception as e:
      self.error.emit(str(e))


from typing import TypeVar, Generic

T = TypeVar("T")


class Cache(Generic[T]):
  lastinp: object = None

  def __init__(self) -> None:
    self.cache: dict[object, T] = {}

  def has(self, item: object) -> bool:
    self.lastinp = item
    return item in self.cache

  def get(self) -> T:
    if not self.has(self.lastinp):
      raise KeyError(f"No such item {self.lastinp}")
    thing = self.cache[self.lastinp]
    del self.lastinp
    return thing

  def set(self, value: T) -> T:
    self.cache[self.lastinp] = value
    del self.lastinp
    return value

  def clear(self) -> None:
    self.cache = {}


iconCache: Cache[QPixmap] = Cache[QPixmap]()
from PySide6.QtGui import QPaintEvent
from PySide6.QtCore import QPointF


class VersionItemWidget(QWidget):
  class ProgressTypes(Enum):
    leftToRight = 0
    both = 1
    rightToLeft = 2

  def __init__(
    self,
    text: str = "",
    color: Qt.GlobalColor = MISSING_COLOR,
    image_source: str | None = None,
  ):
    super().__init__()
    self.text: str = text
    self.progress: float = 0
    self.setModeUnknownEnd()
    self.startTime: float = 0
    self.animSpeed: float = 10
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    self.setStyleSheet("background: transparent; border: none;")
    self.image_label: QLabel = QLabel()
    self.image_label.setFixedSize(50, 50) # Set a standard thumbnail size
    self.label: QLabel = QLabel(text)
    color_hex: Literal[
      "color0",
      "color1",
      "black",
      "white",
      "darkGray",
      "gray",
      "lightGray",
      "red",
      "green",
      "blue",
      "cyan",
      "magenta",
      "yellow",
      "darkRed",
      "darkGreen",
      "darkBlue",
      "darkCyan",
      "darkMagenta",
      "darkYellow",
      "transparent",
    ] = color.name
    self.label.setStyleSheet(f"background: transparent; color: {color_hex};")

    self.qblayout: QHBoxLayout = QHBoxLayout(self)
    self.icon_label: QLabel = QLabel()
    self.icon_label.setFixedSize(32, 32) # Standard thumbnail size
    self.icon_label.setScaledContents(True)
    self.icon_label.hide()
    self.qblayout.addWidget(self.icon_label)
    self.qblayout.setContentsMargins(5, 0, 5, 0)
    self.qblayout.addWidget(self.label)
    self.qblayout.addStretch()
    self.setIcon(image_source)

  def setIcon(self, image_source: str | None) -> None:
    if not image_source:
      self.icon_label.clear()
      return
    self.icon_label.setScaledContents(True)
    image_source = os.path.abspath(image_source)
    pixmap: QPixmap = (
      iconCache.get()
      if iconCache.has(image_source)
      else iconCache.set(QPixmap(image_source))
    )
    if not pixmap.isNull():
      self.icon_label.show()
      self.icon_label.setPixmap(
        pixmap.scaled(
          self.icon_label.size(),
          Qt.AspectRatioMode.KeepAspectRatio,
          Qt.TransformationMode.SmoothTransformation,
        )
      )
      self.updateGeometry()
      self.icon_label.updateGeometry()
    else:
      self.icon_label.setText("N/A")

  def setModeKnownEnd(self) -> None:
    flag = self.noKnownEndPoint
    self.progressColor: tuple[int, int, int] = MAIN_LOADING_COLOR
    self.progressType: VersionItemWidget.ProgressTypes = (
      VersionItemWidget.ProgressTypes.leftToRight
    )
    self.noKnownEndPoint: bool = False
    if flag:
      self.progress = 0
      self.update()

  def setModeUnknownEnd(self) -> None:
    self.progressColor = UNKNOWN_TIME_LOADING_COLOR
    self.progressType = VersionItemWidget.ProgressTypes.both
    self.noKnownEndPoint = True
    self.startTime = time.time()
    self.update()

  def setModeDisabled(self) -> None:
    self.noKnownEndPoint = False
    self.progress = 101
    self.update()

  def setLabelColor(self, color: Qt.GlobalColor) -> None:
    self.label.setStyleSheet(f"background: transparent; color: {color.name};")

  def setProgress(self, percent: float) -> None:
    if percent == self.progress:
      return
    if self.noKnownEndPoint:
      self.noKnownEndPoint = False
      self.setModeKnownEnd()
    self.progress = percent
    self.update()

  @override
  def paintEvent(self, event: QPaintEvent) -> None:
    if not ((0 < self.progress <= 100) or self.noKnownEndPoint):
      super().paintEvent(event)
      return

    painter: QPainter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect: QRect = self.rect()
    w: int = rect.width()
    h: int = rect.height()
    gradSize: int = int(w / 8)
    minGradAlpha = 50
    if self.noKnownEndPoint:
      self.progress = int(((time.time() - self.startTime) * self.animSpeed) % 100)
      QTimer.singleShot(16, self.update)

    if self.progressType == self.ProgressTypes.both:
      fill_end: float = (
        w * self.progress / 100
      ) # pyright: ignore[reportRedeclaration]
      solid_rect: QRectF = QRectF(
        0, 0, max(0, fill_end - gradSize), h
      ) # pyright: ignore[reportRedeclaration]
      tip_rect: QRectF = QRectF(
        solid_rect.right(), 0, int(min(gradSize, fill_end)), h
      ) # pyright: ignore[reportRedeclaration]
      self._drawProgress(painter, solid_rect, minGradAlpha)
      self._drawGradient(
        painter,
        tip_rect,
        tip_rect.topLeft(),
        tip_rect.topRight(),
        minGradAlpha,
      )
      fill_start = w - (w * (100 - self.progress) / 100)
      solid_rect = QRectF(
        int(fill_start + gradSize), 0, w - int(fill_start + gradSize), h
      )
      tip_rect = QRectF(
        int(max(fill_start, 0)), 0, int(min(gradSize, w - fill_start)), h
      )
      self._drawProgress(painter, solid_rect, minGradAlpha)
      self._drawGradient(
        painter,
        tip_rect,
        tip_rect.topRight(),
        tip_rect.topLeft(),
        minGradAlpha,
      )

    elif self.progressType == self.ProgressTypes.leftToRight:
      fill_end: float = w * self.progress / 100
      solid_rect: QRectF = QRectF(0, 0, max(0, fill_end - gradSize), h)
      tip_rect: QRectF = QRectF(solid_rect.right(), 0, min(gradSize, fill_end), h)
      self._drawProgress(painter, solid_rect, minGradAlpha)
      self._drawGradient(
        painter,
        tip_rect,
        tip_rect.topLeft(),
        tip_rect.topRight(),
        minGradAlpha,
      )

    elif self.progressType == self.ProgressTypes.rightToLeft:
      fill_start = w - (w * self.progress / 100)
      solid_rect = QRectF(
        fill_start + gradSize, 0, w - (fill_start + gradSize), h
      )
      tip_rect = QRectF(max(fill_start, 0), 0, min(gradSize, w - fill_start), h)
      self._drawProgress(painter, solid_rect, minGradAlpha)
      self._drawGradient(
        painter,
        tip_rect,
        tip_rect.topRight(),
        tip_rect.topLeft(),
        minGradAlpha,
      )

    super().paintEvent(event)

  def _drawProgress(self, painter: QPainter, rect: QRectF, alpha: int):
    if rect.width() <= 0:
      return
    painter.fillRect(rect, QColor(*self.progressColor, alpha))

  def _drawGradient(
    self,
    painter: QPainter,
    rect: QRectF,
    start_pt: QPointF,
    end_pt: QPointF,
    min_alpha: int,
  ):
    if rect.width() <= 0:
      return
    grad = QLinearGradient(start_pt, end_pt)
    exponent = 5
    for i in range(11):
      pos = i / 10.0
      alpha = int(min_alpha + (255 - min_alpha) * math.pow(pos, exponent))
      grad.setColorAt(pos, QColor(*self.progressColor, alpha))
    painter.fillRect(rect, grad)


os.makedirs(os.path.join(APP_DATA_PATH, "launcherData"), exist_ok=True)
os.makedirs(os.path.join(APP_DATA_PATH, "images"), exist_ok=True)
from PySide6.QtCore import QByteArray


class SettingsData:
  """A container for dot-notation access to settings."""

  def __getattr__(self, name: str) -> object:
    print("WARNING: ", name, "was not set")
    return None


from PySide6.QtCore import QPoint
class Launcher(QWidget):
  def updateLauncher(self) -> None:
    import subprocess
    import os
    import sys

    # Set the repository URL and the local directory where the script is located
    repo_url = "https://github.com/rsa17826/multi-game-launcher.git"
    local_dir: str = os.path.join(
      os.path.dirname(os.path.abspath(__file__)), "../.."
    )

    # Check if the directory is a valid Git repository
    def is_git_repo(path: str) -> bool:
      return os.path.isdir(os.path.join(path, ".git"))

    # Initialize the Git repository if not already initialized
    def init_git_repo(path: str, url: str) -> None:
      try:
        print(f"Initializing new Git repository in {path}...")
        # Run git init to initialize the repo
        _ = subprocess.check_call(["git", "init"], cwd=path)
        # Add the remote repository URL
        _ = subprocess.check_call(
          ["git", "remote", "add", "origin", url], cwd=path
        )
        _ = subprocess.check_call(["git", "add", "-A"], cwd=path)
        _ = subprocess.check_call(["git", "fetch", "origin"], cwd=local_dir)
        print("Git repository initialized and remote set.")
      except subprocess.CalledProcessError as e:
        print("Error initializing repository:", e)
        sys.exit(1)

    if not is_git_repo(local_dir):
      print("No .git directory found. Initializing repository...")
      init_git_repo(local_dir, repo_url)

    try:
      print("Checking for updates...")
      _ = subprocess.check_call(
        ["git", "reset", "--hard", "origin/main"], cwd=local_dir
      )
      result: CompletedProcess[str] = subprocess.run(
        ["git", "pull", "--force", "origin", "main"],
        cwd=local_dir,
        capture_output=True,
        text=True,
      )

      if "Already up to date." in result.stdout:
        print("No updates found. The repository is already up to date.")
      else:
        print("Update successful!")
        self.showRestartPrompt("Launcher updated successfully.")
    except subprocess.CalledProcessError as e:
      print("Error during update:", e)

  def addVersionItem(
    self,
    version: str,
    status: Statuses,
    path: str | None = None,
    release: ReleaseType | None = None, # , image_path:str|None=None
  ) -> None:
    item: QListWidgetItem = QListWidgetItem()

    widget: VersionItemWidget = VersionItemWidget("", MISSING_COLOR)
    widget.setModeKnownEnd()

    item.setSizeHint(widget.sizeHint())
    self.listWidget.addItem(item)
    self.listWidget.setItemWidget(item, widget)

    item.setData(
      Qt.ItemDataRole.UserRole,
      listData(
        version=version,
        status=status,
        path=path,
        release=release,
      ),
    )

  def saveUserSettings(self) -> None:
    local_data: dict[str, object] = {}
    global_data: dict[str, object] = {}

    for key, widget in cast(dict[str, QWidget], self.widgetsToSave).items():
      if isinstance(widget, QLineEdit):
        value = widget.text()
      elif isinstance(widget, QCheckBox):
        value = widget.isChecked()
      elif isinstance(widget, QSpinBox):
        value = widget.value()
      elif isinstance(widget, EnumComboBox):
        value = widget.currentData()
        if widget.usesEnum: # type: ignore
          value = value.value
      else:
        continue

      if key in self.localKeys:
        local_data[key] = value
      else:
        global_data[key] = value

    try:
      # if self.GAME_ID != "-":
      with open(self.LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(local_data, f, indent=2)
      with open(self.GLOBAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(global_data, f, indent=2)
    except Exception as e:
      print(f"Failed to save settings: {e}")

  def loadUserSettings(self) -> None:
    local_data: dict[str, object] = {}
    global_data: dict[str, object] = {}

    try:
      defaultLocalSettingsFile: str = os.path.join(
        APP_DATA_PATH,
        "-",
        "launcherData/launcherSettings.json",
      )
      os.makedirs(os.path.join(APP_DATA_PATH, "-", "launcherData"), exist_ok=True)
      if os.path.exists(defaultLocalSettingsFile):
        with open(defaultLocalSettingsFile, "r", encoding="utf-8") as f:
          local_data = cast(dict[str, object], json.load(f))
      if os.path.exists(self.LOCAL_SETTINGS_FILE):
        with open(self.LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
          for k, v in cast(dict[str, object], json.load(f)).items():
            local_data[k] = v
      if os.path.exists(self.GLOBAL_SETTINGS_FILE):
        with open(self.GLOBAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
          global_data = cast(dict[str, object], json.load(f))
    except Exception as e:
      print(f"Failed to load settings: {e}")

    combined: dict[str, object] = {**global_data, **local_data}

    for key, value in combined.items():
      widget: QWidget | None = self.widgetsToSave.get(key)
      try:
        if widget:
          if isinstance(widget, QLineEdit):
            widget.setText(str(value))
          elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
          elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
          elif isinstance(widget, QComboBox):
            # don't error when node has only one index - might be useful
            try:
              # try to make sure that the change event is sent as setCurrentIndex donesnt send it if current index is same
              idx: int = widget.currentIndex()
              if idx == value:
                widget.setCurrentIndex(1 if idx == 0 else 0)
            except:
              pass
            widget.setCurrentIndex(value)
      except Exception as e:
        print("error loading value for ", key, e)

  @override
  def closeEvent(self, event: QCloseEvent) -> None:
    self.saveUserSettings()
    super().closeEvent(event)

  downloadingVersions: list[str] = []

  def getFileHash(self, path: str) -> str | None:
    """Calculate SHA256 hash of a file in chunks to save memory."""
    hasher: HASH = hashlib.sha256()
    try:
      with open(path, "rb") as f:
        while chunk := f.read(8192):
          hasher.update(chunk)
      return hasher.hexdigest()
    except Exception:
      return None

  def deduplicateWithHardlinks(self, new_version_dir: str) -> None:
    if not (
      self.config.SHOULD_USE_HARD_LINKS
      and self.settings.replaceDuplicateGameFilesWithHardlinks
    ):
      return

    file_map: dict[tuple[int, str], list[str]] = {}

    for root, _dirs, files in os.walk(self.VERSIONS_DIR):

      if os.path.abspath(root).startswith(os.path.abspath(new_version_dir)):
        continue

      for filename in files:
        full_path: str = os.path.join(root, filename)
        try:
          stat: stat_result = os.stat(full_path)

          if stat.st_nlink > 1 and (stat.st_size, filename) in file_map:
            continue
          if (stat.st_size, filename) not in file_map:
            file_map[(stat.st_size, filename)] = []
          file_map[(stat.st_size, filename)].append(full_path)
        except OSError:
          continue

    for root, _dirs, files in os.walk(new_version_dir):
      for filename in files:
        new_file_path: str = os.path.join(root, filename)
        try:
          new_stat: stat_result = os.stat(new_file_path)
          if new_stat.st_nlink > 1:
            continue
          candidates: list[str] | None = file_map.get(
            (new_stat.st_size, filename)
          )
          if candidates is not None:
            for candidate in candidates:
              if os.path.abspath(new_file_path) == os.path.abspath(
                candidate
              ):
                continue
              if self.getFileHash(new_file_path) == self.getFileHash(
                candidate
              ):
                print(f"Hardlinking: {filename} -> {candidate}")
                os.remove(new_file_path)
                os.link(candidate, new_file_path)
        except Exception as e:
          print(f"Error processing {filename}: {e}")

  def onVersionDoubleClicked(self, item: QListWidgetItem) -> None:
    data: listData | None = cast(
      listData | None, item.data(Qt.ItemDataRole.UserRole)
    )
    if not data:
      return
    match data.status:
      case Statuses.gameSelector:
        assert data.release is not None
        run(cast(Config, data.release["config"]), data.version)
        _ = self.close()
        return
      case Statuses.local | Statuses.localOnly:
        path: str | None = data.path
        if path:
          self.startGameVersion(data)
        return
      case Statuses.online:
        self.startQueuedDownloadRequest(data)
      case Statuses.loadingInfo:
        pass

  def startGameVersion(self, data: listData) -> None:
    args: list[str] = (
      sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )

    gdl = self.getGameDataLocation(data.version)
    _ = f.write(
      os.path.join(
        (APP_DATA_PATH),
        self.GAME_ID,
        "launcherData/lastRanVersion.txt",
      ),
      data.version,
    )
    self.config.gameLaunchRequested(
      data.path,
      shlex.split(cast(str, self.settings.extraGameArgs)) + args,
      self.settings,
      self.settings.selectedOs,
      gdl,
    )
    if self.settings.closeOnLaunch:
      QApplication.quit()

  def getGameDataLocation(self, version: str | None = None) -> str:
    usesCentralGameDataLocation: bool = (
      self.config.CAN_USE_CENTRAL_GAME_DATA_FOLDER
      and self.settings.useCentralGameDataFolder
    )
    gdl: str = os.path.join( # pyright: ignore[reportRedeclaration]
      (APP_DATA_PATH),
      self.GAME_ID,
      "gameData",
    )
    if not usesCentralGameDataLocation and version:
      gdl: str = os.path.join(gdl, str(version))
    os.makedirs(gdl, exist_ok=True)
    return gdl

  def startQueuedDownloadRequest(self, *versions: listData) -> None:
    for data in versions:
      tag: str = data.version
      if tag in self.downloadingVersions:
        return

      self.downloadingVersions.append(tag)
      release: ReleaseType | None = data.release
      assert release is not None
      asset: Any | None = next(
        (
          a
          for a in release.get("assets", [])
          if a["name"]
          == self.config.getAssetName(self.settings, self.settings.selectedOs)
        ),
        None,
      )

      if not asset:
        print(f"Asset Not Found for {tag}")
        self.downloadingVersions.remove(tag)
        return

      dest_dir: str = os.path.join(self.VERSIONS_DIR, tag)
      out_file: str = os.path.join(dest_dir, asset["name"])

      widget: Any = self.activeItemRefs[data.version]
      assert isinstance(widget, VersionItemWidget)
      widget.setModeUnknownEnd()

      self.downloadQueue.append(
        (
          tag,
          asset["browser_download_url"],
          out_file,
          dest_dir,
        )
      )
    self.processDownloadQueue()

  def processDownloadQueue(self) -> None:
    assert isinstance(self.settings.maxConcurrentDls, int)
    while self.downloadQueue and (
      len(self.activeDownloads) < self.settings.maxConcurrentDls
      or self.settings.maxConcurrentDls == 0
    ):
      next_dl = self.downloadQueue.pop(0)
      self.startActualDownload(*next_dl)
    print(self.downloadingVersions)
    self.populateList()

  def startActualDownload(
    self, tag: str, url: str, out_file: str, dest_dir: str
  ) -> None:
    print(url, tag)
    os.makedirs(dest_dir, exist_ok=True)

    dl_thread: AssetDownloadThread = AssetDownloadThread(url, out_file)

    self.activeDownloads[tag] = dl_thread

    def onFinished(path: str) -> None:
      self.processDownloadQueue()
      current_widget: QWidget | None = self.activeItemRefs.get(tag)
      assert isinstance(current_widget, VersionItemWidget)
      current_widget.label.setText(f"Extracting {tag}...")
      current_widget.setModeUnknownEnd()

      extracted = False
      try:
        if path.endswith(".zip"):
          with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
          os.remove(path)
          extracted = True
        elif path.endswith(".7z"):
          with py7zr.SevenZipFile(path, mode="r") as archive:
            archive.extractall(path=dest_dir)
          os.remove(path)
          extracted = True

        if extracted and self.config.SHOULD_USE_HARD_LINKS:
          self.deduplicateWithHardlinks(dest_dir)
      except Exception as e:
        print(f"Extraction Error For {tag}: {e}")

      if tag in self.downloadingVersions:
        self.downloadingVersions.remove(tag)

      if extracted:
        print(f"Finished Processing {tag}")
        self.activeDownloads.pop(tag, None)
        assert isinstance(current_widget, VersionItemWidget)
        self.processDownloadQueue()
      else:
        self.activeDownloads.pop(tag, None)
      self.config.onGameVersionDownloadComplete(path, tag)
      if VERSION and VERSION == tag:
        self.startGameVersion(
          listData(
            path=dest_dir, status=Statuses.local, version=tag, release={}
          )
        )

    _ = dl_thread.progress.connect(bind[None](self.handleDownloadProgress, tag))
    _ = dl_thread.onfinished.connect(onFinished)
    _ = dl_thread.error.connect(
      lambda e: print(f"DL Error {tag}: {e}")
    ) # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    _ = dl_thread.onfinished.connect(dl_thread.deleteLater)

    dl_thread.start()

  def handleDownloadProgress(self, version_tag: str, percentage: int) -> None:
    widget: str | None = self.activeItemRefs.get(version_tag)
    assert isinstance(widget, VersionItemWidget)
    widget.setProgress(percentage)
    widget.label.setText(f"Downloading {version_tag}... ({percentage}%)")

  def populateList(self) -> None:
    if not self.listWidget:
      return
    if self.GAME_ID != "-":
      try:
        _ = f.write(
          os.path.join(
            (APP_DATA_PATH),
            self.GAME_ID,
            "launcherData/cache/releases.json",
          ),
          json.dumps(self.foundReleases),
        )
      except Exception as e:
        print("failed to save cached data", e)
    all_items_data: list[listData] = []
    local_versions: set[Any] = set[Any]()
    if self.config.configs:
      for rel in self.foundReleases:
        version = rel.get("tag_name")
        if version and version not in local_versions:
          all_items_data.append(
            listData(
              version=version,
              status=Statuses.gameSelector,
              path=rel.get("path"),
              release=rel,
            )
          )
    else:
      version_map: dict[Any, Any] = {}
      if os.path.isdir(self.VERSIONS_DIR):
        for dirname in os.listdir(self.VERSIONS_DIR):
          full_path = os.path.join(self.VERSIONS_DIR, dirname)
          if os.path.isdir(full_path) and self.config.gameVersionExists(
            full_path, self.settings, self.settings.selectedOs
          ):
            thing: listData = listData(
              version=dirname,
              status=Statuses.localOnly,
              path=full_path,
              release=None,
            )
            all_items_data.append(thing)
            version_map[dirname] = thing
            local_versions.add(dirname)
      for rel in self.foundReleases:
        version: str | None = rel.get("tag_name")
        if version:
          if version in version_map:
            version_map[version].status = Statuses.local
            version_map[version].release = rel
          else:
            all_items_data.append(
              listData(
                version=version,
                status=Statuses.online,
                path=None,
                release=rel,
              )
            )

    sorted_data: list[Any] = self.sortVersions(all_items_data)
    self.listWidget.setUpdatesEnabled(False)
    self.listWidget.blockSignals(True)
    try:
      self.activeItemRefs.clear()
      current_count: Any = self.listWidget.count()
      target_count: int = len(sorted_data)
      if current_count < target_count:
        for _ in range(target_count - current_count):
          self.addVersionItem(version="loading", status=Statuses.loadingInfo)
      elif current_count > target_count:
        for _ in range(current_count - target_count):
          self.listWidget.takeItem(self.listWidget.count() - 1)

      if self.gameName is not None:
        if os.path.isfile(
          os.path.join(APP_DATA_PATH, "images/" + self.gameName + ".png")
        ):
          self.setWindowIcon(
            QIcon(
              os.path.join(
                APP_DATA_PATH, "images/" + self.gameName + ".png"
              )
            )
          )
      for i, data in enumerate(sorted_data):
        assert isinstance(data, listData)
        item: QListWidgetItem = self.listWidget.item(i)

        widget: QWidget = self.listWidget.itemWidget(item)
        self.activeItemRefs[data.version] = widget
        assert isinstance(widget, VersionItemWidget)
        if self.settings.showLauncherImages:
          # if data.status == Statuses.gameSelector:
          #   assert data.release is not None
          #   widget.setIcon(data.release["config"].getImage(data.version))
          # else:
          #   widget.setIcon(self.config.getImage(data.version))
          imagePath: None = None
          if data.status == Statuses.gameSelector:
            assert data.release is not None
            imagePath: None = os.path.join(
              APP_DATA_PATH, "images/" + data.version + ".png"
            )
            print(imagePath)
          widget.setIcon(imagePath)
        else:
          widget.setIcon(None)
        item.setSizeHint(widget.sizeHint())
        if data.version in self.downloadingVersions:
          if not widget.noKnownEndPoint:
            widget.setModeUnknownEnd()
          widget.label.setText(f"Waiting To Download: {data.version}")
        else:
          widget.setModeDisabled()
          match data.status:
            case Statuses.gameSelector:
              assert self.config.configs is not None
              if self.config.configs[data.version].hadErrorLoading:
                widget.label.setText(
                  f"ERROR: Error Loading {data.version} Launcher"
                )
                widget.label.setToolTip(
                  self.config.configs[data.version].errorText
                )
              else:
                widget.label.setText(f"Start {data.version} Launcher")
            case Statuses.local | Statuses.localOnly:
              widget.label.setText(f"Run version {data.version}")
            case Statuses.online:
              widget.label.setText(f"Download version {data.version}")
        match data.status:
          case Statuses.local:
            new_color = LOCAL_COLOR
          case Statuses.localOnly:
            new_color = LOCAL_ONLY_COLOR
          case Statuses.online:
            new_color = ONLINE_COLOR
          case Statuses.gameSelector:
            assert self.config.configs is not None
            if self.config.configs[data.version].hadErrorLoading:
              new_color = ERROR_COLOR
            else:
              new_color = LOCAL_COLOR
          case _:
            new_color = MISSING_COLOR
        widget.setLabelColor(new_color)
        item.setData(Qt.ItemDataRole.UserRole, data)
    except Exception as e:
      print(f"Update Error: {e}")
    self.listWidget.blockSignals(False)
    self.listWidget.setUpdatesEnabled(True)

  def loadLocalVersions(self):
    self.listWidget.clear()

    if not os.path.isdir(self.VERSIONS_DIR):
      return

    for dirname in sorted(os.listdir(self.VERSIONS_DIR), reverse=True):
      full_path = os.path.join(self.VERSIONS_DIR, dirname)
      if not os.path.isdir(full_path):
        continue

      if not self.config.gameVersionExists(
        full_path, self.settings, self.settings.selectedOs
      ):
        continue

      self.addVersionItem(
        version=dirname, status=Statuses.localOnly, path=full_path
      )

  def sortVersions(self, versions_data) -> Any:
    versionThatWasLastRan: None = None
    if self.GAME_ID != "-":
      try:
        versionThatWasLastRan: None = f.read(
          os.path.join(
            APP_DATA_PATH,
            self.GAME_ID,
            "launcherData/lastRanVersion.txt",
          )
        ).strip()
      except Exception as e:
        print("failed reading lastRanVersion", e)

    def getSortKey(
      item,
    ) -> tuple[
      Literal[1, 0], Literal[1, 0], Literal[1, 0], Literal[1, 0], int | Any
    ]:
      version = item.version
      status = item.status

      isLocalOnly: Literal[1, 0] = 1 if status == Statuses.localOnly else 0
      # isNotDownloaded = 1 if status == Statuses.online else 0

      isLastRanVersion: Literal[1, 0] = (
        1
        if version == versionThatWasLastRan
        and (status == Statuses.local or status == Statuses.localOnly)
        else 0
      )

      version_is_numeric: Literal[1, 0] = (
        1 if re.match(r"^-?\d+$", version) else 0
      )
      numeric_value: int = int(version) if version_is_numeric else 0

      return (
        isLastRanVersion,
        (1 if (version in self.downloadingVersions) else 0),
        isLocalOnly,
        # isNotDownloaded if self.settings.sortByDownloadState else 0,
        version_is_numeric,
        numeric_value if version_is_numeric else version,
      )

    versions_data.sort(key=getSortKey, reverse=True)

    return versions_data

  def downloadAllVersions(self) -> None:
    onlineCount = 0
    items: list[Any] = []
    for i in range(self.listWidget.count()):
      item: Any = self.listWidget.item(i)
      data: listData = item.data(Qt.ItemDataRole.UserRole)
      if data and data.status == Statuses.online:
        version: Any | str = data.version
        if version not in self.downloadingVersions:
          items.append(item.data(Qt.ItemDataRole.UserRole))
          onlineCount += 1
    self.startQueuedDownloadRequest(*items)

    if onlineCount > 0:
      print(f"Added {onlineCount} Versions to the Download Queue.")
    else:
      print("No New Online Versions Found to Download.")

  class ReleaseFetchThread(QThread):
    progress: Signal = Signal(int, int, list)
    onfinished: Signal = Signal(list)
    error: Signal = Signal(str)

    def __init__(self, API_URL, pat=None, max_pages=1) -> None:
      super().__init__()
      self.pat: Any | None = pat
      self.maxPages = max_pages
      self.API_URL = API_URL

    def run(self) -> None:
      if OFFLINE:
        self.onfinished.emit([])
        return
      try:
        releases: list[Any] = []
        headers: dict[str, str] = (
          {"Authorization": f"token {self.pat}"} if self.pat else {}
        )
        page = 0
        if self.maxPages == 0:
          rand: float = random.random()
          final_size = -1

          head: Response = requests.head(
            f"{self.API_URL}?page=0&rand={rand}",
            headers=headers,
            timeout=10,
          )
          if "Link" in head.headers:
            m: Match[str] | None = re.search(
              r'\?page=(\d+)&rand=[\d.]+>; rel="last"',
              head.headers["Link"],
            )
            if m:
              final_size: int = int(m.group(1)) + 1

        while True:
          page += 1

          if self.maxPages > 0 and page > self.maxPages:
            break

          r: Response = requests.get(
            f"{self.API_URL}?page={page}", headers=headers, timeout=30
          )
          if r.status_code != 200:
            break
          data = r.json()
          if not data:
            break

          releases.extend(data)
          self.progress.emit(
            page,
            (self.maxPages) if self.maxPages > 0 else final_size,
            releases,
          )

        self.onfinished.emit(releases)
      except Exception as e:
        self.error.emit(str(e))

  def goBackToSelector(self) -> None:
    if selectorConfig:
      # Re-run using the saved selector configuration
      run(selectorConfig, None)
      # Close the current game-specific launcher
      _ = self.close()

  def __init__(self, config: Config, module_name: str | None) -> None:
    global launcherUpdateAlreadyChecked
    super().__init__()
    self.gameName: str | None = module_name
    self.releaseFetchingThread: Launcher.ReleaseFetchThread | None = None
    self.config: Config = config
    self.settings: SettingsData = SettingsData()
    self.activeItemRefs: dict[str, VersionItemWidget] = {}
    self.activeDownloads: dict[str, AssetDownloadThread] = {}
    self.downloadQueue: list[tuple[str, str, str, str]] = []
    self.setWindowTitle(config.WINDOW_TITLE)
    self.setFixedSize(420, 600)
    self.setStyleSheet(
      cast(str, f.read(os.path.join(LAUNCHER_START_PATH, "main.css")))
    )
    self.GAME_ID: str = re.sub(
      r"_{2,}",
      "_",
      re.sub(
        r"[^\w\- ]", "_", f"{self.config.GH_USERNAME} - {self.config.GH_REPO}"
      ),
    ).strip()
    self.VERSIONS_DIR: str = os.path.join(
      APP_DATA_PATH,
      self.GAME_ID,
      "versions",
    )
    self.GLOBAL_SETTINGS_FILE: str = os.path.join(
      APP_DATA_PATH, "launcherData/launcherSettings.json"
    )
    self.LOCAL_SETTINGS_FILE: str = os.path.join(
      APP_DATA_PATH,
      self.GAME_ID,
      "launcherData/launcherSettings.json",
    )

    main_layout: QVBoxLayout = QVBoxLayout(self)
    if selectorConfig and selectorConfig != self.config:
      back_btn: QPushButton = self.newButton(
        "<- Back to Selector", self.goBackToSelector
      )
      # Style it differently if you want (optional)
      main_layout.addWidget(back_btn)
    self.listWidget: QListWidget = QListWidget()
    self.listWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    _ = self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
    main_layout.addWidget(self.listWidget)
    if OFFLINE:
      offline_label = QLabel("OFFLINE MODE")
      offline_label.setStyleSheet("color: orange; font-weight: bold;")
      main_layout.addWidget(offline_label)

    _ = self.listWidget.itemDoubleClicked.connect(self.onVersionDoubleClicked)

    main_layout.addWidget(self.listWidget)

    self.widgetsToSave: dict[Any, Any] = {}

    self.mainProgressBar: VersionItemWidget = VersionItemWidget("", MISSING_COLOR)
    main_layout.addWidget(self.mainProgressBar)

    self.setupSettingsDialog()
    self.loadUserSettings()
    self.loadLocalVersions()

    main_layout.addWidget(self.newButton("Settings", self.openSettings))
    if DOWNLOAD_LAUNCHER:
      assert isinstance(DOWNLOAD_LAUNCHER, str)
      sd: SettingsData = SettingsData()
      sd.LAUNCHER_GH_USERNAME = DOWNLOAD_LAUNCHER[1] # type: ignore # pyright: ignore[reportAttributeAccessIssue]
      sd.LAUNCHER_GH_REPO = DOWNLOAD_LAUNCHER[2] # type: ignore # pyright: ignore[reportAttributeAccessIssue]
      sd.LAUNCHER_ASSET_NAME = DOWNLOAD_LAUNCHER[3] # type: ignore # pyright: ignore[reportAttributeAccessIssue]
      self.updateSubLauncher(
        sd, # type: ignore
        listData(
          path=os.path.join(
            APP_DATA_PATH,
            DOWNLOAD_LAUNCHER[0] + ".py",
          ),
          release=None,
          status=Statuses.gameSelector,
          version=DOWNLOAD_LAUNCHER[0],
        ),
        self.mainProgressBar,
      )
      print(DOWNLOAD_LAUNCHER, "DOWNLOAD_LAUNCHER")

    if self.config.configs is not None:
      self.VERSIONS_DIR = "///" # pyright: ignore[reportConstantRedefinition]
      self.foundReleases: list[dict[str, Any]] = list[dict[str, Any]](
        map[dict[str, Any]](
          lambda x: {"tag_name": x, "config": config.configs[x], "path": paths[x]}, config.configs # type: ignore
        )
      )
      self.populateList()
      self.mainProgressBar.setModeDisabled()
      if not OFFLINE:
        if self.settings.checkForLauncherUpdatesWhenOpening:
          if not launcherUpdateAlreadyChecked:
            self.updateLauncher()
          launcherUpdateAlreadyChecked = True
      return
    self.API_URL: str = (
      f"https://api.github.com/repos/{self.config.GH_USERNAME}/{self.config.GH_REPO}/releases"
    )
    os.makedirs(
      os.path.join(
        APP_DATA_PATH,
        self.GAME_ID,
        "launcherData/cache",
      ),
      exist_ok=True,
    )
    self.foundReleases = json.loads(
      f.read(
        os.path.join(
          (APP_DATA_PATH),
          self.GAME_ID,
          "launcherData/cache/releases.json",
        ),
        "[]",
      )
    )
    self.populateList()
    if not OFFLINE:
      if self.settings.checkForLauncherUpdatesWhenOpening:
        if not launcherUpdateAlreadyChecked:
          self.updateLauncher()
        launcherUpdateAlreadyChecked = True
    if not OFFLINE and self.settings.fetchOnLoad:
      self.startFetch(max_pages=self.settings.maxPagesOnLoad)
      self.releaseFetchingThread.error.connect(
        lambda e: print("Release fetch error:", e)
      )
      self.releaseFetchingThread.start()
      self.mainProgressBar.show()
    else:
      self.mainProgressBar.setModeDisabled()
    if self.gameName and VERSION:
      for i in range(self.listWidget.count()):
        item: Any = self.listWidget.item(i)
        data: listData = item.data(Qt.ItemDataRole.UserRole)
        if not data:
          continue
        if data.version == VERSION:
          if data.status == Statuses.online:
            if data.version not in self.downloadingVersions:
              self.startQueuedDownloadRequest(data)
          if (
            data.status == Statuses.local
            or data.status == Statuses.localOnly
          ):
            self.startGameVersion(data)

  def openSettings(self) -> None:
    result: int = self.settingsDialog.exec()
    if result == QDialog.DialogCode.Accepted:
      print("Saving settings...")
      self.saveUserSettings()
      self.populateList()
    else:
      print("Changes discarded. Reverting UI...")
      self.loadUserSettings()

  def showContextMenu(self, pos:QPoint) -> None:
    item: Any = self.listWidget.itemAt(pos)
    if not item:
      return

    data: listData = item.data(Qt.ItemDataRole.UserRole)
    menu: QMenu = QMenu(self)

    def newAction(text: str, onclick: Callable) -> None:
      run_action: QAction = menu.addAction(text)
      run_action.triggered.connect(onclick)

    print(data.status)
    if data.status == Statuses.gameSelector:
      if self.config.configs is not None:
        print(self.config.configs[data.version].LAUNCHER_ASSET_NAME)
        if self.config.configs[data.version].LAUNCHER_ASSET_NAME:
          menu.addAction(
            "Update",
            bind[None](
              self.updateSubLauncher,
              self.config.configs[data.version],
              data,
            ),
          )
      if data.path:
        newAction("Open Folder", lambda: self.openFile(os.path.dirname(data.path))) # type: ignore
        newAction(
          f"Delete {data.version} Launcher", lambda: os.remove(data.path) # type: ignore
        )
    else:
      if data.path:
        newAction("Open Folder", lambda: self.openFile(data.path)) # type: ignore
        newAction(
          f"Delete Version {data.version}", lambda: (shutil.rmtree(data.path), self.populateList()) # type: ignore
        )
      if data.release:
        newAction(
          f"{"Red" if data.status==Statuses.local else "D"}ownload Version {data.version}",
          lambda: self.startQueuedDownloadRequest(data),
        )

    _ = menu.addSeparator()
    self.config.addContextMenuOptions(self, data, menu, newAction)
    _ = menu.exec(self.listWidget.mapToGlobal(pos))

  def startFetch(self, max_pages:int=1, noDefaultConnections:bool=False):
    """Standard fetch with a page limit."""
    if self.releaseFetchingThread and self.releaseFetchingThread.isRunning():
      return

    self.releaseFetchingThread = self.ReleaseFetchThread(
      self.API_URL, pat=self.settings.githubPat or None, max_pages=max_pages
    )
    if max_pages:
      self.mainProgressBar.setModeKnownEnd()
      self.mainProgressBar.setProgress((0 / max_pages) * 100)
    else:
      self.mainProgressBar.setModeUnknownEnd()
    if max_pages:
      self.mainProgressBar.label.setText(
        f"Fetching {max_pages} Page{'' if max_pages==1 else 's'}..."
      )
    else:
      self.mainProgressBar.label.setText(f"Fetching Page Count...")
    if not noDefaultConnections:
      self.releaseFetchingThread.progress.connect(self.onReleaseProgress)
      self.releaseFetchingThread.finished.connect(self.onReleaseFinished)
    self.releaseFetchingThread.start()

  def mergeReleases(self, existing, new_data) -> list[Any]:

    merged: dict[Any, Any] = {rel["tag_name"]: rel for rel in existing}

    for rel in new_data:
      tag: Any = rel.get("tag_name")
      if tag:
        merged[tag] = rel

    return list[Any](merged.values())

  def startFullFetch(self) -> None:
    """Triggered by button to fetch everything."""
    print("Starting Full Release Fetch...")
    self.startFetch(max_pages=0)

  def onReleaseProgress(self, page, total, releases) -> None:
    self.mainProgressBar.setModeKnownEnd()
    self.mainProgressBar.setProgress((page / total) * 100)
    self.foundReleases = self.mergeReleases(self.foundReleases, releases)
    self.mainProgressBar.label.setText(
      f"Fetching {total} Page{'' if total==1 else 's'}... {(page / total) * 100}% - {page} / {total}"
    )
    self.populateList()

  def onReleaseFinished(self, releases) -> None:
    self.mainProgressBar.label.setText("")
    self.mainProgressBar.setModeDisabled()
    self.foundReleases = self.mergeReleases(self.foundReleases, releases)
    self.populateList()

  def setupSettingsDialog(self) -> None:
    self.settingsDialog: QDialog = QDialog(self)
    self.settingsDialog.setWindowTitle("Settings")
    self.settingsDialog.setFixedWidth(600)
    outerLayout: QVBoxLayout = QVBoxLayout(self.settingsDialog)

    # region launcher
    groupBox: QGroupBox = QGroupBox("Launcher Settings")
    groupLayout: QVBoxLayout = QVBoxLayout()

    groupLayout.addWidget(
      self.newCheckbox(
        "Check for Launcher Updates when Opening",
        False,
        "checkForLauncherUpdatesWhenOpening",
      )
    )
    groupLayout.addWidget(
      self.newButton(
        "Update the Launcher Now (Must Have Git Installed)",
        self.updateLauncher,
      )
    )

    def toggleAlwaysOnTop(win: Launcher, on) -> None:
      win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
      win.show()

    groupLayout.addWidget(
      self.newCheckbox(
        "Keep Launcher Always on Top",
        False,
        "keepLauncherAlwaysOnTop",
        onChange=bind[None](toggleAlwaysOnTop, self),
      )
    )

    # if self.settings.keepLauncherAlwaysOnTop:
    #   self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    groupLayout.addLayout(
      self.newLabel(
        "On Restart Required:",
        self.newSelectBox(
          ["Ask Every Time", "Never Restart", "Always Restart"],
          0,
          "onRestartRequired",
        ),
      )
    )
    groupBox.setLayout(groupLayout)
    outerLayout.addWidget(groupBox)
    # endregion
    # region global
    groupBox: QGroupBox = QGroupBox("Global Settings (All Games)")
    groupLayout: QVBoxLayout = QVBoxLayout()

    groupLayout.addWidget(
      self.newCheckbox(
        "Show Game Images in the Launcher Selector", True, "showLauncherImages"
      )
    )
    groupLayout.addWidget(
      self.newCheckbox("Fetch Releases on Launcher Start", True, "fetchOnLoad")
    )
    groupLayout.addLayout(
      self.newLabel(
        "Max Concurrent Downloads:",
        self.newSpinBox(0, 10, 3, "maxConcurrentDls"),
      )
    )
    groupLayout.addLayout(
      self.newLabel(
        "Max Pages to Fetch:",
        self.newSpinBox(0, 100, 1, "maxPagesOnLoad"),
      )
    )

    fetchBtnRow: QHBoxLayout = QHBoxLayout()
    assert isinstance(self.settings.maxPagesOnLoad, int)
    fetchBtnRow.addWidget(
      self.newButton(
        "Fetch Recent Updates",
        lambda: self.startFetch(max_pages=self.settings.maxPagesOnLoad),
      )
    )
    fetchBtnRow.addWidget(self.newButton("Sync Full History", self.startFullFetch))
    groupLayout.addLayout(fetchBtnRow)
    groupLayout.addWidget(
      self.newButton(
        "Download All Game Versions",
        self.downloadAllVersions,
      )
    )
    groupLayout.addWidget(
      self.newCheckbox(
        "Close Launcher on Game Start (Could Cause some Games to Not Start)",
        False,
        "closeOnLaunch",
      )
    )
    groupLayout.addLayout(
      self.newLabel(
        "GitHub PAT (Optional):",
        self.newLineEdit("GitHub PAT (Optional)", "githubPat", password=True),
        False,
      )
    )

    groupBox.setLayout(groupLayout)
    outerLayout.addWidget(groupBox)
    # endregion
    # region local
    groupBox: QGroupBox = QGroupBox(
      f"Local Settings ({self.gameName or "Default Settings For New Launchers"})"
    )
    groupLayout: QVBoxLayout = QVBoxLayout()
    self.localKeys: list[str] = [
      "extraGameArgs",
      "replaceDuplicateGameFilesWithHardlinks",
      "useCentralGameDataFolder",
    ]
    if self.gameName:
      groupLayout.addWidget(
        self.newButton(
          "Update " + self.gameName + " Launcher",
          bind(self.updateSubLauncher, widget=self.mainProgressBar),
        )
      )
    groupLayout.addLayout(
      self.newLabel(
        "Current Os:",
        self.newSelectBox(self.config.supportedOs, 0, "selectedOs"),
      )
    )
    groupLayout.addLayout(
      self.newLabel(
        "Extra Game Args:",
        self.newLineEdit("Extra Game Args", "extraGameArgs"),
        False,
      )
    )
    groupLayout.addWidget(
      self.newCheckbox(
        "Replace Duplicate Game Files with Hardlinks",
        self.config.SHOULD_USE_HARD_LINKS,
        "replaceDuplicateGameFilesWithHardlinks",
      ),
    )
    if self.config.CAN_USE_CENTRAL_GAME_DATA_FOLDER:
      groupLayout.addWidget(
        self.newCheckbox(
          "Use Central Game Data Folder", True, "useCentralGameDataFolder"
        ),
      )
    self.loadUserSettings()
    if self.config.getGameLogLocation(
      self.settings, self.settings.selectedOs, self.GAME_ID
    ):
      groupLayout.addWidget(
        self.newButton(
          "Open Game Logs",
          lambda: self.openFile(
            self.config.getGameLogLocation(
              self.settings, self.settings.selectedOs, self.GAME_ID
            )
          ),
        )
      )
    groupLayout.addWidget(
      self.newButton(
        "Open Game Data Folder",
        lambda: self.openFile(self.getGameDataLocation()),
      )
    )
    if self.config.addCustomNodes:
      lastWidgetCount: int = len(self.widgetsToSave)
      self.config.addCustomNodes(self, groupLayout)
      for key in islice[Any](self.widgetsToSave.keys(), lastWidgetCount, None):
        if key not in self.localKeys:
          self.localKeys.append(key)

    groupBox.setLayout(groupLayout)
    outerLayout.addWidget(groupBox)

    bottom_btn_layout: QHBoxLayout = QHBoxLayout()
    cancel_btn: QPushButton = QPushButton("Cancel")
    cancel_btn.clicked.connect(self.settingsDialog.reject)
    done_btn: QPushButton = QPushButton("Done")
    done_btn.setDefault(True)
    done_btn.clicked.connect(self.settingsDialog.accept)

    bottom_btn_layout.addWidget(cancel_btn)
    bottom_btn_layout.addWidget(done_btn)
    outerLayout.addLayout(bottom_btn_layout)
    # endregion

  def updateSubLauncher(
    self,
    launcherSettings: Optional[Config] = None,
    data: Optional[listData] = None,
    widget: Optional[VersionItemWidget] = None,
  ) -> None:
    ls: Config = launcherSettings or self.config

    # If no data object provided (e.g. from Settings button),
    # create a mock one or find the one matching the current game
    if data is None:
      # Assuming current running file is the target
      current_path: Any = os.path.abspath(os.path.join(APP_DATA_PATH, sys.modules[self.gameName].__file__)) # type: ignore
      data: listData = listData(
        version=self.gameName,
        path=current_path,
        release=None,
        status=Statuses.gameSelector,
      )

    tag: str = data.version
    if not widget:
      widget: VersionItemWidget | None = self.activeItemRefs.get(tag)
    assert isinstance(widget, VersionItemWidget)
    widget.setModeKnownEnd()

    def on_progress(progress) -> None:
      widget.setProgress(progress)

    self.downloadingVersions.append(tag)
    dest_dir = os.path.join(
      os.path.abspath(os.path.join(APP_DATA_PATH, "-")), f"temp_{tag}"
    )
    out_file = os.path.join(dest_dir, ls.LAUNCHER_ASSET_NAME)
    os.makedirs(dest_dir, exist_ok=True)

    dl_thread: AssetDownloadThread = AssetDownloadThread(
      f"https://github.com/{ls.LAUNCHER_GH_USERNAME or ls.GH_USERNAME}/{ls.LAUNCHER_GH_REPO or ls.GH_REPO}/releases/latest/download/{ls.LAUNCHER_ASSET_NAME}",
      out_file,
    )
    self.activeDownloads[tag] = dl_thread

    def on_finished(path) -> None:
      widget.setModeDisabled()
      found: dict[str, bool] = {"py": False, "png": False}
      extracted = False
      try:
        if path.endswith(".zip"):
          with zipfile.ZipFile(path, "r") as z:
            z.extractall(dest_dir)
          extracted = True
        elif path.endswith(".7z"):
          with py7zr.SevenZipFile(path, "r") as z:
            z.extractall(dest_dir)
          extracted = True

        if extracted:
          # Replacement logic
          for root, _, files in os.walk(dest_dir):
            if f"{tag}.png" in files:
              if data.path:
                print(
                  os.path.dirname(data.path),
                  "os.path.dirname(data.path)",
                )
                imgpath = os.path.join(
                  os.path.dirname(data.path),
                  "images",
                  f"{tag}.png",
                )
                if os.path.exists(imgpath):
                  os.remove(imgpath)
                shutil.move(
                  os.path.join(root, f"{tag}.png"),
                  imgpath,
                )
                found["png"] = True
            if f"{tag}.py" in files:
              if data.path:
                if os.path.exists(data.path):
                  os.remove(data.path)
                shutil.move(os.path.join(root, f"{tag}.py"), data.path)
                found["py"] = True
            if found["png"] and found["py"]:
              break
      except Exception as e:
        print(f"Update failed for {tag}: {e}")
      finally:
        if tag in self.downloadingVersions:
          self.downloadingVersions.remove(tag)
        self.activeDownloads.pop(tag, None)
        self.activeDownloads.pop(f"meta_{tag}", None)
        shutil.rmtree(dest_dir, ignore_errors=True)
        self.populateList()
        if found["py"]:
          self.showRestartPrompt(f"{tag} updated successfully.")

    dl_thread.progress.connect(on_progress)
    dl_thread.onfinished.connect(on_finished)
    dl_thread.onfinished.connect(dl_thread.deleteLater)
    dl_thread.start()

  # def updateSubLauncher(
  #   self,
  #   launcherSettings: Optional[Config] = None,
  #   data: Optional[listData] = None,
  #   widget: Optional[VersionItemWidget] = None,
  # ):
  #   """Refactored unified update logic for the launcher or sub-modules."""
  #   # Fallback to current config if none provided
  #   ls = launcherSettings or self.config

  #   # If no data object provided (e.g. from Settings button),
  #   # create a mock one or find the one matching the current game
  #   if data is None:
  #     # Assuming current running file is the target
  #     current_path = os.path.abspath(sys.modules[self.gameName].__file__) # type: ignore
  #     data = listData(
  #       version=self.gameName,
  #       path=current_path,
  #       release=None,
  #       status=Statuses.gameSelector,
  #     )

  #   tag = data.version
  #   api_url = f"https://api.github.com/repos/{ls.LAUNCHER_GH_USERNAME or ls.GH_USERNAME}/{ls.LAUNCHER_GH_REPO or ls.GH_REPO}/releases"

  #   fetcher = self.ReleaseFetchThread(
  #     api_url, pat=self.settings.githubPat or None, max_pages=1
  #   )
  #   if not widget:
  #     widget = self.activeItemRefs.get(tag)
  #   assert isinstance(widget, VersionItemWidget)
  #   widget.setModeUnknownEnd()

  #   def on_metadata(widget: VersionItemWidget, releases):
  #     if not releases:
  #       return
  #     data.release = releases[0]
  #     assert data.release is not None
  #     widget.setModeKnownEnd()

  #     def on_progress(progress):
  #       widget.setProgress(progress)

  #     asset_name = ls.LAUNCHER_ASSET_NAME
  #     asset = next(
  #       (a for a in data.release.get("assets", []) if a["name"] == asset_name),
  #       None,
  #     )

  #     if not asset or tag in self.downloadingVersions:
  #       self.activeDownloads.pop(f"meta_{tag}", None)
  #       return

  #     self.downloadingVersions.append(tag)
  #     dest_dir = os.path.join(
  #       os.path.abspath(os.path.join(APP_DATA_PATH, "-")), f"temp_{tag}"
  #     )
  #     out_file = os.path.join(dest_dir, asset["name"])
  #     os.makedirs(dest_dir, exist_ok=True)

  #     dl_thread = AssetDownloadThread(asset["browser_download_url"], out_file)
  #     self.activeDownloads[tag] = dl_thread

  #     def on_finished(path):
  #       widget.setModeDisabled()
  #       found = {"py": False, "png": False}
  #       extracted = False
  #       try:
  #         if path.endswith(".zip"):
  #           with zipfile.ZipFile(path, "r") as z:
  #             z.extractall(dest_dir)
  #           extracted = True
  #         elif path.endswith(".7z"):
  #           with py7zr.SevenZipFile(path, "r") as z:
  #             z.extractall(dest_dir)
  #           extracted = True

  #         if extracted:
  #           # Replacement logic
  #           for root, _, files in os.walk(dest_dir):
  #             if f"{tag}.png" in files:
  #               if data.path and os.path.exists(data.path):
  #                 imgpath = os.path.join(
  #                   os.path.dirname(data.path),
  #                   "images",
  #                   f"{tag}.png",
  #                 )
  #                 os.remove(imgpath)
  #                 shutil.move(
  #                   os.path.join(root, f"{tag}.png"),
  #                   imgpath,
  #                 )
  #                 found["png"] = True
  #             if f"{tag}.py" in files:
  #               if data.path and os.path.exists(data.path):
  #                 os.remove(data.path)
  #                 shutil.move(
  #                   os.path.join(root, f"{tag}.py"), data.path
  #                 )
  #                 found["py"] = True
  #             if found["png"] and found["py"]:
  #               break
  #       except Exception as e:
  #         print(f"Update failed for {tag}: {e}")
  #       finally:
  #         if tag in self.downloadingVersions:
  #           self.downloadingVersions.remove(tag)
  #         self.activeDownloads.pop(tag, None)
  #         self.activeDownloads.pop(f"meta_{tag}", None)
  #         shutil.rmtree(dest_dir, ignore_errors=True)
  #         self.populateList()
  #         if found["py"]:
  #           self.showRestartPrompt(f"{tag} updated successfully.")

  #     dl_thread.progress.connect(on_progress)
  #     dl_thread.finished.connect(on_finished)
  #     dl_thread.finished.connect(dl_thread.deleteLater)
  #     dl_thread.start()

  #   fetcher.finished.connect(bind(on_metadata, widget))
  #   fetcher.finished.connect(fetcher.deleteLater)
  #   self.activeDownloads[f"meta_{tag}"] = fetcher
  #   fetcher.start()

  def showRestartPrompt(self, text: str) -> None:
    def restart() -> Never:
      script_path: str = f'"{os.path.abspath(sys.argv[0])}"'
      executable: str = f'"{sys.executable}"'

      # We pass the quoted executable as the path and arg0,
      # then the quoted script path, then the rest of the args.

      args: list[str] = buildArgs(
        *[d for d in ALL_ARG_DATA if d.key != "downloadLauncher"],
        useArgs=LAST_USED_ARGS,
      )
      print("NEW ARGS", args)
      # buildArgs(LAST_USED_ARGS)
      os.execl(sys.executable, executable, script_path, *args)

    print(self.settings.onRestartRequired)
    match self.settings.onRestartRequired:
      case 0:
        msg = QMessageBox(self)
        msg.setText(text)
        msg.setInformativeText("Restart now to apply changes?")
        msg.setStandardButtons(
          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() == QMessageBox.StandardButton.Yes:
          restart()
      case 1:
        return
      case 2:
        restart()

  def openFile(self, p: str) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(p)))

  def newSpinBox(self, min_val, max_val, default, saveId, width=60) -> QSpinBox:
    node: QSpinBox = QSpinBox()
    node.setRange(min_val, max_val)
    node.setValue(default)
    node.setFixedWidth(width)

    node.valueChanged.connect(lambda v: setattr(self.settings, saveId, v))

    setattr(self.settings, saveId, default)

    self.widgetsToSave[saveId] = node
    return node

  def newButton(self, text: str, onclick: Callable[[], None] | None) -> QPushButton:
    node: QPushButton = QPushButton(text)
    if onclick is not None:
      _ = node.pressed.connect(onclick)
    return node

  def newLabel(
    self, label_text: str, widget: QWidget, addStretch: bool = True
  ) -> QHBoxLayout:
    row: QHBoxLayout = QHBoxLayout()
    row.addWidget(QLabel(label_text))
    row.addWidget(widget)
    if addStretch:
      row.addStretch()
    return row

  def newCheckbox(
    self,
    text: str,
    default: bool,
    saveId: str,
    tooltip: str = "",
    onChange: Callable[[bool], None] | None = None,
  ) -> QCheckBox:
    node: QCheckBox = QCheckBox(text)
    node.setChecked(default)
    if tooltip:
      node.setToolTip(tooltip)
    if onChange:
      _ = node.toggled.connect(onChange)
    _ = node.toggled.connect(lambda v: setattr(self.settings, saveId, v))
    setattr(self.settings, saveId, default)
    self.widgetsToSave[saveId] = node
    return node

  def newLineEdit(
    self, placeholder: str, saveId: str, password: bool = False
  ) -> QLineEdit:
    node: QLineEdit = QLineEdit()
    node.setPlaceholderText(placeholder)
    if password:
      node.setEchoMode(QLineEdit.EchoMode.Password)
    _ = node.textChanged.connect(lambda v: setattr(self.settings, saveId, v))
    setattr(self.settings, saveId, "")
    self.widgetsToSave[saveId] = node
    return node

  def newSelectBox(
    self,
    values: type[Enum] | list[str] | dict[str, object] | set[str],
    default_value: int,
    saveId: str,
  ) -> EnumComboBox:
    node: EnumComboBox = EnumComboBox()
    node.usesEnum = False
    if isinstance(values, EnumMeta):
      node.usesEnum = True
      node.usedEnum = values
      for thing in values:
        node.addItem(thing.name, thing)
    elif isinstance(values, list):
      for i, thing in enumerate(values):
        node.addItem(thing, i)
    elif isinstance(values, dict):
      for k, v in values.items():
        node.addItem(k, v)
    node.setCurrentIndex(default_value)
    _ = node.currentIndexChanged.connect(
      lambda: setattr(self.settings, saveId, node.currentData())
    )
    setattr(self.settings, saveId, default_value)
    self.widgetsToSave[saveId] = node
    return node


_current_window: Launcher | None = None


def run(config: Config, module_name: str | None) -> None:
  global _current_window

  is_new_app = False
  app: QCoreApplication | None = QApplication.instance()
  if not app:
    app = QApplication(sys.argv)
    is_new_app = True

  # Save the old geometry if a window is currently open
  _last_geometry: QByteArray | None = None
  if _current_window is not None:
    _last_geometry = _current_window.saveGeometry()

  _current_window = Launcher(config, module_name)

  # Apply the saved geometry before showing the window
  if _last_geometry is not None:
    _current_window.restoreGeometry(_last_geometry)

  _current_window.show()

  if is_new_app: # Only exec if loop isn't running
    if LAUNCHER_TO_LAUNCH in modules:
      lwin: None = _current_window
      run(modules[LAUNCHER_TO_LAUNCH], LAUNCHER_TO_LAUNCH)
      lwin.close()
    sys.exit(app.exec())


modules: dict[str, Config] = {}
paths: dict[str, str] = {}
_is_selector_loading = False


def loadConfig(config: Config) -> None:
  # 1. Get the actual main module (the one running the loop)
  main_app: ModuleType = sys.modules["__main__"]

  caller_frame: FrameInfo = inspect.stack()[1]
  caller_filename: str = caller_frame.filename
  module_name: str = Path(caller_filename).stem
  # 2. Check if the main app has the 'modules' list (meaning we are in the Selector)
  # _is_selector_loading is for if ran like `launcher`
  # hasattr(main_app, "modules") and isinstance(main_app.modules, dict) is for if ran like `python ./__init__.py`
  if _is_selector_loading or (
    hasattr(main_app, "modules")
    and isinstance(main_app.modules, dict) # pyright: ignore[reportAny]
  ):
    # We are inside the selector loop!
    # Use 'inspect' to automatically find the name of the file calling this function

    # Register the config into the MAIN list
    if _is_selector_loading:
      modules[module_name] = config
      if importHavingError:
        config.errorText = importHavingError
        config.hadErrorLoading = True
      paths[module_name] = os.path.abspath(caller_filename)
    else:
      main_app.paths[module_name] = os.path.abspath(
        caller_filename
      ) # pyright: ignore[reportAny]
      main_app.modules[module_name] = (
        config # pyright: ignore[reportUnknownMemberType]
      )
  else:
    # We are NOT in the selector (User ran "python mygame.py" directly)
    run(config, module_name)


importHavingError: str | None = None


def findAllLaunchables() -> None:
  global selectorConfig, _is_selector_loading
  import importlib

  # 1. Force 'import launcher' to use THIS running module instance
  # This ensures the sub-module sees the modified Config below
  sys.modules["launcher"] = sys.modules[__name__]

  class supportedOs(Enum):
    windows = 0
    linux = 1

  _is_selector_loading = True
  sys.path.append(os.path.abspath(APP_DATA_PATH))
  print("Current Working Directory:", os.getcwd())

  for filename in os.listdir(APP_DATA_PATH):
    if filename.endswith(".py") and filename != "__init__.py":
      module_name = filename[:-3]
      try:
        _ = importlib.import_module(module_name)
      except Exception as e:
        paths[module_name] = os.path.abspath(filename)
        global importHavingError
        importHavingError = f"{e}"

        this_module = sys.modules[__name__]
        original_config: Config = ( # pyright: ignore[reportAny]
          this_module.Config
        )

        def a(**kwargs: object) -> SettingsData:
          sd: SettingsData = SettingsData()
          for k, v in kwargs.items():
            setattr(sd, k, v)
          return sd

        this_module.Config = a # pyright: ignore[reportAttributeAccessIssue]
        _ = importlib.import_module(module_name)
        this_module.Config = ( # pyright: ignore[reportAttributeAccessIssue]
          original_config
        )
        print("error loading launcher", module_name, e)

  selectorConfig = Config(
    WINDOW_TITLE="launcher selector",
    CAN_USE_CENTRAL_GAME_DATA_FOLDER=False,
    GH_USERNAME="",
    GH_REPO="",
    supportedOs=supportedOs,
    configs=modules,
  )
  run(selectorConfig, None)


# def checkImageExtension(p):
#   # Check if object of the extensions exist
#   extensions = ("jpg", "jpeg", "png", "webp")
#   return next(
#     (p + "." + ext for ext in extensions if os.path.isfile(p + "." + ext)),
#     None,
#   )


if __name__ == "__main__":
  findAllLaunchables()
# APP_DATA_PATH
#             if True
#             else ""
# self.settings.centralGameDataLocations

# TODO make del on launcher selector update ui
# TODO add settying in app to register proto
