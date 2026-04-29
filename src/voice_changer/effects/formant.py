import numpy as np

from .base import BaseEffect


def _calc_a_weights(n_bins: int, sample_rate: int, frame: int) -> np.ndarray:
    """各 bin の A特性重み（1kHz 基準で正規化）を計算する。

    A特性は人間の聴覚感度の周波数特性を表す。これで重み付けすることで
    ratio 変化による知覚音量のズレを補正できる。
    """
    freqs = np.arange(n_bins) * sample_rate / frame
    freqs[0] = 1e-3  # DC の 0 除算を防ぐ
    f2 = freqs**2
    num = (12194.0**2) * freqs**4
    den = (
        (f2 + 20.6**2)
        * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2))
        * (f2 + 12194.0**2)
    )
    weights = num / den
    # 1kHz の値で正規化（1kHz = 0dB 基準）
    f1k2 = 1000.0**2
    ref = (12194.0**2 * 1000.0**4) / (
        (f1k2 + 20.6**2)
        * np.sqrt((f1k2 + 107.7**2) * (f1k2 + 737.9**2))
        * (f1k2 + 12194.0**2)
    )
    return weights / ref


class FormantShifter(BaseEffect):
    """OLA 付き FFT スペクトル補間によるフォルマントシフター。

    ratio > 1.0 で女声方向（フォルマント上昇）、< 1.0 で男声方向（フォルマント下降）。
    A特性（聴覚感度の周波数特性）で重み付けした知覚音量を入出力で揃えることで、
    ratio の大小に関わらず音量を一定に保つ。
    """

    FRAME = 2048
    HOP = 256

    def __init__(self, sample_rate: int, ratio: float = 1.0):
        super().__init__(sample_rate)
        self.ratio = ratio

        self._win = np.hanning(self.FRAME)
        self._in_buf = np.zeros(self.FRAME)
        self._out_buf = np.zeros(self.FRAME + self.HOP)
        self._ola_norm = float(np.sum(self._win**2) / self.HOP)

        n_bins = self.FRAME // 2 + 1
        self._dst_bins = np.arange(n_bins, dtype=np.float64)
        # A特性重みを事前計算（sample_rate と FRAME が決まれば固定）
        self._a_weights = _calc_a_weights(n_bins, sample_rate, self.FRAME)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.ratio == 1.0:
            return audio
        n = len(audio)

        self._in_buf[:-n] = self._in_buf[n:]
        self._in_buf[-n:] = audio.astype(np.float64)

        X = np.fft.rfft(self._in_buf * self._win)

        # スペクトル補間: dst bin i の値を src bin i/ratio から取る
        # ratio > 1 → 低域を高域にマッピング → フォルマント上昇
        src = np.clip(self._dst_bins / self.ratio, 0.0, len(self._dst_bins) - 1)
        warped = (
            np.interp(src, self._dst_bins, X.real)
            + 1j * np.interp(src, self._dst_bins, X.imag)
        )

        # A特性で重み付けした知覚音量を入出力で揃える。
        # これにより ratio の大小に関わらず聞こえる音量が一定になる。
        mag_in = np.abs(X) * self._a_weights
        mag_out = np.abs(warped) * self._a_weights
        l_in = np.dot(mag_in, mag_in)
        l_out = np.dot(mag_out, mag_out)
        if l_in > 1e-30 and l_out > 1e-30:
            warped *= np.sqrt(l_in / l_out)

        synth = np.real(np.fft.irfft(warped, n=self.FRAME)) * self._win

        self._out_buf[: self.FRAME] += synth
        out = self._out_buf[:n].copy() / self._ola_norm
        self._out_buf[:-n] = self._out_buf[n:]
        self._out_buf[-n:] = 0.0

        return out.astype(np.float32)
