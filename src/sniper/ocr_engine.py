"""
Pix2Text OCR 引擎封装 —— 版面分析 + 文字识别 + 公式识别

基于 Pix2Text (P2T) 的统一流水线：
1. 版面分析：将输入图像分割为文字区域与公式区域
2. 文字区域 → 通用 OCR 模型 → 纯文本
3. 公式区域 → 数学识别模型 → LaTeX 字符串
4. 按版面阅读顺序拼接为 Markdown + LaTeX 混合格式
"""

import threading
from typing import Optional
from PIL import Image


class OCREngine:
    """Pix2Text 识别引擎封装。

    负责延迟加载模型（首次使用时）、执行识别流水线、
    合并结果并处理空结果拦截。
    """

    def __init__(self, device: str = "cpu"):
        self._device = device
        self._p2t = None  # 延迟加载
        self._lock = threading.Lock()
        self._processing = False

    # ─── 并发控制 ───────────────────────────────────────────

    @property
    def is_processing(self) -> bool:
        return self._processing

    # ─── 公共接口 ───────────────────────────────────────────
    def warm_up(self) -> None:
        """启动时预加载所有模型，避免首次截图长时间等待。"""
        print("[OCREngine] 正在预加载模型...")
        try:
            dummy = Image.new("RGB", (1, 1))
            self._do_recognize(dummy)
        except Exception:
            self._get_engine()
        print("[OCREngine] 模型就绪（本地缓存）")
    def recognize(self, image: Image.Image) -> str:
        """执行完整的 OCR 流水线。

        Args:
            image: PIL RGB Image，截图区域。

        Returns:
            Markdown + LaTeX 混合格式字符串。
            若结果为空，返回空字符串。

        Raises:
            RuntimeError: 识别过程出错。
        """
        if self._processing:
            print("[OCREngine] 上一次识别仍在进行中，丢弃本次请求")
            return ""

        self._processing = True
        try:
            return self._do_recognize(image)
        finally:
            self._processing = False

    # ─── 内部流水线 ─────────────────────────────────────────

    def _do_recognize(self, image: Image.Image) -> str:
        """实际执行识别流水线。"""
        engine = self._get_engine()
        if engine is None:
            raise RuntimeError("Pix2Text 模型未加载")

        # P2T 原生流水线：file_type='text_formula' 自动版面分析+文字OCR+公式识别
        # 首次调用会自动下载模型（~1-2GB），请耐心等待
        result = engine.recognize(
            image,
            file_type="text_formula",
        )

        if isinstance(result, str):
            return self._sanitize_result(result)

        # 结构化对象（Document/Page），提取 Markdown
        if hasattr(result, "to_markdown"):
            markdown = result.to_markdown()
            return self._sanitize_result(str(markdown))

        return self._sanitize_result(str(result))

    def _sanitize_result(self, text: str) -> str:
        """清洗识别结果：去噪、规范化空白。"""
        import re
        # 去除首尾空白
        text = text.strip()
        # 合并连续空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 修正常见 OCR 错误（可扩展）
        return text

    def _get_engine(self):
        """延迟加载 Pix2Text 引擎（首次使用时加载模型）。"""
        if self._p2t is not None:
            return self._p2t

        with self._lock:
            if self._p2t is not None:  # 双重检查
                return self._p2t

            print(f"[OCREngine] 正在加载 Pix2Text 模型 (device={self._device})...")
            try:
                from pix2text import Pix2Text
                self._p2t = Pix2Text(device=self._device)
            except ImportError:
                raise RuntimeError(
                    "Pix2Text 未安装。请运行: pip install pix2text"
                )
            except Exception as e:
                raise RuntimeError(f"Pix2Text 模型加载失败: {e}")

        return self._p2t

    # ─── 备选方案：分离式流水线 ─────────────────────────────

    def recognize_separate(self, image: Image.Image) -> str:
        """分离式识别（备选）：先版面分析，再分别 OCR。

        适用于需要更细粒度控制或调试的场景。
        """
        if self._processing:
            return ""

        self._processing = True
        try:
            engine = self._get_engine()
            if engine is None:
                raise RuntimeError("Pix2Text 模型未加载")

            # 版面分析
            layout_result = engine.recognize(image, return_text=False)
            if hasattr(layout_result, "to_markdown"):
                return self._sanitize_result(str(layout_result.to_markdown()))
            return self._sanitize_result(str(layout_result))

        finally:
            self._processing = False


# ─── 工具函数 ──────────────────────────────────────────────


def is_result_empty(text: Optional[str]) -> bool:
    """判断识别结果是否为空或纯空白。"""
    if text is None:
        return True
    return len(text.strip()) == 0
