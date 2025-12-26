import sys
import subprocess
from misc import f
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

from PySide6.QtCore import Qt
import os
import zipfile
import py7zr  # install with pip install py7zr
import re

OFFLINE = False
SILENT = False
ASSET_NAME = "windows.zip"
GAME_FILE_NAME = "vex.pck"
VERSIONS_DIR = "versions"
USE_HARD_LINKS = True


class hooks:
  @staticmethod
  def gameVersionExists(full_path):
    return os.path.isfile(os.path.join(full_path, GAME_FILE_NAME))

  @staticmethod
  def gameLaunchRequested(path):
    exe = os.path.join(path, "vex.exe")
    if os.path.isfile(exe):
      subprocess.Popen([exe], cwd=path)


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

        # OPTIMIZATION: If this file is already a hardlink (nlink > 1),
        # we don't need to add it to the map because another copy
        # of it (the original) is already likely in the map.
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
  widget = create_version_item_widget(text, color)

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


def download_asset(self, asset_url, out_path):
  self.progress = ProgressDialog()
  self.progress.show()

  self.dl_thread = AssetDownloadThread(asset_url, out_path)
  self.dl_thread.progress.connect(self.progress.bar.setValue)
  self.dl_thread.finished.connect(self.progress.close)
  self.dl_thread.error.connect(lambda e: print("DL error:", e))

  self.dl_thread.start()


# ------------------- Progress Dialog -------------------
class ProgressDialog(QDialog):
  def __init__(self, title="Loading releases"):
    super().__init__()
    self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    self.setWindowTitle(title)

    layout = QVBoxLayout(self)

    self.text = QLabel("Starting...")
    self.text.setAlignment(Qt.AlignCenter)

    self.percent = QLabel("0% Done")
    self.percent.setAlignment(Qt.AlignCenter)

    self.bar = QProgressBar()
    self.bar.setRange(0, 100)

    layout.addWidget(self.text)
    layout.addWidget(self.bar)
    layout.addWidget(self.percent)
    self.resize(250, 90)


# ------------------- Release Fetch Thread -------------------
class ReleaseFetchThread(QThread):
  progress = Signal(int, int)  # current page, total pages
  finished = Signal(list)  # list of releases
  error = Signal(str)

  def __init__(self, api_url, pat=None):
    super().__init__()
    self.api_url = api_url
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
        f"{self.api_url}?page=0&rand={rand}", headers=headers, timeout=10
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
          f"{self.api_url}?page={page}&rand={rand}",
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
          self.progress.emit(page + 1, final_size)

      self.finished.emit(releases)

    except Exception as e:
      self.finished.emit(releases)
      self.error.emit(str(e))


import time
import random
import requests

doing_something = False

import json

SETTINGS_FILE = "launcher_settings.json"


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


def launch_game():
  # Example launch command
  subprocess.Popen(["./mygame"])  # Change for Windows if needed


def create_version_item_widget(version_text, color):
  return VersionItemWidget(version_text, color)


class VersionItemWidget(QWidget):
  def __init__(self, text, color):  # Added color argument
    super().__init__()
    self.text = text
    self.progress = 0

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

  # Add a method to change color dynamically if needed
  def set_label_color(self, color):
    self.label.setStyleSheet(f"background: transparent; color: {color.name};")

  def set_progress(self, percent):
    self.progress = percent
    self.update()  # repaint

  def paintEvent(self, event):
    painter = QPainter(self)
    rect = self.rect()
    minGradAlpha = 50
    if self.progress > 0 and self.progress < 100:
      progress_rect = QRectF(rect)
      gradSize = rect.width() / 5
      progress_rect.setWidth(
        max(0, (rect.width() * self.progress / 100) - gradSize)
      )

      tr = progress_rect.topRight()
      tr.setX(progress_rect.topRight().x() - gradSize)
      gradient = QLinearGradient(progress_rect.topLeft(), tr)

      gradient.setColorAt(0, QColor(0, 210, 255, minGradAlpha))
      gradient.setColorAt(1, QColor(0, 210, 255, minGradAlpha))

      painter.fillRect(progress_rect, gradient)

      # Adjust the second gradient position for a smoother transition
      tip_rect = QRectF(rect)
      tip_rect.setLeft(max(0, (rect.width() * self.progress / 100) - gradSize))
      tip_rect.setWidth(min(gradSize, (rect.width() * self.progress / 100)))

      # Slightly adjust the position of the second gradient for smoothness
      gradient2 = QLinearGradient(tip_rect.topLeft(), tip_rect.topRight())
      # Number of stops to simulate the curve (more stops = smoother curve)
      num_stops = 10
      # The exponent: 2 is a standard curve, 3+ is very "sharp"
      exponent = 5

      for i in range(num_stops + 1):
        pos = i / float(num_stops)
        # Exponential interpolation formula:
        # alpha = min + (max - min) * (pos ^ exponent)
        alpha = minGradAlpha + (255 - minGradAlpha) * math.pow(pos, exponent)

        gradient2.setColorAt(pos, QColor(0, 210, 255, int(alpha)))

      gradient2.setColorAt(
        0, QColor(0, 210, 255, minGradAlpha)
      )  # Less transparent
      gradient2.setColorAt(1, QColor(0, 210, 255, 255))  # Fully opaque at the end

      # Apply the second gradient
      painter.fillRect(tip_rect, gradient2)

    # Draw children (label) on top
    super().paintEvent(event)


