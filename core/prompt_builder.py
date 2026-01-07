"""Prompt构建器 - 生成自拍提示词"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

from datetime import datetime
from typing import Optional
from src.plugin_system.apis import config_api
from .selfie_generator import SelfieStyle, PhotoPerspective


# 日系动漫风格基础提示词（强力避免恐怖谷效应）
ANIME_STYLE_BASE = """
=== CRITICAL: ART STYLE REQUIREMENTS ===

【强制画风】Japanese 2D Anime Illustration Style ONLY:
- Pure hand-drawn 2D anime aesthetic (セル画風/デジタルイラスト)
- Flat cel-shading with clean line art (クリーンな線画)
- Stylized anime face: large expressive eyes, small nose, simplified features
- Vibrant anime color palette with characteristic highlights (ハイライト)
- Smooth skin texture WITHOUT any realistic details (no pores, no wrinkles)

【技术参数 - Technical Specs】:
- Line weight: Clean, consistent anime-style outlines
- Coloring: Flat base colors + anime-style cel shading (2-3 tone shading)
- Eyes: Large, glossy anime eyes with characteristic light reflections (目のハイライト)
- Hair: Flowing anime hair with distinct color blocks and highlights
- Skin: Smooth, porcelain-like anime skin tone

【绝对禁止 - NEVER Generate】:
- ❌ Photorealistic or semi-realistic style
- ❌ 3D rendered / CGI / Unreal Engine look
- ❌ Uncanny valley effect (恐怖谷) - NO blending between realistic and anime
- ❌ AI art artifacts: distorted faces, extra fingers, melted features
- ❌ Western cartoon style (Disney/Pixar/DreamWorks)
- ❌ Chibi/SD style (unless specified)

【风格对标 - Reference Styles】:
- ✅ Light novel cover illustrations (ラノベ表紙)
- ✅ Visual novel / Galgame CG (ギャルゲCG)
- ✅ Genshin Impact / Honkai: Star Rail character art (原神/崩铁立绘)
- ✅ High-quality Pixiv illustrations (Pixiv人気イラスト)
- ✅ Kyoto Animation / ufotable character designs
- ✅ Modern seasonal anime key visuals

【画面要求 - Image Requirements】:
- NO text, speech bubbles, subtitles, watermarks, signatures
- NO UI elements, frames, filter labels, camera interface
- Clean composition like a single anime frame or illustration
- Professional illustration quality (商業イラストレベル)

=== END STYLE REQUIREMENTS ===
"""


def get_time_context() -> str:
    """获取当前时间段的描述"""
    hour = datetime.now().hour

    if 5 <= hour < 7:
        return "清晨，天刚亮，晨光微熹"
    elif 7 <= hour < 9:
        return "早晨，阳光明媚，早餐时间"
    elif 9 <= hour < 11:
        return "上午，阳光充足"
    elif 11 <= hour < 13:
        return "中午，阳光强烈，午餐时间"
    elif 13 <= hour < 15:
        return "下午早些时候，阳光温暖"
    elif 15 <= hour < 17:
        return "下午，阳光斜照"
    elif 17 <= hour < 19:
        return "傍晚，夕阳西下，天空泛橙"
    elif 19 <= hour < 21:
        return "晚上，天色已暗，室内灯光"
    elif 21 <= hour < 23:
        return "深夜，夜色浓重，灯光昏暗"
    else:  # 23-5
        return "凌晨，夜深人静，只有微弱灯光"


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

        # 选择质量风格描述
        quality_desc = self._professional_desc if style == SelfieStyle.PROFESSIONAL else self._casual_desc

        # 选择视角描述
        perspective_desc = self._selfie_desc if perspective == PhotoPerspective.SELFIE else self._pov_desc

        # 获取当前时间描述
        time_context = get_time_context()

        # 根据视角构建不同的prompt
        if perspective == PhotoPerspective.SELFIE:
            scene_prompt = f"""{bot_name}正在{activity}，拍了一张自拍。

当前时间: {time_context}
{quality_desc}。
{perspective_desc}。

角色设定: {personality if personality else "可爱的动漫风格女孩"}

请生成这张自拍图片。图片应该能看到人物的脸和当前活动的场景。注意光线和环境要符合当前时间段。"""
        else:
            # POV 视角
            scene_prompt = f"""{bot_name}正在{activity}，拍了一张眼前看到的景象。

当前时间: {time_context}
{quality_desc}。
{perspective_desc}。

角色设定: {personality if personality else "可爱的动漫风格女孩"}

请生成这张图片。这是第一人称视角，展示{bot_name}眼前看到的场景。注意光线和环境要符合当前时间段。"""

        # 组合最终prompt：场景 + 日系动漫风格要求
        prompt = f"""{scene_prompt}

{ANIME_STYLE_BASE}"""

        if context:
            prompt += f"\n\n补充信息: {context}"

        return prompt
