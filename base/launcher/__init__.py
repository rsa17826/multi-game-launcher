# @name a
# @regex (?<=[^ ])  #
# @replace  #
# @endregex
import shutil
import inspect
from dataclasses import dataclass
from typing import Callable, Dict, List, Any, Tuple, Optional
from functools import partial as bind
from itertools import islice
import sys
import time
import random
import requests
import shlex
from enum import Enum, EnumMeta
import json
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon
from PySide6.QtCore import QUrl
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
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import (
  QPainter,
  QLinearGradient,
  QColor,
)
from PySide6.QtCore import QTimer
import os
import zipfile
import py7zr
import re
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
import math

import hashlib


@dataclass
class ArgumentData:
  key: str | list[str]
  afterCount: int
  default: Optional[Any] = None

  def __post_init__(self):
    if self.afterCount == 0:
      self.default = False
    if isinstance(self.key, str):
      self.key = self.key.lstrip("-")
    else:
      self.key = [*map(lambda x: x.lstrip("-"), self.key)]


def checkArgs(*argData: ArgumentData) -> list[Any]:
  args: List[str] = sys.argv[1:] # Ignore the script name, only check arguments
  if "--" in args:
    beforeDashArgs = args[: args.index("--")]
  else:
    beforeDashArgs = args
 # print(beforeDashArgs, args)
 # Initialize results with the default values from argData
  results: List[Any | None] = [data.default for data in argData]

  i = 0
  while i < len(beforeDashArgs):
    nextArg: str = beforeDashArgs[i].lstrip("-")
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
      assert idx is not None

      if afterCount == 0:
        # If afterCount is 0, consume the key (do not use its value)
        beforeDashArgs.pop(i)
        results[idx] = True # True for a valid flag

      elif afterCount == 1:
        # If afterCount is 1, consume the next argument as the value for the key
        if i + 1 < len(beforeDashArgs):
          value = beforeDashArgs[i + 1]
          beforeDashArgs.pop(i) # Remove the key
          beforeDashArgs.pop(i) # Remove the value
          results[idx] = value # Then the value
        else:
          # If no argument follows the key, use the default
          beforeDashArgs.pop(i) # Remove the key
          print(
            "err",
            nextArg,
            "requires",
            afterCount,
            "args",
            "but received",
            len(beforeDashArgs),
            "args",
          )
          results[idx] = foundKey.default

      elif afterCount > 1:
        # If afterCount > 1, return the next `afterCount` arguments
        if len(beforeDashArgs) >= i + 1 + afterCount:
          values = beforeDashArgs[i + 1 : i + 1 + afterCount]
          beforeDashArgs = (
            beforeDashArgs[:i] + beforeDashArgs[i + 1 + afterCount :]
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
            len(beforeDashArgs),
            "args",
          )
          beforeDashArgs = []

    else:
      # If the key is invalid, just skip it and move to the next argument
      beforeDashArgs.pop(i)
      continue # Skip to the next argument

    # Skip over the processed argument
    continue

 # print(results)
  return results


selectorConfig = None

LAUNCHER_START_PATH = os.path.abspath(os.path.dirname(__file__))
# asdadsas
OFFLINE, LAUNCHER_TO_LAUNCH, TRY_UPDATE, HEADLESS, VERSION = checkArgs(
  ArgumentData(key="offline", afterCount=0),
  ArgumentData(key="launcherName", afterCount=1),
  ArgumentData(key="tryupdate", afterCount=0),
  ArgumentData(key=["silent", "headless"], afterCount=0),
  ArgumentData(key="version", afterCount=1),
)
# print(HEADLESS)
LOCAL_COLOR = Qt.GlobalColor.green
ERROR_COLOR = Qt.GlobalColor.darkRed
LOCAL_ONLY_COLOR = Qt.GlobalColor.yellow
ONLINE_COLOR = Qt.GlobalColor.cyan
MISSING_COLOR = Qt.GlobalColor.gray

MAIN_LOADING_COLOR = (0, 210, 255)
UNKNOWN_TIME_LOADING_COLOR = (255, 108, 0)

launcherUpdateAlreadyChecked = False


class Statuses(Enum):
  local = 0
  online = 1
  gameSelector = 2
  loadingInfo = 3
  localOnly = 4


# downloading = 2
# waitingForDownload = 3


from typing import Type


@dataclass
class ItemListData:
  path: str | None
  release: Dict[Any, Any] | None
  status: Statuses
  version: str


@dataclass
class Config:
  supportedOs: Type[Enum]
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
  getImage: Callable = lambda *a: ""
  """
returns the path to the image that should be shown

Args:
  version: the game version or the name of the python file.
"""
  addContextMenuOptions: Callable = lambda *a: None
  """
Injects custom actions into the right-click menu of a version item.

Args:
  _self: Reference to the Launcher instance.
  menu: The QMenu object being constructed.
  data: The metadata dictionary of the selected version (version, status, path, etc.).
"""
  getGameLogLocation: Callable = lambda *a: ""
  gameLaunchRequested: Callable = lambda *a: None
  """
Handles the execution of the game binary when the user double-clicks a version.

Args:
  path (str): The directory containing the specific game version.
  args (list[str]): Base command-line arguments provided by the launcher.
  settings: The current settings object containing user-defined flags.
"""
  getAssetName: Callable = lambda *a: ""
  """Identifies which file to download from the GitHub Release assets.
Args:
  settings (launcher.SettingsData): The current settings object containing user-defined flags
Returns:
  str: the name of the asset to download from gh
"""
  onGameVersionDownloadComplete: Callable = lambda *a: None
  gameVersionExists: Callable = lambda *a: False
  """
Validation check to see if a folder contains a valid installation.
Used by the launcher to decide if a version is 'Local' (Run) or 'Online' (Download).

Args:
  path (str): path to check
  settings (launcher.SettingsData): The current settings object containing user-defined flags

Returns:
  bool: return true if the path has a game in it
"""
  addCustomNodes: Callable = lambda *a: None
  """
Injects custom UI elements into the 'Local Settings' section of the Launcher.

Args:
  _self: Reference to the Launcher instance to use its helper methods (newCheckbox, etc.)
  layout: The layout where these widgets will be added.
"""
  WINDOW_TITLE: str = "No Window Title Has Been Set"
  """what to set the launchers title to"""
  USE_HARD_LINKS: bool = False
  """if true will scan all new version downloads and check to see if any files are the same between different versions and replace the new files with hardlinks instead"""
  CAN_USE_CENTRAL_GAME_DATA_FOLDER: bool = False
  """if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location"""
  configs: Dict[Any, Any] | None = None
  """if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location"""
  hadErrorLoading: bool = False
  errorText: str = ""


