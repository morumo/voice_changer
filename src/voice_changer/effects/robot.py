import numpy as np

from .base import BaseEffect


class RobotEffect(BaseEffect):
    """リングモジュレーションでロボット声を生成する。"""

    def __init__(self, sample_rate: int, carrier_freq: float = 50.0):
        super().__init__(sample_rate)
        self.carrier_freq = carrier_freq
        self._phase = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        n = len(audio)
        t = (self._phase + np.arange(n)) / self.sample_rate
        carrier = np.sin(2 * np.pi * self.carrier_freq * t)
        self._phase = (self._phase + n) % self.sample_rate
        return (audio * carrier).astype(np.float32)
