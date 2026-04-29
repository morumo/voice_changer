import numpy as np

from .base import BaseEffect


class EchoEffect(BaseEffect):
    def __init__(self, sample_rate: int, delay_ms: float = 300.0, decay: float = 0.4):
        super().__init__(sample_rate)
        self.decay = decay
        self._delay_samples = int(sample_rate * delay_ms / 1000)
        self._buffer = np.zeros(self._delay_samples, dtype=np.float32)
        self._buf_pos = 0

    @property
    def delay_ms(self) -> float:
        return self._delay_samples / self.sample_rate * 1000

    @delay_ms.setter
    def delay_ms(self, value: float) -> None:
        self._delay_samples = int(self.sample_rate * value / 1000)
        self._buffer = np.zeros(self._delay_samples, dtype=np.float32)
        self._buf_pos = 0

    def process(self, audio: np.ndarray) -> np.ndarray:
        out = np.empty_like(audio)
        for i, sample in enumerate(audio):
            delayed = self._buffer[self._buf_pos]
            out[i] = sample + delayed * self.decay
            self._buffer[self._buf_pos] = out[i]
            self._buf_pos = (self._buf_pos + 1) % self._delay_samples
        return out
