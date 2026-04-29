import sys

import sounddevice as sd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from voice_changer.setup import blackhole

console = Console()


def select_device(prompt_text: str, kind: str) -> int:
    """入力または出力デバイスをユーザーに選択させる。"""
    devices = sd.query_devices()
    table = Table(title=f"{kind} デバイス一覧")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("名前")
    table.add_column("ch", width=4)

    key = "max_input_channels" if kind == "Input" else "max_output_channels"
    valid_ids = []
    for i, d in enumerate(devices):
        if d[key] > 0:
            table.add_row(str(i), d["name"], str(d[key]))
            valid_ids.append(i)

    console.print(table)
    while True:
        idx = IntPrompt.ask(prompt_text)
        if idx in valid_ids:
            return idx
        console.print(f"[red]無効な ID です。{valid_ids} から選んでください。[/red]")


def setup_flow() -> None:
    """BlackHole が未検出の場合にセットアップを促す。"""
    if blackhole.is_installed():
        return

    console.print(Panel(
        "[yellow]BlackHole 2ch が検出されませんでした。[/yellow]\n"
        "Discord / Zoom 等で仮想マイクとして使うには BlackHole が必要です。",
        title="セットアップ"
    ))

    if not Confirm.ask("今すぐインストールしますか？"):
        msg = "[red]BlackHole なしでは仮想マイク出力ができません。パススルーモードで起動します。[/red]"
        console.print(msg)
        return

    success = blackhole.install(console)
    if success:
        console.print("[green]インストール完了！アプリを再起動してください。[/green]")
        sys.exit(0)
    else:
        msg = "[red]インストールに失敗しました。手動で BlackHole をインストールしてください。[/red]"
        console.print(msg)
        console.print("  https://github.com/ExistentialAudio/BlackHole")


def print_status(effects: dict, capture) -> None:
    table = Table(title="エフェクト状態", show_header=True)
    table.add_column("エフェクト", style="cyan")
    table.add_column("状態")
    table.add_column("パラメータ")

    for name, effect in effects.items():
        status = "[green]ON[/green]" if effect.enabled else "[dim]OFF[/dim]"
        params = _effect_params(effect)
        table.add_row(name, status, params)

    monitor_state = "[green]ON[/green]" if capture._monitor_active else "[dim]OFF[/dim]"
    monitor_avail = "" if capture.has_monitor else " [dim](デバイス未選択)[/dim]"
    table.add_row("monitor", monitor_state + monitor_avail, "変換後音声のモニタリング")

    console.print(table)


def _effect_params(effect) -> str:
    cls = type(effect).__name__
    if cls == "PitchShifter":
        return f"semitones={effect.semitones:+.1f}"
    if cls == "FormantShifter":
        return f"ratio={effect.ratio:.2f}"
    if cls == "RobotEffect":
        return f"carrier={effect.carrier_freq:.0f}Hz"
    if cls == "EchoEffect":
        return f"delay={effect.delay_ms:.0f}ms, decay={effect.decay:.2f}"
    return ""


def run_command_loop(effects: dict, capture, stop_event) -> None:
    """キーボード入力でエフェクトを操作するループ。"""
    console.print(Panel(
        "[bold]コマンド一覧[/bold]\n"
        "  [cyan]status[/cyan]           : エフェクト状態表示\n"
        "  [cyan]preset <name>[/cyan]    : プリセット適用 (m2f / f2m / robot / echo)\n"
        "  [cyan]on <effect>[/cyan]      : エフェクト ON (pitch / formant / robot / echo)\n"
        "  [cyan]off <effect>[/cyan]     : エフェクト OFF\n"
        "  [cyan]set pitch <n>[/cyan]    : ピッチ半音数 (例: set pitch 5)\n"
        "  [cyan]set formant <r>[/cyan]  : フォルマント比率 (例: set formant 1.3)\n"
        "  [cyan]set carrier <f>[/cyan]  : ロボット搬送波周波数 Hz\n"
        "  [cyan]set delay <ms>[/cyan]   : エコーディレイ ms\n"
        "  [cyan]monitor on/off[/cyan]   : 変換後音声のモニタリング切り替え\n"
        "  [cyan]reset[/cyan]            : 全エフェクト OFF\n"
        "  [cyan]quit[/cyan]             : 終了",
        title="Voice Changer 起動中"
    ))

    presets = {
        "m2f": {"pitch": (True, {"semitones": 5.0}), "formant": (True, {"ratio": 1.3})},
        "f2m": {"pitch": (True, {"semitones": -5.0}), "formant": (True, {"ratio": 0.75})},
        "robot": {"robot": (True, {})},
        "echo": {"echo": (True, {})},
    }

    while not stop_event.is_set():
        try:
            cmd = Prompt.ask("[bold cyan]>[/bold cyan]").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        parts = cmd.split()
        if not parts:
            continue

        if parts[0] == "quit":
            stop_event.set()
            break

        elif parts[0] == "status":
            print_status(effects, capture)

        elif parts[0] == "reset":
            for e in effects.values():
                e.enabled = False
            console.print("[green]全エフェクトをリセットしました。[/green]")

        elif parts[0] == "monitor" and len(parts) == 2:
            if parts[1] not in ("on", "off"):
                console.print("[red]monitor on または monitor off を入力してください。[/red]")
                continue
            enabled = parts[1] == "on"
            if capture.set_monitor(enabled):
                state = "ON" if enabled else "OFF"
                console.print(f"[green]モニタリングを {state} にしました。[/green]")
            else:
                console.print("[yellow]モニタリングデバイスが設定されていません。再起動時にデバイスを選択してください。[/yellow]")

        elif parts[0] == "preset" and len(parts) == 2:
            name = parts[1]
            if name not in presets:
                console.print(f"[red]不明なプリセット: {name}[/red]")
                continue
            for e in effects.values():
                e.enabled = False
            for eff_name, (enabled, params) in presets[name].items():
                if eff_name in effects:
                    effects[eff_name].enabled = enabled
                    for k, v in params.items():
                        setattr(effects[eff_name], k, v)
            console.print(f"[green]プリセット '{name}' を適用しました。[/green]")

        elif parts[0] in ("on", "off") and len(parts) == 2:
            eff_name = parts[1]
            if eff_name not in effects:
                console.print(f"[red]不明なエフェクト: {eff_name}[/red]")
                continue
            effects[eff_name].enabled = parts[0] == "on"
            state = "ON" if parts[0] == "on" else "OFF"
            console.print(f"[green]{eff_name} を {state} にしました。[/green]")

        elif parts[0] == "set" and len(parts) >= 3:
            target, value = parts[1], parts[2]
            try:
                if target == "pitch":
                    effects["pitch"].semitones = float(value)
                elif target == "formant":
                    effects["formant"].ratio = float(value)
                elif target == "carrier":
                    effects["robot"].carrier_freq = float(value)
                elif target == "delay":
                    effects["echo"].delay_ms = float(value)
                else:
                    console.print(f"[red]不明なパラメータ: {target}[/red]")
                    continue
                console.print(f"[green]{target} = {value} に設定しました。[/green]")
            except ValueError:
                console.print("[red]数値を入力してください。[/red]")

        else:
            console.print("[red]不明なコマンドです。[/red]")
