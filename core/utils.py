"""工具函数"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import hashlib
from datetime import datetime
from typing import List, Optional, Tuple
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


def get_current_activity_detailed() -> Tuple[Optional[str], Optional[str]]:
    """
    从自主规划插件获取当前活动的详细信息

    Returns:
        (活动名称, 活动描述) 或 (None, None)
    """
    try:
        # 尝试导入规划插件的 GoalManager
        from plugins.xuqian13_autonomous_planning_plugin.planner.goal_manager import get_goal_manager
        from plugins.xuqian13_autonomous_planning_plugin.utils.time_utils import parse_time_window
    except ImportError:
        debug_log("无法导入 autonomous_planning_plugin")
        return None, None

    try:
        goal_manager = get_goal_manager()
        if not goal_manager:
            debug_log("无法获取 goal_manager 实例")
            return None, None

        # 获取今日所有日程
        schedule_goals = goal_manager.get_schedule_goals(chat_id="global")
        if not schedule_goals:
            debug_log("今日没有日程")
            return None, None

        # 获取当前时间（分钟数）
        # 优先使用规划插件的时区感知时间，保证与日程判定一致
        now = goal_manager.tz_manager.get_now() if hasattr(goal_manager, "tz_manager") else datetime.now()
        current_minutes = now.hour * 60 + now.minute

        debug_log(f"当前时间: {now.strftime('%H:%M')} ({current_minutes} 分钟)")
        debug_log(f"今日日程数量: {len(schedule_goals)}")

        # 遍历日程，找到当前时间范围内的活动
        for goal in schedule_goals:
            # 获取 time_window
            time_window = None
            if goal.parameters and "time_window" in goal.parameters:
                time_window = goal.parameters["time_window"]
            elif goal.conditions and "time_window" in goal.conditions:
                time_window = goal.conditions["time_window"]

            if not time_window or len(time_window) < 2:
                continue

            start_minutes, end_minutes = parse_time_window(time_window)
            if start_minutes is None or end_minutes is None:
                continue

            # 处理跨夜时间窗口（end_minutes > 1440）
            # 例如 23:00-01:00 会被转换为 [1380, 1500]
            if end_minutes > 1440:
                is_in_window = (start_minutes <= current_minutes < 1440) or (
                    0 <= current_minutes < (end_minutes - 1440)
                )
            else:
                is_in_window = start_minutes <= current_minutes < end_minutes

            if is_in_window:
                activity_name = goal.name
                # 优先从 parameters 获取描述，其次从 goal.description
                activity_desc = None
                if goal.parameters and "description" in goal.parameters:
                    activity_desc = goal.parameters["description"]
                elif hasattr(goal, 'description') and goal.description:
                    activity_desc = goal.description

                start_time = f"{start_minutes // 60:02d}:{start_minutes % 60:02d}"
                end_minutes_display = end_minutes % 1440 if end_minutes > 1440 else end_minutes
                end_time = f"{end_minutes_display // 60:02d}:{end_minutes_display % 60:02d}"
                debug_log(f"当前活动: {activity_name} ({start_time}-{end_time})")
                debug_log(f"活动描述: {activity_desc}")

                return activity_name, activity_desc

        debug_log("当前时间没有匹配的活动")
        return None, None

    except Exception as e:
        logger.debug(f"获取当前活动详情失败: {e}")
        return None, None


def get_current_activity() -> Optional[str]:
    """
    获取当前活动名称（兼容旧接口）

    Returns:
        活动名称或 None
    """
    name, desc = get_current_activity_detailed()
    # 如果有描述，返回 "活动名（描述）" 格式
    if name and desc:
        return f"{name}（{desc}）"
    return name
