from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from voice_changer.audio.capture import AudioCapture
from voice_changer.audio.pipeline import EffectPipeline
from voice_changer.effects.echo import EchoEffect
from voice_changer.effects.formant import FormantShifter
from voice_changer.effects.pitch import PitchShifter
from voice_changer.effects.robot import RobotEffect
from voice_changer.setup.blackhole import display_name as _va_display_name
from voice_changer.setup.blackhole import get_device_index, is_installed
from voice_changer.setup.blackhole import install_url as _va_install_url

from .preset_manager import PresetManager
from .waveform_window import WaveformWindow
from .widgets.effect_row import EffectRow, ParamSpec
from .widgets.toggle_switch import ToggleSwitch


def _load_config() -> dict:
    config_path = Path(__file__).parents[3] / "config" / "default.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Changer")
        self.setMinimumWidth(520)

        config = _load_config()
        self._audio_cfg = config["audio"]

        sr = self._audio_cfg["sample_rate"]
        self._pitch = PitchShifter(sr)
        self._formant = FormantShifter(sr)
        self._robot = RobotEffect(sr)
        self._echo = EchoEffect(sr)
        self._pipeline = EffectPipeline([self._pitch, self._formant, self._robot, self._echo])

        self._capture: AudioCapture | None = None
        self._waveform_window: WaveformWindow | None = None
        self._output_gain: float = 1.0
        self._preset_manager = PresetManager()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_device_section())
        layout.addWidget(self._build_preset_section())
        layout.addWidget(self._build_custom_preset_section())
        layout.addWidget(self._build_effects_section())
        layout.addWidget(self._build_volume_section())
        layout.addWidget(self._build_status_section())
        layout.addStretch()

        if not is_installed():
            dev = _va_display_name()
            QMessageBox.warning(
                self,
                f"{dev} 未インストール",
                f"{dev} が見つかりません。\n"
                "Discord / Zoom 等で仮想マイクとして使用するにはインストールが必要です。\n\n"
                f"{_va_install_url()}",
            )

    # --- デバイスセクション ---

    def _build_device_section(self) -> QGroupBox:
        box = QGroupBox("デバイス設定")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        devices = sd.query_devices()
        inputs = [(i, d["name"]) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
        outputs = [(i, d["name"]) for i, d in enumerate(devices) if d["max_output_channels"] > 0]
        bh_index = get_device_index()

        def combo_row(label: str, items: list[tuple[int, str]], default_id: int | None = None):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(70)
            combo = QComboBox()
            for idx, name in items:
                combo.addItem(f"{idx}: {name}", idx)
            if default_id is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == default_id:
                        combo.setCurrentIndex(i)
                        break
            row.addWidget(lbl)
            row.addWidget(combo)
            return row, combo

        in_row, self._input_combo = combo_row("入力:", inputs)
        out_row, self._output_combo = combo_row("出力:", outputs, default_id=bh_index)
        mon_row, self._monitor_combo = combo_row("モニター:", [(-1, "なし")] + outputs)

        layout.addLayout(in_row)
        layout.addLayout(out_row)
        layout.addLayout(mon_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._start_btn = QPushButton("開始")
        self._start_btn.setObjectName("start-btn")
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn = QPushButton("停止")
        self._stop_btn.setObjectName("stop-btn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        return box

    # --- プリセットセクション ---

    def _build_preset_section(self) -> QGroupBox:
        box = QGroupBox("プリセット")
        layout = QHBoxLayout(box)
        layout.setSpacing(8)

        self._preset_btns: dict[str, QPushButton] = {}
        _presets = [
            ("m2f", "男 → 女"), ("f2m", "女 → 男"), ("gal", "ギャル声"),
            ("robot", "ロボット"), ("echo", "エコー"),
        ]
        for key, label in _presets:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("preset-btn")
            btn.setFixedHeight(44)
            btn.toggled.connect(lambda checked, k=key: self._apply_preset(k, checked))
            self._preset_btns[key] = btn
            layout.addWidget(btn)

        return box

    # --- カスタムプリセットセクション ---

    def _build_custom_preset_section(self) -> QGroupBox:
        box = QGroupBox("カスタムプリセット")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        # Row 1: 選択・適用・削除
        row1 = QHBoxLayout()
        self._custom_preset_combo = QComboBox()
        self._custom_preset_combo.setPlaceholderText("プリセットを選択")
        self._custom_preset_combo.currentIndexChanged.connect(self._on_preset_selection_changed)
        row1.addWidget(self._custom_preset_combo, 1)

        self._preset_apply_btn = QPushButton("適用")
        self._preset_apply_btn.setObjectName("preset-action-btn")
        self._preset_apply_btn.setEnabled(False)
        self._preset_apply_btn.clicked.connect(self._on_preset_apply)
        row1.addWidget(self._preset_apply_btn)

        self._preset_delete_btn = QPushButton("削除")
        self._preset_delete_btn.setObjectName("preset-delete-btn")
        self._preset_delete_btn.setEnabled(False)
        self._preset_delete_btn.clicked.connect(self._on_preset_delete)
        row1.addWidget(self._preset_delete_btn)
        layout.addLayout(row1)

        # Row 2: 名前入力・新規保存・上書き保存
        row2 = QHBoxLayout()
        name_lbl = QLabel("名前:")
        name_lbl.setFixedWidth(36)
        row2.addWidget(name_lbl)

        self._preset_name_edit = QLineEdit()
        self._preset_name_edit.setPlaceholderText("プリセット名を入力")
        self._preset_name_edit.textChanged.connect(self._on_preset_name_changed)
        row2.addWidget(self._preset_name_edit, 1)

        self._preset_save_btn = QPushButton("新規保存")
        self._preset_save_btn.setObjectName("preset-action-btn")
        self._preset_save_btn.setEnabled(False)
        self._preset_save_btn.clicked.connect(self._on_preset_save)
        row2.addWidget(self._preset_save_btn)

        self._preset_update_btn = QPushButton("上書き保存")
        self._preset_update_btn.setObjectName("preset-action-btn")
        self._preset_update_btn.setEnabled(False)
        self._preset_update_btn.clicked.connect(self._on_preset_update)
        row2.addWidget(self._preset_update_btn)
        layout.addLayout(row2)

        self._refresh_preset_combo()
        return box

    def _capture_state(self) -> dict:
        return {
            "pitch": {"enabled": self._pitch.enabled, "semitones": self._pitch.semitones},
            "formant": {"enabled": self._formant.enabled, "ratio": self._formant.ratio},
            "robot": {"enabled": self._robot.enabled, "carrier_freq": self._robot.carrier_freq},
            "echo": {"enabled": self._echo.enabled, "delay_ms": self._echo.delay_ms, "decay": self._echo.decay},
            "output_gain": self._output_gain,
        }

    def _apply_state(self, data: dict) -> None:
        if "pitch" in data:
            p = data["pitch"]
            self._pitch.enabled = p.get("enabled", False)
            self._pitch.semitones = p.get("semitones", 0.0)
            self._pitch_row.set_enabled(self._pitch.enabled)
            self._pitch_row.set_value("semitones", self._pitch.semitones)

        if "formant" in data:
            f = data["formant"]
            self._formant.enabled = f.get("enabled", False)
            self._formant.ratio = f.get("ratio", 1.0)
            self._formant_row.set_enabled(self._formant.enabled)
            self._formant_row.set_value("ratio", self._formant.ratio)

        if "robot" in data:
            r = data["robot"]
            self._robot.enabled = r.get("enabled", False)
            self._robot.carrier_freq = r.get("carrier_freq", 50.0)
            self._robot_row.set_enabled(self._robot.enabled)
            self._robot_row.set_value("carrier_freq", self._robot.carrier_freq)

        if "echo" in data:
            e = data["echo"]
            self._echo.enabled = e.get("enabled", False)
            self._echo.delay_ms = e.get("delay_ms", 300.0)
            self._echo.decay = e.get("decay", 0.4)
            self._echo_row.set_enabled(self._echo.enabled)
            self._echo_row.set_value("delay_ms", self._echo.delay_ms)
            self._echo_row.set_value("decay", self._echo.decay)

        if "output_gain" in data:
            self._output_gain = data["output_gain"]
            int_val = round(self._output_gain / 0.05)
            self._volume_slider.blockSignals(True)
            self._volume_slider.setValue(int_val)
            self._volume_slider.blockSignals(False)
            self._volume_lbl.setText(f"{int_val * 5}%")

    def _refresh_preset_combo(self, select_name: str | None = None) -> None:
        self._custom_preset_combo.blockSignals(True)
        self._custom_preset_combo.clear()
        for name in self._preset_manager.names():
            self._custom_preset_combo.addItem(name)
        self._custom_preset_combo.blockSignals(False)

        if select_name is not None:
            idx = self._custom_preset_combo.findText(select_name)
            self._custom_preset_combo.setCurrentIndex(idx)
        else:
            self._custom_preset_combo.setCurrentIndex(-1)

        has_selection = self._custom_preset_combo.currentIndex() >= 0
        self._preset_apply_btn.setEnabled(has_selection)
        self._preset_delete_btn.setEnabled(has_selection)
        self._update_preset_save_btn_state()

    def _update_preset_save_btn_state(self) -> None:
        name = self._preset_name_edit.text().strip()
        self._preset_save_btn.setEnabled(bool(name))
        selected = self._custom_preset_combo.currentIndex() >= 0
        self._preset_update_btn.setEnabled(bool(name) and selected and self._custom_preset_combo.currentText() == name)

    def _on_preset_selection_changed(self, index: int) -> None:
        has = index >= 0
        self._preset_apply_btn.setEnabled(has)
        self._preset_delete_btn.setEnabled(has)
        if has:
            self._preset_name_edit.setText(self._custom_preset_combo.currentText())
        self._update_preset_save_btn_state()

    def _on_preset_name_changed(self, _text: str) -> None:
        self._update_preset_save_btn_state()

    def _on_preset_apply(self) -> None:
        name = self._custom_preset_combo.currentText()
        data = self._preset_manager.get(name)
        if data:
            self._apply_state(data)

    def _on_preset_save(self) -> None:
        name = self._preset_name_edit.text().strip()
        if not name:
            return
        if self._preset_manager.get(name) is not None:
            if QMessageBox.question(
                self, "上書き確認", f'"{name}" は既に存在します。上書きしますか？'
            ) != QMessageBox.Yes:
                return
        self._preset_manager.save(name, self._capture_state())
        self._refresh_preset_combo(select_name=name)

    def _on_preset_update(self) -> None:
        name = self._custom_preset_combo.currentText()
        if not name:
            return
        self._preset_manager.save(name, self._capture_state())
        self._refresh_preset_combo(select_name=name)

    def _on_preset_delete(self) -> None:
        name = self._custom_preset_combo.currentText()
        if not name:
            return
        if QMessageBox.question(
            self, "削除確認", f'"{name}" を削除しますか？'
        ) != QMessageBox.Yes:
            return
        self._preset_manager.delete(name)
        self._preset_name_edit.clear()
        self._refresh_preset_combo()

    # --- エフェクトセクション ---

    def _build_effects_section(self) -> QGroupBox:
        box = QGroupBox("エフェクト")
        layout = QVBoxLayout(box)
        layout.setSpacing(12)

        self._pitch_row = EffectRow("ピッチ", [
            ParamSpec("半音数", "semitones", -12.0, 12.0, 0.1, "+.1f", 0.0),
        ])
        self._pitch_row.enabled_changed.connect(lambda v: setattr(self._pitch, "enabled", v))
        self._pitch_row.param_changed.connect(lambda a, v: setattr(self._pitch, a, v))
        layout.addWidget(self._pitch_row)
        layout.addWidget(self._make_separator())

        self._formant_row = EffectRow("フォルマント", [
            ParamSpec("比率", "ratio", 0.5, 2.0, 0.01, ".2f", 1.0),
        ])
        self._formant_row.enabled_changed.connect(lambda v: setattr(self._formant, "enabled", v))
        self._formant_row.param_changed.connect(lambda a, v: setattr(self._formant, a, v))
        layout.addWidget(self._formant_row)
        layout.addWidget(self._make_separator())

        self._robot_row = EffectRow("ロボット", [
            ParamSpec("搬送波周波数 (Hz)", "carrier_freq", 20.0, 500.0, 5.0, ".0f", 50.0),
        ])
        self._robot_row.enabled_changed.connect(lambda v: setattr(self._robot, "enabled", v))
        self._robot_row.param_changed.connect(lambda a, v: setattr(self._robot, a, v))
        layout.addWidget(self._robot_row)
        layout.addWidget(self._make_separator())

        self._echo_row = EffectRow("エコー", [
            ParamSpec("ディレイ (ms)", "delay_ms", 50.0, 1000.0, 10.0, ".0f", 300.0),
            ParamSpec("減衰", "decay", 0.0, 0.9, 0.05, ".2f", 0.4),
        ])
        self._echo_row.enabled_changed.connect(lambda v: setattr(self._echo, "enabled", v))
        self._echo_row.param_changed.connect(lambda a, v: setattr(self._echo, a, v))
        layout.addWidget(self._echo_row)

        return box

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        return sep

    # --- 出力音量セクション ---

    def _build_volume_section(self) -> QGroupBox:
        box = QGroupBox("出力設定")
        row = QHBoxLayout(box)
        row.setSpacing(8)

        lbl = QLabel("出力音量")
        lbl.setProperty("class", "param-label")
        lbl.setFixedWidth(150)
        row.addWidget(lbl)

        # 0% to 200%, 5% step → 40 steps
        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setRange(0, 40)
        self._volume_slider.setValue(20)  # 100%
        self._volume_slider.setFixedHeight(20)
        row.addWidget(self._volume_slider)

        self._volume_lbl = QLabel("100%")
        self._volume_lbl.setFixedWidth(56)
        self._volume_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._volume_lbl.setProperty("class", "param-value")
        row.addWidget(self._volume_lbl)

        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        return box

    def _on_volume_changed(self, int_val: int) -> None:
        self._output_gain = int_val * 0.05
        self._volume_lbl.setText(f"{int_val * 5}%")

    # --- ステータスセクション ---

    def _build_status_section(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)

        self._status_lbl = QLabel("● 停止中")
        self._status_lbl.setStyleSheet("color: #9090A0; font-weight: bold;")
        row.addWidget(self._status_lbl)
        row.addStretch()

        self._waveform_btn = QPushButton("波形表示")
        self._waveform_btn.setObjectName("waveform-btn")
        self._waveform_btn.setEnabled(False)
        self._waveform_btn.clicked.connect(self._on_waveform_btn)
        row.addWidget(self._waveform_btn)

        row.addWidget(QLabel("モニタリング:"))
        self._monitor_toggle = ToggleSwitch()
        self._monitor_toggle.setEnabled(False)
        self._monitor_toggle.toggled.connect(self._on_monitor_toggle)
        row.addWidget(self._monitor_toggle)

        return w

    # --- イベントハンドラ ---

    def _audio_callback(self, audio):
        """パイプラインを実行し、出力ゲインを適用する。"""
        processed = self._pipeline.process(audio)
        if self._output_gain != 1.0:
            processed = np.clip(processed * self._output_gain, -1.0, 1.0).astype(np.float32)
        if self._waveform_window and self._waveform_window.isVisible():
            self._waveform_window.push(audio, processed)
        return processed

    def _on_start(self) -> None:
        input_device = self._input_combo.currentData()
        output_device = self._output_combo.currentData()
        monitor_device = self._monitor_combo.currentData()
        if monitor_device == -1:
            monitor_device = None

        try:
            self._capture = AudioCapture(
                callback=self._audio_callback,
                input_device=input_device,
                output_device=output_device,
                sample_rate=self._audio_cfg["sample_rate"],
                block_size=self._audio_cfg["block_size"],
                channels=self._audio_cfg["channels"],
                monitor_device=monitor_device,
            )
            self._capture.start()
        except Exception as e:
            QMessageBox.critical(self, "起動エラー", f"音声ストリームを開始できませんでした。\n{e}")
            self._capture = None
            return

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._input_combo.setEnabled(False)
        self._output_combo.setEnabled(False)
        self._monitor_combo.setEnabled(False)
        self._monitor_toggle.setEnabled(self._capture.has_monitor)
        self._waveform_btn.setEnabled(True)
        self._status_lbl.setText("● 変換中")
        self._status_lbl.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _on_stop(self) -> None:
        if self._capture:
            self._capture.stop()
            self._capture = None

        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._input_combo.setEnabled(True)
        self._output_combo.setEnabled(True)
        self._monitor_combo.setEnabled(True)
        self._monitor_toggle.set_checked_instant(False)
        self._monitor_toggle.setEnabled(False)
        self._waveform_btn.setEnabled(False)
        self._status_lbl.setText("● 停止中")
        self._status_lbl.setStyleSheet("color: #9090A0; font-weight: bold;")

    def _on_waveform_btn(self) -> None:
        sr = self._audio_cfg["sample_rate"]
        if self._waveform_window is None:
            self._waveform_window = WaveformWindow(sample_rate=sr)
        self._waveform_window.show()
        self._waveform_window.raise_()

    def _on_monitor_toggle(self, enabled: bool) -> None:
        if self._capture and not self._capture.set_monitor(enabled):
            self._monitor_toggle.set_checked_instant(False)

    def _apply_preset(self, name: str, checked: bool) -> None:
        # m2f / f2m / gal はピッチ+フォルマントを同時に操作するため排他
        if name in ("m2f", "f2m", "gal") and checked:
            for other in ("m2f", "f2m", "gal"):
                if other != name:
                    self._preset_btns[other].blockSignals(True)
                    self._preset_btns[other].setChecked(False)
                    self._preset_btns[other].blockSignals(False)

        if name == "m2f":
            self._pitch.enabled = checked
            self._formant.enabled = checked
            self._pitch_row.set_enabled(checked)
            self._formant_row.set_enabled(checked)
            if checked:
                self._pitch.semitones = 5.0
                self._formant.ratio = 1.3
                self._pitch_row.set_value("semitones", 5.0)
                self._formant_row.set_value("ratio", 1.3)

        elif name == "f2m":
            self._pitch.enabled = checked
            self._formant.enabled = checked
            self._pitch_row.set_enabled(checked)
            self._formant_row.set_enabled(checked)
            if checked:
                self._pitch.semitones = -5.0
                self._formant.ratio = 0.75
                self._pitch_row.set_value("semitones", -5.0)
                self._formant_row.set_value("ratio", 0.75)

        elif name == "gal":
            self._pitch.enabled = checked
            self._formant.enabled = checked
            self._pitch_row.set_enabled(checked)
            self._formant_row.set_enabled(checked)
            if checked:
                self._pitch.semitones = 12.0
                self._formant.ratio = 1.2
                self._pitch_row.set_value("semitones", 12.0)
                self._formant_row.set_value("ratio", 1.2)

        elif name == "robot":
            self._robot.enabled = checked
            self._robot_row.set_enabled(checked)
            if checked:
                self._robot.carrier_freq = 50.0
                self._robot_row.set_value("carrier_freq", 50.0)

        elif name == "echo":
            self._echo.enabled = checked
            self._echo_row.set_enabled(checked)
            if checked:
                self._echo.delay_ms = 300.0
                self._echo.decay = 0.4
                self._echo_row.set_value("delay_ms", 300.0)
                self._echo_row.set_value("decay", 0.4)

    def closeEvent(self, event) -> None:
        if self._capture:
            self._capture.stop()
        if self._waveform_window:
            self._waveform_window.close()
        event.accept()
