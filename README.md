# Voice Changer

マイク入力音声をリアルタイムで変換する DSP ベースのボイスチェンジャー。  
Discord / Google Meet / Zoom 等の仮想マイクとして利用できます。

## 特徴

- 低レイテンシ（目標 20〜30ms）
- 完全ローカル動作（外部 API 不使用）
- 男声/女声変換・ロボット・エコー・ピッチ調整に対応
- CLI でリアルタイムにパラメータ変更可能

---

## 必要環境

- macOS 12 Monterey 以降
- Python 3.11 以降
- [uv](https://github.com/astral-sh/uv)（パッケージ管理）
- [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole)（仮想オーディオデバイス）

> **BlackHole について**  
> 初回起動時にインストールされていない場合、アプリが自動でダウンロード・インストールを行います。  
> 管理者パスワードの入力が必要です。

---

## インストール

```bash
git clone https://github.com/<your-name>/voice-changer.git
cd voice-changer
uv sync
```

---

## 起動

```bash
uv run voice-changer
```

起動後の流れ：

1. BlackHole の有無を自動確認（未インストールの場合セットアップを案内）
2. 入力デバイス（マイク）を ID で選択
3. 出力デバイス（BlackHole 2ch）が自動選択される
4. `>` プロンプトが表示されたら操作開始

---

## コマンド一覧

### プリセット

| コマンド | 効果 |
|---------|------|
| `preset m2f` | 男声 → 女声（pitch +5半音 + formant 1.3） |
| `preset f2m` | 女声 → 男声（pitch -5半音 + formant 0.75） |
| `preset robot` | ロボット声 |
| `preset echo` | エコー |

### エフェクト ON/OFF

```
on <effect>    # エフェクトを ON にする
off <effect>   # エフェクトを OFF にする
```

`<effect>` に指定できる値: `pitch` / `formant` / `robot` / `echo`

### パラメータ調整（リアルタイム反映）

| コマンド | 説明 | デフォルト |
|---------|------|-----------|
| `set pitch <n>` | ピッチ半音数（負で低く） | `0.0` |
| `set formant <r>` | フォルマント比率（1.0 = 原音） | `1.0` |
| `set carrier <hz>` | ロボット搬送波周波数 | `50.0` |
| `set delay <ms>` | エコーディレイ ms | `300` |

### モニタリング（変換後の音声を自分で確認）

起動時に「モニタリングしますか？」と聞かれるので、`y` を選んでスピーカー/イヤホンのデバイスを選択します。  
起動後は以下のコマンドでリアルタイムに切り替えられます。

```
monitor on    # モニタリング開始
monitor off   # モニタリング停止
```

> **注意**: イヤホンなしでモニタリングをONにするとハウリングが発生します。必ずイヤホンを使用してください。

### その他

| コマンド | 説明 |
|---------|------|
| `status` | 現在のエフェクト状態とモニタリング状態を表示 |
| `reset` | 全エフェクトを OFF |
| `quit` | アプリを終了 |

### 操作例

```
> preset m2f          # 男声→女声プリセットを適用
> set pitch 3         # ピッチを +3半音に調整
> set formant 1.2     # フォルマントを微調整
> on echo             # エコーを追加
> set delay 200       # エコーディレイを 200ms に
> status              # 状態確認
> reset               # 全リセット
```

---

## Discord / Zoom / Google Meet での使い方

1. アプリを起動し、出力を BlackHole 2ch に設定する
2. Discord / Zoom 等のマイク設定で **BlackHole 2ch** を選択する
3. アプリ上でエフェクトを操作すると、通話相手に変換後の声が届く

---

## 開発者向け

### 環境構築

```bash
uv sync
```

### コマンド

```bash
# アプリ起動
uv run voice-changer

# テスト実行
uv run pytest tests/ -v

# Lint / Format チェック
uv run ruff check src/
uv run ruff format src/
```

### ディレクトリ構成

```
voice_changer/
├── src/voice_changer/
│   ├── main.py              # エントリポイント
│   ├── audio/
│   │   ├── capture.py       # マイク入力ストリーム管理
│   │   └── pipeline.py      # エフェクトの直列実行
│   ├── effects/
│   │   ├── base.py          # BaseEffect 抽象クラス
│   │   ├── pitch.py         # ピッチシフト（pyrubberband）
│   │   ├── formant.py       # フォルマントシフト（pyworld）
│   │   ├── robot.py         # ロボット声（リングモジュレーション）
│   │   └── echo.py          # エコー（循環ディレイバッファ）
│   ├── setup/
│   │   └── blackhole.py     # BlackHole 検出・インストール支援
│   └── cli/
│       └── app.py           # rich ベースの CLI UI
├── config/
│   └── default.yaml         # デフォルト設定・プリセット定義
├── docs/
│   ├── requirements.md      # 要件定義
│   └── architecture.md      # アーキテクチャ設計
└── tests/
    └── test_effects.py
```

### エフェクトの追加方法

`BaseEffect` を継承したクラスを `src/voice_changer/effects/` に追加し、`main.py` のパイプラインに組み込む。

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

| Phase | 内容 |
|-------|------|
| 1 ✅ | DSP エフェクト・CLI・BlackHole セットアップ |
| 2 | デスクトップ GUI・Windows 対応 |
| 3 | ML ベース変換（RVC / WORLD Vocoder） |

## ライセンス

MIT
