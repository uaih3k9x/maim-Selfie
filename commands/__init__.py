"""调试命令 - 强制触发拍照"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import re
from typing import Tuple, Optional
from src.plugin_system import BaseCommand
from src.common.logger import get_logger

from ..core import SelfieGenerator, SelfiePromptBuilder, TargetSelector, SelfieStyle, PhotoPerspective

logger = get_logger("selfie_plugin.command")


class SelfieCommand(BaseCommand):
    """
    自拍调试命令

    用法:
        /selfie                     - 自动获取当前活动，随机风格
        /selfie 吃饭                - 指定活动
        /selfie 吃饭 selfie         - 指定活动和视角
        /selfie 吃饭 pov casual     - 指定活动、视角和质量
    """

    command_name = "selfie_command"
    command_description = "强制触发拍照（调试用）"
    command_pattern = r"^/selfie(?:\s+(?P<args>.*))?$"

    def _get_current_activity(self) -> Optional[str]:
        """尝试从自主规划插件获取当前活动"""
        try:
            from src.plugin_system import get_plugin_manager
            pm = get_plugin_manager()

            planning_plugin = pm.get_plugin("autonomous_planning_plugin")
            if not planning_plugin:
                return None

            # 尝试获取当前活动
            if hasattr(planning_plugin, 'get_current_activity'):
                return planning_plugin.get_current_activity()

            if hasattr(planning_plugin, 'schedule_manager'):
                schedule_mgr = planning_plugin.schedule_manager
                if hasattr(schedule_mgr, 'get_current_activity'):
                    return schedule_mgr.get_current_activity()

            return None
        except Exception as e:
            logger.debug(f"获取当前活动失败: {e}")
            return None

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        """执行命令"""
        # 检查插件是否启用
        if not self.get_config("plugin.enabled", True):
            await self.send_text("自拍插件已禁用")
            return True, None, 2

        try:
            # 解析参数
            args_str = self.matched_groups.get("args", "") or ""
            args = args_str.strip().split() if args_str.strip() else []

            # 获取配置
            selfie_config = self.get_config("selfie", {})

            # 权限检查：检查当前群是否在白名单中
            stream_id = getattr(self, 'stream_id', None) or getattr(self, '_stream_id', None)
            if stream_id:
                permission_cfg = selfie_config.get("permission", {})
                allow_all = permission_cfg.get("allow_all", False)
                allowed_groups = permission_cfg.get("allowed_groups", [])

                if not allow_all:
                    if not allowed_groups:
                        await self.send_text("这个群没有开启自拍权限")
                        return True, None, 2
                    if stream_id not in allowed_groups:
                        await self.send_text("这个群没有开启自拍权限")
                        return True, None, 2

            # 初始化组件
            generator = SelfieGenerator(selfie_config)
            prompt_builder = SelfiePromptBuilder(selfie_config)

            # 解析活动（第一个参数，或自动获取）
            activity = None
            perspective = None
            style = None

            # 检查第一个参数是否是视角/质量关键词
            first_is_keyword = False
            if len(args) > 0:
                first_lower = args[0].lower()
                if first_lower in ("selfie", "自拍", "pov", "第一人称", "professional", "精美", "pro", "casual", "随手拍", "糊"):
                    first_is_keyword = True

            if len(args) > 0 and not first_is_keyword:
                activity = args[0]
                remaining_args = args[1:]
            else:
                # 尝试自动获取当前活动
                activity = self._get_current_activity()
                if activity:
                    logger.info(f"自动获取到当前活动: {activity}")
                else:
                    activity = "休息"
                remaining_args = args

            # 解析视角和质量
            for arg in remaining_args:
                arg_lower = arg.lower()
                if arg_lower in ("selfie", "自拍"):
                    perspective = PhotoPerspective.SELFIE
                elif arg_lower in ("pov", "第一人称"):
                    perspective = PhotoPerspective.POV
                elif arg_lower in ("professional", "精美", "pro"):
                    style = SelfieStyle.PROFESSIONAL
                elif arg_lower in ("casual", "随手拍", "糊"):
                    style = SelfieStyle.CASUAL

            # 未指定则随机
            if perspective is None:
                perspective = generator.select_perspective()
            if style is None:
                style = generator.select_style()

            # 发送提示
            perspective_name = "自拍" if perspective == PhotoPerspective.SELFIE else "POV"
            style_name = "精美" if style == SelfieStyle.PROFESSIONAL else "随手拍"
            await self.send_text(f"正在生成照片...\n活动: {activity}\n视角: {perspective_name}\n质量: {style_name}")

            # 构建prompt并生成
            prompt = prompt_builder.build_prompt(activity, style, perspective)
            logger.info(f"调试命令生成: activity={activity}, perspective={perspective.value}, style={style.value}")

            image_base64, error = await generator.generate_selfie(prompt)

            if error:
                await self.send_text(f"生成失败: {error}")
                return True, None, 2

            # 发送图片
            success = await self.send_image(image_base64)
            if success:
                logger.info("调试命令: 照片发送成功")
                return True, None, 2
            else:
                await self.send_text("发送图片失败")
                return True, None, 2

        except Exception as e:
            logger.error(f"调试命令执行失败: {e}", exc_info=True)
            await self.send_text(f"出错了: {str(e)}")
            return True, None, 2
