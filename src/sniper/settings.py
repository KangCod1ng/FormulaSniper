"""
配置管理模块 —— 读取、合并、持久化用户设置

加载顺序：default_settings.json → 用户自定义 settings.json
支持热键重绑定、OCR 参数调整等。
"""

import json
import os
from typing import Any, Dict, Optional


class Settings:
    """配置管理器。

    单例模式，首次初始化时合并默认配置与用户配置。
    """

    # 项目根目录（相对于本文件向上 3 级）
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    _DEFAULT_PATH = os.path.join(_PROJECT_ROOT, "config", "default_settings.json")
    _USER_PATH = os.path.join(_PROJECT_ROOT, "config", "settings.json")

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._load()

    # ─── 数据访问 ───────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """支持点号分隔的嵌套键读取。

        Examples:
            settings.get("ocr.device")  → "cpu"
            settings.get("hotkey.key")  → "m"
        """
        keys = key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        """设置配置值（仅内存，需调用 save 持久化）。"""
        keys = key.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def save(self) -> None:
        """持久化当前配置到用户配置文件。"""
        os.makedirs(os.path.dirname(self._USER_PATH), exist_ok=True)
        with open(self._USER_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        print(f"[Settings] 配置已保存到 {self._USER_PATH}")

    # ─── 便捷属性 ───────────────────────────────────────────

    @property
    def hotkey_string(self) -> str:
        """返回 hotkey 库可识别的快捷键字符串，如 'ctrl+shift+m'。"""
        key = self.get("hotkey.key", "m")
        mods = self.get("hotkey.modifiers", ["ctrl", "shift"])
        return "+".join(mods + [key])

    @property
    def ocr_device(self) -> str:
        return self.get("ocr.device", "cpu")

    @property
    def models_dir(self) -> str:
        return self.get("models.cache_dir", "./models")

    # ─── 内部实现 ───────────────────────────────────────────

    def _load(self) -> None:
        """加载配置：默认 → 用户覆盖。"""
        # 加载默认配置
        try:
            with open(self._DEFAULT_PATH, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[Settings] 默认配置加载失败: {e}，使用空配置")
            self._data = {}

        # 合并用户配置
        try:
            with open(self._USER_PATH, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            self._deep_merge(self._data, user_data)
            print(f"[Settings] 用户配置已加载: {self._USER_PATH}")
        except FileNotFoundError:
            print("[Settings] 用户配置文件不存在，使用默认配置")
        except json.JSONDecodeError as e:
            print(f"[Settings] 用户配置解析失败: {e}")

    @staticmethod
    def _deep_merge(base: Dict, overlay: Dict) -> None:
        """递归合并 overlay 到 base（原地修改）。"""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Settings._deep_merge(base[key], value)
            else:
                base[key] = value


# ─── 全局单例 ──────────────────────────────────────────────

_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取 Settings 全局单例。"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
