# Voice Changer

マイク入力音声をリアルタイムで変換する DSP ベースのボイスチェンジャー。  
Discord / Google Meet / Zoom 等の仮想マイクとして利用できます。

## 特徴

- **低レイテンシ** — OLA 位相ボコーダ採用、実測 ≈ 47ms
- **完全ローカル動作** — 外部 API・有料サービス不使用
- **高品質フォルマント変換** — WORLD CheapTrick による声道包絡推定
- **ダークテーマ GUI** — PySide6 製デスクトップアプリ（CLI モードも選択可）、macOS / Windows 対応
- **カスタムプリセット** — 設定に名前を付けて保存・読み込み・削除

---

## 必要環境

- Python 3.11 以降
- [uv](https://github.com/astral-sh/uv)（パッケージ管理）
- 仮想オーディオデバイス（未インストールの場合、起動時にダイアログで案内されます）

| OS | 仮想オーディオデバイス |
|----|----------------------|
| macOS 12 Monterey 以降 | [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole)（起動時に自動インストール可） |
| Windows 10 / 11 | [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)（起動時にブラウザで案内） |

---

## インストール

```bash
git clone https://github.com/<your-name>/voice-changer.git
cd voice-changer
uv sync
```

---

## 起動

### GUI（デフォルト）

```bash
uv run voice-changer
```

### CLI モード

```bash
uv run voice-changer --cli
```

---

## GUI の使い方

### 1. デバイス設定

| 項目 | macOS | Windows |
|------|-------|---------|
| 入力 | マイクデバイス | マイクデバイス |
| 出力 | BlackHole 2ch | CABLE Input |
| モニター | スピーカー / イヤホン（任意） | スピーカー / イヤホン（任意） |

設定後、「**開始**」ボタンで変換スタート。

### 2. 組み込みプリセット

| ボタン | 効果 |
|--------|------|
| 男 → 女 | ピッチ +5 半音 + フォルマント 1.3 |
| 女 → 男 | ピッチ -5 半音 + フォルマント 0.75 |
| ギャル声 | ピッチ +12 半音（1 オクターブ上）+ フォルマント 1.2 |
| ロボット | リングモジュレーション（搬送波 50 Hz） |
| エコー | ディレイ 300ms、減衰 0.4 |

「男 → 女」「女 → 男」「ギャル声」は相互排他です。

### 3. エフェクト個別調整

各エフェクト行のトグルスイッチで ON/OFF、スライダーでパラメータをリアルタイム調整できます。

| エフェクト | パラメータ | 範囲 |
|-----------|-----------|------|
| ピッチ | 半音数 | -12〜+12（0.1 刻み） |
| フォルマント | 比率（声道長） | 0.5〜2.0（0.01 刻み） |
| ロボット | 搬送波周波数 (Hz) | 20〜500 |
| エコー | ディレイ (ms) | 50〜1000 |
| エコー | 減衰 | 0〜0.9 |

### 4. カスタムプリセット

調整した設定を名前を付けて保存・呼び出しできます。

| 操作 | 方法 |
|------|------|
| 保存 | 名前欄に入力 → 「新規保存」 |
| 適用 | リストから選択 → 「適用」 |
| 上書き | 選択した状態で同名を入力 → 「上書き保存」 |
| 削除 | リストから選択 → 「削除」 |

保存先: `~/.voice_changer/presets.json`

### 5. 出力音量

0〜200%（5% 刻み）のスライダーで出力ゲインを調整できます。  
フォルマント変換時に音量が下がる場合はここで補正できます。

### 6. 波形モニター

「**波形表示**」ボタンを押すと変換前/後の波形を別ウィンドウで確認できます（約 30fps）。

---

## CLI モードのコマンド一覧

`uv run voice-changer --cli` で起動後、`>` プロンプトで以下のコマンドが使えます。

### プリセット

| コマンド | 効果 |
|---------|------|
| `preset m2f` | 男声 → 女声 |
| `preset f2m` | 女声 → 男声 |
| `preset robot` | ロボット声 |
| `preset echo` | エコー |

### エフェクト ON/OFF

```
on <effect>    # pitch / formant / robot / echo
off <effect>
```

### パラメータ調整

| コマンド | 説明 | デフォルト |
|---------|------|-----------|
| `set pitch <n>` | 半音数 | `0.0` |
| `set formant <r>` | フォルマント比率 | `1.0` |
| `set carrier <hz>` | ロボット搬送波周波数 | `50.0` |
| `set delay <ms>` | エコーディレイ | `300` |

### その他

| コマンド | 説明 |
|---------|------|
| `monitor on / off` | モニタリング切り替え |
| `status` | 現在の設定を表示 |
| `reset` | 全エフェクトを OFF |
| `quit` | 終了 |

---

## Discord / Zoom / Google Meet での使い方

1. アプリを起動し、出力を仮想デバイスに設定して「開始」
2. Discord / Zoom 等のマイク設定で仮想デバイスを選択

| OS | アプリの出力デバイス | Discord 等のマイク設定 |
|----|--------------------|-----------------------|
| macOS | BlackHole 2ch | BlackHole 2ch |
| Windows | CABLE Input | CABLE Output |

3. アプリ上でエフェクトを操作すると通話相手に変換後の声が届く

> モニタリングをONにする場合は必ずイヤホンを使用してください（ハウリング防止）。

---

## 開発者向け

### コマンド

```bash
# 依存関係インストール
uv sync

# GUI 起動
uv run voice-changer

# CLI 起動
uv run voice-changer --cli

# テスト
uv run pytest tests/ -v

# Lint / Format
uv run ruff check src/
uv run ruff format src/
```

### ディレクトリ構成

```
voice_changer/
├── src/voice_changer/
│   ├── main.py              # エントリポイント（デフォルト: GUI / --cli: CLI）
│   ├── __main__.py          # python -m voice_changer サポート
│   ├── audio/
│   │   ├── capture.py       # マイク入力・BlackHole 出力・モニタリング
│   │   └── pipeline.py      # エフェクト直列実行
│   ├── effects/
│   │   ├── base.py          # BaseEffect 抽象クラス
│   │   ├── pitch.py         # 位相ボコーダ OLA
│   │   ├── formant.py       # WORLD CheapTrick スペクトル包絡 + OLA
│   │   ├── robot.py         # リングモジュレーション
│   │   └── echo.py          # 循環ディレイバッファ
│   ├── gui/
│   │   ├── app.py           # QApplication・ダークテーマ stylesheet
│   │   ├── main_window.py   # メインウィンドウ
│   │   ├── preset_manager.py # カスタムプリセット永続化
│   │   ├── waveform_window.py # リアルタイム波形表示
│   │   └── widgets/
│   │       ├── toggle_switch.py  # アニメーション付きトグルスイッチ
│   │       └── effect_row.py     # エフェクト行ウィジェット
│   ├── setup/
│   │   └── blackhole.py     # 仮想オーディオ検出・セットアップ（Mac: BlackHole / Win: VB-Audio Cable）
│   └── cli/
│       └── app.py           # rich ベース CLI UI
├── config/
│   └── default.yaml         # 音声設定・組み込みプリセット定義
├── docs/
│   ├── requirements.md      # 要件定義
│   └── architecture.md      # アーキテクチャ設計
└── tests/
    └── test_effects.py
```

### エフェクトの追加方法

`BaseEffect` を継承して `src/voice_changer/effects/` に追加し、`main_window.py` のパイプラインに組み込む。

```python
from voice_changer.effects.base import BaseEffect
import numpy as np

class MyEffect(BaseEffect):
    def process(self, audio: np.ndarray) -> np.ndarray:
        # audio: float32 モノラル配列
        return audio  # 加工した配列を返す
```

### 設計ドキュメント

- [要件定義](docs/requirements.md)
- [アーキテクチャ設計](docs/architecture.md)

---

## ロードマップ

| Phase | 内容 | 状態 |
|-------|------|------|
| 1 | DSP エフェクト・CLI・BlackHole セットアップ | ✅ 完了 |
| 2 | デスクトップ GUI・カスタムプリセット・波形モニター・Windows 対応 | ✅ 完了 |
| 3 | スタンドアロン配布（PyInstaller）・ML ベース変換（RVC / WORLD Vocoder） | 未着手 |

---

## ライセンス

MIT
