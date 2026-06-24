"""
系统托盘模块 —— 托盘图标、右键菜单、气泡通知

提供系统托盘常驻能力，包括：
- 托盘图标显示
- 右键菜单（状态信息 / 设置 / 退出）
- 气泡通知绑定
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QWidget,
)


def _create_default_icon(size: int = 64) -> QIcon:
    """生成默认托盘图标（程序化绘制，无需外部图片文件）。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 圆形背景
    painter.setBrush(QColor("#4A9EFF"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 文字
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", size // 2, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")

    painter.end()
    return QIcon(pixmap)


class SystemTray:
    """系统托盘管理器。

    封装 QSystemTrayIcon 的创建、菜单绑定和通知。
    """

    def __init__(self, icon_path: Optional[str] = None):
        self._tray = QSystemTrayIcon()

        # 图标
        if icon_path:
            self._tray.setIcon(QIcon(icon_path))
        else:
            self._tray.setIcon(_create_default_icon())

        self._tray.setToolTip("FormulaSniper — 截图 OCR 就绪")
        self._tray.setVisible(True)

        # 右键菜单
        self._menu = QMenu()
        self._build_menu()

        self._tray.setContextMenu(self._menu)

        # 信号
        self._tray.activated.connect(self._on_activated)

    # ─── 公共接口 ───────────────────────────────────────────

    @property
    def qt_tray(self) -> QSystemTrayIcon:
        """暴露原生 QSystemTrayIcon 供 Notifier 绑定。"""
        return self._tray

    def show_notification(self, title: str, message: str, duration_ms: int = 3000):
        """直接显示托盘气泡通知。"""
        self._tray.showMessage(
            title, message,
            QSystemTrayIcon.MessageIcon.Information,
            duration_ms,
        )

    def set_quit_callback(self, callback: callable) -> None:
        """设置退出回调。"""
        self._quit_callback = callback

    # ─── 菜单构建 ───────────────────────────────────────────

    def _build_menu(self) -> None:
        """构建右键菜单。"""
        self._menu.clear()

        # 状态项
        status_action = QAction("⚡ FormulaSniper 运行中")
        status_action.setEnabled(False)
        self._menu.addAction(status_action)

        self._menu.addSeparator()

        # 手动触发
        trigger_action = QAction("📷 立即截图 (Ctrl+Shift+M)")
        trigger_action.triggered.connect(self._on_trigger)
        self._menu.addAction(trigger_action)

        self._menu.addSeparator()

        # 退出
        quit_action = QAction("❌ 退出")
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

    # ─── 事件处理 ───────────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盘图标交互事件。"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_trigger()

    def _on_trigger(self) -> None:
        """手动触发截图。"""
        from src.sniper.capture import ScreenshotCapture
        # 通过快捷键模拟触发（简化实现）
        print("[SystemTray] 手动触发截图")

    def _on_quit(self) -> None:
        """退出应用。"""
        print("[SystemTray] 用户请求退出")
        if hasattr(self, "_quit_callback"):
            self._quit_callback()
        QApplication.instance().quit()

    def _quit_callback(self) -> None:
        """默认退出回调（空）。"""
        pass
