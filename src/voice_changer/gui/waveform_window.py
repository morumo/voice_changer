import collections
import queue

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget


class WaveformWindow(QWidget):
    """入力/出力波形をリアルタイム表示するサブウィンドウ。"""

    _DISPLAY_SAMPLES = 4096    # 表示サンプル数（約93ms @ 44100Hz）
    _QUEUE_MAXSIZE = 16        # 音声コールバックからの受信キュー上限（あふれたらドロップ）
    _UPDATE_INTERVAL_MS = 33   # 描画更新間隔（約30fps）

    def __init__(self, sample_rate: int, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("波形モニター")
        self.resize(720, 440)
        self._sample_rate = sample_rate

        self._queue: queue.Queue = queue.Queue(maxsize=self._QUEUE_MAXSIZE)
        self._in_deque: collections.deque = collections.deque(
            [0.0] * self._DISPLAY_SAMPLES, maxlen=self._DISPLAY_SAMPLES
        )
        self._out_deque: collections.deque = collections.deque(
            [0.0] * self._DISPLAY_SAMPLES, maxlen=self._DISPLAY_SAMPLES
        )

        pg.setConfigOptions(background="#1A1B2E", foreground="#E8E8F0")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # x 軸ティック（サンプル数 → ms 表記）
        tick_samples = np.linspace(0, self._DISPLAY_SAMPLES, 7, dtype=int)
        tick_ms = [f"{v:.0f}" for v in tick_samples / sample_rate * 1000]
        tick_pairs = list(zip(tick_samples.tolist(), tick_ms))

        # 入力波形プロット
        in_plot = pg.PlotWidget(title="入力（変換前）")
        in_plot.setYRange(-1.0, 1.0, padding=0)
        in_plot.setXRange(0, self._DISPLAY_SAMPLES, padding=0)
        in_plot.setMouseEnabled(x=False, y=False)
        in_plot.getPlotItem().hideAxis("bottom")
        self._in_curve = in_plot.plot(pen=pg.mkPen("#4FC3F7", width=1))
        layout.addWidget(in_plot)

        # 出力波形プロット
        out_plot = pg.PlotWidget(title="出力（変換後）")
        out_plot.setYRange(-1.0, 1.0, padding=0)
        out_plot.setXRange(0, self._DISPLAY_SAMPLES, padding=0)
        out_plot.setMouseEnabled(x=False, y=False)
        out_plot.getAxis("bottom").setTicks([tick_pairs])
        out_plot.getAxis("bottom").setLabel("時間 (ms)")
        self._out_curve = out_plot.plot(pen=pg.mkPen("#4CAF50", width=1))
        layout.addWidget(out_plot)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)

    def push(self, in_audio: np.ndarray, out_audio: np.ndarray) -> None:
        """音声コールバックスレッドから呼ばれる。ブロックしない。"""
        try:
            self._queue.put_nowait((in_audio, out_audio))
        except queue.Full:
            pass

    def _refresh(self) -> None:
        """Qt メインスレッドで定期的に呼ばれ、キューを消費して波形を更新する。"""
        updated = False
        while True:
            try:
                in_audio, out_audio = self._queue.get_nowait()
                self._in_deque.extend(in_audio)
                self._out_deque.extend(out_audio)
                updated = True
            except queue.Empty:
                break
        if updated:
            self._in_curve.setData(np.array(self._in_deque))
            self._out_curve.setData(np.array(self._out_deque))

    def showEvent(self, event) -> None:
        self._timer.start(self._UPDATE_INTERVAL_MS)
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        event.accept()
