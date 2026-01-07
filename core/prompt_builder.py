"""Prompt构建器 - 生成自拍提示词"""

from typing import Optional
from src.plugin_system.apis import config_api
from .selfie_generator import SelfieStyle, PhotoPerspective


# 日系动漫风格基础提示词（避免恐怖谷效应）
ANIME_STYLE_BASE = """风格要求：
- 日系动漫/插画风格，不要写实风格
- 2D手绘质感，色彩鲜明
- 避免恐怖谷效应，不要3D渲染或真人照片风格
- 参考：轻小说插画、Galgame CG、日系手游立绘"""


class SelfiePromptBuilder:
    """构建生图Prompt"""

    def __init__(self, config: dict):
        self.config = config
        style_cfg = config.get("style", {})
        self._professional_desc = style_cfg.get(
            "professional_desc",
            "光线很好，画面清晰，像是精心拍摄的"
        )
        self._casual_desc = style_cfg.get(
            "casual_desc",
            "照片有点糊但是很真实，像是随手用手机拍的"
        )
        self._selfie_desc = style_cfg.get(
            "selfie_desc",
            "自拍照，能看到人物的脸和表情"
        )
        self._pov_desc = style_cfg.get(
            "pov_desc",
            "第一人称视角，像是自己眼睛看到的场景"
        )

    def build_prompt(
        self,
        activity: str,
        style: SelfieStyle,
        perspective: PhotoPerspective = PhotoPerspective.SELFIE,
        context: Optional[str] = None
    ) -> str:
        """
        构建生图prompt

        Args:
            activity: 当前活动描述
            style: 照片质量风格
            perspective: 照片视角
            context: 可选的补充上下文

        Returns:
            完整的生图prompt
        """
        # 获取bot信息
        bot_name = config_api.get_global_config("bot.nickname", "麦麦")
        personality = config_api.get_global_config("personality.personality", "")

        # 截取人设前150字，避免prompt过长
        if personality and len(personality) > 150:
            personality = personality[:150] + "..."

        # 选择质量风格描述
        quality_desc = self._professional_desc if style == SelfieStyle.PROFESSIONAL else self._casual_desc

        # 选择视角描述
        perspective_desc = self._selfie_desc if perspective == PhotoPerspective.SELFIE else self._pov_desc

        # 根据视角构建不同的prompt
        if perspective == PhotoPerspective.SELFIE:
            scene_prompt = f"""{bot_name}正在{activity}，拍了一张自拍。
{quality_desc}。
{perspective_desc}。

角色设定: {personality if personality else "可爱的动漫风格女孩"}

请生成这张自拍图片。图片应该能看到人物的脸和当前活动的场景。"""
        else:
            # POV 视角
            scene_prompt = f"""{bot_name}正在{activity}，拍了一张眼前看到的景象。
{quality_desc}。
{perspective_desc}。

角色设定: {personality if personality else "可爱的动漫风格女孩"}

请生成这张图片。这是第一人称视角，展示{bot_name}眼前看到的场景。"""

        # 组合最终prompt：场景 + 日系动漫风格要求
        prompt = f"""{scene_prompt}

{ANIME_STYLE_BASE}"""

        if context:
            prompt += f"\n\n补充信息: {context}"

        return prompt
