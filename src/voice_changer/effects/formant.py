import math

import numpy as np
import pyworld as pw

from .base import BaseEffect


class FormantShifter(BaseEffect):
    """WORLD CheapTrick スペクトル包絡推定 + OLA フォルマントシフター。

    ratio > 1.0 で女声方向（フォルマント上昇）、< 1.0 で男声方向（フォルマント下降）。

    WORLD の CheapTrick でピッチ依存のないスムーズな声道包絡（フォルマント情報）を推定し、
    周波数軸方向にワープして FFT スペクトルに適用する。
    従来の生 FFT スペクトル補間と異なり高調波構造をそのまま保つため、
    自然な声質とエネルギー保存が両立できる。
    """

    FRAME = 2048
    HOP = 256
    _WORLD_FRAME_PERIOD_MS = 10.0  # WORLD 分析フレーム間隔（短いほど精度↑・負荷↑）
    _ENV_UPDATE_HOPS = 4            # スペクトル包絡の更新間隔（ホップ数）

    def __init__(self, sample_rate: int, ratio: float = 1.0):
        super().__init__(sample_rate)
        self.ratio = ratio

        self._win = np.hanning(self.FRAME)
        self._in_buf = np.zeros(self.FRAME)
        self._out_buf = np.zeros(self.FRAME + self.HOP)
        self._ola_norm = float(np.sum(self._win**2) / self.HOP)

        # CheapTrick の FFT サイズ: 2^ceil(log2(3*fs/f0_floor + 1))、通常 FRAME と一致
        self._ct_fft_size = int(2 ** math.ceil(math.log2(3 * sample_rate / 71.0 + 1)))
        n_bins = self._ct_fft_size // 2 + 1
        self._dst_bins = np.arange(n_bins, dtype=np.float64)

        # スペクトル包絡キャッシュ（更新コストを分散させるため定期更新）
        self._sp_cache: np.ndarray | None = None
        self._hop_count = 0

    def _update_spectral_envelope(self) -> None:
        """WORLD CheapTrick でスペクトル包絡（パワー）を推定しキャッシュする。"""
        x = self._in_buf.copy()
        f0, t = pw.dio(
            x,
            self.sample_rate,
            f0_floor=71.0,
            f0_ceil=800.0,
            frame_period=self._WORLD_FRAME_PERIOD_MS,
            speed=12,
        )
        f0 = pw.stonemask(x, f0, t, self.sample_rate)
        sp = pw.cheaptrick(x, f0, t, self.sample_rate, fft_size=self._ct_fft_size)
        sp_mean = sp.mean(axis=0)
        if np.all(np.isfinite(sp_mean)) and len(sp_mean) == len(self._dst_bins):
            self._sp_cache = sp_mean

    def _warp_envelope(self, sp: np.ndarray) -> np.ndarray:
        """スペクトル包絡を周波数軸方向に ratio 倍伸縮する。"""
        src = np.clip(self._dst_bins / self.ratio, 0.0, len(sp) - 1)
        return np.interp(src, self._dst_bins, sp)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.ratio == 1.0:
            return audio

        n = len(audio)
        self._in_buf[:-n] = self._in_buf[n:]
        self._in_buf[-n:] = audio.astype(np.float64)

        # スペクトル包絡を一定間隔で更新（毎ホップは重いためキャッシュを活用）
        self._hop_count += 1
        if self._hop_count % self._ENV_UPDATE_HOPS == 0 or self._sp_cache is None:
            try:
                self._update_spectral_envelope()
            except Exception:
                pass

        if self._sp_cache is None:
            return audio

        # FFT
        X = np.fft.rfft(self._in_buf * self._win)
        n_rfft = len(X)

        # CT の bin 数と rfft bin 数が一致しない場合はリサンプル
        if len(self._dst_bins) == n_rfft:
            sp_orig = self._sp_cache
            sp_shifted = self._warp_envelope(self._sp_cache)
        else:
            rfft_bins = np.linspace(0, len(self._dst_bins) - 1, n_rfft)
            sp_orig = np.interp(rfft_bins, self._dst_bins, self._sp_cache)
            sp_shifted = np.interp(rfft_bins, self._dst_bins, self._warp_envelope(self._sp_cache))

        # フォルマント変換: X_shifted[k] = X[k] * sqrt(sp_shifted[k] / sp_orig[k])
        # 包絡比を FFT スペクトルに乗算することで高調波構造を保ちながら声道特性だけを変える
        warped = X * np.sqrt(np.maximum(sp_shifted, 0.0) / np.maximum(sp_orig, 1e-30))

        # IFFT + Hann 窓 + OLA
        synth = np.real(np.fft.irfft(warped, n=self.FRAME)) * self._win
        self._out_buf[: self.FRAME] += synth
        out = self._out_buf[:n].copy() / self._ola_norm
        self._out_buf[:-n] = self._out_buf[n:]
        self._out_buf[-n:] = 0.0

        return out.astype(np.float32)
