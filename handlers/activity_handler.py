"""活动变化触发自拍处理器"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import asyncio
import random
from typing import Optional, Tuple
from src.plugin_system import BaseEventHandler, EventType
from src.plugin_system.apis import send_api
from src.common.logger import get_logger

from ..core import SelfieGenerator, SelfiePromptBuilder, TargetSelector

logger = get_logger("selfie_plugin.handler")


class SelfieActivityHandler(BaseEventHandler):
    """
    活动变化触发自拍

    监控当前活动变化，在活动切换时有小概率自动发送自拍。
    依赖自主规划插件来获取当前活动。
    """

    event_type = EventType.ON_START
    handler_name = "selfie_activity_handler"
    handler_description = "监控活动变化，小概率自动发送自拍"
    weight = 5
    intercept_message = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._task: Optional[asyncio.Task] = None
        self._is_running = False
        self._last_activity: Optional[str] = None

    async def execute(self, message=None) -> Tuple[bool, bool, Optional[str], None, None]:
        """启动时开始监控"""
        # 检查插件是否启用
        if not self.get_config("plugin.enabled", True):
            return True, True, None, None, None

        if not self.get_config("selfie.trigger.enable_activity_trigger", True):
            logger.debug("活动触发已禁用")
            return True, True, None, None, None

        # 启动监控循环
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("自拍活动监控已启动")

        return True, True, None, None, None

    async def _monitor_loop(self):
        """监控循环 - 检测活动变化"""
        interval = self.get_config("selfie.trigger.check_interval_seconds", 60)
        probability = self.get_config("selfie.trigger.activity_trigger_probability", 0.1)

        logger.info(f"活动监控配置: 间隔={interval}秒, 触发概率={probability}")

        while self._is_running:
            try:
                # 获取当前活动
                activity = self._get_current_activity()

                if activity and activity != self._last_activity:
                    old = self._last_activity
                    self._last_activity = activity

                    # 首次检测不触发（避免启动时触发）
                    if old is not None:
                        # 按概率触发
                        if random.random() < probability:
                            logger.info(f"活动变化触发自拍: {old} -> {activity}")
                            await self._take_selfie(activity)
                        else:
                            logger.debug(f"活动变化但未触发: {old} -> {activity}")

            except asyncio.CancelledError:
                logger.info("活动监控被取消")
                break
            except Exception as e:
                logger.error(f"活动监控出错: {e}")

            await asyncio.sleep(interval)

    def _get_current_activity(self) -> Optional[str]:
        """
        获取当前活动（从自主规划插件）

        Returns:
            当前活动名称，或None（如果无法获取）
        """
        try:
            # 尝试从自主规划插件获取当前活动
            from src.plugin_system import get_plugin_manager
            pm = get_plugin_manager()

            # 查找自主规划插件
            planning_plugin = pm.get_plugin("autonomous_planning_plugin")
            if not planning_plugin:
                return None

            # 尝试获取当前活动
            # 注意：这里需要根据自主规划插件的实际API来调整
            if hasattr(planning_plugin, 'get_current_activity'):
                return planning_plugin.get_current_activity()

            # 备选方案：从schedule_manager获取
            if hasattr(planning_plugin, 'schedule_manager'):
                schedule_mgr = planning_plugin.schedule_manager
                if hasattr(schedule_mgr, 'get_current_activity'):
                    return schedule_mgr.get_current_activity()

            return None

        except ImportError:
            logger.debug("无法导入plugin_system")
            return None
        except Exception as e:
            logger.debug(f"获取当前活动失败: {e}")
            return None

    async def _take_selfie(self, activity: str):
        """拍摄并发送照片"""
        try:
            selfie_config = self.get_config("selfie", {})

            generator = SelfieGenerator(selfie_config)
            prompt_builder = SelfiePromptBuilder(selfie_config)
            target_selector = TargetSelector(selfie_config)

            # 检查是否可以拍照
            can_take, reason = generator.can_take_selfie()
            if not can_take:
                logger.debug(f"跳过拍照: {reason}")
                return

            # 选择风格和视角
            style = generator.select_style()
            perspective = generator.select_perspective()
            prompt = prompt_builder.build_prompt(activity, style, perspective)

            # 生成图片
            image_base64, error = await generator.generate_selfie(prompt)
            if error:
                logger.error(f"生成照片失败: {error}")
                return

            # 获取目标群并发送
            stream_id = target_selector.get_target_stream_id()
            if stream_id:
                success = await send_api.image_to_stream(image_base64, stream_id)
                if success:
                    style_name = "精美" if style.value == "professional" else "随手拍"
                    perspective_name = "自拍" if perspective.value == "selfie" else "POV"
                    logger.info(f"自动拍照已发送: stream={stream_id}, activity={activity}, {perspective_name}, {style_name}")
                else:
                    logger.error(f"发送照片失败: stream={stream_id}")
            else:
                logger.debug("没有可用的目标群，跳过发送")

        except Exception as e:
            logger.error(f"自动自拍失败: {e}", exc_info=True)

    def stop(self):
        """停止监控"""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("自拍活动监控已停止")
