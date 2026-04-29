import sys
import threading
from pathlib import Path

import yaml
from rich.prompt import Confirm

from voice_changer.audio.capture import AudioCapture
from voice_changer.audio.pipeline import EffectPipeline
from voice_changer.cli.app import console, run_command_loop, select_device, setup_flow
from voice_changer.effects.echo import EchoEffect
from voice_changer.effects.formant import FormantShifter
from voice_changer.effects.pitch import PitchShifter
from voice_changer.effects.robot import RobotEffect
from voice_changer.setup.blackhole import get_device_index


def load_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def _run() -> None:
    config = load_config()
    audio_cfg = config["audio"]

    setup_flow()

    console.print("[bold green]Voice Changer[/bold green] を起動します。\n")

    input_device = select_device("入力デバイス ID を選択してください", "Input")

    bh_index = get_device_index()
    if bh_index is not None:
        output_device = bh_index
        console.print(f"[green]出力: BlackHole 2ch (ID={bh_index})[/green]")
    else:
        msg = "[yellow]BlackHole が見つかりません。出力デバイスを手動選択してください。[/yellow]"
        console.print(msg)
        output_device = select_device("出力デバイス ID を選択してください", "Output")

    monitor_device = None
    if Confirm.ask("\n変換後の音声をスピーカー/イヤホンでモニタリングしますか？"):
        monitor_device = select_device("モニタリング用出力デバイス ID を選択してください", "Output")

    sr = audio_cfg["sample_rate"]

    pitch = PitchShifter(sr)
    formant = FormantShifter(sr)
    robot = RobotEffect(sr)
    echo = EchoEffect(sr)
    effects = {"pitch": pitch, "formant": formant, "robot": robot, "echo": echo}

    pipeline = EffectPipeline([pitch, formant, robot, echo])

    stop_event = threading.Event()

    with AudioCapture(
        callback=pipeline.process,
        input_device=input_device,
        output_device=output_device,
        sample_rate=sr,
        block_size=audio_cfg["block_size"],
        channels=audio_cfg["channels"],
        monitor_device=monitor_device,
    ) as capture:
        run_command_loop(effects, capture, stop_event)


def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[bold]終了しました。[/bold]")
        sys.exit(0)


if __name__ == "__main__":
    main()