class Launcher(QWidget):
  api_url = "https://api.github.com/repos/rsa17826/vex-plus-plus/releases"

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

  def on_version_double_clicked(self, item):
    data = item.data(Qt.UserRole)
    if not data:
      return

    # Local → run
    if data["status"] == "Local":
      path = data.get("path")
      if path:
        hooks.gameLaunchRequested(path)
      return

    # Online → download
    if data["status"] == "Online":
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

      # pass dest_dir for extraction
      self.download_online_version(item, url, out_file, dest_dir)

  def download_online_version(self, item, url, out_file, extract_dir):
    data = item.data(Qt.UserRole)
    data["status"] = "Local"
    data["path"] = extract_dir
    widget = data["widget"]
    dl_thread = AssetDownloadThread(url, out_file)
    self.active_downloads.append(dl_thread)  # keep reference

    dl_thread.progress.connect(widget.set_progress)

    def on_finished(path):
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
      widget.set_progress(100)
      item.setData(Qt.UserRole, data)
      widget.set_label_color(LOCAL_COLOR)
      item.setText(f"Run version {data['version']}")
      if extracted:
        print(f"{data['version']} downloaded and extracted successfully.")

    dl_thread = AssetDownloadThread(url, out_file)
    self.active_downloads.append(dl_thread)  # keep reference

    dl_thread.progress.connect(widget.set_progress)

    dl_thread.finished.connect(on_finished)
    dl_thread.error.connect(lambda e: print("DL error:", e))
    dl_thread.start()

  def update_version_list(self, releases):
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

  def __init__(self):
    super().__init__()

    self.active_downloads = []
    self.setWindowTitle("Vex++ Version Manager")
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

    # --- Command input ---
    self.command_input = QLineEdit("--loadMap NEWEST")
    main_layout.addWidget(self.command_input)
    self.widgets_to_save["command_input"] = self.command_input

    # --- Buttons row ---
    btn_row1 = QHBoxLayout()
    btn_row1.addWidget(QPushButton("open launcher log"))
    btn_row1.addWidget(QPushButton("open game logs folder"))
    main_layout.addLayout(btn_row1)

    btn_row2 = QHBoxLayout()
    btn_row2.addWidget(QPushButton("open game data folder"))
    main_layout.addLayout(btn_row2)

    # --- Masked field ---
    self.github_pat = QLineEdit()
    self.github_pat.setEchoMode(QLineEdit.Password)
    self.github_pat.setPlaceholderText("github pat (optional)")
    main_layout.addWidget(self.github_pat)
    self.widgets_to_save["github_pat"] = self.github_pat

    # --- Fix button ---
    main_layout.addWidget(QPushButton("try fix new maps for old versions"))

    # --- Checkboxes ---
    self.checkboxes = {}
    checks = [
      "check for updates on boot",
      "use xdm",
      "check for updates when opening",
      "open console with game",
    ]
    for text in checks:
      cb = QCheckBox(text)
      cb.setChecked(True)
      main_layout.addWidget(cb)
      self.checkboxes[text] = cb
      self.widgets_to_save[f"cb_{text}"] = cb

    # --- Launch button ---
    launch_btn = QPushButton("Launch Selected Version")
    launch_btn.clicked.connect(launch_game)
    main_layout.addWidget(launch_btn, alignment=Qt.AlignBottom)

    # Load saved settings
    self.load_user_settings()

    # ---- ONLINE FETCH (only if not offline) ----
    if not OFFLINE:
      self.progress_dialog = ProgressDialog("Loading releases")
      self.release_thread = ReleaseFetchThread(
        self.api_url, pat=self.github_pat.text() or None
      )
      self.release_thread.progress.connect(self.on_release_progress)
      self.release_thread.finished.connect(self.on_release_finished)
      self.release_thread.error.connect(
        lambda e: print("Release fetch error:", e)
      )
      self.release_thread.start()
      self.progress_dialog.show()

  def on_release_progress(self, page, total):
    percent = int(page / total * 100)
    self.progress_dialog.bar.setValue(percent)
    self.progress_dialog.text.setText(f"Loading releases... ({page}/{total})")
    self.progress_dialog.percent.setText(f"{percent}% Done")

  def on_release_finished(self, releases):
    self.progress_dialog.close()
    self.update_version_list(releases)


app = QApplication(sys.argv)
window = Launcher()
window.show()
sys.exit(app.exec())
