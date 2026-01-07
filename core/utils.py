"""工具函数"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import hashlib
from typing import List
from src.common.logger import get_logger

logger = get_logger("selfie_plugin.utils")

# 全局调试开关
_debug_mode = False


def set_debug_mode(enabled: bool):
    """设置调试模式"""
    global _debug_mode
    _debug_mode = enabled
    if enabled:
        logger.info("[DEBUG] 自拍插件调试模式已开启")


def is_debug_mode() -> bool:
    """检查是否开启调试模式"""
    return _debug_mode


def debug_log(message: str):
    """调试日志（仅在调试模式下输出）"""
    if _debug_mode:
        logger.info(f"[DEBUG] {message}")


def normalize_stream_id(config_id: str) -> str:
    """
    将配置格式的 ID 转换为 stream_id (MD5 hash)

    支持格式:
    - qq:123456 -> hash
    - qq_123456 -> hash
    - 已经是 hash 格式 -> 原样返回

    Args:
        config_id: 配置文件中的群 ID

    Returns:
        标准化后的 stream_id (MD5 hash)
    """
    # 如果已经是 32 位 hex，认为是 hash 格式
    if len(config_id) == 32 and all(c in '0123456789abcdef' for c in config_id.lower()):
        return config_id.lower()

    # 处理 qq:123456 格式
    if ':' in config_id:
        parts = config_id.split(':', 1)
        platform = parts[0]
        group_id = parts[1]
        key = f"{platform}_{group_id}"
        return hashlib.md5(key.encode()).hexdigest()

    # 处理 qq_123456 格式
    if '_' in config_id:
        key = config_id
        return hashlib.md5(key.encode()).hexdigest()

    # 无法识别的格式，原样返回
    debug_log(f"无法识别的 ID 格式: {config_id}")
    return config_id


def is_stream_in_list(stream_id: str, config_list: List[str]) -> bool:
    """
    检查 stream_id 是否在配置列表中

    Args:
        stream_id: 实际的 stream_id (MD5 hash)
        config_list: 配置文件中的群列表（支持多种格式）

    Returns:
        是否在列表中
    """
    if not config_list:
        return False

    stream_id_lower = stream_id.lower()

    for config_id in config_list:
        normalized = normalize_stream_id(config_id)
        if normalized == stream_id_lower:
            debug_log(f"stream_id 匹配: {stream_id} == {config_id} (normalized: {normalized})")
            return True

    debug_log(f"stream_id 不在列表中: {stream_id}, 列表: {config_list}")
    return False


def get_stream_id_info(stream_id: str) -> str:
    """
    获取 stream_id 的调试信息

    Args:
        stream_id: stream_id (MD5 hash)

    Returns:
        调试信息字符串
    """
    return f"stream_id={stream_id} (这是 platform_groupId 的 MD5 hash，如 qq_123456 -> {hashlib.md5(b'qq_123456').hexdigest()})"
