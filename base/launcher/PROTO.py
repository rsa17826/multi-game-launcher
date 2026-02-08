import sys
import os
from typing import Callable
from pathlib import Path
import platform
import urllib.parse
import subprocess


def _winreg():
  if platform.system() != "Windows":
    raise RuntimeError("Windows-only")
  import winreg

  return winreg


# TODO test on linux
class PROTO:
  errorOnAddFailure = True

  # ==================================================
  # Runtime helpers (AHK-style)
  # ==================================================
  @staticmethod
  def calledFromProto() -> bool:
    return len(sys.argv) > 1 and ":" in sys.argv[1]

  @staticmethod
  def isSelf(proto: str) -> bool:
    if platform.system() != "Windows":
      return False

    winreg = _winreg()
    try:
      with winreg.OpenKey(
        winreg.HKEY_CLASSES_ROOT, rf"{proto}\shell\open\command"
      ) as k:
        return winreg.QueryValueEx(k, None)[0].lower() == PROTO._command().lower()  # type: ignore
    except FileNotFoundError:
      return False

  @staticmethod
  def _command() -> str:
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" "%1"'

  # ==================================================
  # Protocol handler registration
  # ==================================================
  @staticmethod
  def add(proto: str, cb: Callable, force: int = 0) -> int:
    proto = proto.lower()

    # ---------- Handle protocol invocation ----------
    if PROTO.calledFromProto():
      url = sys.argv[1]
      scheme, _, payload = url.partition(":")

      if scheme == proto:
        data = urllib.parse.unquote(payload)
        try:
          cb(data, scheme)
        except TypeError:
          cb(data)
    if PROTO.isSelf(proto):
      return True
    # ---------- Register handler ----------
    if platform.system() == "Windows":
      return PROTO._add_windows(proto, force)
    else:
      return PROTO._add_linux(proto)

  # ==================================================
  # Windows
  # ==================================================
  @staticmethod
  def _add_windows(proto: str, force: int) -> int:
    winreg = _winreg()

    if PROTO._exists_windows(proto):
      if not force and not PROTO.isSelf(proto):
        if PROTO.errorOnAddFailure:
          raise RuntimeError(f"Protocol already exists: {proto}")
        return False

    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, proto) as k:
      winreg.SetValueEx(k, None, 0, winreg.REG_SZ, f"URL:{proto}")
      winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")

    with winreg.CreateKey(
      winreg.HKEY_CLASSES_ROOT, rf"{proto}\shell\open\command"
    ) as k:
      winreg.SetValueEx(k, None, 0, winreg.REG_SZ, PROTO._command())

    return True

  @staticmethod
  def _exists_windows(proto: str) -> bool:
    winreg = _winreg()
    try:
      winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, proto)
      return True
    except FileNotFoundError:
      return False

  # ==================================================
  # Linux
  # ==================================================
  @staticmethod
  def _desktop_path(proto: str) -> Path:
    return Path.home() / ".local/share/applications" / f"{proto}.desktop"

  @staticmethod
  def _add_linux(proto: str) -> bool:
    desktop = PROTO._desktop_path(proto)
    desktop.parent.mkdir(parents=True, exist_ok=True)

    desktop.write_text(
      f"""\n[Desktop Entry]\nName={proto} handler\nExec={sys.executable} {os.path.abspath(sys.argv[0])} %u\nType=Application\nTerminal=false\nMimeType=x-scheme-handler/{proto};"""
    )

    subprocess.run(
      ["xdg-mime", "default", desktop.name, f"x-scheme-handler/{proto}"],
      check=True,
    )

    return True
