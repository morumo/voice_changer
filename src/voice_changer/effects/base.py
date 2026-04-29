from abc import ABC, abstractmethod

import numpy as np


class BaseEffect(ABC):
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False

    @abstractmethod
    def process(self, audio: np.ndarray) -> np.ndarray:
        """audio: float32 モノラル配列を受け取り、同サイズの配列を返す"""

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled:
            return audio
        return self.process(audio)
