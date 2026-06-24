"""
区域截图选择器 —— 全屏透明窗口 + 半透明遮罩 + 选区挖空

无背景截图，无 DPI 缩放画面闪烁：
- 窗口完全透明（WA_TranslucentBackground），直接看到真实桌面
- 涂一层半透明暗色遮罩，选区"挖空"透过看到原始画面
- 坐标：QCursor.pos()（逻辑）× devicePixelRatio → 物理像素
"""

from typing import Optional, Callable
from PIL import Image

from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QMouseEvent, QKeyEvent, QPaintEvent,
    QPainterPath, QCursor,
)
from PySide6.QtWidgets import QApplication, QWidget


class RegionSelectorWidget(QWidget):
    """全屏透明选区窗口——遮罩挖空式。"""

    selection_done = Signal(int, int, int, int)  # 物理像素: x, y, w, h

    def __init__(self):
        super().__init__()
        self._start: Optional[QPoint] = None
        self._end: Optional[QPoint] = None
        self._start_global: Optional[QPoint] = None
        self._end_global: Optional[QPoint] = None
        self._dragging = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # 关键：完全透明背景，遮罩层挖空直接看到真实桌面
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        self._dpr = screen.devicePixelRatio() if screen else 1.0

    # ─── 事件 ───────────────────────────────────────────────

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._start = e.position().toPoint()
            self._end = self._start
            self._start_global = QCursor.pos()
            self._end_global = self._start_global
            self._dragging = True
            self.update()
        elif e.button() == Qt.MouseButton.RightButton:
            self._cancel()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._dragging:
            self._end = e.position().toPoint()
            self._end_global = QCursor.pos()
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._end = e.position().toPoint()
            self._end_global = QCursor.pos()
            self._finish()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Escape:
            self._cancel()

    # ─── 绘制：遮罩 + 挖空选区 ──────────────────────────────

    def paintEvent(self, _: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 遮罩路径：全屏 - 选区 = 挖空效果
        mask = QPainterPath()
        mask.addRect(self.rect())

        if self._start and self._end:
            r = self._normalized_rect()
            if r.width() > 0 and r.height() > 0:
                hole = QPainterPath()
                hole.addRect(r)
                mask = mask.subtracted(hole)

        p.fillPath(mask, QColor(0, 0, 0, 120))

        # 选区边框 + 尺寸提示
        if self._start and self._end:
            r = self._normalized_rect()
            if r.width() > 0 and r.height() > 0:
                p.setPen(QPen(QColor("#4A9EFF"), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(r)
                self._draw_size(p, r)
        p.end()

    def _draw_size(self, p: QPainter, r: QRect):
        text = f"{r.width()} x {r.height()}"
        f = QFont("Consolas", 11)
        f.setBold(True)
        p.setFont(f)
        tr = p.boundingRect(QRect(), Qt.AlignmentFlag.AlignCenter, text)
        tr.moveBottomRight(r.bottomRight() - QPoint(8, 8))
        p.fillRect(tr.adjusted(-6, -2, 6, 2), QColor(0, 0, 0, 160))
        p.setPen(QColor(255, 255, 255))
        p.drawText(tr, Qt.AlignmentFlag.AlignCenter, text)

    # ─── 选区完成 ───────────────────────────────────────────

    def _normalized_rect(self) -> QRect:
        if not self._start or not self._end:
            return QRect()
        return QRect(
            min(self._start.x(), self._end.x()),
            min(self._start.y(), self._end.y()),
            abs(self._end.x() - self._start.x()),
            abs(self._end.y() - self._start.y()),
        )

    def _finish(self):
        if not self._start_global or not self._end_global:
            self._cancel()
            return

        x1, y1 = self._start_global.x(), self._start_global.y()
        x2, y2 = self._end_global.x(), self._end_global.y()
        dpr = self._dpr

        # 先乘后减，避免取整误差
        px1 = int(min(x1, x2) * dpr)
        py1 = int(min(y1, y2) * dpr)
        px2 = int(max(x1, x2) * dpr)
        py2 = int(max(y1, y2) * dpr)
        pw = px2 - px1
        ph = py2 - py1

        if pw < 5 or ph < 5:
            self._cancel()
            return

        print(f"[RegionSelector] 选区: 逻辑({min(x1,x2)},{min(y1,y2)}) {abs(x2-x1)}x{abs(y2-y1)}"
              f" xDPR{dpr:.1f} → 物理({px1},{py1}) {pw}x{ph}")

        # 先隐藏窗口（去掉遮罩和标签），再截图
        self.hide()
        QApplication.processEvents()
        self.selection_done.emit(px1, py1, pw, ph)
        self.close()

    def _cancel(self):
        print("[RegionSelector] 选区取消")
        self.close()


# ─── 静态入口 ──────────────────────────────────────────────


class RegionSelector:
    """区域截图选择器的静态入口。"""

    _active_widget = None

    @staticmethod
    def select(on_selected: Callable[[Optional[Image.Image]], None]):
        app = QApplication.instance()
        if app is None:
            print("[RegionSelector] 无 Qt Application")
            on_selected(None)
            return

        widget = RegionSelectorWidget()
        RegionSelector._active_widget = widget

        def on_done(x: int, y: int, w: int, h: int):
            from src.sniper.capture import capture_region
            try:
                img = capture_region(x, y, w, h)
                print(f"[RegionSelector] 截图完成: {img.width}x{img.height}")
                on_selected(img)
            except Exception as e:
                print(f"[RegionSelector] 截图异常: {e}")
                on_selected(None)
            RegionSelector._active_widget = None

        widget.selection_done.connect(on_done)
        widget.destroyed.connect(
            lambda: on_selected(None) if RegionSelector._active_widget else None
        )

        widget.showFullScreen()
        widget.activateWindow()
        widget.raise_()
        print(f"[RegionSelector] 选区窗口已显示 (DPR={widget._dpr:.1f})")
