import sys
import subprocess
from misc import f
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
  QProgressBar,
  QDialog,
)
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt
import os
import zipfile
import py7zr
import re

OFFLINE = False
SILENT = False
ASSET_NAME = "windows.zip"
GAME_FILE_NAME = "vex.pck"
VERSIONS_DIR = "versions"
GAME_LOG_LOCATION = ""
WINDOW_TITLE = "vex++ launcher"
MAIN_LOADING_COLOR = (0, 210, 255)
UNKNOWN_TIME_LOADING_COLOR = (255, 108, 0)
USE_HARD_LINKS = True
USE_CENTRAL_GAME_DATA_FOLDER = True
API_URL = "https://api.github.com/repos/rsa17826/vex-plus-plus/releases"


SETTINGS_FILE = "launcher_settings.json"


class hooks:
  @staticmethod
  def gameVersionExists(full_path):
    return os.path.isfile(os.path.join(full_path, GAME_FILE_NAME))

  @staticmethod
  def gameLaunchRequested(path):
    exe = os.path.join(path, "vex.exe")
    if os.path.isfile(exe):
      subprocess.Popen([exe], cwd=path)

  @staticmethod
  def addCustomNodes(_self):
    pass


LOCAL_COLOR = Qt.green
ONLINE_COLOR = Qt.cyan
MISSING_COLOR = Qt.gray
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QLinearGradient, QColor
from PySide6.QtCore import Qt, QRectF
import math

import hashlib
import os

