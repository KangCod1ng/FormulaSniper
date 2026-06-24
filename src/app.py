"""
FormulaSniper 主应用 —— 组装所有模块，管理应用生命周期

职责：
1. 初始化 Qt Application
2. 加载配置
3. 创建系统托盘
4. 注册全局热键
5. 编排截图 → OCR → 剪贴板 → 通知流水线
"""

import sys
import signal
import threading
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PIL import Image

from src.sniper.settings import get_settings
from src.sniper.capture import ScreenshotCapture
from src.sniper.ocr_engine import OCREngine
from src.sniper.clipboard import get_clipboard
from src.sniper.notifier import get_notifier
from src.ui.tray import SystemTray


class FormulaSniperApp:
    """FormulaSniper 应用主控制器。

    管理整个应用的生命周期：初始化 → 运行 → 清理。
    """

    def __init__(self):
        self._app: Optional[QApplication] = None
        self._tray: Optional[SystemTray] = None
        self._capture: Optional[ScreenshotCapture] = None
        self._ocr_engine: Optional[OCREngine] = None

    # ─── 初始化 ─────────────────────────────────────────────

    def initialize(self) -> None:
        """初始化所有子系统。"""
        print("=" * 50)
        print("  FormulaSniper — 学习秘书截图 OCR 工具")
        print("=" * 50)

        # 1. 配置
        settings = get_settings()
        print(f"[App] 热键: {settings.hotkey_string}")
        print(f"[App] OCR 设备: {settings.ocr_device}")

        # 2. Qt Application
        self._app = QApplication.instance()
        if self._app is None:
            self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        # 3. 系统托盘
        self._tray = SystemTray()
        self._tray.set_quit_callback(self.shutdown)

        # 4. 通知模块绑定托盘
        notifier = get_notifier()
        notifier.attach_tray(self._tray.qt_tray)

        # 5. OCR 引擎（延迟加载模型）
        self._ocr_engine = OCREngine(device=settings.ocr_device)
        self._ocr_engine.warm_up()

        # 6. 截图捕获（注册全局热键）
        # 使用 Qt 信号/槽的跨线程 QueuedConnection：
        # Hook 线程 emit → Qt 自动排队 → 主线程 slot，全程线程安全
        self._capture = ScreenshotCapture(hotkey=settings.hotkey_string)
        self._capture.captured.connect(self._on_screenshot_captured)
        self._capture.start()

        print("[App] 初始化完成，等待截图...")

    # ─── 核心流水线 ─────────────────────────────────────────

    def _on_screenshot_captured(self, image: Image.Image) -> None:
        """截图完成回调 → OCR → 剪贴板 → 通知（主线程安全）。"""
        try:
            print(f"[App] 开始 OCR ({image.width}x{image.height})...")

            # 1. OCR 识别
            result = self._ocr_engine.recognize(image)

            # 2. 空结果拦截 + 写剪贴板
            clipboard = get_clipboard()
            notifier = get_notifier()

            if not result or not result.strip():
                notifier.notify_empty()
                return

            clipboard.write(result)
            notifier.notify_ready()

        except Exception as e:
            print(f"[App] 识别流程异常: {e}")
            get_notifier().notify_error(str(e))

    # ─── 运行 ───────────────────────────────────────────────

    def run(self) -> int:
        """启动 Qt 事件循环。"""
        if self._app is None:
            print("[App] 错误：未初始化")
            return 1

        # 注册优雅退出信号（Ctrl+C）
        signal.signal(signal.SIGINT, lambda *a: self.shutdown())

        return self._app.exec()

    # ─── 清理 ───────────────────────────────────────────────

    def shutdown(self) -> None:
        """优雅关闭应用，释放所有资源。"""
        print("[App] 正在关闭...")

        if self._capture:
            self._capture.stop()

        if self._tray and self._tray.qt_tray:
            self._tray.qt_tray.hide()

        if self._app:
            self._app.quit()

        print("[App] 已关闭")


def main():
    """程序入口。"""
    app = FormulaSniperApp()
    app.initialize()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
