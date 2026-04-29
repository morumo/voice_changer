import json
from pathlib import Path


class PresetManager:
    """カスタムプリセットの保存・読み込み・削除を管理する。

    設定は ~/.voice_changer/presets.json に JSON 形式で永続化する。
    """

    _SAVE_DIR = Path.home() / ".voice_changer"
    _SAVE_PATH = _SAVE_DIR / "presets.json"

    def __init__(self):
        self._presets: dict[str, dict] = {}
        self._load()

    def names(self) -> list[str]:
        return sorted(self._presets.keys())

    def get(self, name: str) -> dict | None:
        return self._presets.get(name)

    def save(self, name: str, data: dict) -> None:
        self._presets[name] = data
        self._persist()

    def delete(self, name: str) -> None:
        self._presets.pop(name, None)
        self._persist()

    def _load(self) -> None:
        if self._SAVE_PATH.exists():
            try:
                with open(self._SAVE_PATH, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._presets = loaded
            except Exception:
                self._presets = {}

    def _persist(self) -> None:
        try:
            self._SAVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