class f:
  @staticmethod
  def read(
    file,
    default="",
    asbinary=False,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener=None,
  ):
    if Path(file).exists():
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
        text = f.read()
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
        f.write(default)
      return default

  @staticmethod
  def write(
    file,
    text,
    asbinary=False,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener=None,
  ):
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
      f.write(text)
    return text


class AssetDownloadThread(QThread):
  progress = Signal(int)
  finished = Signal(str)
  error = Signal(str)

  def __init__(self, url, dest):
    super().__init__()
    self.url = url
    self.dest = dest

  def run(self):
    try:
      with requests.get(self.url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0

        with open(self.dest, "wb") as f:
          for chunk in r.iter_content(chunk_size=8192):
            if chunk:
              f.write(chunk)
              downloaded += len(chunk)
              if total:
                percent = int(downloaded / total * 100)
                self.progress.emit(percent)

      self.finished.emit(self.dest)
    except Exception as e:
      self.error.emit(str(e))


class Cache:
  lastinp = None

  def __init__(self):
    self.cache = {}

  def has(self, item):
    self.lastinp = item
    return item in self.cache

  def get(self):
    if not self.has(self.lastinp):
      raise KeyError(f"No such item {self.lastinp}")
    thing = self.cache[self.lastinp]
    del self.lastinp
    return thing

  def set(self, value):
    self.cache[self.lastinp] = value
    del self.lastinp
    return value

  def clear(self):
    self.cache = {}


iconCache = Cache()


class VersionItemWidget(QWidget):
  class ProgressTypes(Enum):
    leftToRight = 0
    both = 1
    rightToLeft = 2

  def __init__(self, text="", color=MISSING_COLOR, image_source=None):
    super().__init__()
    self.text = text
    self.progress = 0
    self.setModeUnknownEnd()
    self.startTime = 0
    self.animSpeed = 10
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    self.setStyleSheet("background: transparent; border: none;")
    self.image_label = QLabel()
    self.image_label.setFixedSize(50, 50) # Set a standard thumbnail size
    self.label = QLabel(text)
    color_hex = color.name
    self.label.setStyleSheet(f"background: transparent; color: {color_hex};")

    self.qblayout = QHBoxLayout(self)
    self.icon_label = QLabel()
    self.icon_label.setFixedSize(32, 32) # Standard thumbnail size
    self.icon_label.setScaledContents(True)
    self.icon_label.hide()
    self.qblayout.addWidget(self.icon_label)
    self.qblayout.setContentsMargins(5, 0, 5, 0)
    self.qblayout.addWidget(self.label)
    self.qblayout.addStretch()
    self.setIcon(image_source)

  def setIcon(self, image_source):
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

  def setModeKnownEnd(self):
    flag = self.noKnownEndPoint
    self.progressColor = MAIN_LOADING_COLOR
    self.progressType = VersionItemWidget.ProgressTypes.leftToRight
    self.noKnownEndPoint = False
    if flag:
      self.progress = 0
      self.update()

  def setModeUnknownEnd(self):
    self.progressColor = UNKNOWN_TIME_LOADING_COLOR
    self.progressType = VersionItemWidget.ProgressTypes.both
    self.noKnownEndPoint = True
    self.startTime = time.time()
    self.update()

  def setModeDisabled(self):
    self.noKnownEndPoint = False
    self.progress = 101
    self.update()

  def setLabelColor(self, color):
    self.label.setStyleSheet(f"background: transparent; color: {color.name};")

  def setProgress(self, percent):
    if percent == self.progress:
      return
    if self.noKnownEndPoint:
      self.noKnownEndPoint = False
      self.setModeKnownEnd()
    self.progress = percent
    self.update()

  def paintEvent(self, event):
    if not ((0 < self.progress <= 100) or self.noKnownEndPoint):
      super().paintEvent(event)
      return

    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = self.rect()
    w = rect.width()
    h = rect.height()
    gradSize = int(w / 8)
    minGradAlpha = 50
    if self.noKnownEndPoint:
      self.progress = int(((time.time() - self.startTime) * self.animSpeed) % 100)
      QTimer.singleShot(16, self.update)

    if self.progressType == self.ProgressTypes.both:
      fill_end = w * self.progress / 100
      solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
      tip_rect = QRectF(solid_rect.right(), 0, int(min(gradSize, fill_end)), h)
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
      fill_end = w * self.progress / 100
      solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
      tip_rect = QRectF(solid_rect.right(), 0, min(gradSize, fill_end), h)
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

  def _drawProgress(self, painter, rect, alpha):
    if rect.width() <= 0:
      return
    painter.fillRect(rect, QColor(*self.progressColor, alpha))

  def _drawGradient(self, painter, rect, start_pt, end_pt, min_alpha):
    if rect.width() <= 0:
      return
    grad = QLinearGradient(start_pt, end_pt)
    exponent = 5
    for i in range(11):
      pos = i / 10.0
      alpha = int(min_alpha + (255 - min_alpha) * math.pow(pos, exponent))
      grad.setColorAt(pos, QColor(*self.progressColor, alpha))
    painter.fillRect(rect, grad)


from typing import Any


class SettingsData:
  """A container for dot-notation access to settings."""

  def __getattr__(self, name) -> Any:
    print("WARNING: ", name, "was not set")
    return None


class Launcher(QWidget):
  def updateLauncher(self):
    import subprocess
    import os
    import sys

    # Set the repository URL and the local directory where the script is located
    repo_url = "https://github.com/rsa17826/multi-game-launcher.git"
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")

    # Check if the directory is a valid Git repository
    def is_git_repo(path):
      return os.path.isdir(os.path.join(path, ".git"))

    # Initialize the Git repository if not already initialized
    def init_git_repo(path, url):
      try:
        print(f"Initializing new Git repository in {path}...")
        # Run git init to initialize the repo
        subprocess.check_call(["git", "init"], cwd=path)
        # Add the remote repository URL
        subprocess.check_call(["git", "remote", "add", "origin", url], cwd=path)
        subprocess.check_call(["git", "add", "-A"], cwd=path)
        subprocess.check_call(["git", "fetch", "origin"], cwd=local_dir)
        print("Git repository initialized and remote set.")
      except subprocess.CalledProcessError as e:
        print("Error initializing repository:", e)
        sys.exit(1)

    if not is_git_repo(local_dir):
      print("No .git directory found. Initializing repository...")
      init_git_repo(local_dir, repo_url)

    try:
      print("Checking for updates...")
      subprocess.check_call(
        ["git", "reset", "--hard", "origin/main"], cwd=local_dir
      )
      result = subprocess.run(
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
    self, version: str, status: Statuses, path=None, release=None, image_path=None
  ):
    item = QListWidgetItem()

    widget = VersionItemWidget("", MISSING_COLOR)
    widget.setModeKnownEnd()

    item.setSizeHint(widget.sizeHint())
    self.versionList.addItem(item)
    self.versionList.setItemWidget(item, widget)

    item.setData(
      Qt.ItemDataRole.UserRole,
      ItemListData(
        version=version,
        status=status,
        path=path,
        release=release,
      ),
    )

  def saveUserSettings(self):
    local_data = {}
    global_data = {}

    for key, widget in self.widgetsToSave.items():
      if isinstance(widget, QLineEdit):
        value = widget.text()
      elif isinstance(widget, QCheckBox):
        value = widget.isChecked()
      elif isinstance(widget, QSpinBox):
        value = widget.value()
      elif isinstance(widget, QComboBox):
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
      if self.GAME_ID != "-":
        with open(self.LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
          json.dump(local_data, f, indent=2)
      with open(self.GLOBAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(global_data, f, indent=2)
    except Exception as e:
      print(f"Failed to save settings: {e}")

  def loadUserSettings(self):
    local_data = {}
    global_data = {}

    try:
      if self.GAME_ID != "-" and os.path.exists(self.LOCAL_SETTINGS_FILE):
        with open(self.LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
          local_data = json.load(f)
      if os.path.exists(self.GLOBAL_SETTINGS_FILE):
        with open(self.GLOBAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
          global_data = json.load(f)
    except Exception as e:
      print(f"Failed to load settings: {e}")

    combined = {**global_data, **local_data}

    for key, value in combined.items():
      widget = self.widgetsToSave.get(key)
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
              idx = widget.currentIndex()
              if idx == value:
                widget.setCurrentIndex(1 if idx == 0 else 0)
            except:
              pass
            widget.setCurrentIndex(value)
      except Exception as e:
        print("error loading value for ", key, e)

  def closeEvent(self, event):
    self.saveUserSettings()
    super().closeEvent(event)

  downloadingVersions = []

  def getFileHash(self, path):
    """Calculate SHA256 hash of a file in chunks to save memory."""
    hasher = hashlib.sha256()
    try:
      with open(path, "rb") as f:
        while chunk := f.read(8192):
          hasher.update(chunk)
      return hasher.hexdigest()
    except Exception:
      return None

  def deduplicateWithHardlinks(self, new_version_dir):
    if not (
      self.config.USE_HARD_LINKS
      and self.settings.replaceDuplicateGameFilesWithHardlinks
    ):
      return

    file_map = {}

    for root, dirs, files in os.walk(self.VERSIONS_DIR):

      if os.path.abspath(root).startswith(os.path.abspath(new_version_dir)):
        continue

      for filename in files:
        full_path = os.path.join(root, filename)
        try:
          stat = os.stat(full_path)

          if stat.st_nlink > 1 and (stat.st_size, filename) in file_map:
            continue
          if (stat.st_size, filename) not in file_map:
            file_map[(stat.st_size, filename)] = []
          file_map[(stat.st_size, filename)].append(full_path)
        except OSError:
          continue

    for root, dirs, files in os.walk(new_version_dir):
      for filename in files:
        new_file_path = os.path.join(root, filename)
        try:
          new_stat = os.stat(new_file_path)
          if new_stat.st_nlink > 1:
            continue
          candidates = file_map.get((new_stat.st_size, filename))
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

  def onVersionDoubleClicked(self, item):
    data: ItemListData = item.data(Qt.ItemDataRole.UserRole)
    if not data:
      return
    match data.status:
      case Statuses.gameSelector:
        assert data.release is not None
        run(data.release["config"], data.version)
        self.close()
        return
      case Statuses.local | Statuses.localOnly:
        path = data.path
        if path:
          self.startGameVersion(data)
        return
      case Statuses.online:
        self.startQueuedDownloadRequest(data)

  def startGameVersion(self, data:ItemListData):
    args: List[str] = (
      sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    usesCentralGameDataLocation = (
      self.config.CAN_USE_CENTRAL_GAME_DATA_FOLDER
      and self.settings.useCentralGameDataFolder
    )
    gdl = self.gameDataLocation
    if not usesCentralGameDataLocation:
      gdl = os.path.join(gdl, str(data.version))
    os.makedirs(gdl, exist_ok=True)
    self.config.gameLaunchRequested(
      data.path,
      shlex.split(self.settings.extraGameArgs) + args,
      self.settings,
      self.settings.selectedOs,
      gdl,
    )
    f.write(
      os.path.join(
        (LAUNCHER_START_PATH if True else ""),
        self.GAME_ID,
        "launcherData/lastRanVersion.txt",
      ),
      data.version,
    )
    if self.settings.closeOnLaunch:
      QApplication.quit()

  def startQueuedDownloadRequest(self, *versions: ItemListData):
    for data in versions:
      tag = data.version
      if tag in self.downloadingVersions:
        return

      self.downloadingVersions.append(tag)
      release = data.release
      assert release is not None
      asset = next(
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

      dest_dir = os.path.join(self.VERSIONS_DIR, tag)
      out_file = os.path.join(dest_dir, asset["name"])

      widget = self.activeItemRefs[data.version]
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

  def processDownloadQueue(self):
    assert isinstance(self.settings.maxConcurrentDls, int)
    while self.downloadQueue and (
      len(self.activeDownloads) < self.settings.maxConcurrentDls
      or self.settings.maxConcurrentDls == 0
    ):
      next_dl = self.downloadQueue.pop(0)
      self.startActualDownload(*next_dl)
    print(self.downloadingVersions)
    self.updateVersionList()

  def startActualDownload(self, tag, url, out_file, dest_dir):
    print(url, tag)
    os.makedirs(dest_dir, exist_ok=True)

    dl_thread = AssetDownloadThread(url, out_file)

    self.activeDownloads[tag] = dl_thread

    def onFinished(path):
      self.processDownloadQueue()
      current_widget = self.activeItemRefs.get(tag)
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

        if extracted and self.config.USE_HARD_LINKS:
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
        self.startGameVersion(ItemListData(path=dest_dir, status=Statuses.local, version=tag, release={}))

    dl_thread.progress.connect(bind(self.handleDownloadProgress, tag))
    dl_thread.finished.connect(onFinished)
    dl_thread.error.connect(lambda e: print(f"DL Error {tag}: {e}"))

    dl_thread.finished.connect(dl_thread.deleteLater)

    dl_thread.start()

  def handleDownloadProgress(self, version_tag, percentage):
    widget = self.activeItemRefs.get(version_tag)
    assert isinstance(widget, VersionItemWidget)
    widget.setProgress(percentage)
    widget.label.setText(f"Downloading {version_tag}... ({percentage}%)")

  def updateVersionList(self):
    if not self.versionList:
      return
    if self.GAME_ID != "-":
      try:
        f.write(
          os.path.join(
            (LAUNCHER_START_PATH if True else ""),
            self.GAME_ID,
            "launcherData/cache/releases.json",
          ),
          json.dumps(self.foundReleases),
        )
      except Exception as e:
        print("failed to save cached data", e)
    all_items_data = []
    local_versions = set()
    if self.config.configs:
      for rel in self.foundReleases:
        version = rel.get("tag_name")
        if version and version not in local_versions:
          all_items_data.append(
            ItemListData(
              version=version,
              status=Statuses.gameSelector,
              path=rel.get("path"),
              release=rel,
            )
          )
    else:
      version_map = {}
      if os.path.isdir(self.VERSIONS_DIR):
        for dirname in os.listdir(self.VERSIONS_DIR):
          full_path = os.path.join(self.VERSIONS_DIR, dirname)
          if os.path.isdir(full_path) and self.config.gameVersionExists(
            full_path, self.settings, self.settings.selectedOs
          ):
            thing = ItemListData(
              version=dirname,
              status=Statuses.localOnly,
              path=full_path,
              release=None,
            )
            all_items_data.append(thing)
            version_map[dirname] = thing
            local_versions.add(dirname)
      for rel in self.foundReleases:
        version = rel.get("tag_name")
        if version:
          if version in version_map:
            version_map[version].status = Statuses.local
            version_map[version].release = rel
          else:
            all_items_data.append(
              ItemListData(
                version=version,
                status=Statuses.online,
                path=None,
                release=rel,
              )
            )

    sorted_data = self.sortVersions(all_items_data)
    self.versionList.setUpdatesEnabled(False)
    self.versionList.blockSignals(True)
    try:
      self.activeItemRefs.clear()
      current_count = self.versionList.count()
      target_count = len(sorted_data)
      if current_count < target_count:
        for _ in range(target_count - current_count):
          self.addVersionItem(version="loading", status=Statuses.loadingInfo)
      elif current_count > target_count:
        for _ in range(current_count - target_count):
          self.versionList.takeItem(self.versionList.count() - 1)

      if self.gameName is not None:
        if os.path.isfile("images/" + self.gameName + ".png"):
          self.setWindowIcon(QIcon("images/" + self.gameName + ".png"))
      for i, data in enumerate(sorted_data):
        assert isinstance(data, ItemListData)
        item = self.versionList.item(i)

        widget = self.versionList.itemWidget(item)
        self.activeItemRefs[data.version] = widget
        assert isinstance(widget, VersionItemWidget)
        if self.settings.showLauncherImages:
          # if data.status == Statuses.gameSelector:
          #   assert data.release is not None
          #   widget.setIcon(data.release["config"].getImage(data.version))
          # else:
          #   widget.setIcon(self.config.getImage(data.version))
          imagePath = None
          if data.status == Statuses.gameSelector:
            assert data.release is not None
            imagePath = "images/" + data.version + ".png"
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
    self.versionList.blockSignals(False)
    self.versionList.setUpdatesEnabled(True)

  def loadLocalVersions(self):
    self.versionList.clear()

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

  def sortVersions(self, versions_data):
    last_ran = None
    if self.GAME_ID != "-":
      try:
        last_ran = f.read(
          os.path.join(
            LAUNCHER_START_PATH if True else "",
            self.GAME_ID,
            "launcherData/lastRanVersion.txt",
          )
        ).strip()
      except Exception as e:
        print("failed reading lastRanVersion", e)

    def getSortKey(item):
      version = item.version
      status = item.status

      is_localOnly = 1 if status == Statuses.localOnly else 0
      is_local = 1 if status == Statuses.local else 0

      is_last_ran = 1 if version == last_ran and is_local else 0

      version_is_numeric = 1 if re.match(r"^\d+$", version) else 0
      numeric_value = int(version) if version_is_numeric else 0

      return (
        is_last_ran,
        (1 if (version in self.downloadingVersions) else 0),
        is_localOnly,
        is_local,
        version_is_numeric,
        numeric_value if version_is_numeric else version,
      )

    versions_data.sort(key=getSortKey, reverse=True)

    return versions_data

  def downloadAllVersions(self):
    onlineCount = 0
    items = []
    for i in range(self.versionList.count()):
      item = self.versionList.item(i)
      data: ItemListData = item.data(Qt.ItemDataRole.UserRole)
      if data and data.status == Statuses.online:
        version = data.version
        if version not in self.downloadingVersions:
          items.append(item.data(Qt.ItemDataRole.UserRole))
          onlineCount += 1
    self.startQueuedDownloadRequest(*items)

    if onlineCount > 0:
      print(f"Added {onlineCount} Versions to the Download Queue.")
    else:
      print("No New Online Versions Found to Download.")

  class ReleaseFetchThread(QThread):
    progress = Signal(int, int, list)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, API_URL, pat=None, max_pages=1):
      super().__init__()
      self.pat = pat
      self.maxPages = max_pages
      self.API_URL = API_URL

    def run(self):
      if OFFLINE:
        self.finished.emit([])
        return
      try:
        releases = []
        headers = {"Authorization": f"token {self.pat}"} if self.pat else {}
        page = 0
        if self.maxPages == 0:
          rand = random.random()
          final_size = -1

          head = requests.head(
            f"{self.API_URL}?page=0&rand={rand}",
            headers=headers,
            timeout=10,
          )
          if "Link" in head.headers:
            m = re.search(
              r'\?page=(\d+)&rand=[\d.]+>; rel="last"',
              head.headers["Link"],
            )
            if m:
              final_size = int(m.group(1)) + 1

        while True:
          page += 1

          if self.maxPages > 0 and page > self.maxPages:
            break

          r = requests.get(
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

        self.finished.emit(releases)
      except Exception as e:
        self.error.emit(str(e))

  def goBackToSelector(self):
    if selectorConfig:
      # Re-run using the saved selector configuration
      run(selectorConfig, None)
      # Close the current game-specific launcher
      self.close()

  def __init__(self, config: Config, module_name):
    global launcherUpdateAlreadyChecked
    super().__init__()
    self.gameName = module_name
    self.releaseFetchingThread: Any = None
    self.config = config
    self.settings = SettingsData()
    self.activeItemRefs = {}
    self.activeDownloads = {}
    self.downloadQueue = []
    self.setWindowTitle(config.WINDOW_TITLE)
    self.setFixedSize(420, 600)
    self.setStyleSheet(f.read(os.path.join(LAUNCHER_START_PATH, "main.css")))
    self.localKeys = ["extraGameArgs"]
    self.GAME_ID = re.sub(
      r"_{2,}",
      "_",
      re.sub(
        r"[^\w\- ]", "_", f"{self.config.GH_USERNAME} - {self.config.GH_REPO}"
      ),
    ).strip()
    self.VERSIONS_DIR = os.path.join(
      LAUNCHER_START_PATH if True else "",
      self.GAME_ID,
      "versions",
    )
    self.GLOBAL_SETTINGS_FILE = os.path.join(
      LAUNCHER_START_PATH, "launcherData/launcherSettings.json"
    )
    self.LOCAL_SETTINGS_FILE = os.path.join(
      LAUNCHER_START_PATH if True else "",
      self.GAME_ID,
      "launcherData/launcherSettings.json",
    )

    main_layout = QVBoxLayout(self)
    if selectorConfig and selectorConfig != self.config:
      back_btn = self.newButton("<- Back to Selector", self.goBackToSelector)
      # Style it differently if you want (optional)
      main_layout.addWidget(back_btn)
    self.versionList = QListWidget()
    self.versionList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.versionList.customContextMenuRequested.connect(self.showContextMenu)
    main_layout.addWidget(self.versionList)
    if OFFLINE:
      offline_label = QLabel("OFFLINE MODE")
      offline_label.setStyleSheet("color: orange; font-weight: bold;")
      main_layout.addWidget(offline_label)

    self.versionList.itemDoubleClicked.connect(self.onVersionDoubleClicked)

    main_layout.addWidget(self.versionList)

    self.widgetsToSave = {}

    self.mainProgressBar = VersionItemWidget("", MISSING_COLOR)
    main_layout.addWidget(self.mainProgressBar)

    self.setupSettingsDialog()
    self.loadUserSettings()
    self.loadLocalVersions()

    main_layout.addWidget(self.newButton("Settings", self.openSettings))

    if self.config.configs is not None:
      self.VERSIONS_DIR = "///"
      self.foundReleases = list(
        map(
          lambda x: {"tag_name": x, "config": config.configs[x], "path": paths[x]}, config.configs # type: ignore
        )
      )
      self.updateVersionList()
      self.mainProgressBar.setModeDisabled()
      if not OFFLINE:
        if self.settings.checkForLauncherUpdatesWhenOpening:
          if not launcherUpdateAlreadyChecked:
            self.updateLauncher()
          launcherUpdateAlreadyChecked = True
      return
    self.API_URL = f"https://api.github.com/repos/{self.config.GH_USERNAME}/{self.config.GH_REPO}/releases"
    os.makedirs(os.path.join(LAUNCHER_START_PATH, "launcherData"), exist_ok=True)
    os.makedirs("images", exist_ok=True)
    os.makedirs(
      os.path.join(
        LAUNCHER_START_PATH if True else "",
        self.GAME_ID,
        "launcherData/cache",
      ),
      exist_ok=True,
    )
    self.gameDataLocation = os.path.join(
      (LAUNCHER_START_PATH if True else ""),
      self.GAME_ID,
      "gameData",
    )
    if config.CAN_USE_CENTRAL_GAME_DATA_FOLDER:
      os.makedirs(
        self.gameDataLocation,
        exist_ok=True,
      )

    self.foundReleases = json.loads(
      f.read(
        os.path.join(
          (LAUNCHER_START_PATH if True else ""),
          self.GAME_ID,
          "launcherData/cache/releases.json",
        ),
        "[]",
      )
    )
    self.updateVersionList()
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
      for i in range(self.versionList.count()):
        item = self.versionList.item(i)
        data: ItemListData = item.data(Qt.ItemDataRole.UserRole)
        if not data:
          continue
        if data.version == VERSION:
          if data.status == Statuses.online:
            if data.version not in self.downloadingVersions:
              self.startQueuedDownloadRequest(data)
          if data.status == Statuses.local or data.status == Statuses.localOnly:
            self.startGameVersion(data)

  def openSettings(self):
    result = self.settingsDialog.exec()
    if result == QDialog.DialogCode.Accepted:
      print("Saving settings...")
      self.saveUserSettings()
      self.updateVersionList()
    else:
      print("Changes discarded. Reverting UI...")
      self.loadUserSettings()

  def showContextMenu(self, pos):
    item = self.versionList.itemAt(pos)
    if not item:
      return

    data: ItemListData = item.data(Qt.ItemDataRole.UserRole)
    menu = QMenu(self)

    def newAction(text: str, onclick: Callable):
      run_action = menu.addAction(text)
      run_action.triggered.connect(onclick)

    print(data.status)
    if data.status == Statuses.gameSelector:
      if self.config.configs is not None:
        print(self.config.configs[data.version].LAUNCHER_ASSET_NAME)
        if self.config.configs[data.version].LAUNCHER_ASSET_NAME:
          menu.addAction(
            "Update",
            bind(
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
          f"Delete Version {data.version}", lambda: shutil.rmtree(data.path) # type: ignore
        )
      if data.release:
        newAction(
          f"{"Red" if data.status==Statuses.local else "D"}ownload Version {data.version}",
          lambda: self.startQueuedDownloadRequest(data),
        )

    menu.addSeparator()
    self.config.addContextMenuOptions(self, data, menu, newAction)
    menu.exec(self.versionList.mapToGlobal(pos))

  def startFetch(self, max_pages=1, noDefaultConnections=False):
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

  def mergeReleases(self, existing, new_data):

    merged = {rel["tag_name"]: rel for rel in existing}

    for rel in new_data:
      tag = rel.get("tag_name")
      if tag:
        merged[tag] = rel

    return list(merged.values())

  def startFullFetch(self):
    """Triggered by button to fetch everything."""
    print("Starting Full Release Fetch...")
    self.startFetch(max_pages=0)

  def onReleaseProgress(self, page, total, releases):
    self.mainProgressBar.setModeKnownEnd()
    self.mainProgressBar.setProgress((page / total) * 100)
    self.foundReleases = self.mergeReleases(self.foundReleases, releases)
    self.mainProgressBar.label.setText(
      f"Fetching {total} Page{'' if total==1 else 's'}... {(page / total) * 100}% - {page} / {total}"
    )
    self.updateVersionList()

  def onReleaseFinished(self, releases):
    self.mainProgressBar.label.setText("")
    self.mainProgressBar.setModeDisabled()
    self.foundReleases = self.mergeReleases(self.foundReleases, releases)
    self.updateVersionList()

  def setupSettingsDialog(self):
    self.settingsDialog = QDialog(self)
    self.settingsDialog.setWindowTitle("Settings")
    self.settingsDialog.setFixedWidth(600)
    outerLayout = QVBoxLayout(self.settingsDialog)

    # region launcher
    groupBox = QGroupBox("Launcher Settings")
    groupLayout = QVBoxLayout()

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

    def toggleAlwaysOnTop(win: Launcher, on):
      win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
      win.show()

    groupLayout.addWidget(
      self.newCheckbox(
        "Keep Launcher Always on Top",
        False,
        "keepLauncherAlwaysOnTop",
        onChange=bind(toggleAlwaysOnTop, self),
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
    groupBox = QGroupBox("Global Settings (All Games)")
    groupLayout = QVBoxLayout()

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

    fetchBtnRow = QHBoxLayout()
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
        "Close Launcher on Game Start (May Cause some Games to Not Start)",
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
    groupBox = QGroupBox(f"Local Settings ({self.config.GH_REPO})")
    groupLayout = QVBoxLayout()
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
    if self.config.USE_HARD_LINKS:
      groupLayout.addWidget(
        self.newCheckbox(
          "Replace Duplicate Game Files with Hardlinks",
          True,
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
        lambda: self.openFile(
          os.path.join(self.GAME_ID, "gameData")
          if self.config.CAN_USE_CENTRAL_GAME_DATA_FOLDER
          else self.GAME_ID
        ),
      )
    )
    if self.config.addCustomNodes:
      lastWidgetCount = len(self.widgetsToSave)
      self.config.addCustomNodes(self, groupLayout)
      for key in islice(self.widgetsToSave.keys(), lastWidgetCount, None):
        if key not in self.localKeys:
          self.localKeys.append(key)

    groupBox.setLayout(groupLayout)
    outerLayout.addWidget(groupBox)

    bottom_btn_layout = QHBoxLayout()
    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(self.settingsDialog.reject)
    done_btn = QPushButton("Done")
    done_btn.setDefault(True)
    done_btn.clicked.connect(self.settingsDialog.accept)

    bottom_btn_layout.addWidget(cancel_btn)
    bottom_btn_layout.addWidget(done_btn)
    outerLayout.addLayout(bottom_btn_layout)
    # endregion

  def updateSubLauncher(
    self,
    launcherSettings: Optional[Config] = None,
    data: Optional[ItemListData] = None,
    widget: Optional[VersionItemWidget] = None,
  ):
    """Refactored unified update logic for the launcher or sub-modules."""
    # Fallback to current config if none provided
    ls = launcherSettings or self.config

    # If no data object provided (e.g. from Settings button),
    # create a mock one or find the one matching the current game
    if data is None:
      # Assuming current running file is the target
      current_path = os.path.abspath(sys.modules[self.gameName].__file__) # type: ignore
      data = ItemListData(
        version=self.gameName,
        path=current_path,
        release=None,
        status=Statuses.gameSelector,
      )

    tag = data.version
    api_url = f"https://api.github.com/repos/{ls.LAUNCHER_GH_USERNAME or ls.GH_USERNAME}/{ls.LAUNCHER_GH_REPO or ls.GH_REPO}/releases"

    fetcher = self.ReleaseFetchThread(
      api_url, pat=self.settings.githubPat or None, max_pages=1
    )
    if not widget:
      widget = self.activeItemRefs.get(tag)
    assert isinstance(widget, VersionItemWidget)
    widget.setModeUnknownEnd()

    def on_metadata(widget: VersionItemWidget, releases):
      if not releases:
        return
      data.release = releases[0]
      assert data.release is not None
      widget.setModeKnownEnd()

      def on_progress(progress):
        widget.setProgress(progress)

      asset_name = ls.LAUNCHER_ASSET_NAME
      asset = next(
        (a for a in data.release.get("assets", []) if a["name"] == asset_name),
        None,
      )

      if not asset or tag in self.downloadingVersions:
        self.activeDownloads.pop(f"meta_{tag}", None)
        return

      self.downloadingVersions.append(tag)
      dest_dir = os.path.join(
        os.path.abspath(os.path.join(LAUNCHER_START_PATH, "-")), f"temp_{tag}"
      )
      out_file = os.path.join(dest_dir, asset["name"])
      os.makedirs(dest_dir, exist_ok=True)

      dl_thread = AssetDownloadThread(asset["browser_download_url"], out_file)
      self.activeDownloads[tag] = dl_thread

      def on_finished(path):
        widget.setModeDisabled()
        found = {"py": False, "png": False}
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
                if data.path and os.path.exists(data.path):
                  imgpath = os.path.join(
                    os.path.dirname(data.path),
                    "images",
                    f"{tag}.png",
                  )
                  os.remove(imgpath)
                  shutil.move(
                    os.path.join(root, f"{tag}.png"),
                    imgpath,
                  )
                  found["png"] = True
              if f"{tag}.py" in files:
                if data.path and os.path.exists(data.path):
                  os.remove(data.path)
                  shutil.move(
                    os.path.join(root, f"{tag}.py"), data.path
                  )
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
          self.updateVersionList()
          if found["py"]:
            self.showRestartPrompt(f"{tag} updated successfully.")

      dl_thread.progress.connect(on_progress)
      dl_thread.finished.connect(on_finished)
      dl_thread.finished.connect(dl_thread.deleteLater)
      dl_thread.start()

    fetcher.finished.connect(bind(on_metadata, widget))
    fetcher.finished.connect(fetcher.deleteLater)
    self.activeDownloads[f"meta_{tag}"] = fetcher
    fetcher.start()

  def showRestartPrompt(self, text):
    def restart():
      script_path = f'"{os.path.abspath(sys.argv[0])}"'
      executable = f'"{sys.executable}"'

      # We pass the quoted executable as the path and arg0,
      # then the quoted script path, then the rest of the args.
      os.execl(sys.executable, executable, script_path, *sys.argv[1:])

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

  def openFile(self, p: str):
    return QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(p)))

  def newSpinBox(self, min_val, max_val, default, saveId, width=60):
    node = QSpinBox()
    node.setRange(min_val, max_val)
    node.setValue(default)
    node.setFixedWidth(width)

    node.valueChanged.connect(lambda v: setattr(self.settings, saveId, v))

    setattr(self.settings, saveId, default)

    self.widgetsToSave[saveId] = node
    return node

  def newButton(self, text, onclick):
    node = QPushButton(text)
    node.pressed.connect(onclick)
    return node

  def newLabel(self, label_text, widget, addStretch=True):
    """Creates a horizontal row with a label and a widget."""
    row = QHBoxLayout()
    row.addWidget(QLabel(label_text))
    row.addWidget(widget)
    if addStretch:
      row.addStretch()
    return row

  def newCheckbox(self, text, default, saveId, tooltip="", onChange=None):
    node = QCheckBox(text)
    node.setChecked(default)
    if tooltip:
      node.setToolTip(tooltip)
    if onChange:
      node.toggled.connect(onChange)

    node.toggled.connect(lambda v: setattr(self.settings, saveId, v))
    setattr(self.settings, saveId, default)

    self.widgetsToSave[saveId] = node
    return node

  def newLineEdit(self, placeholder, saveId, password=False):
    node = QLineEdit()
    node.setPlaceholderText(placeholder)
    if password:
      node.setEchoMode(QLineEdit.EchoMode.Password)

    node.textChanged.connect(lambda v: setattr(self.settings, saveId, v))
    setattr(self.settings, saveId, "")

    self.widgetsToSave[saveId] = node
    return node

  def newSelectBox(
    self,
    values: Type[Enum] | list[str] | dict[str, Any] | set[str],
    default_value,
    saveId,
  ):
    node = QComboBox()

    node.usesEnum = False # type: ignore
    if isinstance(values, EnumMeta):
      node.usesEnum = True # type: ignore
      node.usedEnum = values # type: ignore
      for thing in values:
        node.addItem(thing.name, thing)
    elif isinstance(values, list):
      i = -1
      for thing in values:
        i += 1
        node.addItem(thing, i)
    elif isinstance(values, dict):
      for k, v in values.items():
        node.addItem(k, v)
    node.setCurrentIndex(default_value)
    node.currentIndexChanged.connect(
      lambda: setattr(self.settings, saveId, node.currentData())
    )
    setattr(self.settings, saveId, default_value)

    self.widgetsToSave[saveId] = node
    return node


_current_window = None


def run(config: Config, module_name):
  global _current_window

  is_new_app = False
  app = QApplication.instance()
  if not app:
    app = QApplication(sys.argv)
    is_new_app = True

 # Save the old geometry if a window is currently open
  _last_geometry = None
  if _current_window is not None:
    _last_geometry = _current_window.saveGeometry()

  _current_window = Launcher(config, module_name)

 # Apply the saved geometry before showing the window
  if _last_geometry is not None:
    _current_window.restoreGeometry(_last_geometry)

  _current_window.show()

  if is_new_app: # Only exec if loop isn't running
    if LAUNCHER_TO_LAUNCH in modules:
      lwin = _current_window
      run(modules[LAUNCHER_TO_LAUNCH], LAUNCHER_TO_LAUNCH)
      lwin.close()
    sys.exit(app.exec())


modules = {}
paths = {}
_is_selector_loading = False


def loadConfig(config: Config):
 # 1. Get the actual main module (the one running the loop)
  main_app = sys.modules["__main__"]

  caller_frame = inspect.stack()[1]
  caller_filename = caller_frame.filename
  module_name = Path(caller_filename).stem
 # 2. Check if the main app has the 'modules' list (meaning we are in the Selector)
 # _is_selector_loading is for if ran like `launcher`
 # hasattr(main_app, "modules") and isinstance(main_app.modules, dict) is for if ran like `python ./__init__.py`
  if _is_selector_loading or (
    hasattr(main_app, "modules") and isinstance(main_app.modules, dict)
  ):
    # We are inside the selector loop!
    # Use 'inspect' to automatically find the name of the file calling this function

    # Register the config into the MAIN list
    if _is_selector_loading:
      modules[module_name] = config
      paths[module_name] = os.path.abspath(caller_filename)
    else:
      main_app.paths[module_name] = os.path.abspath(caller_filename)
      main_app.modules[module_name] = config
  else:
    # We are NOT in the selector (User ran "python mygame.py" directly)
    run(config, module_name)


def findAllLaunchables():
  global selectorConfig, _is_selector_loading
  import importlib

  class supportedOs(Enum):
    windows = 0
    linux = 1

  _is_selector_loading = True
  sys.path.append(os.path.abspath("."))
  print("Current Working Directory:", os.getcwd())

  for filename in os.listdir():
    if filename.endswith(".py") and filename != "__init__.py":
      module_name = filename[:-3]
      try:
        importlib.import_module(module_name)
      except Exception as e:
        paths[module_name] = os.path.abspath(filename)
        modules[module_name] = Config(
          WINDOW_TITLE=module_name,
          GH_USERNAME="",
          GH_REPO="",
          supportedOs=supportedOs,
          hadErrorLoading=True,
          errorText=f"{e}",
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
#   # Check if any of the extensions exist
#   extensions = ("jpg", "jpeg", "png", "webp")
#   return next(
#     (p + "." + ext for ext in extensions if os.path.isfile(p + "." + ext)),
#     None,
#   )


if __name__ == "__main__":
  findAllLaunchables()
# LAUNCHER_START_PATH
#             if True
#             else ""
# self.settings.centralGameDataLocations

# TODO
# make ui reload when deleting things
