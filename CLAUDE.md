# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

マイク入力音声をリアルタイムで変換する DSP ベースのボイスチェンジャー。
Discord / Google Meet / Zoom 等で仮想マイクとして利用できる。

詳細は `docs/` を参照：
- `docs/requirements.md` — 機能要件・非機能要件
- `docs/architecture.md` — 技術スタック・コンポーネント設計

## Working Rules

- 対話中に判明したプロジェクトルールは随時このファイルに追記する
- 要件・設計に関する情報は `docs/` 配下に Markdown ファイルとして作成する
- 曖昧な点は実装前に必ず確認を取る
- ドキュメントの想定読者は AI とエンジニア（基本用語の説明は省く）

## Tech Stack

- **言語**: Python 3.11+
- **パッケージ管理**: uv
- **Lint / Format**: ruff
- **音声 I/O**: sounddevice (PortAudio)
- **DSP**: numpy / scipy / pyrubberband / pyworld
- **CLI UI**: rich
- **仮想オーディオ**: BlackHole 2ch（Mac）

## Development Commands

```bash
# 依存関係インストール
uv sync

# アプリ起動
uv run python -m voice_changer

# Lint
uv run ruff check src/
uv run ruff format src/

# テスト
uv run pytest tests/
```

## Architecture

```
src/voice_changer/
├── main.py          # エントリポイント
├── audio/           # キャプチャ・出力・パイプライン
├── effects/         # BaseEffect + 各エフェクト実装
├── setup/           # BlackHole 検出・セットアップ
└── cli/             # rich ベースの CLI UI
```

エフェクトは `BaseEffect` を継承した独立モジュール。`pipeline.py` が直列に実行する。

## Latency Budget

目標: < 50ms（理想 20〜30ms）
- バッファサイズ: 256〜512 samples @ 44100Hz（約 6〜12ms）
- バッファサイズの変更はレイテンシと安定性のトレードオフになるため注意する

## Development Phases

| Phase | 内容 |
|-------|------|
| 1 (現在) | DSP エフェクト・CLI・BlackHole セットアップ |
| 2 | デスクトップ GUI・Windows 対応 |
| 3 | ML ベース変換（RVC / WORLD Vocoder） |
