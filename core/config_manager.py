"""配置管理器 - 自动合并用户配置与默认配置"""
"""
// KIRISAME SYSTEMS™ | uaih3k9x
// "We shape the void."
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # fallback

try:
    import tomli_w
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False

from src.common.logger import get_logger

logger = get_logger("selfie_plugin.config")


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典
    - override 中的值会覆盖 base 中的值
    - base 中有但 override 中没有的键会保留
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = deep_merge(result[key], value)
        else:
            # 直接覆盖
            result[key] = value
    
    return result


def load_toml(file_path: Path) -> Optional[Dict[str, Any]]:
    """加载 TOML 文件"""
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败 {file_path}: {e}")
        return None


def save_toml(file_path: Path, data: Dict[str, Any]) -> bool:
    """保存 TOML 文件（需要 tomli_w）"""
    if not HAS_TOMLI_W:
        logger.warning("tomli_w 未安装，无法保存配置文件")
        return False
    
    try:
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败 {file_path}: {e}")
        return False


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = Path(plugin_dir)
        self.default_config_path = self.plugin_dir / "config.default.toml"
        self.user_config_path = self.plugin_dir / "config.toml"
    
    def ensure_user_config(self) -> Dict[str, Any]:
        """
        确保用户配置存在并与默认配置合并
        
        返回合并后的配置字典
        """
        # 1. 加载默认配置
        default_config = load_toml(self.default_config_path)
        if default_config is None:
            logger.warning("默认配置文件不存在，使用空配置")
            default_config = {}
        
        default_version = default_config.get("config_version", 1)
        
        # 2. 检查用户配置是否存在
        if not self.user_config_path.exists():
            logger.info("用户配置不存在，从默认配置创建")
            self._create_user_config_from_default()
            return default_config
        
        # 3. 加载用户配置
        user_config = load_toml(self.user_config_path)
        if user_config is None:
            logger.warning("用户配置加载失败，使用默认配置")
            return default_config
        
        user_version = user_config.get("config_version", 0)
        
        # 4. 检查版本兼容性
        if user_version < default_version:
            logger.info(f"配置版本升级: {user_version} -> {default_version}")
            # 合并配置，用户值优先
            merged_config = deep_merge(default_config, user_config)
            # 更新版本号
            merged_config["config_version"] = default_version
            
            # 尝试保存合并后的配置
            if HAS_TOMLI_W:
                # 备份旧配置
                backup_path = self.user_config_path.with_suffix(".toml.bak")
                shutil.copy(self.user_config_path, backup_path)
                logger.info(f"已备份旧配置到 {backup_path}")
                
                # 保存合并后的配置
                if save_toml(self.user_config_path, merged_config):
                    logger.info("配置已自动合并并保存")
            else:
                logger.info("检测到新配置项，但 tomli_w 未安装，请手动更新 config.toml")
            
            return merged_config
        
        # 5. 版本相同，直接合并（补充新字段）
        merged_config = deep_merge(default_config, user_config)
        
        # 检查是否有新字段
        new_fields = self._find_new_fields(default_config, user_config)
        if new_fields:
            logger.info(f"发现新配置字段: {new_fields}")
            if HAS_TOMLI_W:
                save_toml(self.user_config_path, merged_config)
                logger.info("新字段已自动添加到用户配置")
        
        return merged_config
    
    def _create_user_config_from_default(self):
        """从默认配置创建用户配置"""
        if self.default_config_path.exists():
            shutil.copy(self.default_config_path, self.user_config_path)
            logger.info(f"已创建用户配置: {self.user_config_path}")
    
    def _find_new_fields(
        self, 
        default: Dict[str, Any], 
        user: Dict[str, Any], 
        prefix: str = ""
    ) -> list:
        """找出默认配置中有但用户配置中没有的字段"""
        new_fields = []
        
        for key, value in default.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if key not in user:
                new_fields.append(full_key)
            elif isinstance(value, dict) and isinstance(user.get(key), dict):
                new_fields.extend(
                    self._find_new_fields(value, user[key], full_key)
                )
        
        return new_fields


def get_merged_config(plugin_dir: Path) -> Dict[str, Any]:
    """便捷函数：获取合并后的配置"""
    manager = ConfigManager(plugin_dir)
    return manager.ensure_user_config()
