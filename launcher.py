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
    QPlainTextEdit,
    QDialog,
    QGroupBox,
  )
  from PySide6.QtCore import QThread, Signal
  from PySide6.QtGui import (
    QDesktopServices,
    QTextCursor,
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

    @staticmethod
    def append(
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
        "a",
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
      ) as f:
        f.write(text)
      return text

    @staticmethod
    def writeline(
      file,
      text,
      buffering: int = -1,
      encoding: str | None = None,
      errors: str | None = None,
      newline: str | None = None,
      closefd: bool = True,
      opener=None,
    ):
      with open(
        file,
        "a",
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
      ) as f:
        f.write("\n" + text)
      return text

  SETTINGS_FILE = "launcher_settings.json"

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

  def get_file_hash(path):
    """Calculate SHA256 hash of a file in chunks to save memory."""
    hasher = hashlib.sha256()
    try:
      with open(path, "rb") as f:
        while chunk := f.read(8192):
          hasher.update(chunk)
      return hasher.hexdigest()
    except Exception:
      return None

  def deduplicate_with_hardlinks(new_version_dir):
    if not config.USE_HARD_LINKS:
      return

    # { (size, filename): existing_file_path }
    file_map = {}

    # 1. Map out existing potential "source" files
    for root, dirs, files in os.walk(VERSIONS_DIR):
      # Skip the new directory
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

    # 2. Process new files
    for root, dirs, files in os.walk(new_version_dir):
      for filename in files:
        new_file_path = os.path.join(root, filename)
        try:
          new_stat = os.stat(new_file_path)

          # If the new file is somehow already a link, skip it
          if new_stat.st_nlink > 1:
            continue

          candidates = file_map.get((new_stat.st_size, filename))

          if candidates is not None:
            for candidate in candidates:
              # Final safety check: ensure we aren't linking a file to itself
              if os.path.abspath(new_file_path) == os.path.abspath(
                candidate
              ):
                continue
              # print(
              #   new_file_path,
              #   get_file_hash(new_file_path),
              #   candidate,
              #   get_file_hash(candidate),
              # )
              if get_file_hash(new_file_path) == get_file_hash(candidate):
                print(f"Hardlinking: {filename} -> {candidate}")
                os.remove(new_file_path)
                os.link(candidate, new_file_path)
        except Exception as e:
          print(f"Error processing {filename}: {e}")

  def add_version_item(list_widget, version, status, path=None, release=None):
    item = QListWidgetItem()

    # Determine color based on status
    if status == "Local":
      color = LOCAL_COLOR
    elif status == "Online":
      color = ONLINE_COLOR
    else:
      color = MISSING_COLOR

    text = (
      f"Run version {version}"
      if status == "Local"
      else f"Download version {version}"
    )

    # Pass the color to the widget
    widget = VersionItemWidget(text, color)
    widget.setModeKnownEnd()

    item.setSizeHint(widget.sizeHint())
    list_widget.addItem(item)
    list_widget.setItemWidget(item, widget)

    item.setData(
      Qt.ItemDataRole.UserRole,
      {
        "version": version,
        "status": status,
        "path": path,
        "widget": widget,
        "release": release,
      },
    )

  class AssetDownloadThread(QThread):
    progress = Signal(int)  # percent
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

  # ------------------- Release Fetch Thread -------------------
  class ReleaseFetchThread(QThread):
    progress = Signal(int, int, list)  # current page, total pages
    finished = Signal(list)  # list of releases
    error = Signal(str)

    def __init__(self, pat=None, max_pages=1):
      super().__init__()
      self.pat = pat
      self.max_pages = max_pages  # 0 means "All"

    def run(self):
      if OFFLINE:
        self.finished.emit([])
        return
      try:
        releases = []
        headers = {"Authorization": f"token {self.pat}"} if self.pat else {}
        page = 0
        if self.max_pages == 0:
          rand = random.random()
          final_size = -1

          # HEAD request to detect total pages
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

        # Fetch pages
        while True:
          page += 1
          # Check if we should stop based on max_pages
          if self.max_pages > 0 and page > self.max_pages:
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
            (self.max_pages) if self.max_pages > 0 else final_size,
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

    def __init__(self, text="", color=MISSING_COLOR):  # Added color argument
      super().__init__()
      self.text = text
      self.progress = 0
      self.setModeUnknownEnd()
      self.startTime = 0
      self.animSpeed = 10
      self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
      self.setStyleSheet("background: transparent; border: none;")

      self.label = QLabel(text)
      # Convert QColor to hex for stylesheet
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

    def set_label_color(self, color):
      self.label.setStyleSheet(f"background: transparent; color: {color.name};")

    def set_progress(self, percent):
      if percent == self.progress:
        return
      if self.noKnownEndPoint:
        self.noKnownEndPoint = False
        self.setModeKnownEnd()
      self.progress = percent
      self.update()  # repaint

    def paintEvent(self, event):
      if not ((0 < self.progress <= 100) or self.noKnownEndPoint):
        super().paintEvent(event)
        return

      painter = QPainter(self)
      painter.setRenderHint(QPainter.RenderHint.Antialiasing)
      rect = self.rect()
      w = rect.width()
      h = rect.height()
      gradSize = int(w / 8)  # Slightly smaller grad for 'both' to avoid crowding
      minGradAlpha = 50
      if self.noKnownEndPoint:
        self.progress = int(
          ((time.time() - self.startTime) * self.animSpeed) % 100
        )
        QTimer.singleShot(0, self.update)

      if self.progressType == self.ProgressTypes.both:
        fill_end = w * self.progress / 100
        solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
        tip_rect = QRectF(
          solid_rect.right(), 0, int(min(gradSize, fill_end)), h
        )
        self._draw_progress(painter, solid_rect, minGradAlpha)
        self._draw_gradient(
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
        self._draw_progress(painter, solid_rect, minGradAlpha)
        self._draw_gradient(
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
        self._draw_progress(painter, solid_rect, minGradAlpha)
        self._draw_gradient(
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
        self._draw_progress(painter, solid_rect, minGradAlpha)
        self._draw_gradient(
          painter,
          tip_rect,
          tip_rect.topRight(),
          tip_rect.topLeft(),
          minGradAlpha,
        )

      super().paintEvent(event)

    def _draw_progress(self, painter, rect, alpha):
      if rect.width() <= 0:
        return
      painter.fillRect(rect, QColor(*self.progressColor, alpha))

    def _draw_gradient(self, painter, rect, start_pt, end_pt, min_alpha):
      if rect.width() <= 0:
        return
      grad = QLinearGradient(start_pt, end_pt)
      exponent = 5
      for i in range(11):
        pos = i / 10.0
        alpha = int(min_alpha + (255 - min_alpha) * math.pow(pos, exponent))
        grad.setColorAt(pos, QColor(*self.progressColor, alpha))
      painter.fillRect(rect, grad)

  class Launcher(QWidget):
    def save_user_settings(self):
      local_data = {}
      global_data = {}

      for key, widget in self.widgets_to_save.items():
        # Determine value based on widget type
        if isinstance(widget, QLineEdit):
          value = widget.text()
        elif isinstance(widget, QCheckBox):
          value = widget.isChecked()
        elif isinstance(widget, QSpinBox):
          value = widget.value()
        else:
          continue

        # Sort into appropriate bucket
        if key in self.local_keys:
          local_data[key] = value
        else:
          global_data[key] = value

      # Save to separate files
      try:
        with open(self.local_settings_file, "w", encoding="utf-8") as f:
          json.dump(local_data, f, indent=2)
        with open(self.GLOBAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
          json.dump(global_data, f, indent=2)
      except Exception as e:
        print(f"Failed to save settings: {e}")

    def load_user_settings(self):
      # Load both files
      local_data = {}
      global_data = {}

      try:
        if os.path.exists(self.local_settings_file):
          with open(self.local_settings_file, "r", encoding="utf-8") as f:
            local_data = json.load(f)
        if os.path.exists(self.GLOBAL_SETTINGS_FILE):
          with open(self.GLOBAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
            global_data = json.load(f)
      except Exception as e:
        print(f"Failed to load settings: {e}")

      # Combine for easy application
      combined = {**global_data, **local_data}

      for key, value in combined.items():
        widget = self.widgets_to_save.get(key)
        if widget:
          if isinstance(widget, QLineEdit):
            widget.setText(str(value))
          elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
          elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))

    def closeEvent(self, event):
      self.save_user_settings()
      super().closeEvent(event)

    downloadingVersions = []

    def on_version_double_clicked(self, item):
      data = item.data(Qt.ItemDataRole.UserRole)
      if not data:
        return

      # Local → run
      if data["status"] == "Local":
        path = data.get("path")
        if path:
          config.gameLaunchRequested(path)
          f.write(
            os.path.join(GAME_ID, "launcherData/lastRanVersion.txt"),
            data.get("version"),
          )
          # if settings.closeOnGameStart:

        return

      # Online → download
      if data["status"] == "Online":
        self.start_queued_download_request(item)

    def start_queued_download_request(self, item):
      data = item.data(Qt.ItemDataRole.UserRole)
      tag = data["version"]

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
        print(f"Asset not found for {tag}")
        self.downloadingVersions.remove(tag)
        return

      dest_dir = os.path.join(VERSIONS_DIR, tag)
      os.makedirs(dest_dir, exist_ok=True)
      out_file = os.path.join(dest_dir, asset["name"])

      # UI state: Waiting (Orange Pulse)
      widget = data["widget"]
      widget.label.setText(f"Waiting: {tag}")
      widget.setModeUnknownEnd()

      # Add to queue and process
      self.download_queue.append(
        (item, asset["browser_download_url"], out_file, dest_dir)
      )
      self.process_download_queue()

    def process_download_queue(self):
      # While we have room for more downloads and items in the queue
      while self.download_queue and (
        len(self.active_downloads) < self.max_dl_spinbox.value()
        or self.max_dl_spinbox.value() == 0
      ):
        next_dl = self.download_queue.pop(0)
        self.start_actual_download(*next_dl)

    def start_actual_download(self, item, url, out_file, dest_dir):
      data = item.data(Qt.ItemDataRole.UserRole)
      tag = data["version"]

      # 1. Create the thread
      dl_thread = AssetDownloadThread(url, out_file)
      # Store a strong reference to prevent garbage collection
      self.active_downloads[tag] = dl_thread

      def on_finished(path):
        # Move cleanup to the start of the finish logic
        self.process_download_queue()

        # Find the CURRENT item reference (it may have moved due to sorting)
        current_item = self.active_item_refs.get(tag)
        assert current_item is not None
        current_widget = self.version_list.itemWidget(current_item)
        assert isinstance(current_widget, VersionItemWidget)
        current_widget.label.setText(f"Extracting {tag}...")
        current_widget.setModeUnknownEnd()  # Pulse while unzipping

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
            deduplicate_with_hardlinks(dest_dir)
        except Exception as e:
          print(f"Extraction error for {tag}: {e}")

        # Cleanup tracking lists
        if tag in self.downloadingVersions:
          self.downloadingVersions.remove(tag)

        # 2. Finalize UI
        if extracted:
          print(f"Finished processing {tag}")
          # Use a small delay before clearing the thread reference to prevent the "Destroyed" error
          QTimer.singleShot(100, lambda: self.active_downloads.pop(tag, None))
          # Trigger a refresh to show the new 'Local' status
          assert isinstance(current_widget, VersionItemWidget)
          current_widget.setModeKnownEnd()
          current_widget.set_progress(101)
          self.update_version_list()
        else:
          self.active_downloads.pop(tag, None)

      # Connect signals
      dl_thread.progress.connect(bind(self.handle_download_progress, tag))
      dl_thread.finished.connect(on_finished)
      dl_thread.error.connect(lambda e: print(f"DL Error {tag}: {e}"))

      # Ensure thread deletes itself properly
      dl_thread.finished.connect(dl_thread.deleteLater)

      dl_thread.start()

    def handle_download_progress(self, version_tag, percentage):
      # O(1) Lookup - No Loop!
      item = self.active_item_refs.get(version_tag)

      if item:
        widget = self.version_list.itemWidget(item)
        assert isinstance(widget, VersionItemWidget)
        widget.set_progress(percentage)
        widget.label.setText(f"Downloading {version_tag}... ({percentage}%)")

    def update_version_list(self):
      if not self.version_list:
        return
      f.write(
        os.path.join(GAME_ID, "launcherData/cache/releases.json"),
        json.dumps(self.found_releases),
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
                "status": "Local",
                "path": full_path,
                "release": None,
              }
            )
            local_versions.add(dirname)
      for rel in self.found_releases:
        version = rel.get("tag_name")
        if version and version not in local_versions:
          all_items_data.append(
            {
              "version": version,
              "status": "Online",
              "path": None,
              "release": rel,
            }
          )

      sorted_data = self.sort_versions(all_items_data)
      self.version_list.setUpdatesEnabled(False)
      self.version_list.blockSignals(True)
      try:
        self.active_item_refs.clear()
        current_count = self.version_list.count()
        target_count = len(sorted_data)
        if current_count < target_count:
          for _ in range(target_count - current_count):
            add_version_item(self.version_list, "loading", "Online")
        elif current_count > target_count:
          for _ in range(current_count - target_count):
            self.version_list.takeItem(self.version_list.count() - 1)

        for i, data in enumerate(sorted_data):
          item = self.version_list.item(i)
          self.active_item_refs[data["version"]] = item
          item = self.version_list.item(i)
          old_data = item.data(Qt.ItemDataRole.UserRole)
          if (
            old_data
            and old_data.get("version") == data["version"]
            and old_data.get("status") == data["status"]
          ):
            continue

          widget = self.version_list.itemWidget(item)
          new_text = (
            f"Run version {data['version']}"
            if data["status"] == "Local"
            else f"Download version {data['version']}"
          )
          if data["version"] in self.downloadingVersions:
            new_text = f"Downloading {data['version']}..."
          new_color = (
            LOCAL_COLOR
            if data["status"] == "Local"
            else (
              ONLINE_COLOR
              if data["status"] == "Online"
              else MISSING_COLOR
            )
          )
          assert isinstance(widget, VersionItemWidget)
          widget.label.setText(new_text)
          widget.set_label_color(new_color)
          if (
            data["status"] == "Online"
            and data["version"] not in self.downloadingVersions
          ):
            widget.setModeKnownEnd()
            widget.set_progress(0)
          data["widget"] = widget
          item.setData(Qt.ItemDataRole.UserRole, data)
      except Exception as e:
        print(f"Update Error: {e}")
      finally:
        self.version_list.blockSignals(False)
        self.version_list.setUpdatesEnabled(True)

    def load_local_versions(self):
      self.version_list.clear()

      if not os.path.isdir(VERSIONS_DIR):
        return

      for dirname in sorted(os.listdir(VERSIONS_DIR), reverse=True):
        full_path = os.path.join(VERSIONS_DIR, dirname)
        if not os.path.isdir(full_path):
          continue

        if not config.gameVersionExists(full_path):
          continue

        add_version_item(
          self.version_list, dirname, status="Local", path=full_path
        )

    def sort_versions(self, versions_data):
      # 1. Load the last ran version
      last_ran = f.read(
        os.path.join(GAME_ID, "launcherData/lastRanVersion.txt")
      ).strip()

      def get_sort_key(item):
        version = item["version"]
        status = item["status"]

        # Priority 2: Local Status
        # (Assuming "Local" in your Python code corresponds to "LocalOnly")
        is_local = 1 if status == "Local" else 0

        # Priority 1: Last Ran Version
        is_last_ran = 1 if version == last_ran and is_local else 0

        # Priority 3: Numeric vs String versioning
        # We use a tuple for the key. Python sorts tuples element by element.
        # Since you .Reverse() at the end, we'll keep values positive
        # and use reverse=True in the sort() call.

        version_is_numeric = 1 if re.match(r"^\d+$", version) else 0
        numeric_value = int(version) if version_is_numeric else 0

        # The key returns: (IsLastRan, IsLocal, IsNumeric, Value/String)
        return (
          is_last_ran,
          is_local,
          version_is_numeric,
          numeric_value if version_is_numeric else version,
        )

      versions_data.sort(key=get_sort_key, reverse=True)
      # versions_data.sort(key=get_sort_key, reverse=False)
      return versions_data

    def download_all_versions(self):
      online_count = 0
      for i in range(self.version_list.count()):
        item = self.version_list.item(i)
        data = item.data(Qt.ItemDataRole.UserRole)

        # Check if it's Online and not already in the process of downloading
        if data and data.get("status") == "Online":
          version = data.get("version")
          if version not in self.downloadingVersions:
            # We reuse the logic from on_version_double_clicked
            self.start_queued_download_request(item)
            online_count += 1

      if online_count > 0:
        print(f"Added {online_count} versions to the download queue.")
      else:
        print("No new online versions found to download.")

    def __init__(self):
      super().__init__()
      self.active_item_refs = {}  # Key: version_tag, Value: QListWidgetItem
      self.active_downloads = {}  # {version_tag: thread_object}
      self.download_queue = []  # List of (item, url, out_file, extract_dir)
      self.setWindowTitle(config.WINDOW_TITLE)
      self.setFixedSize(420, 600)
      self.setStyleSheet(f.read("./main.css"))
      self.local_keys = ["extra_game_args"]
      self.global_keys = [
        "github_pat",
        "cb_check for launcher updates when opening",
        "max_concurrent_dls",
      ]

      self.GLOBAL_SETTINGS_FILE = "./launcherData/launcherSettings.json"
      self.local_settings_file = os.path.join(
        GAME_ID, "launcherData/launcherSettings.json"
      )
      os.makedirs(os.path.join(GAME_ID, "launcherData/cache"), exist_ok=True)
      if config.CAN_USE_CENTRAL_GAME_DATA_FOLDER:
        os.makedirs(os.path.join(GAME_ID, "gameData"), exist_ok=True)

      main_layout = QVBoxLayout(self)

      # Version list
      self.version_list = QListWidget()
      self.load_local_versions()

      main_layout.addWidget(self.version_list)
      if OFFLINE:
        offline_label = QLabel("OFFLINE MODE")
        offline_label.setStyleSheet("color: orange; font-weight: bold;")
        main_layout.addWidget(offline_label)

      self.version_list.itemDoubleClicked.connect(self.on_version_double_clicked)

      main_layout.addWidget(self.version_list)

      self.widgets_to_save = {}  # store widgets for saving

      self.main_progress_bar = VersionItemWidget("", MISSING_COLOR)
      main_layout.addWidget(self.main_progress_bar)

      # Load saved settings
      self.setup_settings_dialog()
      self.load_user_settings()

      # --- 4. MAIN WINDOW SETTINGS BUTTON ---
      self.btn_settings = QPushButton("Settings")
      self.btn_settings.clicked.connect(self.open_settings)
      main_layout.addWidget(self.btn_settings)

      # ---- ONLINE FETCH (only if not offline) ----
      self.found_releases = json.loads(
        f.read(os.path.join(GAME_ID, "launcherData/cache/releases.json"), "[]")
      )
      self.update_version_list()
      if not OFFLINE and self.fetch_on_load.isChecked():
        self.start_fetch(max_pages=self.max_pages_spin.value())
        self.release_thread.error.connect(
          lambda e: print("Release fetch error:", e)
        )
        self.release_thread.start()
        self.main_progress_bar.show()
      else:
        self.main_progress_bar.set_progress(101)

    def open_settings(self):
      # .exec() halts the script here until the dialog is closed
      result = self.settings_dialog.exec()

      if result == QDialog.DialogCode.Accepted:
        # User clicked 'Done'
        print("Saving settings...")
        self.save_user_settings()
      else:
        # User clicked 'Cancel' or closed via 'X'
        print("Changes discarded. Reverting UI...")
        self.load_user_settings()

    def start_fetch(self, max_pages=1):
      """Standard fetch with a page limit."""
      if hasattr(self, "release_thread") and self.release_thread.isRunning():
        return

      self.release_thread = ReleaseFetchThread(
        pat=self.github_pat.text() or None, max_pages=max_pages
      )
      if max_pages:
        self.main_progress_bar.setModeKnownEnd()
        self.main_progress_bar.set_progress((0 / max_pages) * 100)
      else:
        self.main_progress_bar.setModeUnknownEnd()
      self.main_progress_bar.label.setText(f"Fetching {max_pages} page(s)...")
      self.release_thread.progress.connect(self.on_release_progress)
      self.release_thread.finished.connect(self.on_release_finished)
      self.release_thread.start()

    def merge_releases(self, existing, new_data):
      # Use a dictionary to handle the "replace=True" logic by 'tag_name'
      # Dictionary keys are unique, so setting a key again replaces the value
      merged = {rel["tag_name"]: rel for rel in existing}

      for rel in new_data:
        tag = rel.get("tag_name")
        if tag:
          merged[tag] = rel  # This adds new ones OR replaces existing ones

      # Return as a sorted list (usually you want newest at the top)
      return list(merged.values())

    def start_full_fetch(self):
      """Triggered by button to fetch everything."""
      print("Starting full release fetch...")
      self.start_fetch(max_pages=0)  # 0 signals 'All' in our thread logic

    def on_release_progress(self, page, total, releases):
      self.main_progress_bar.setModeKnownEnd()
      self.main_progress_bar.set_progress((page / total) * 100)
      self.found_releases = self.merge_releases(self.found_releases, releases)
      self.main_progress_bar.label.setText(
        f"Fetching {total} page(s)... {(page / total) * 100}% - {page} / {total}"
      )
      self.update_version_list()

    def on_release_finished(self, releases):
      self.main_progress_bar.label.setText("")
      self.main_progress_bar.set_progress(101)
      self.found_releases = self.merge_releases(self.found_releases, releases)
      self.update_version_list()

    def setup_settings_dialog(self):
      self.settings_dialog = QDialog(self)
      self.settings_dialog.setWindowTitle("Settings")
      self.settings_dialog.setFixedWidth(420)
      outer_layout = QVBoxLayout(self.settings_dialog)

      # --- GLOBAL SETTINGS SECTION ---
      global_box = QGroupBox("Global Settings (All Games)")
      global_layout = QVBoxLayout()

      # Max Downloads
      max_dl_row = QHBoxLayout()
      max_dl_row.addWidget(QLabel("Max Concurrent Downloads:"))
      self.max_dl_spinbox = QSpinBox()
      self.max_dl_spinbox.setRange(0, 10)
      self.max_dl_spinbox.setValue(3)
      self.max_dl_spinbox.setFixedWidth(60)
      self.max_dl_spinbox.valueChanged.connect(self.process_download_queue)
      max_dl_row.addWidget(self.max_dl_spinbox)
      max_dl_row.addStretch()
      global_layout.addLayout(max_dl_row)
      self.widgets_to_save["max_concurrent_dls"] = self.max_dl_spinbox

      # Fetch on Load Bool
      self.fetch_on_load = QCheckBox("Fetch releases on launcher start")
      self.fetch_on_load.setChecked(True)
      global_layout.addWidget(self.fetch_on_load)
      self.widgets_to_save["fetch_on_load"] = self.fetch_on_load

      # Max Pages Int
      page_row = QHBoxLayout()
      page_row.addWidget(QLabel("Max pages to fetch on load:"))
      self.max_pages_spin = QSpinBox()
      self.max_pages_spin.setRange(0, 100)
      self.max_pages_spin.setValue(1)
      page_row.addWidget(self.max_pages_spin)
      page_row.addStretch()
      global_layout.addLayout(page_row)
      self.widgets_to_save["max_pages_on_load"] = self.max_pages_spin

      # --- Fetch Actions Row ---
      fetch_btn_row = QHBoxLayout()

      # Button 1: Fetch based on the SpinBox limit
      self.btn_fetch_limit = QPushButton("Fetch Recent Updates")
      self.btn_fetch_limit.setToolTip(
        "Fetch the number of pages specified in the limit above"
      )
      self.btn_fetch_limit.clicked.connect(
        lambda: self.start_fetch(max_pages=self.max_pages_spin.value())
      )
      fetch_btn_row.addWidget(self.btn_fetch_limit)

      # Button 2: Fetch everything
      self.btn_fetch_all = QPushButton("Sync Full Version History")
      self.btn_fetch_all.setToolTip(
        "Fetch every single release ever posted to this repository"
      )
      self.btn_fetch_all.clicked.connect(self.start_full_fetch)
      fetch_btn_row.addWidget(self.btn_fetch_all)

      global_layout.addLayout(fetch_btn_row)

      # Global Checkboxes
      update_cb = QCheckBox("check for launcher updates when opening")
      global_layout.addWidget(update_cb)
      self.widgets_to_save["cb_check for launcher updates when opening"] = (
        update_cb
      )

      # GitHub PAT
      self.github_pat = QLineEdit()
      self.github_pat.setEchoMode(QLineEdit.EchoMode.Password)
      self.github_pat.setPlaceholderText("GitHub PAT (Optional)")
      global_layout.addWidget(self.github_pat)
      self.widgets_to_save["github_pat"] = self.github_pat

      global_box.setLayout(global_layout)
      outer_layout.addWidget(global_box)

      # --- LOCAL SETTINGS SECTION ---
      local_box = QGroupBox(f"Local Settings ({config.GH_REPO})")
      local_layout = QVBoxLayout()

      # extra_game_args
      self.extra_game_args = QLineEdit()
      self.extra_game_args.setPlaceholderText("Game arguments (e.g. -windowed)")
      local_layout.addWidget(self.extra_game_args)
      self.widgets_to_save["extra_game_args"] = self.extra_game_args

      # Utility Buttons (Local context)
      btn_row = QHBoxLayout()
      if config.getGameLogLocation():
        btn_log = QPushButton("Open Game Logs")
        btn_log.clicked.connect(
          lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(os.path.abspath(config.getGameLogLocation()))
          )
        )
        btn_row.addWidget(btn_log)

      btn_dl_all = QPushButton("Download All")
      btn_dl_all.clicked.connect(self.download_all_versions)
      btn_row.addWidget(btn_dl_all)
      local_layout.addLayout(btn_row)

      local_box.setLayout(local_layout)
      outer_layout.addWidget(local_box)

      # --- Bottom Action Buttons ---
      bottom_btn_layout = QHBoxLayout()

      # Cancel Button: Discards changes and closes
      cancel_btn = QPushButton("Cancel")
      cancel_btn.clicked.connect(self.settings_dialog.reject)
      bottom_btn_layout.addWidget(cancel_btn)

      # Done Button: Saves changes and closes
      done_btn = QPushButton("Done")
      done_btn.setDefault(True)  # Pressing Enter triggers this
      done_btn.clicked.connect(self.settings_dialog.accept)
      bottom_btn_layout.addWidget(done_btn)

      outer_layout.addLayout(bottom_btn_layout)

      custom_widgets = config.addCustomNodes(self, local_layout)

      # Register them for saving/loading and mark as Local
      for key, widget in custom_widgets.items():
        self.widgets_to_save[key] = widget
        if key not in self.local_keys:
          self.local_keys.append(key)

  app = QApplication(sys.argv)
  window = Launcher()
  window.show()

  sys.exit(app.exec())