"""麦麦自拍插件 - 主文件"""

from typing import List, Tuple, Type

from src.plugin_system import BasePlugin, register_plugin, ConfigField
from src.common.logger import get_logger

from .tools import TakeSelfiePhotoTool
from .handlers import SelfieActivityHandler
from .commands import SelfieCommand

logger = get_logger("selfie_plugin")


@register_plugin
class SelfiePlugin(BasePlugin):
    """
    麦麦自拍插件

    让麦麦能够拍摄自拍并发送到群里，基于人设和当前活动生成图片。
    支持精美照片和随手拍两种风格。
    """

    plugin_name: str = "selfie_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []  # 不强制依赖其他插件
    python_dependencies: List[str] = ["aiohttp"]
    config_file_name: str = "config.toml"

    config_section_descriptions = {
        "plugin": "插件基本配置",
        "selfie": "自拍功能配置",
        "selfie.api": "生图API配置",
        "selfie.character": "人设图片配置",
        "selfie.style": "照片风格配置",
        "selfie.trigger": "触发机制配置",
        "selfie.target": "目标群配置",
    }

    config_schema: dict = {
        "plugin": {
            "enabled": ConfigField(
                type=bool,
                default=True,
                description="是否启用插件"
            ),
        },
        "selfie": {
            "cooldown_seconds": ConfigField(
                type=int,
                default=3600,
                description="冷却时间（秒）"
            ),
            "max_daily_selfies": ConfigField(
                type=int,
                default=5,
                description="每日上限"
            ),
            "api": {
                "api_base": ConfigField(
                    type=str,
                    default="https://one-api.ygxz.in/v1/chat/completions",
                    description="生图API地址（OpenAI兼容格式）"
                ),
                "api_key": ConfigField(
                    type=str,
                    default="",
                    description="API密钥（留空则从环境变量SELFIE_API_KEY读取）"
                ),
                "model": ConfigField(
                    type=str,
                    default="gemini-3-pro-image",
                    description="模型名称"
                ),
                "timeout": ConfigField(
                    type=int,
                    default=120,
                    description="超时秒数"
                ),
                "max_retries": ConfigField(
                    type=int,
                    default=2,
                    description="重试次数"
                ),
            },
            "character": {
                "image_folder": ConfigField(
                    type=str,
                    default="",
                    description="人设图片文件夹路径（留空则不使用参考图）"
                ),
                "use_random_image": ConfigField(
                    type=bool,
                    default=True,
                    description="随机选图（false则按顺序轮换）"
                ),
                "supported_formats": ConfigField(
                    type=list,
                    default=["jpg", "jpeg", "png", "webp"],
                    description="支持的图片格式"
                ),
            },
            "style": {
                "professional_ratio": ConfigField(
                    type=float,
                    default=0.3,
                    description="精美照片比例（0.0-1.0）"
                ),
                "casual_ratio": ConfigField(
                    type=float,
                    default=0.7,
                    description="随手拍比例（0.0-1.0）"
                ),
                "selfie_ratio": ConfigField(
                    type=float,
                    default=0.5,
                    description="自拍视角比例（0.0-1.0）"
                ),
                "pov_ratio": ConfigField(
                    type=float,
                    default=0.5,
                    description="POV视角比例（0.0-1.0）"
                ),
                "professional_desc": ConfigField(
                    type=str,
                    default="光线很好，画面清晰，像是精心拍摄的",
                    description="精美风格描述"
                ),
                "casual_desc": ConfigField(
                    type=str,
                    default="照片有点糊但是很真实，像是随手用手机拍的",
                    description="随手拍风格描述"
                ),
                "selfie_desc": ConfigField(
                    type=str,
                    default="自拍照，能看到人物的脸和表情",
                    description="自拍视角描述"
                ),
                "pov_desc": ConfigField(
                    type=str,
                    default="第一人称视角，像是自己眼睛看到的场景",
                    description="POV视角描述"
                ),
            },
            "trigger": {
                "enable_llm_tool": ConfigField(
                    type=bool,
                    default=True,
                    description="允许LLM工具调用"
                ),
                "enable_activity_trigger": ConfigField(
                    type=bool,
                    default=True,
                    description="启用活动变化触发"
                ),
                "activity_trigger_probability": ConfigField(
                    type=float,
                    default=0.1,
                    description="活动变化触发概率（0.0-1.0）"
                ),
                "check_interval_seconds": ConfigField(
                    type=int,
                    default=60,
                    description="活动检查间隔（秒）"
                ),
            },
            "target": {
                "selection_mode": ConfigField(
                    type=str,
                    default="most_active",
                    description="目标选择模式：most_active(最活跃群) 或 configured(指定群)"
                ),
                "activity_window_minutes": ConfigField(
                    type=int,
                    default=30,
                    description="活跃度计算窗口（分钟）"
                ),
                "configured_groups": ConfigField(
                    type=list,
                    default=[],
                    description="指定群列表，格式如 [\"qq:123456\", \"qq:789012\"]"
                ),
            },
        },
    }

    def __init__(self, *args, **kwargs):
        """初始化插件"""
        super().__init__(*args, **kwargs)
        logger.info("麦麦自拍插件初始化完成")

    def get_plugin_components(self) -> List[Tuple]:
        """获取插件组件"""
        return [
            # LLM工具 - 供LLM直接调用
            (TakeSelfiePhotoTool.get_tool_info(), TakeSelfiePhotoTool),
            # 事件处理器 - 活动变化触发
            (SelfieActivityHandler.get_handler_info(), SelfieActivityHandler),
            # 命令 - 调试用
            (SelfieCommand.get_command_info(), SelfieCommand),
        ]