os.makedirs("./launcherData", exist_ok=True)
os.makedirs("./gameData", exist_ok=True)


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
  if not USE_HARD_LINKS:
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
            if os.path.abspath(new_file_path) == os.path.abspath(candidate):
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
    f"Run version {version}" if status == "Local" else f"Download version {version}"
  )

  # Pass the color to the widget
  widget = VersionItemWidget(text, color)
  widget.setModeKnownEnd()

  item.setSizeHint(widget.sizeHint())
  list_widget.addItem(item)
  list_widget.setItemWidget(item, widget)

  item.setData(
    Qt.UserRole,
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

  def __init__(self, pat=None):
    super().__init__()
    self.pat = pat

  def run(self):
    if OFFLINE:
      self.finished.emit([])
      return

    try:
      releases = []
      headers = {"Authorization": f"token {self.pat}"} if self.pat else {}
      rand = random.random()
      page = 0
      final_size = -1

      # HEAD request to detect total pages
      head = requests.head(
        f"{API_URL}?page=0&rand={rand}", headers=headers, timeout=10
      )
      if "Link" in head.headers:
        m = re.search(
          r'\?page=(\d+)&rand=[\d.]+>; rel="last"', head.headers["Link"]
        )
        if m:
          final_size = int(m.group(1)) + 2

      # Fetch pages
      while True:
        page += 1
        r = requests.get(
          f"{API_URL}?page={page}&rand={rand}",
          headers=headers,
          timeout=30,
        )
        if r.status_code != 200:
          raise RuntimeError(f"Download failed: {r.status_code} - {r.reason}")

        data = r.json()
        if not data:
          break
        releases.extend(data)

        if final_size > 0:
          self.progress.emit(page + 1, final_size, releases)

      self.finished.emit(releases)

    except Exception as e:
      self.finished.emit(releases)
      self.error.emit(str(e))


def save_settings(settings: dict):
  try:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
      json.dump(settings, f, indent=2)
  except Exception as e:
    print("Failed to save settings:", e)


def load_settings() -> dict:
  try:
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  except FileNotFoundError:
    return {}
  except Exception as e:
    print("Failed to load settings:", e)
    return {}


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
    self.setAttribute(Qt.WA_TranslucentBackground)
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
    painter.setRenderHint(QPainter.Antialiasing)
    rect = self.rect()
    w = rect.width()
    h = rect.height()
    gradSize = int(w / 8)  # Slightly smaller grad for 'both' to avoid crowding
    minGradAlpha = 50
    if self.noKnownEndPoint:
      self.progress = int(((time.time() - self.startTime) * self.animSpeed) % 100)
      QTimer.singleShot(0, self.update)

    if self.progressType == self.ProgressTypes.both:
      fill_end = w * self.progress / 100
      solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
      tip_rect = QRectF(solid_rect.right(), 0, int(min(gradSize, fill_end)), h)
      self._draw_progress(painter, solid_rect, minGradAlpha)
      self._draw_gradient(
        painter, tip_rect, tip_rect.topLeft(), tip_rect.topRight(), minGradAlpha
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
        painter, tip_rect, tip_rect.topRight(), tip_rect.topLeft(), minGradAlpha
      )

    elif self.progressType == self.ProgressTypes.leftToRight:
      fill_end = w * self.progress / 100
      solid_rect = QRectF(0, 0, max(0, fill_end - gradSize), h)
      tip_rect = QRectF(solid_rect.right(), 0, min(gradSize, fill_end), h)
      self._draw_progress(painter, solid_rect, minGradAlpha)
      self._draw_gradient(
        painter, tip_rect, tip_rect.topLeft(), tip_rect.topRight(), minGradAlpha
      )

    elif self.progressType == self.ProgressTypes.rightToLeft:
      fill_start = w - (w * self.progress / 100)
      solid_rect = QRectF(
        fill_start + gradSize, 0, w - (fill_start + gradSize), h
      )
      tip_rect = QRectF(max(fill_start, 0), 0, min(gradSize, w - fill_start), h)
      self._draw_progress(painter, solid_rect, minGradAlpha)
      self._draw_gradient(
        painter, tip_rect, tip_rect.topRight(), tip_rect.topLeft(), minGradAlpha
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


import sys
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QTextCursor


class ConsoleRedirector:
  def __init__(self, text_widget):
    self.text_widget = text_widget

  def write(self, text):
    # Move cursor to the end so it scrolls automatically
    self.text_widget.moveCursor(QTextCursor.End)
    self.text_widget.insertPlainText(text)
    # Ensure it scrolls to the new text
    self.text_widget.ensureCursorVisible()

  def flush(self):
    # Required for file-like objects
    pass


class Launcher(QWidget):
  def save_user_settings(self):
    settings = {}

    # Line edits
    for key, widget in self.widgets_to_save.items():
      if isinstance(widget, QLineEdit):
        settings[key] = widget.text()
      elif isinstance(widget, QCheckBox):
        settings[key] = widget.isChecked()

    save_settings(settings)

  def load_user_settings(self):
    settings = load_settings()
    for key, value in settings.items():
      widget = self.widgets_to_save.get(key)
      if widget:
        if isinstance(widget, QLineEdit):
          widget.setText(value)
        elif isinstance(widget, QCheckBox):
          widget.setChecked(bool(value))

  def closeEvent(self, event):
    self.save_user_settings()
    super().closeEvent(event)

  downloadingVersions = []

  def on_version_double_clicked(self, item):
    data = item.data(Qt.UserRole)
    if not data:
      return

    # Local → run
    if data["status"] == "Local":
      path = data.get("path")
      if path:
        hooks.gameLaunchRequested(path)
        f.write("./launcherData/lastRanVersion.txt", data.get("version"))
      return

    # Online → download
    if data["status"] == "Online":
      if data["version"] in self.downloadingVersions:
        return
      self.downloadingVersions.append(data["version"])
      release = data.get("release")
      if not release:
        return

      assets = release.get("assets", [])
      if not assets:
        print("No assets to download")
        return

      # find asset by name
      asset = next((a for a in assets if a["name"] == ASSET_NAME), None)
      if not asset:
        print(f"Asset '{ASSET_NAME}' not found for {release['tag_name']}")
        return

      url = asset["browser_download_url"]
      tag = release["tag_name"]
      dest_dir = os.path.join(VERSIONS_DIR, tag)
      os.makedirs(dest_dir, exist_ok=True)

      out_file = os.path.join(dest_dir, asset["name"])
      # Set widget to "Waiting" state immediately
      widget = data["widget"]
      widget.label.setText(f"Waiting to download {tag}...")
      widget.setModeUnknownEnd()  # orange pulsing bar

      # Add to queue
      self.download_queue.append(
        (item, asset["browser_download_url"], out_file, dest_dir)
      )
      self.process_download_queue()
      # pass dest_dir for extraction
      # self.download_online_version(item, url, out_file, dest_dir)

  def process_download_queue(self):
    # While we have room for more downloads and items in the queue
    while (
      len(self.active_downloads) < self.max_concurrent_dls and self.download_queue
    ):
      next_dl = self.download_queue.pop(0)
      self.start_actual_download(*next_dl)

  def start_actual_download(self, item, url, out_file, dest_dir):
    data = item.data(Qt.UserRole)
    tag = data["version"]
    widget = data["widget"]

    # Change state from 'Waiting' to 'Downloading'
    widget.label.setText(f"Downloading {tag}...")
    widget.setModeKnownEnd()  # blue bar

    dl_thread = self.download_online_version(item, url, out_file, dest_dir)
    self.active_downloads[tag] = dl_thread

    dl_thread.progress.connect(widget.set_progress)

    def on_finished(path):
      # 1. Clean up tracking
      if tag in self.active_downloads:
        del self.active_downloads[tag]
      self.process_download_queue()

    dl_thread.finished.connect(on_finished)
    dl_thread.error.connect(lambda e: print(f"DL Error {tag}: {e}"))
    dl_thread.start()

  def download_online_version(self, item, url, out_file, extract_dir):
    data = item.data(Qt.UserRole)
    data["status"] = "Local"
    data["path"] = extract_dir
    widget = data["widget"]
    dl_thread = AssetDownloadThread(url, out_file)

    dl_thread.progress.connect(widget.set_progress)

    def on_finished(path):
      widget.set_progress(100)
      widget.setModeUnknownEnd()
      extracted = False
      # check extension and extract
      if path.endswith(".zip"):
        try:
          with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
          os.remove(path)
          extracted = True
        except Exception as e:
          print("Failed to unzip:", e)
      elif path.endswith(".7z"):
        try:
          with py7zr.SevenZipFile(path, mode="r") as archive:
            archive.extractall(path=extract_dir)
          os.remove(path)
          extracted = True
        except Exception as e:
          print("Failed to extract 7z:", e)
      else:
        print(f"Downloaded file saved as {path} (no extraction)")

      if extracted and USE_HARD_LINKS:
        deduplicate_with_hardlinks(extract_dir)
      # Update list item as Local
      widget.set_progress(101)
      item.setData(Qt.UserRole, data)
      widget.set_label_color(LOCAL_COLOR)
      widget.label.setText(f"Run version {data['version']}")
      self.downloadingVersions.remove(data["version"])
      if extracted:
        print(f"{data['version']} downloaded and extracted successfully.")

    dl_thread = AssetDownloadThread(url, out_file)

    dl_thread.progress.connect(widget.set_progress)

    dl_thread.finished.connect(on_finished)
    dl_thread.error.connect(lambda e: print("DL error:", e))
    dl_thread.start()
    return dl_thread

  def update_version_list(self, releases):
    self.version_list.setUpdatesEnabled(False)
    scrollbar = self.version_list.verticalScrollBar()
    previous_scroll_pos = scrollbar.value()
    # 1. Gather all data into a temporary list first
    all_items_data = []

    # Get local versions from disk
    if os.path.isdir(VERSIONS_DIR):
      for dirname in os.listdir(VERSIONS_DIR):
        full_path = os.path.join(VERSIONS_DIR, dirname)
        if os.path.isdir(full_path) and hooks.gameVersionExists(full_path):
          all_items_data.append(
            {
              "version": dirname,
              "status": "Local",
              "path": full_path,
              "release": None,
            }
          )

    # Add online versions that aren't already local
    local_names = [d["version"] for d in all_items_data]
    for rel in releases:
      version = rel["tag_name"]
      if version not in local_names:
        all_items_data.append(
          {
            "version": version,
            "status": "Online",
            "path": None,
            "release": rel,
          }
        )

    # 2. Sort the data using the logic above
    sorted_data = self.sort_versions(all_items_data)

    # 3. Clear and Re-populate the UI
    self.version_list.clear()
    for data in sorted_data:
      add_version_item(
        self.version_list,
        data["version"],
        data["status"],
        data["path"],
        data["release"],
      )
    local_versions = set()

    # Collect local versions
    for i in range(self.version_list.count()):
      data = self.version_list.item(i).data(Qt.UserRole)
      if data:
        local_versions.add(data["version"])

    # Add online versions
    for rel in releases:
      version = rel["tag_name"]

      if version in local_versions:
        continue

      add_version_item(
        self.version_list, version, status="Online", path=None, release=rel
      )
    scrollbar.setValue(previous_scroll_pos)
    self.version_list.setUpdatesEnabled(True)

  def load_local_versions(self):
    self.version_list.clear()

    if not os.path.isdir(VERSIONS_DIR):
      return

    for dirname in sorted(os.listdir(VERSIONS_DIR), reverse=True):
      full_path = os.path.join(VERSIONS_DIR, dirname)
      if not os.path.isdir(full_path):
        continue

      if not hooks.gameVersionExists(full_path):
        continue

      add_version_item(self.version_list, dirname, status="Local", path=full_path)

  def sort_versions(self, versions_data):
    # 1. Load the last ran version
    last_ran = f.read("./launcherData/lastRanVersion.txt").strip()

    def get_sort_key(item):
      version = item["version"]
      status = item["status"]

      # Priority 1: Last Ran Version
      is_last_ran = 1 if version == last_ran else 0

      # Priority 2: Local Status
      # (Assuming "Local" in your Python code corresponds to "LocalOnly")
      is_local = 1 if status == "Local" else 0

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

    # Sort using the key and reverse it (like your .Reverse() call)
    versions_data.sort(key=get_sort_key, reverse=True)
    return versions_data

  def toggle_console(self):
    if self.is_console_expanded:
      self.console_output.setFixedHeight(28)
      # Hide scrollbar in one-line mode
      self.console_output.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.console_toggle_btn.setText("▲")
      self.is_console_expanded = False
    else:
      self.console_output.setFixedHeight(150)
      # Show scrollbar in expanded mode
      self.console_output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
      self.console_toggle_btn.setText("▼")
      self.is_console_expanded = True

  def __init__(self):
    super().__init__()
    self.active_downloads = {}  # {version_tag: thread_object}
    self.download_queue = []  # List of (item, url, out_file, extract_dir)
    self.max_concurrent_dls = 3
    self.setWindowTitle(WINDOW_TITLE)
    self.setFixedSize(420, 600)
    self.setStyleSheet(f.read("./main.css"))

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

    btn_row1 = QHBoxLayout()
    temp = QPushButton("open launcher log")
    btn_row1.addWidget(temp)

    def a():
      path = os.path.abspath("./logs")
      QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    temp.clicked.connect(a)

    if GAME_LOG_LOCATION:
      temp = QPushButton("open game logs folder")
      btn_row1.addWidget(temp)

      def a():
        path = os.path.abspath(GAME_LOG_LOCATION)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

      temp.clicked.connect(a)

    main_layout.addLayout(btn_row1)
    btn_row2 = QHBoxLayout()
    if USE_CENTRAL_GAME_DATA_FOLDER:
      temp = QPushButton("open game data folder")

      def a():
        path = os.path.abspath("./gameData")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

      temp.clicked.connect(a)
      btn_row2.addWidget(temp)
      main_layout.addLayout(btn_row2)

    self.github_pat = QLineEdit()
    self.github_pat.setEchoMode(QLineEdit.Password)
    self.github_pat.setPlaceholderText("github pat (optional)")
    main_layout.addWidget(self.github_pat)
    self.widgets_to_save["github_pat"] = self.github_pat

    # --- Checkboxes ---
    self.checkboxes = {}
    checks = [
      # "check for updates on boot",
      # "use xdm",
      "check for launcher updates when opening",
      # "open console with game",
    ]
    for text in checks:
      cb = QCheckBox(text)
      cb.setChecked(True)
      main_layout.addWidget(cb)
      self.checkboxes[text] = cb
      self.widgets_to_save[f"cb_{text}"] = cb
    self.command_input = QLineEdit("")
    self.command_input.setPlaceholderText("game args go here")
    main_layout.addWidget(self.command_input)
    self.widgets_to_save["command_input"] = self.command_input
    # Load saved settings
    self.load_user_settings()
    hooks.addCustomNodes(self)

    # Container for the console
    self.console_row_layout = QHBoxLayout()
    self.console_row_layout.setSpacing(2)

    # 2. Setup the Console Widget
    self.console_output = QPlainTextEdit()
    self.console_output.setReadOnly(True)
    self.console_output.setFixedHeight(28)
    self.is_console_expanded = False
    self.console_output.setStyleSheet(
      """background-color: #1e1e1e; color: #d4d4d4;font-family: 'Consolas', monospace; font-size: 10pt;border: 1px solid #333;"""
    )

    # 3. Setup the 1x1 Toggle Button
    self.console_toggle_btn = QPushButton("▲")
    self.console_toggle_btn.setFixedSize(28, 28)
    self.console_toggle_btn.setCursor(Qt.PointingHandCursor)
    self.console_toggle_btn.clicked.connect(self.toggle_console)

    # 4. Add widgets with explicit Bottom Alignment
    # The console expands, so it doesn't need a specific alignment,
    # but the button must be told to stay down.
    self.console_row_layout.addWidget(self.console_output)
    self.console_row_layout.addWidget(
      self.console_toggle_btn, alignment=Qt.AlignBottom
    )

    # 5. Add the row to your main layout
    main_layout.addLayout(self.console_row_layout)

    # Redirects
    sys.stdout = ConsoleRedirector(self.console_output)
    sys.stderr = ConsoleRedirector(self.console_output)
    # ---- ONLINE FETCH (only if not offline) ----
    if not OFFLINE:
      self.release_thread = ReleaseFetchThread(pat=self.github_pat.text() or None)
      self.main_progress_bar.label.setText("Loading Game Versions")
      self.main_progress_bar.setModeUnknownEnd()
      self.release_thread.progress.connect(self.on_release_progress)
      self.release_thread.finished.connect(self.on_release_finished)
      self.update_version_list([])
      self.release_thread.error.connect(
        lambda e: print("Release fetch error:", e)
      )
      self.release_thread.start()
      self.main_progress_bar.show()

  def on_release_progress(self, page, total, releases):
    self.main_progress_bar.setModeKnownEnd()
    self.main_progress_bar.set_progress((page / total) * 100)
    self.update_version_list(releases)

  def on_release_finished(self, releases):
    self.main_progress_bar.label.setText("")
    self.main_progress_bar.set_progress(101)
    self.update_version_list(releases)


app = QApplication(sys.argv)
window = Launcher()
window.show()
sys.exit(app.exec())
