"""
通知模块 —— 系统托盘气泡通知

负责在 OCR 完成后通过系统托盘显示简短的反馈通知。
运行模式：
- 有 Qt 环境时：使用 QSystemTrayIcon.showMessage
- 无 Qt 环境时：回退到终端打印（CLI 模式）
"""

from typing import Optional
from enum import Enum, auto


class NotifyLevel(Enum):
    """通知级别。"""
    SUCCESS = auto()   # 识别成功
    WARNING = auto()   # 空结果
    ERROR = auto()     # 识别出错


class Notifier:
    """系统托盘通知管理器。

    根据运行环境自动选择通知方式：
    - Qt 可用 → 托盘气泡
    - CLI 模式 → 终端输出
    """

    def __init__(self):
        self._tray_icon: Optional[object] = None  # QSystemTrayIcon
        self._duration_ms = 3000

    # ─── 公共接口 ───────────────────────────────────────────

    def attach_tray(self, tray_icon: object, duration_ms: int = 3000) -> None:
        """绑定系统托盘图标。

        Args:
            tray_icon: QSystemTrayIcon 实例。
            duration_ms: 气泡显示时长（毫秒）。
        """
        self._tray_icon = tray_icon
        self._duration_ms = duration_ms

    def notify(self, title: str, message: str, level: NotifyLevel) -> None:
        """发送通知。

        Args:
            title: 通知标题。
            message: 通知正文。
            level: 通知级别（影响图标和终端颜色）。
        """
        # 尝试 Qt 托盘通知
        if self._tray_icon is not None:
            self._notify_via_tray(title, message, level)
        else:
            self._notify_via_terminal(title, message, level)

    # ─── 便捷方法 ───────────────────────────────────────────

    def notify_ready(self) -> None:
        """通知：内容已就绪。"""
        self.notify("FormulaSniper", "内容已就绪", NotifyLevel.SUCCESS)

    def notify_empty(self) -> None:
        """通知：未识别到内容。"""
        self.notify("FormulaSniper", "未识别到内容", NotifyLevel.WARNING)

    def notify_error(self, detail: str = "") -> None:
        """通知：识别出错。"""
        msg = f"识别出错{': ' + detail if detail else ''}"
        self.notify("FormulaSniper", msg, NotifyLevel.ERROR)

    # ─── 内部实现 ───────────────────────────────────────────

    def _notify_via_tray(
        self, title: str, message: str, level: NotifyLevel
    ) -> None:
        """通过系统托盘气泡通知。"""
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            icon_map = {
                NotifyLevel.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
                NotifyLevel.WARNING: QSystemTrayIcon.MessageIcon.Warning,
                NotifyLevel.ERROR: QSystemTrayIcon.MessageIcon.Critical,
            }
            icon = icon_map.get(level, QSystemTrayIcon.MessageIcon.Information)
            self._tray_icon.showMessage(title, message, icon, self._duration_ms)
        except Exception as e:
            print(f"[Notifier] 托盘通知失败: {e}")
            self._notify_via_terminal(title, message, level)

    def _notify_via_terminal(
        self, title: str, message: str, level: NotifyLevel
    ) -> None:
        """终端降级通知。"""
        prefix_map = {
            NotifyLevel.SUCCESS: "✅",
            NotifyLevel.WARNING: "⚠️",
            NotifyLevel.ERROR: "❌",
        }
        prefix = prefix_map.get(level, "📢")
        print(f"{prefix} [{title}] {message}")


# ─── 全局单例 ──────────────────────────────────────────────

_notifier_instance: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """获取 Notifier 全局单例。"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = Notifier()
    return _notifier_instance
