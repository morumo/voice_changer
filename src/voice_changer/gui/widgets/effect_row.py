from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .toggle_switch import ToggleSwitch


@dataclass
class ParamSpec:
    label: str
    attr: str
    min_val: float
    max_val: float
    step: float
    fmt: str = ".2f"
    default: float = 0.0


class EffectRow(QWidget):
    """エフェクト名 + 有効トグル + パラメータスライダー行。"""

    enabled_changed = Signal(bool)
    param_changed = Signal(str, float)  # (attr, value)

    def __init__(self, name: str, params: list[ParamSpec], parent=None):
        super().__init__(parent)
        self._specs = {spec.attr: spec for spec in params}
        self._sliders: dict[str, tuple[QSlider, QLabel]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(8)

        # ヘッダー行: エフェクト名 + トグル
        header = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setProperty("class", "effect-name")
        header.addWidget(name_lbl)
        header.addStretch()
        self._toggle = ToggleSwitch()
        self._toggle.toggled.connect(self.enabled_changed)
        header.addWidget(self._toggle)
        root.addLayout(header)

        # パラメータスライダー行
        for spec in params:
            row = QHBoxLayout()
            row.setSpacing(8)

            param_lbl = QLabel(spec.label)
            param_lbl.setProperty("class", "param-label")
            param_lbl.setFixedWidth(150)
            row.addWidget(param_lbl)

            slider = QSlider(Qt.Horizontal)
            n_steps = round((spec.max_val - spec.min_val) / spec.step)
            slider.setRange(0, n_steps)
            slider.setFixedHeight(20)

            val_lbl = QLabel()
            val_lbl.setFixedWidth(56)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_lbl.setProperty("class", "param-value")

            # デフォルト値をシグナルなしで設定
            init_steps = round((spec.default - spec.min_val) / spec.step)
            init_steps = max(0, min(n_steps, init_steps))
            slider.setValue(init_steps)
            val_lbl.setText(format(spec.default, spec.fmt))

            # シグナル接続（デフォルト値設定の後）
            slider.valueChanged.connect(
                lambda v, s=spec, vl=val_lbl: self._on_slider_changed(v, s, vl)
            )

            row.addWidget(slider)
            row.addWidget(val_lbl)
            self._sliders[spec.attr] = (slider, val_lbl)
            root.addLayout(row)

    def _on_slider_changed(self, int_val: int, spec: ParamSpec, val_lbl: QLabel) -> None:
        value = round(spec.min_val + int_val * spec.step, 10)
        val_lbl.setText(format(value, spec.fmt))
        self.param_changed.emit(spec.attr, value)

    def set_enabled(self, enabled: bool) -> None:
        """シグナルを発さずに有効状態を更新する（プリセット適用時など）。"""
        self._toggle.set_checked_instant(enabled)

    def set_value(self, attr: str, value: float) -> None:
        """シグナルを発さずにスライダー値を更新する（プリセット適用時など）。"""
        if attr not in self._sliders or attr not in self._specs:
            return
        slider, val_lbl = self._sliders[attr]
        spec = self._specs[attr]
        int_val = round((value - spec.min_val) / spec.step)
        int_val = max(0, min(slider.maximum(), int_val))
        slider.blockSignals(True)
        slider.setValue(int_val)
        val_lbl.setText(format(value, spec.fmt))
        slider.blockSignals(False)
