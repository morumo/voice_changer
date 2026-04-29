from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton


class ToggleSwitch(QAbstractButton):
    """スライドアニメーション付きトグルスイッチ。"""

    def __init__(self, parent=None, on_color: str = "#4CAF50", off_color: str = "#546E7A"):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(50, 26)
        self._on_color = QColor(on_color)
        self._off_color = QColor(off_color)
        self._handle_x = 3.0

        self._anim = QPropertyAnimation(self, b"handle_x", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.toggled.connect(self._start_animation)

    def _start_animation(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setEndValue(27.0 if checked else 3.0)
        self._anim.start()

    def set_checked_instant(self, checked: bool) -> None:
        """アニメーションなしでチェック状態を設定する（シグナルも発しない）。"""
        self._anim.stop()
        self.blockSignals(True)
        self.setChecked(checked)
        self._handle_x = 27.0 if checked else 3.0
        self.blockSignals(False)
        self.update()

    def get_handle_x(self) -> float:
        return self._handle_x

    def set_handle_x(self, value: float) -> None:
        self._handle_x = value
        self.update()

    handle_x = Property(float, get_handle_x, set_handle_x)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        p.setPen(Qt.NoPen)
        p.setBrush(self._on_color if self.isChecked() else self._off_color)
        p.drawRoundedRect(0, 0, w, h, r, r)

        p.setBrush(QColor("white"))
        diameter = h - 6
        p.drawEllipse(int(self._handle_x), 3, diameter, diameter)

    def sizeHint(self) -> QSize:
        return QSize(50, 26)
