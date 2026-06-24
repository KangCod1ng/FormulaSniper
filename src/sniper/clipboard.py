"""
剪贴板管理模块 —— 将 OCR 结果写入系统剪贴板

提供跨平台的剪贴板写入能力，包含空结果拦截逻辑。
"""

from typing import Optional


class ClipboardManager:
    """系统剪贴板管理器。

    封装剪贴板读写操作，提供空结果拦截保护。
    """

    def __init__(self):
        self._last_content: str = ""

    # ─── 公共接口 ───────────────────────────────────────────

    def write(self, text: str) -> bool:
        """将文本写入系统剪贴板。

        Args:
            text: 要写入的文本。

        Returns:
            True 表示写入成功，False 表示被拦截。

        Raises:
            RuntimeError: 剪贴板写入异常。
        """
        # 空结果拦截
        if self._is_blank(text):
            print("[ClipboardManager] 空结果拦截，不覆写剪贴板")
            return False

        try:
            self._do_write(text)
            self._last_content = text
            print(f"[ClipboardManager] 已写入剪贴板 ({len(text)} 字符)")
            return True
        except Exception as e:
            raise RuntimeError(f"剪贴板写入失败: {e}")

    def read(self) -> str:
        """读取剪贴板当前内容。"""
        try:
            return self._do_read()
        except Exception:
            return ""

    # ─── 内部实现 ───────────────────────────────────────────

    @staticmethod
    def _is_blank(text: Optional[str]) -> bool:
        """判断文本是否为空或纯空白。"""
        if text is None:
            return True
        return len(text.strip()) == 0

    @staticmethod
    def _do_write(text: str) -> None:
        """执行剪贴板写入。

        优先使用 pyperclip（跨平台），
        若不可用则回退到 PySide6 QClipboard。
        """
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # 回退到 Qt 剪贴板
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QClipboard
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("Qt Application 未初始化")
            clipboard = app.clipboard()
            if clipboard is None:
                raise RuntimeError("无法获取 QClipboard")
            clipboard.setText(text, QClipboard.Mode.Clipboard)

    @staticmethod
    def _do_read() -> str:
        """读取剪贴板内容。"""
        try:
            import pyperclip
            return pyperclip.paste() or ""
        except ImportError:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                return ""
            clipboard = app.clipboard()
            if clipboard is None:
                return ""
            return clipboard.text() or ""


# ─── 全局单例 ──────────────────────────────────────────────

_clipboard_instance: Optional[ClipboardManager] = None


def get_clipboard() -> ClipboardManager:
    """获取 ClipboardManager 全局单例。"""
    global _clipboard_instance
    if _clipboard_instance is None:
        _clipboard_instance = ClipboardManager()
    return _clipboard_instance
