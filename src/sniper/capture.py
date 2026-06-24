"""
截图捕获模块 —— 全局快捷键触发 → 区域选择 → 返回 PIL Image

线程模型（关键！）：
- keyboard 库的 hotkey 回调在 Hook 线程中执行
- Qt GUI 必须在主线程操作
- 解决方案：使用 QObject 信号/槽的跨线程自动队列机制
  Hook 线程 emit 信号 → Qt 自动 QueuedConnection → 主线程 slot
"""

import threading
from typing import Optional, Callable
from PIL import Image
import keyboard

from PySide6.QtCore import QObject, Signal, Qt


class _HotkeyBridge(QObject):
    """跨线程信号桥：Hook 线程 emit，主线程接收。"""
    triggered = Signal()  # 热键被按下


class ScreenshotCapture(QObject):
    """全局快捷键截图管理器（Qt 信号/槽版本）。

    通过 keyboard 库注册全局热键，利用 Qt 的跨线程信号队列
    自动将 Hook 线程的事件安全转发到主线程。
    """

    # 截图完成信号（主线程安全）
    captured = Signal(object)  # PIL Image

    def __init__(self, hotkey: str = "ctrl+shift+m"):
        super().__init__()
        self._hotkey = hotkey
        self._bridge = _HotkeyBridge()
        # 跨线程安全：Hook 线程 emit → Qt 自动排队到主线程
        self._bridge.triggered.connect(
            self._start_region_selection, Qt.ConnectionType.QueuedConnection
        )
        self._running = False

    # ─── 公共接口 ───────────────────────────────────────────

    def start(self) -> None:
        """注册全局热键并开始监听。"""
        self._running = True
        keyboard.add_hotkey(self._hotkey, self._on_hotkey_triggered)
        print(f"[ScreenshotCapture] 热键 {self._hotkey} 已注册")

    def stop(self) -> None:
        """停止热键监听。"""
        self._running = False
        try:
            keyboard.remove_hotkey(self._hotkey)
        except Exception:
            pass
        print("[ScreenshotCapture] 热键已注销")

    # ─── 内部：Hook 线程 → 主线程桥接 ──────────────────────

    def _on_hotkey_triggered(self) -> None:
        """热键触发（Hook 线程）。

        唯一操作：emit Qt 信号，Qt 自动通过 QueuedConnection
        将后续处理投递到主线程事件队列。绝不操作 GUI！
        """
        print("[ScreenshotCapture] 热键触发 (Hook 线程)")
        self._bridge.triggered.emit()

    def _start_region_selection(self) -> None:
        """在主线程中启动区域截图窗口（由 QueuedConnection 保证）。"""
        print("[ScreenshotCapture] 启动选区窗口 (主线程)")
        from src.ui.region_selector import RegionSelector
        RegionSelector.select(on_selected=self._on_region_selected)

    def _on_region_selected(self, pil_image: Optional[Image.Image]) -> None:
        """用户完成区域选择后发射 captured 信号。"""
        if pil_image is None:
            print("[ScreenshotCapture] 用户取消了选区")
            return
        self.captured.emit(pil_image)


# ─── 工具函数 ──────────────────────────────────────────────


def capture_fullscreen() -> Image.Image:
    """截取全屏（备用，用于调试或全屏 OCR）。"""
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 主显示器
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """截取指定坐标的屏幕区域。

    Args:
        x, y: 左上角坐标。
        w, h: 宽高。

    Returns:
        PIL RGB Image。
    """
    import mss
    region = {"left": x, "top": y, "width": w, "height": h}
    with mss.mss() as sct:
        screenshot = sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
