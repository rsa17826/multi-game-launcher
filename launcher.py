from dataclasses import dataclass
from typing import Callable
from functools import partial as bind


@dataclass
class Config:
  GH_USERNAME: str
  """github username eg rsa17826"""
  GH_REPO: str
  """github repo name eg vex-plus-plus"""
  getGameLogLocation: Callable
  gameLaunchRequested: Callable
  getAssetName: Callable
  gameVersionExists: Callable
  addCustomNodes: Callable
  WINDOW_TITLE: str = "Default Launcher"
  """what to set the launchers title to"""
  USE_HARD_LINKS: bool = False
  """if true will scan all new version downloads and check to see if any files are the same between different versions and replace the new files with hardlinks instead"""
  CAN_USE_CENTRAL_GAME_DATA_FOLDER: bool = False
  """if true will make all game versions appear to be launched from a single dir else will just launch each one from a separate location"""


from enum import Enum


class Statuses(Enum):
  local = 0
  online = 1
  # downloading = 2
  # waitingForDownload = 3


def run(config: Config):
  import sys
  import time
  import random
  import requests
  from enum import Enum
  import json
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
  )
  from PySide6.QtCore import QThread, Signal
  from PySide6.QtGui import (
    QPainter,
    QLinearGradient,
    QColor,
  )
  from PySide6.QtCore import QUrl
  from PySide6.QtCore import QTimer
  import os
  import zipfile
  import py7zr
  import re
  from pathlib import Path
  from PySide6.QtCore import Qt, QRectF
  import math

  import hashlib

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

  OFFLINE = "offline" in sys.argv

  MAIN_LOADING_COLOR = (0, 210, 255)
  UNKNOWN_TIME_LOADING_COLOR = (255, 108, 0)
  GAME_ID = re.sub(
    r"_{2,}",
    "_",
    re.sub(r"[^\w\- ]", "_", f"{config.GH_USERNAME} - {config.GH_REPO}"),
  ).strip()
  VERSIONS_DIR = os.path.join(GAME_ID, "versions")
  API_URL = (
    f"https://api.github.com/repos/{config.GH_USERNAME}/{config.GH_REPO}/releases"
  )

  LOCAL_COLOR = Qt.GlobalColor.green
  ONLINE_COLOR = Qt.GlobalColor.cyan
  MISSING_COLOR = Qt.GlobalColor.gray

  os.makedirs("./launcherData", exist_ok=True)

  def getFileHash(path):
    """Calculate SHA256 hash of a file in chunks to save memory."""
    hasher = hashlib.sha256()
    try:
      with open(path, "rb") as f:
        while chunk := f.read(8192):
          hasher.update(chunk)
      return hasher.hexdigest()
    except Exception:
      return None

  def deduplicateWithHardlinks(new_version_dir):
    if not config.USE_HARD_LINKS:
      return

    file_map = {}

    for root, dirs, files in os.walk(VERSIONS_DIR):

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
              if getFileHash(new_file_path) == getFileHash(candidate):
                print(f"Hardlinking: {filename} -> {candidate}")
                os.remove(new_file_path)
                os.link(candidate, new_file_path)
        except Exception as e:
          print(f"Error processing {filename}: {e}")

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

  class ReleaseFetchThread(QThread):
    progress = Signal(int, int, list)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, pat=None, max_pages=1):
      super().__init__()
      self.pat = pat
      self.maxPages = max_pages

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
            f"{API_URL}?page=0&rand={rand}", headers=headers, timeout=10
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
            f"{API_URL}?page={page}", headers=headers, timeout=30
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

  class VersionItemWidget(QWidget):
    class ProgressTypes(Enum):
      leftToRight = 0
      both = 1
      rightToLeft = 2

    def __init__(self, text="", color=MISSING_COLOR):
      super().__init__()
      self.text = text
      self.progress = 0
      self.setModeUnknownEnd()
      self.startTime = 0
      self.animSpeed = 10
      self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
      self.setStyleSheet("background: transparent; border: none;")

      self.label = QLabel(text)

      color_hex = color.name
      self.label.setStyleSheet(f"background: transparent; color: {color_hex};")

      layout = QHBoxLayout(self)
      layout.setContentsMargins(5, 0, 5, 0)
      layout.addWidget(self.label)
      layout.addStretch()

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
        self.progress = int(
          ((time.time() - self.startTime) * self.animSpeed) % 100
        )
        QTimer.singleShot(16, self.update)

      if self.progressType == self.ProgressTypes.both:
        fill_end = w * self.progress / 100
        solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
        tip_rect = QRectF(
          solid_rect.right(), 0, int(min(gradSize, fill_end)), h
        )
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
        tip_rect = QRectF(
          max(fill_start, 0), 0, min(gradSize, w - fill_start), h
        )
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
      return None

  class Launcher(QWidget):
    def addVersionItem(
      self, version: str, status: Statuses, path=None, release=None
    ):
      item = QListWidgetItem()

      if status == Statuses.local:
        color = LOCAL_COLOR
      elif status == Statuses.online:
        color = ONLINE_COLOR
      else:
        color = MISSING_COLOR

      text = (
        f"Run version {version}"
        if status == Statuses.local
        else f"Download version {version}"
      )

      widget = VersionItemWidget(text, color)
      widget.setModeKnownEnd()

      item.setSizeHint(widget.sizeHint())
      self.versionList.addItem(item)
      self.versionList.setItemWidget(item, widget)

      item.setData(
        Qt.ItemDataRole.UserRole,
        {
          "version": version,
          "status": status,
          "path": path,
          "release": release,
        },
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
        else:
          continue

        if key in self.localKeys:
          local_data[key] = value
        else:
          global_data[key] = value

      try:
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
        if os.path.exists(self.LOCAL_SETTINGS_FILE):
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
        if widget:
          if isinstance(widget, QLineEdit):
            widget.setText(str(value))
          elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
          elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))

    def closeEvent(self, event):
      self.saveUserSettings()
      super().closeEvent(event)

    downloadingVersions = []

    def onVersionDoubleClicked(self, item):
      data = item.data(Qt.ItemDataRole.UserRole)
      if not data:
        return

      if data["status"] == Statuses.local:
        path = data.get("path")
        if path:
          config.gameLaunchRequested(path)
          f.write(
            os.path.join(GAME_ID, "launcherData/lastRanVersion.txt"),
            data.get("version"),
          )
          if self.settings.closeOnLaunch:
            QApplication.quit()
        return

      if data["status"] == Statuses.online:
        self.startQueuedDownloadRequest(item.data(Qt.ItemDataRole.UserRole))

    def startQueuedDownloadRequest(self, *versions):
      for data in versions:
        tag = data['version']
        if tag in self.downloadingVersions:
          return

        self.downloadingVersions.append(tag)
        release = data.get("release")
        asset = next(
          (
            a
            for a in release.get("assets", [])
            if a["name"] == config.getAssetName()
          ),
          None,
        )

        if not asset:
          print(f"Asset Not Found for {tag}")
          self.downloadingVersions.remove(tag)
          return

        dest_dir = os.path.join(VERSIONS_DIR, tag)
        out_file = os.path.join(dest_dir, asset["name"])

        widget = self.activeItemRefs[data["version"]]
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

          if extracted and config.USE_HARD_LINKS:
            deduplicateWithHardlinks(dest_dir)
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
      f.write(
        os.path.join(GAME_ID, "launcherData/cache/releases.json"),
        json.dumps(self.foundReleases),
      )
      all_items_data = []
      local_versions = set()
      if os.path.isdir(VERSIONS_DIR):
        for dirname in os.listdir(VERSIONS_DIR):
          full_path = os.path.join(VERSIONS_DIR, dirname)
          if os.path.isdir(full_path) and config.gameVersionExists(full_path):
            all_items_data.append(
              {
                "version": dirname,
                "status": Statuses.local,
                "path": full_path,
                "release": None,
              }
            )
            local_versions.add(dirname)
      for rel in self.foundReleases:
        version = rel.get("tag_name")
        if version and version not in local_versions:
          all_items_data.append(
            {
              "version": version,
              "status": Statuses.online,
              "path": None,
              "release": rel,
            }
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
            self.addVersionItem(version="loading", status=Statuses.online)
        elif current_count > target_count:
          for _ in range(current_count - target_count):
            self.versionList.takeItem(self.versionList.count() - 1)

        for i, data in enumerate(sorted_data):
          item = self.versionList.item(i)

          widget = self.versionList.itemWidget(item)
          self.activeItemRefs[data["version"]] = widget
          assert isinstance(widget, VersionItemWidget)
          if data["version"] in self.downloadingVersions:
            if not widget.noKnownEndPoint:
              widget.setModeUnknownEnd()
            widget.label.setText(f"Waiting To Download: {data['version']}")
          else:
            widget.setModeDisabled()
            widget.label.setText(
              f"Run version {data['version']}"
              if data["status"] == Statuses.local
              else f"Download version {data['version']}"
            )
          match data["status"]:
            case Statuses.local:
              new_color = LOCAL_COLOR
            case Statuses.online:
              new_color = ONLINE_COLOR
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

      if not os.path.isdir(VERSIONS_DIR):
        return

      for dirname in sorted(os.listdir(VERSIONS_DIR), reverse=True):
        full_path = os.path.join(VERSIONS_DIR, dirname)
        if not os.path.isdir(full_path):
          continue

        if not config.gameVersionExists(full_path):
          continue

        self.addVersionItem(
          version=dirname, status=Statuses.local, path=full_path
        )

    def sortVersions(self, versions_data):

      last_ran = f.read(
        os.path.join(GAME_ID, "launcherData/lastRanVersion.txt")
      ).strip()

      def getSortKey(item):
        version = item["version"]
        status = item["status"]

        is_local = 1 if status == Statuses.local else 0

        is_last_ran = 1 if version == last_ran and is_local else 0

        version_is_numeric = 1 if re.match(r"^\d+$", version) else 0
        numeric_value = int(version) if version_is_numeric else 0

        return (
          is_last_ran,
          (1 if (version in self.downloadingVersions) else 0),
          is_local,
          version_is_numeric,
          numeric_value if version_is_numeric else version,
        )

      versions_data.sort(key=getSortKey, reverse=True)

      return versions_data

    def downloadAllVersions(self):
      onlineCount = 0
      for i in range(self.versionList.count()):
        item = self.versionList.item(i)
        data = item.data(Qt.ItemDataRole.UserRole)
        items = []
        if data and data.get("status") == Statuses.online:
          version = data.get("version")
          if version not in self.downloadingVersions:
            items.append(item.data(Qt.ItemDataRole.UserRole))
            onlineCount += 1
        self.startQueuedDownloadRequest(*items)

      if onlineCount > 0:
        print(f"Added {onlineCount} Versions to the Download Queue.")
      else:
        print("No New Online Versions Found to Download.")

    def __init__(self):
      super().__init__()
      self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
      self.settings = SettingsData()
      self.activeItemRefs = {}
      self.activeDownloads = {}
      self.downloadQueue = []
      self.setWindowTitle(config.WINDOW_TITLE)
      self.setFixedSize(420, 600)
      self.setStyleSheet(f.read("./main.css"))
      self.localKeys = ["extraGameArgs"]

      self.GLOBAL_SETTINGS_FILE = "./launcherData/launcherSettings.json"
      self.LOCAL_SETTINGS_FILE = os.path.join(
        GAME_ID, "launcherData/launcherSettings.json"
      )
      os.makedirs(os.path.join(GAME_ID, "launcherData/cache"), exist_ok=True)
      if config.CAN_USE_CENTRAL_GAME_DATA_FOLDER:
        os.makedirs(os.path.join(GAME_ID, "gameData"), exist_ok=True)

      main_layout = QVBoxLayout(self)

      self.versionList = QListWidget()
      self.loadLocalVersions()

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

      main_layout.addWidget(self.newButton("Settings", self.openSettings))

      self.foundReleases = json.loads(
        f.read(os.path.join(GAME_ID, "launcherData/cache/releases.json"), "[]")
      )
      self.updateVersionList()
      if not OFFLINE and self.settings.fetchOnLoad:
        self.startFetch(max_pages=self.settings.maxPagesOnLoad)
        self.releaseFetchingThread.error.connect(
          lambda e: print("Release fetch error:", e)
        )
        self.releaseFetchingThread.start()
        self.mainProgressBar.show()
      else:
        self.mainProgressBar.setProgress(101)

    def openSettings(self):
      result = self.settingsDialog.exec()
      if result == QDialog.DialogCode.Accepted:
        print("Saving settings...")
        self.saveUserSettings()
      else:
        print("Changes discarded. Reverting UI...")
        self.loadUserSettings()

    def startFetch(self, max_pages=1):
      """Standard fetch with a page limit."""
      if (
        self.releaseFetchingThread.isRunning()
      ):
        return

      self.releaseFetchingThread = ReleaseFetchThread(
        pat=self.settings.githubPat or None, max_pages=max_pages
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
      self.mainProgressBar.setProgress(101)
      self.foundReleases = self.mergeReleases(self.foundReleases, releases)
      self.updateVersionList()

    def setupSettingsDialog(self):
      self.settingsDialog = QDialog(self)
      self.settingsDialog.setWindowTitle("Settings")
      self.settingsDialog.setFixedWidth(420)
      outer_layout = QVBoxLayout(self.settingsDialog)

      global_box = QGroupBox("Global Settings (All Games)")
      global_layout = QVBoxLayout()

      global_layout.addLayout(
        self.newRow(
          "Max Concurrent Downloads:",
          self.newSpinBox(0, 10, 3, "maxConcurrentDls"),
        )
      )

      global_layout.addWidget(
        self.newCheckbox(
          "Check for Launcher Updates when Opening",
          False,
          "checkForLauncherUpdatesWhenOpening",
        )
      )
      global_layout.addWidget(
        self.newCheckbox(
          "Fetch Releases on Launcher Start", True, "fetchOnLoad"
        )
      )

      global_layout.addLayout(
        self.newRow(
          "Max Pages to Fetch:",
          self.newSpinBox(0, 100, 1, "maxPagesOnLoad"),
        )
      )

      fetch_btn_row = QHBoxLayout()
      assert isinstance(self.settings.maxPagesOnLoad, int)
      fetch_btn_row.addWidget(
        self.newButton(
          "Fetch Recent Updates",
          lambda: self.startFetch(max_pages=self.settings.maxPagesOnLoad),
        )
      )
      fetch_btn_row.addWidget(
        self.newButton("Sync Full History", self.startFullFetch)
      )
      global_layout.addLayout(fetch_btn_row)
      global_layout.addWidget(
        self.newButton(
          "Download All Game Versions (May Hang for a Bit)",
          self.downloadAllVersions,
        )
      )
      global_layout.addWidget(
        self.newCheckbox(
          "Close Launcher on Game Start (May Cause some Games to Not Start)",
          False,
          "closeOnLaunch",
        )
      )
      global_layout.addLayout(
        self.newRow(
          "GitHub PAT (Optional):",
          self.newLineEdit(
            "GitHub PAT (Optional)", "githubPat", password=True
          ),
        )
      )

      global_box.setLayout(global_layout)
      outer_layout.addWidget(global_box)

      local_box = QGroupBox(f"Local Settings ({config.GH_REPO})")
      local_layout = QVBoxLayout()

      local_layout.addLayout(
        self.newRow(
          "Extra Game Args:",
          self.newLineEdit("Extra Game Args", "extraGameArgs"),
        )
      )

      if config.addCustomNodes:
        custom_widgets = config.addCustomNodes(self, local_layout)
        if custom_widgets:
          for key, widget in custom_widgets.items():
            self.widgetsToSave[key] = widget
            if key not in self.localKeys:
              self.localKeys.append(key)

      local_box.setLayout(local_layout)
      outer_layout.addWidget(local_box)

      bottom_btn_layout = QHBoxLayout()
      cancel_btn = QPushButton("Cancel")
      cancel_btn.clicked.connect(self.settingsDialog.reject)
      done_btn = QPushButton("Done")
      done_btn.setDefault(True)
      done_btn.clicked.connect(self.settingsDialog.accept)

      bottom_btn_layout.addWidget(cancel_btn)
      bottom_btn_layout.addWidget(done_btn)
      outer_layout.addLayout(bottom_btn_layout)

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

    def newRow(self, label_text, widget, saveId=None):
      """Creates a horizontal row with a label and a widget."""
      row = QHBoxLayout()
      row.addWidget(QLabel(label_text))
      row.addWidget(widget)
      row.addStretch()
      if saveId:
        self.widgetsToSave[saveId] = widget
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

  app = QApplication(sys.argv)
  window = Launcher()
  window.show()

  sys.exit(app.exec())
