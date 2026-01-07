"""自拍工具 - 供LLM调用"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

from typing import Any, Dict
from src.plugin_system import BaseTool, ToolParamType
from src.plugin_system.apis import send_api
from src.common.logger import get_logger

from ..core import (
    SelfieGenerator, SelfiePromptBuilder, TargetSelector, SelfieStyle, PhotoPerspective,
    set_debug_mode, debug_log, is_stream_in_list, get_stream_id_info,
)

logger = get_logger("selfie_plugin.tool")


class TakeSelfiePhotoTool(BaseTool):
    """
    拍照工具 - 供LLM调用

    让麦麦可以拍一张照片发到群里，可以在想分享当前状态、
    群友想看你在干嘛时使用。支持自拍和POV两种视角。
    """

    name = "take_selfie_photo"
    description = "拍一张照片发到群里。可以拍自拍（能看到脸）或者POV视角（第一人称看到的场景）。"
    parameters = [
        ("activity", ToolParamType.STRING, "当前正在做的事情（如：吃饭、学习、散步）", True, None),
        ("reason", ToolParamType.STRING, "拍照原因或想说的话（可选）", False, None),
        ("style", ToolParamType.STRING, "质量: professional(精美) 或 casual(随手拍)，不填则随机", False, ["professional", "casual"]),
        ("perspective", ToolParamType.STRING, "视角: selfie(自拍) 或 pov(第一人称)，不填则随机", False, ["selfie", "pov"]),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行拍照"""
        # 检查插件是否启用
        if not self.get_config("plugin.enabled", True):
            return {"name": self.name, "content": "自拍插件已禁用"}

        if not self.get_config("selfie.trigger.enable_llm_tool", True):
            return {"name": self.name, "content": "LLM工具调用已禁用"}

        try:
            # 初始化调试模式
            debug_mode = self.get_config("plugin.debug_mode", False)
            set_debug_mode(debug_mode)

            # 获取selfie配置
            selfie_config = self.get_config("selfie", {})

            # 权限检查：检查当前群是否在白名单中
            stream_id = function_args.get("_chat_id")
            if stream_id:
                debug_log(f"LLM工具调用 - {get_stream_id_info(stream_id)}")

                permission_cfg = selfie_config.get("permission", {})
                allow_all = permission_cfg.get("allow_all", False)
                allowed_groups = permission_cfg.get("allowed_groups", [])

                debug_log(f"权限配置: allow_all={allow_all}, allowed_groups={allowed_groups}")

                if not allow_all and not is_stream_in_list(stream_id, allowed_groups):
                    # 只输出到 console，不返回消息给群
                    logger.info(f"[权限拒绝] 群 {stream_id} 没有开启自拍权限，已静默拒绝 (配置格式提示: 使用 qq:群号 或直接填 hash)")
                    return {"name": self.name, "content": ""}

            # 初始化组件
            generator = SelfieGenerator(selfie_config)
            prompt_builder = SelfiePromptBuilder(selfie_config)
            target_selector = TargetSelector(selfie_config)

            # 检查是否可以拍照（冷却+每日上限）
            can_take, reason = generator.can_take_selfie()
            if not can_take:
                return {"name": self.name, "content": f"现在不能拍照: {reason}"}

            # 获取参数
            activity = function_args.get("activity", "休息")
            context = function_args.get("reason")
            style_arg = function_args.get("style")
            perspective_arg = function_args.get("perspective")

            # 选择质量风格
            if style_arg == "professional":
                style = SelfieStyle.PROFESSIONAL
            elif style_arg == "casual":
                style = SelfieStyle.CASUAL
            else:
                style = generator.select_style()

            # 选择视角
            if perspective_arg == "selfie":
                perspective = PhotoPerspective.SELFIE
            elif perspective_arg == "pov":
                perspective = PhotoPerspective.POV
            else:
                perspective = generator.select_perspective()

            logger.info(f"开始生成照片: activity={activity}, style={style.value}, perspective={perspective.value}")

            # 构建prompt
            prompt = prompt_builder.build_prompt(activity, style, perspective, context)

            # 生成图片
            image_base64, error = await generator.generate_selfie(prompt)
            if error:
                logger.error(f"生成照片失败: {error}")
                return {"name": self.name, "content": f"生成失败: {error}"}

            # 获取目标群
            # 优先使用当前对话的stream_id，否则自动选择
            stream_id = function_args.get("_chat_id") or target_selector.get_target_stream_id()
            if not stream_id:
                return {"name": self.name, "content": "没有可发送的目标群"}

            # 发送图片
            success = await send_api.image_to_stream(image_base64, stream_id)
            if success:
                style_name = "精美" if style == SelfieStyle.PROFESSIONAL else "随手拍"
                perspective_name = "自拍" if perspective == PhotoPerspective.SELFIE else "POV"
                logger.info(f"照片发送成功: stream={stream_id}, style={style_name}, perspective={perspective_name}")
                return {
                    "name": self.name,
                    "content": f"照片已发送！(活动: {activity}, {perspective_name}, {style_name})"
                }
            else:
                logger.error(f"发送图片失败: stream={stream_id}")
                return {"name": self.name, "content": "发送失败"}

        except Exception as e:
            logger.error(f"拍照工具执行失败: {e}", exc_info=True)
            return {"name": self.name, "content": f"出错了: {str(e)}"}
