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

from PySide6.QtCore import Qt
import os
import zipfile
import py7zr  # install with pip install py7zr

OFFLINE = False
SILENT = False
ASSET_NAME = "windows.zip"

LOCAL_COLOR = Qt.green
ONLINE_COLOR = Qt.cyan
MISSING_COLOR = Qt.gray

def add_version_item(list_widget, version, status, path=None, release=None):
  item = QListWidgetItem(f"Run version {version}")

  if status == "Local":
    item.setForeground(LOCAL_COLOR)
  elif status == "Online":
    item.setForeground(ONLINE_COLOR)
  else:
    item.setForeground(MISSING_COLOR)

  item.setData(
    Qt.UserRole,
    {
      "version": version,
      "status": status,
      "path": path,
      "release": release,  # store release object for downloads
    },
  )

  list_widget.addItem(item)


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


VERSIONS_DIR = "versions"


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
        import re

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
        exe = os.path.join(path, "vex.exe")
        if os.path.isfile(exe):
          subprocess.Popen([exe], cwd=path)
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
    self.progress_dialog_dl = ProgressDialog(f"Downloading {item.text()}")
    self.progress_dialog_dl.show()

    self.dl_thread = AssetDownloadThread(url, out_file)

    def on_finished(path):
      self.progress_dialog_dl.close()
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

      # Update list item as Local
      data = item.data(Qt.UserRole)
      data["status"] = "Local"
      data["path"] = extract_dir
      item.setData(Qt.UserRole, data)
      item.setForeground(LOCAL_COLOR)
      item.setText(f"Run version {data['version']}")
      if extracted:
        print(f"{data['version']} downloaded and extracted successfully.")

    self.dl_thread.progress.connect(self.progress_dialog_dl.bar.setValue)
    self.dl_thread.finished.connect(on_finished)
    self.dl_thread.error.connect(lambda e: print("DL error:", e))
    self.dl_thread.start()

  def update_version_list(self, releases):
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

      if not os.path.isfile(os.path.join(full_path, "vex.pck")):
        continue

      add_version_item(self.version_list, dirname, status="Local", path=full_path)

  def __init__(self):
    super().__init__()

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

    # for v in range(242, 227, -1):
    #   self.version_list.addItem(f"Run version {v}")
    self.version_list.itemDoubleClicked.connect(self.on_version_double_clicked)

    main_layout.addWidget(self.version_list)

    self.widgets_to_save = {}  # store widgets for saving

    # --- Command input ---
    self.command_input = QLineEdit("-loadMap NEWEST")
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
    self.github_pat.setText("passwordplaceholder")
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
