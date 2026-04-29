import numpy as np

from voice_changer.effects.base import BaseEffect


class EffectPipeline:
    """エフェクトを直列に適用するパイプライン。"""

    def __init__(self, effects: list[BaseEffect]):
        self._effects = effects

    def process(self, audio: np.ndarray) -> np.ndarray:
        for effect in self._effects:
            try:
                audio = effect(audio)
            except Exception:
                # エフェクト処理失敗時はそのブロックをパススルーする
                pass
        return audio
