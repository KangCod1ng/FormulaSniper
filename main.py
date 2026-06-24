"""
FormulaSniper 入口文件

用法：
    python main.py              # 启动 GUI 模式（系统托盘 + 全局热键）
    python main.py --cli        # CLI 模式（手动触发截图 + OCR）
    python main.py --help       # 查看帮助
"""

import sys
import argparse


def run_gui():
    """GUI 模式：系统托盘常驻 + 全局热键截图。"""
    from src.app import main
    main()


def run_cli():
    """CLI 模式：命令行交互式截图。"""
    import os
    print("=" * 50)
    print("  FormulaSniper CLI 模式")
    print("  输入 's' 截图, 'q' 退出")
    print("=" * 50)

    from src.sniper.settings import get_settings
    from src.sniper.capture import ScreenshotCapture
    from src.sniper.ocr_engine import OCREngine
    from src.sniper.clipboard import get_clipboard

    settings = get_settings()
    engine = OCREngine(
        device=settings.ocr_device,
        models_dir=settings.models_dir,
    )
    clipboard = get_clipboard()

    def on_captured(image):
        print(f"识别中 ({image.width}x{image.height})...")
        try:
            result = engine.recognize(image)
            if result.strip():
                clipboard.write(result)
                print(f"✅ 已写入剪贴板:\n{result[:200]}...")
            else:
                print("⚠️ 未识别到内容")
        except Exception as e:
            print(f"❌ 识别出错: {e}")

    # 在 CLI 模式下手动触发一次截图即可
    from src.ui.region_selector import RegionSelector
    RegionSelector.select(on_selected=lambda img: on_captured(img) if img else print("已取消"))

    # CLI 模式下需要 QApplication 驱动 RegionSelector
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.exec()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FormulaSniper — 截图 OCR 工具，识别文字与数学公式为 Markdown+LaTeX"
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="CLI 模式（无托盘，手动触发一次截图）"
    )
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        run_gui()
