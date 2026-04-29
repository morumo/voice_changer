import numpy as np

from .base import BaseEffect

_TWO_PI = 2.0 * np.pi


class PitchShifter(BaseEffect):
    """位相ボコーダ (OLA) によるリアルタイムピッチシフター。

    FRAME=2048, HOP=256。config の block_size と HOP を一致させること。
    ブロック境界をまたいで位相を連続的に管理するため、機械音にならない。
    """

    FRAME = 2048
    HOP = 256  # config/default.yaml の block_size と合わせる

    def __init__(self, sample_rate: int, semitones: float = 0.0):
        super().__init__(sample_rate)
        self.semitones = semitones
        n_bins = self.FRAME // 2 + 1

        self._win = np.hanning(self.FRAME)
        # HOP サンプルで各 bin が進む期待位相量
        self._bin_phase_step = _TWO_PI * np.arange(n_bins) * self.HOP / self.FRAME

        # 位相ボコーダ状態（ブロックをまたいで保持）
        self._prev_phase = np.zeros(n_bins)
        self._synth_phase = np.zeros(n_bins)

        self._in_buf = np.zeros(self.FRAME)
        self._out_buf = np.zeros(self.FRAME + self.HOP)
        # OLA 正規化: ∑ w²[n] / HOP（Hann 窓、8× 重複で ≈ 3.0）
        self._ola_norm = float(np.sum(self._win**2) / self.HOP)

    def process(self, audio: np.ndarray) -> np.ndarray:
        alpha = 2.0 ** (self.semitones / 12.0)
        n = len(audio)

        # 入力バッファをスライド（最新 n サンプルを末尾へ）
        self._in_buf[:-n] = self._in_buf[n:]
        self._in_buf[-n:] = audio.astype(np.float64)

        # --- 分析 ---
        X = np.fft.rfft(self._in_buf * self._win)
        mag = np.abs(X)
        phase = np.angle(X)

        # 瞬時周波数: 期待位相差からのずれを princarg で主値に折り返す
        dphi = phase - self._prev_phase - self._bin_phase_step
        dphi = (dphi + np.pi) % _TWO_PI - np.pi
        true_freq = self._bin_phase_step + dphi
        self._prev_phase = phase.copy()

        # --- ピッチシフト: bin k → bin round(k * alpha) ---
        n_bins = len(mag)
        k = np.arange(n_bins)
        dst = np.clip(np.round(k * alpha).astype(int), 0, n_bins - 1)

        s_mag = np.zeros(n_bins)
        s_freq = np.zeros(n_bins)
        np.add.at(s_mag, dst, mag)
        # 各 dst bin には最も強いソース bin の周波数を使う
        order = np.argsort(mag)
        s_freq[dst[order]] = true_freq[order] * alpha

        # --- 合成 ---
        self._synth_phase += s_freq
        Y = s_mag * np.exp(1j * self._synth_phase)
        synth = np.real(np.fft.irfft(Y, n=self.FRAME)) * self._win

        # --- OLA: 合成フレームを出力バッファに積算 ---
        self._out_buf[: self.FRAME] += synth
        out = self._out_buf[:n].copy() / self._ola_norm
        self._out_buf[:-n] = self._out_buf[n:]
        self._out_buf[-n:] = 0.0

        return out.astype(np.float32)
