"""目标群选择器 - 选择自拍发送目标"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import time
from typing import Optional, List
from src.plugin_system.apis import chat_api
from src.common.logger import get_logger

logger = get_logger("selfie_plugin.target")


class TargetSelector:
    """选择发送目标群"""

    def __init__(self, config: dict):
        target_cfg = config.get("target", {})
        self._mode = target_cfg.get("selection_mode", "most_active")
        self._window_minutes = target_cfg.get("activity_window_minutes", 30)
        self._configured_groups = target_cfg.get("configured_groups", [])

        # 权限配置
        permission_cfg = config.get("permission", {})
        self._allow_all = permission_cfg.get("allow_all", False)
        self._allowed_groups = permission_cfg.get("allowed_groups", [])

    def _is_group_allowed(self, stream_id: str) -> bool:
        """检查群是否在白名单中"""
        if self._allow_all:
            return True
        if not self._allowed_groups:
            return False
        return stream_id in self._allowed_groups

    def get_target_stream_id(self) -> Optional[str]:
        """
        获取目标stream_id

        Returns:
            stream_id 或 None（如果没有合适的目标）
        """
        if self._mode == "configured":
            return self._get_configured_target()
        return self._get_most_active_target()

    def _get_most_active_target(self) -> Optional[str]:
        """获取最活跃的群（只从白名单中选择）"""
        try:
            streams = chat_api.get_group_streams()
            if not streams:
                logger.debug("没有可用的群聊")
                return None

            current_time = time.time()
            window_seconds = self._window_minutes * 60

            best_stream = None
            best_time = 0

            for stream in streams:
                stream_id = getattr(stream, 'stream_id', None)
                if not stream_id:
                    continue

                # 权限检查
                if not self._is_group_allowed(stream_id):
                    continue

                # 获取最后活跃时间
                last_active = getattr(stream, 'last_active_time', 0)
                if last_active is None:
                    continue

                # 检查是否在时间窗口内
                if current_time - last_active <= window_seconds:
                    if last_active > best_time:
                        best_time = last_active
                        best_stream = stream

            if best_stream:
                stream_id = getattr(best_stream, 'stream_id', None)
                if stream_id:
                    logger.debug(f"选择最活跃群: {stream_id}")
                    return stream_id

            logger.debug("没有在时间窗口内活跃的白名单群")
            return None

        except Exception as e:
            logger.error(f"获取最活跃群失败: {e}")
            return None

    def _get_configured_target(self) -> Optional[str]:
        """从配置列表获取目标（需要同时在白名单中）"""
        if not self._configured_groups:
            logger.debug("未配置指定群列表")
            return None

        try:
            streams = chat_api.get_group_streams()
            stream_ids = {getattr(s, 'stream_id', None) for s in streams if s}

            for group_id in self._configured_groups:
                if group_id in stream_ids:
                    # 权限检查
                    if not self._is_group_allowed(group_id):
                        logger.debug(f"配置群 {group_id} 不在白名单中，跳过")
                        continue
                    logger.debug(f"选择配置群: {group_id}")
                    return group_id

            logger.debug("配置的群都不在可用列表或白名单中")
            return None

        except Exception as e:
            logger.error(f"获取配置目标群失败: {e}")
            return None

    def get_all_available_targets(self) -> List[str]:
        """获取所有可用的目标群列表（只返回白名单中的）"""
        try:
            streams = chat_api.get_group_streams()
            return [
                getattr(s, 'stream_id', None)
                for s in streams
                if s and getattr(s, 'stream_id', None) and self._is_group_allowed(getattr(s, 'stream_id', None))
            ]
        except Exception as e:
            logger.error(f"获取可用目标列表失败: {e}")
            return []
