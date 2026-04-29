import numpy as np
import pytest

from voice_changer.audio.pipeline import EffectPipeline
from voice_changer.effects.echo import EchoEffect
from voice_changer.effects.formant import FormantShifter
from voice_changer.effects.pitch import PitchShifter
from voice_changer.effects.robot import RobotEffect

SR = 44100
BLOCK = 256
# OLA 実装のウォームアップ: FRAME / HOP ブロック以上流してから評価する
WARMUP_BLOCKS = PitchShifter.FRAME // PitchShifter.HOP + 1


@pytest.fixture
def audio():
    rng = np.random.default_rng(42)
    return rng.standard_normal(BLOCK).astype(np.float32) * 0.1


def _feed(effect, blocks: int) -> np.ndarray:
    """effect に blocks 個のランダムブロックを流し、最後のブロックの出力を返す。"""
    rng = np.random.default_rng(0)
    out = None
    for _ in range(blocks):
        chunk = rng.standard_normal(BLOCK).astype(np.float32) * 0.1
        out = effect(chunk)
    return out


# ---- RobotEffect ----

def test_robot_passthrough_when_disabled(audio):
    robot = RobotEffect(SR)
    assert (robot(audio) == audio).all()


def test_robot_output_shape(audio):
    robot = RobotEffect(SR, carrier_freq=50.0)
    robot.enabled = True
    assert robot(audio).shape == audio.shape


def test_robot_modifies_signal(audio):
    robot = RobotEffect(SR, carrier_freq=50.0)
    robot.enabled = True
    assert not np.allclose(robot(audio), audio)


# ---- EchoEffect ----

def test_echo_output_shape(audio):
    echo = EchoEffect(SR, delay_ms=300, decay=0.4)
    echo.enabled = True
    assert echo(audio).shape == audio.shape


def test_echo_passthrough_when_disabled(audio):
    echo = EchoEffect(SR, delay_ms=300, decay=0.4)
    assert (echo(audio) == audio).all()


def test_echo_delay_setter_resets_buffer(audio):
    echo = EchoEffect(SR, delay_ms=300, decay=0.4)
    echo.delay_ms = 200
    assert echo._delay_samples == int(SR * 200 / 1000)
    assert len(echo._buffer) == echo._delay_samples


# ---- PitchShifter ----

def test_pitch_output_shape(audio):
    """PitchShifter は 256 サンプルブロックでも同サイズを返す。"""
    pitch = PitchShifter(SR, semitones=5.0)
    pitch.enabled = True
    assert pitch(audio).shape == audio.shape


def test_pitch_passthrough_when_disabled(audio):
    pitch = PitchShifter(SR, semitones=5.0)
    assert (pitch(audio) == audio).all()


def test_pitch_modifies_signal_after_warmup():
    """OLA ウォームアップ後に信号が変化していること。"""
    pitch = PitchShifter(SR, semitones=5.0)
    pitch.enabled = True
    out = _feed(pitch, WARMUP_BLOCKS)
    rng = np.random.default_rng(0)
    last_input = rng.standard_normal(BLOCK).astype(np.float32) * 0.1
    assert not np.allclose(out, last_input)


# ---- FormantShifter ----

def test_formant_output_shape(audio):
    """FormantShifter は 256 サンプルブロックでも同サイズを返す。"""
    formant = FormantShifter(SR, ratio=1.3)
    formant.enabled = True
    assert formant(audio).shape == audio.shape


def test_formant_passthrough_when_disabled(audio):
    formant = FormantShifter(SR, ratio=1.3)
    assert (formant(audio) == audio).all()


def test_formant_modifies_signal_after_warmup():
    """OLA ウォームアップ後に信号が変化していること。"""
    formant = FormantShifter(SR, ratio=1.3)
    formant.enabled = True
    out = _feed(formant, WARMUP_BLOCKS)
    rng = np.random.default_rng(0)
    last_input = rng.standard_normal(BLOCK).astype(np.float32) * 0.1
    assert not np.allclose(out, last_input)


# ---- Pipeline ----

def test_pipeline_passthrough(audio):
    """全エフェクト OFF のとき入力がそのまま返る。"""
    robot = RobotEffect(SR)
    echo = EchoEffect(SR)
    pipeline = EffectPipeline([robot, echo])
    assert (pipeline.process(audio) == audio).all()


def test_pipeline_applies_effects(audio):
    robot = RobotEffect(SR, carrier_freq=50.0)
    robot.enabled = True
    pipeline = EffectPipeline([robot])
    assert not np.allclose(pipeline.process(audio), audio)


# ---- AudioCapture ----

def test_capture_set_monitor_without_device():
    """monitor_device 未設定時は set_monitor が False を返す。"""
    from unittest.mock import patch

    with patch("sounddevice.Stream"), patch("sounddevice.query_devices", return_value=[]):
        from voice_changer.audio.capture import AudioCapture

        cap = AudioCapture(
            callback=lambda x: x,
            input_device=None,
            output_device=None,
            sample_rate=SR,
            block_size=BLOCK,
            channels=1,
            monitor_device=None,
        )
        assert cap.has_monitor is False
        assert cap.set_monitor(True) is False
