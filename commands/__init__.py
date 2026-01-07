"""调试命令 - 强制触发拍照"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import re
from typing import Tuple, Optional
from src.plugin_system import BaseCommand
from src.common.logger import get_logger

from ..core import (
    SelfieGenerator, SelfiePromptBuilder, TargetSelector, SelfieStyle, PhotoPerspective,
    set_debug_mode, debug_log, is_stream_in_list, get_stream_id_info, get_current_activity,
)

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
        """从自主规划插件获取当前活动（使用详细信息）"""
        return get_current_activity()

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        """执行命令"""
        # 检查插件是否启用
        if not self.get_config("plugin.enabled", True):
            return True, None, 2

        try:
            # 初始化调试模式
            debug_mode = self.get_config("plugin.debug_mode", False)
            set_debug_mode(debug_mode)

            # 获取配置
            selfie_config = self.get_config("selfie", {})
            permission_cfg = selfie_config.get("permission", {})
            debug_groups = permission_cfg.get("debug_groups", [])

            # 权限检查：只有调试群可以使用 /selfie 命令
            stream_id = None
            if hasattr(self, 'message') and hasattr(self.message, 'chat_stream'):
                stream_id = getattr(self.message.chat_stream, 'stream_id', None)

            debug_log(f"/selfie 命令 - {get_stream_id_info(stream_id) if stream_id else 'stream_id=None'}")
            debug_log(f"debug_groups 配置: {debug_groups}")

            if not stream_id or not is_stream_in_list(stream_id, debug_groups):
                # 非调试群静默忽略，只输出到 console
                logger.info(f"[调试命令] 群 {stream_id} 不在调试群列表中，已忽略 (配置格式提示: 使用 qq:群号 或直接填 hash)")
                return True, None, 2

            # 解析参数
            args_str = self.matched_groups.get("args", "") or ""
            args = args_str.strip().split() if args_str.strip() else []

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
                if not activity:
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

            # 获取API配置用于调试输出
            api_cfg = selfie_config.get("api", {})
            model = api_cfg.get("model", "unknown")

            # 发送详细调试信息
            perspective_name = "自拍" if perspective == PhotoPerspective.SELFIE else "POV"
            style_name = "精美" if style == SelfieStyle.PROFESSIONAL else "随手拍"

            debug_info = f"""[DEBUG] 自拍调试信息
━━━━━━━━━━━━━━━━━━━━
stream_id: {stream_id}
activity: {activity}
perspective: {perspective.value} ({perspective_name})
style: {style.value} ({style_name})
model: {model}
━━━━━━━━━━━━━━━━━━━━
正在生成..."""

            await self.send_text(debug_info)
            logger.info(f"[调试命令] stream={stream_id}, activity={activity}, perspective={perspective.value}, style={style.value}")

            # 构建prompt并生成
            prompt = prompt_builder.build_prompt(activity, style, perspective)

            # 输出 prompt 到 console
            logger.info(f"[调试命令] Prompt:\n{prompt}")

            # debug 模式下，把完整 prompt 也发送到群里
            if debug_mode:
                prompt_msg = f"""[DEBUG] 完整 Prompt
━━━━━━━━━━━━━━━━━━━━
{prompt}
━━━━━━━━━━━━━━━━━━━━"""
                await self.send_text(prompt_msg)

            image_base64, error = await generator.generate_selfie(prompt)

            if error:
                error_msg = f"""[DEBUG] 生成失败
━━━━━━━━━━━━━━━━━━━━
error: {error}
━━━━━━━━━━━━━━━━━━━━"""
                await self.send_text(error_msg)
                logger.error(f"[调试命令] 生成失败: {error}")
                return True, None, 2

            # 发送图片
            success = await self.send_image(image_base64)

            # 发送结果
            result_msg = f"""[DEBUG] 生成完成
━━━━━━━━━━━━━━━━━━━━
success: {success}
image_size: {len(image_base64) if image_base64 else 0} bytes (base64)
━━━━━━━━━━━━━━━━━━━━"""
            await self.send_text(result_msg)

            if success:
                logger.info(f"[调试命令] 照片发送成功")
            else:
                logger.error(f"[调试命令] 照片发送失败")

            return True, None, 2

        except Exception as e:
            logger.error(f"[调试命令] 执行失败: {e}", exc_info=True)
            await self.send_text(f"[DEBUG] Exception: {str(e)}")
            return True, None, 2
