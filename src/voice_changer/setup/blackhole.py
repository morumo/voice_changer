import sys

import sounddevice as sd

# --- プラットフォーム別設定 ---
if sys.platform == "darwin":
    _DEVICE_NAME = "BlackHole 2ch"
    _DISPLAY_NAME = "BlackHole 2ch"
    _INSTALL_URL = "https://github.com/ExistentialAudio/BlackHole"
else:
    # Windows: VB-Audio Cable の出力デバイス名
    # "CABLE Input" がアプリから書き込む仮想デバイス（Discord 等はここを入力として使う）
    _DEVICE_NAME = "CABLE Input"
    _DISPLAY_NAME = "VB-Audio Virtual Cable"
    _INSTALL_URL = "https://vb-audio.com/Cable/"


def display_name() -> str:
    """UI 表示用のデバイス名を返す。"""
    return _DISPLAY_NAME


def install_url() -> str:
    """インストール先 URL を返す。"""
    return _INSTALL_URL


def is_installed() -> bool:
    """仮想オーディオデバイスがシステムに認識されているか確認する。"""
    devices = sd.query_devices()
    return any(_DEVICE_NAME.lower() in d["name"].lower() for d in devices)


def get_device_index() -> int | None:
    """仮想オーディオデバイスのインデックスを返す。見つからない場合は None。"""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if _DEVICE_NAME.lower() in d["name"].lower():
            return i
    return None


def install(console=None) -> bool:
    """仮想オーディオデバイスをインストールする。
    Mac: pkg インストーラを自動実行。
    Windows: ブラウザでダウンロードページを開く（手動インストールが必要）。
    """
    if sys.platform == "darwin":
        return _install_mac(console)
    return _install_windows(console)


def _install_mac(console=None) -> bool:
    import subprocess
    import tempfile
    import urllib.request
    from pathlib import Path

    _PKG_URL = (
        "https://github.com/ExistentialAudio/BlackHole/releases/download/"
        "v0.6.0/BlackHole2ch-0.6.0.pkg"
    )

    log = console.print if console else print

    log("[yellow]BlackHole インストーラをダウンロードします...[/yellow]" if console
        else "BlackHole インストーラをダウンロードします...")

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "BlackHole2ch.pkg"
        try:
            urllib.request.urlretrieve(_PKG_URL, pkg_path)
        except Exception as e:
            log(f"[red]ダウンロード失敗: {e}[/red]" if console else f"ダウンロード失敗: {e}")
            return False

        log("インストーラを実行します（管理者パスワードが必要な場合があります）...")
        result = subprocess.run(
            ["sudo", "installer", "-pkg", str(pkg_path), "-target", "/"],
            capture_output=False,
        )
        if result.returncode != 0:
            log("[red]インストールに失敗しました。[/red]" if console else "インストールに失敗しました。")
            return False

    log("[green]インストール完了。Core Audio を再起動します...[/green]" if console
        else "インストール完了。Core Audio を再起動します...")
    subprocess.run(
        ["sudo", "launchctl", "kickstart", "-k", "system/com.apple.audio.coreaudiod"],
        capture_output=True,
    )
    return True


def _install_windows(console=None) -> bool:
    import webbrowser

    log = console.print if console else print
    msg = f"ブラウザでダウンロードページを開きます: {_INSTALL_URL}"
    log(f"[yellow]{msg}[/yellow]" if console else msg)
    webbrowser.open(_INSTALL_URL)
    # 手動インストールが必要なため False を返す（呼び出し元が再起動を案内する）
    return False
