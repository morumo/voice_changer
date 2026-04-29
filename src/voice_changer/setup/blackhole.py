import subprocess
import tempfile
import urllib.request
from pathlib import Path

import sounddevice as sd

BLACKHOLE_PKG_URL = (
    "https://github.com/ExistentialAudio/BlackHole/releases/download/"
    "v0.6.0/BlackHole2ch-0.6.0.pkg"
)
DEVICE_NAME = "BlackHole 2ch"


def is_installed() -> bool:
    """BlackHole 2ch がオーディオデバイスとして認識されているか確認する。"""
    devices = sd.query_devices()
    return any(DEVICE_NAME.lower() in d["name"].lower() for d in devices)


def get_device_index() -> int | None:
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if DEVICE_NAME.lower() in d["name"].lower():
            return i
    return None


def install(console=None) -> bool:
    """pkg インストーラをダウンロードして実行する。成功したら True を返す。"""
    log = console.print if console else print

    log("[yellow]BlackHole インストーラをダウンロードします...[/yellow]" if console else
        "BlackHole インストーラをダウンロードします...")

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "BlackHole2ch.pkg"
        try:
            urllib.request.urlretrieve(BLACKHOLE_PKG_URL, pkg_path)
        except Exception as e:
            log(f"[red]ダウンロード失敗: {e}[/red]" if console else f"ダウンロード失敗: {e}")
            return False

        log("インストーラを実行します（管理者パスワードが必要な場合があります）...")
        result = subprocess.run(
            ["sudo", "installer", "-pkg", str(pkg_path), "-target", "/"],
            capture_output=False,
        )

        if result.returncode != 0:
            msg = "[red]インストールに失敗しました。[/red]" if console else "インストールに失敗しました。"
            log(msg)
            return False

    log("[green]インストール完了。Core Audio を再起動します...[/green]" if console else
        "インストール完了。Core Audio を再起動します...")
    subprocess.run(["sudo", "launchctl", "kickstart", "-k", "system/com.apple.audio.coreaudiod"],
                   capture_output=True)
    return True
