import queue
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd

_MONITOR_QUEUE_MAXSIZE = 8  # バッファ上限（超えたブロックは破棄してレイテンシを維持）


class AudioCapture:
    """マイク入力を取得し、コールバックに渡すストリーム管理クラス。"""

    def __init__(
        self,
        callback: Callable[[np.ndarray], np.ndarray],
        input_device: int | str | None,
        output_device: int | str | None,
        sample_rate: int,
        block_size: int,
        channels: int,
        monitor_device: int | str | None = None,
    ):
        self._callback = callback
        self._channels = channels
        self._monitor_active = False
        self._monitor_queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=_MONITOR_QUEUE_MAXSIZE)
        self._monitor_thread: threading.Thread | None = None

        self._stream = sd.Stream(
            samplerate=sample_rate,
            blocksize=block_size,
            dtype="float32",
            channels=channels,
            device=(input_device, output_device),
            callback=self._sd_callback,
            latency="low",
        )

        self._monitor_stream: sd.OutputStream | None = None
        if monitor_device is not None:
            self._monitor_stream = sd.OutputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                dtype="float32",
                channels=channels,
                device=monitor_device,
                latency="low",
            )

    @property
    def has_monitor(self) -> bool:
        return self._monitor_stream is not None

    def set_monitor(self, enabled: bool) -> bool:
        """モニタリングを切り替える。monitor_device 未設定の場合は False を返す。"""
        if not self.has_monitor:
            return False
        self._monitor_active = enabled
        return True

    def _sd_callback(self, indata, outdata, frames, time, status):
        audio = indata[:, 0].copy()
        processed = self._callback(audio)

        if processed.ndim == 1:
            outdata[:, 0] = processed
            if outdata.shape[1] > 1:
                outdata[:, 1] = processed
        else:
            outdata[:] = processed

        # コールバック内ではキューに積むだけ。書き込みはワーカースレッドが行う
        if self._monitor_active:
            try:
                self._monitor_queue.put_nowait(outdata.copy())
            except queue.Full:
                pass  # バッファあふれ時は破棄してレイテンシを優先

    def _monitor_worker(self) -> None:
        """モニタースストリームへの書き込みを専用スレッドで行う。"""
        while True:
            chunk = self._monitor_queue.get()
            if chunk is None:  # 停止シグナル
                break
            try:
                self._monitor_stream.write(chunk)  # type: ignore[union-attr]
            except Exception:
                pass

    def start(self) -> None:
        if self._monitor_stream:
            self._monitor_stream.start()
            self._monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self._monitor_thread.start()
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()
        if self._monitor_stream:
            self._monitor_stream.stop()
        if self._monitor_thread is not None:
            self._monitor_queue.put(None)  # ワーカーを終了させる
            self._monitor_thread.join(timeout=1.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
