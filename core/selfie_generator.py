"""自拍生成器 - 核心生图模块"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import os
import re
import time
import random
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from enum import Enum
import aiohttp
from src.common.logger import get_logger

logger = get_logger("selfie_plugin.generator")


class SelfieStyle(Enum):
    """照片质量风格"""
    PROFESSIONAL = "professional"  # 精美照片
    CASUAL = "casual"  # 随手拍


class PhotoPerspective(Enum):
    """照片视角"""
    SELFIE = "selfie"  # 自拍（能看到脸）
    POV = "pov"  # 第一人称视角


class SelfieGenerator:
    """自拍生成器"""

    # Gemini 2.5 系列模型前缀
    GEMINI_25_PREFIXES = ("gemini-2.5", "gemini-2.0", "gemini-exp")

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._last_selfie_time: float = 0
        self._daily_count: int = 0
        self._daily_reset_date: str = ""
        self._image_index: int = 0  # 用于顺序轮换

        # API配置
        api_cfg = config.get("api", {})
        self._api_base = api_cfg.get("api_base", "")
        self._api_key = api_cfg.get("api_key", "") or os.environ.get("SELFIE_API_KEY", "")
        self._model = api_cfg.get("model", "gemini-3-pro-image")
        self._timeout = api_cfg.get("timeout", 120)
        self._max_retries = api_cfg.get("max_retries", 2)

        # 风格配置
        style_cfg = config.get("style", {})
        self._professional_ratio = style_cfg.get("professional_ratio", 0.3)
        self._selfie_ratio = style_cfg.get("selfie_ratio", 0.5)

        # 人设图片配置
        char_cfg = config.get("character", {})
        self._image_folder = char_cfg.get("image_folder", "")
        self._use_random = char_cfg.get("use_random_image", True)
        self._supported_formats = char_cfg.get("supported_formats", ["jpg", "jpeg", "png", "webp"])
        self._character_images: List[Path] = []
        self._load_character_images()

    def _is_gemini_25(self) -> bool:
        """检测是否使用 Gemini 2.5 系列模型"""
        model_lower = self._model.lower()
        return any(model_lower.startswith(prefix) for prefix in self.GEMINI_25_PREFIXES)

    def _load_character_images(self):
        """加载人设图片列表"""
        if not self._image_folder:
            return

        folder = Path(self._image_folder)
        if not folder.exists() or not folder.is_dir():
            logger.warning(f"人设图片文件夹不存在: {self._image_folder}")
            return

        for fmt in self._supported_formats:
            self._character_images.extend(folder.glob(f"*.{fmt}"))
            self._character_images.extend(folder.glob(f"*.{fmt.upper()}"))

        # 去重并排序
        self._character_images = sorted(set(self._character_images))
        if self._character_images:
            logger.info(f"加载了 {len(self._character_images)} 张人设参考图")
        else:
            logger.warning(f"人设图片文件夹为空: {self._image_folder}")

    def _get_reference_image(self) -> Optional[Tuple[str, str]]:
        """
        获取一张参考图片

        Returns:
            (base64_data, mime_type) 或 None
        """
        if not self._character_images:
            return None

        # 选择图片
        if self._use_random:
            image_path = random.choice(self._character_images)
        else:
            image_path = self._character_images[self._image_index % len(self._character_images)]
            self._image_index += 1

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # 获取 mime type
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type:
                mime_type = "image/jpeg"

            logger.debug(f"使用参考图: {image_path.name}")
            return image_data, mime_type

        except Exception as e:
            logger.error(f"读取参考图失败 {image_path}: {e}")
            return None

    def can_take_selfie(self) -> Tuple[bool, Optional[str]]:
        """检查是否可以拍照（冷却+每日上限）"""
        current_time = time.time()
        today = time.strftime("%Y-%m-%d")

        # 重置每日计数
        if today != self._daily_reset_date:
            self._daily_count = 0
            self._daily_reset_date = today

        # 检查每日上限
        max_daily = self.config.get("max_daily_selfies", 5)
        if self._daily_count >= max_daily:
            return False, f"今日已达上限({max_daily}张)"

        # 检查冷却
        cooldown = self.config.get("cooldown_seconds", 3600)
        elapsed = current_time - self._last_selfie_time
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            return False, f"冷却中({remaining}秒)"

        return True, None

    def select_style(self) -> SelfieStyle:
        """按配置比例随机选择质量风格"""
        return SelfieStyle.PROFESSIONAL if random.random() < self._professional_ratio else SelfieStyle.CASUAL

    def select_perspective(self) -> PhotoPerspective:
        """按配置比例随机选择视角"""
        return PhotoPerspective.SELFIE if random.random() < self._selfie_ratio else PhotoPerspective.POV

    def _build_message_content(self, prompt: str) -> Any:
        """
        构建消息内容（支持多模态）

        如果有人设参考图，返回多模态格式；否则返回纯文本。

        Args:
            prompt: 文本提示词

        Returns:
            str 或 List[dict] - 消息内容
        """
        ref_image = self._get_reference_image()

        if ref_image is None:
            # 无参考图，返回纯文本
            return prompt

        image_b64, mime_type = ref_image

        # 多模态格式（OpenAI Vision API 兼容）
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}"
                }
            },
            {
                "type": "text",
                "text": f"这是角色的参考形象图片。请基于这个形象生成图片。\n\n{prompt}"
            }
        ]

        logger.debug("使用多模态消息（含参考图）")
        return content

    async def generate_selfie(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        生成自拍图片

        Args:
            prompt: 生图提示词

        Returns:
            (base64_image, error_message) - 成功返回(base64, None)，失败返回(None, error)
        """
        if not self._api_key:
            return None, "API密钥未配置"
        if not self._api_base:
            return None, "API地址未配置"

        # 构建消息内容（支持多模态）
        message_content = self._build_message_content(prompt)

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": message_content}]
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        is_25 = self._is_gemini_25()
        if is_25:
            logger.info(f"检测到 Gemini 2.5 系列模型: {self._model}，使用兼容解析")

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                logger.debug(f"生成图片 (尝试 {attempt + 1}/{self._max_retries + 1})")
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self._api_base,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self._timeout)
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            last_error = f"API返回 {resp.status}: {error_text[:100]}"
                            logger.warning(last_error)
                            continue

                        data = await resp.json()

                        # 根据模型版本选择解析方式
                        if is_25:
                            image_data = await self._extract_image_gemini_25(data)
                        else:
                            image_data = await self._extract_image(data)

                        if image_data:
                            self._last_selfie_time = time.time()
                            self._daily_count += 1
                            logger.info(f"图片生成成功，今日第{self._daily_count}张")
                            return image_data, None
                        else:
                            last_error = "无法从响应中提取图片"
                            logger.warning(last_error)

            except aiohttp.ClientTimeout:
                last_error = f"请求超时 ({self._timeout}秒)"
                logger.warning(f"生图超时 (尝试 {attempt + 1})")
            except Exception as e:
                last_error = str(e)
                logger.error(f"生图失败 (尝试 {attempt + 1}): {e}")

        return None, last_error or "生成失败，请稍后重试"

    async def _extract_image(self, response: Dict) -> Optional[str]:
        """从API响应中提取图片base64 (Gemini 3.x 格式)"""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                logger.warning("响应内容为空")
                return None

            # 方法1: 匹配 markdown 图片格式 ![](url)
            url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
            if url_match:
                image_url = url_match.group(1)
                logger.debug(f"从markdown提取到图片URL: {image_url[:50]}...")
                return await self._download_image_as_base64(image_url)

            # 方法2: 匹配 data:image base64 格式
            if "data:image" in content:
                b64_match = re.search(r'base64,([A-Za-z0-9+/=]+)', content)
                if b64_match:
                    logger.debug("从data:image格式提取到base64")
                    return b64_match.group(1)

            # 方法3: 纯base64字符串
            content_stripped = content.strip()
            if len(content_stripped) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', content_stripped):
                logger.debug("检测到纯base64格式")
                return content_stripped

            logger.warning(f"无法识别的响应格式，内容前100字符: {content[:100]}")
            return None

        except Exception as e:
            logger.error(f"提取图片失败: {e}")
            return None

    async def _extract_image_gemini_25(self, response: Dict) -> Optional[str]:
        """
        从API响应中提取图片base64 (Gemini 2.5 兼容格式)

        Gemini 2.5 可能返回：
        1. markdown 格式 ![](url)
        2. data:image base64 格式
        3. 纯 URL（不带 markdown）
        4. 原始 base64（以 /9j/ 或 iVBOR 开头）
        """
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                logger.warning("响应内容为空")
                return None

            # 方法1: 匹配 markdown 图片格式 ![](url)
            url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
            if url_match:
                image_url = url_match.group(1)
                logger.debug(f"[2.5兼容] 从markdown提取到图片URL")
                return await self._download_image_as_base64(image_url)

            # 方法2: 检查 data:image base64 格式
            if "data:image" in content:
                if "base64," in content:
                    img_data = content.split("base64,")[1]
                    # 清理可能的尾部内容
                    img_data = re.match(r'^[A-Za-z0-9+/=]+', img_data)
                    if img_data:
                        logger.debug("[2.5兼容] 从data:image格式提取到base64")
                        return img_data.group(0)

            # 方法3: 检查原始 base64 (JPEG 以 /9j/ 开头，PNG 以 iVBOR 开头)
            if content.startswith("/9j/") or content.startswith("iVBOR"):
                logger.debug("[2.5兼容] 检测到原始base64格式")
                return content.strip()

            # 方法4: 检查纯 URL（不带 markdown 格式）
            if "http" in content:
                # 匹配图片 URL
                url_match2 = re.search(r'(https?://[^\s\)\"\']+\.(?:png|jpg|jpeg|webp|gif))', content, re.IGNORECASE)
                if url_match2:
                    image_url = url_match2.group(1)
                    logger.debug(f"[2.5兼容] 从纯文本提取到图片URL")
                    return await self._download_image_as_base64(image_url)

                # 匹配任意 URL（可能是 CDN 链接不带扩展名）
                url_match3 = re.search(r'(https?://[^\s\)\"\']+)', content)
                if url_match3:
                    image_url = url_match3.group(1)
                    logger.debug(f"[2.5兼容] 尝试下载通用URL")
                    result = await self._download_image_as_base64(image_url)
                    if result:
                        return result

            # 方法5: 纯base64字符串（长度检查）
            content_stripped = content.strip()
            if len(content_stripped) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', content_stripped):
                logger.debug("[2.5兼容] 检测到纯base64格式")
                return content_stripped

            logger.warning(f"[2.5兼容] 无法识别的响应格式，内容前200字符: {content[:200]}")
            return None

        except Exception as e:
            logger.error(f"[2.5兼容] 提取图片失败: {e}")
            return None

    async def _download_image_as_base64(self, url: str) -> Optional[str]:
        """下载图片并转换为base64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        image_bytes = await resp.read()
                        return base64.b64encode(image_bytes).decode('utf-8')
                    else:
                        logger.warning(f"下载图片失败: HTTP {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None
