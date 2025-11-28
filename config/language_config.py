# -*- coding: utf-8 -*-
"""
语言配置管理器 - 提供语言相关的数据源、模板、提示词路径
"""

from pathlib import Path
from typing import Dict
from .constants import (
    LANGUAGE_DATA_SOURCES,
    TEMPLATE_BASE_DIRS,
    PROMPT_BASE_DIRS,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE
)


class LanguageConfig:
    """
    语言配置管理器
    
    职责：
    - 提供指定语言的数据源路径
    - 提供指定语言的模板路径
    - 提供指定语言的提示词路径
    - 统一管理语言相关的配置
    """
    
    def __init__(self, language: str = None):
        """
        初始化语言配置
        
        Args:
            language: 语言代码（'zh' 或 'en'），默认使用 DEFAULT_LANGUAGE
        """
        self.language = self._normalize_language(language)
        
        if self.language not in LANGUAGE_DATA_SOURCES:
            raise ValueError(
                f"Unsupported language: {self.language}. "
                f"Supported: {list(LANGUAGE_DATA_SOURCES.keys())}"
            )
        
        # 从统一配置读取数据源
        self.data_sources = LANGUAGE_DATA_SOURCES[self.language]
        
        # 模板目录（按模块组织）
        self.template_dirs = {
            module: base_dir / self.language
            for module, base_dir in TEMPLATE_BASE_DIRS.items()
        }
        
        # 提示词目录（按模块组织）
        self.prompt_dirs = {
            module: base_dir / self.language
            for module, base_dir in PROMPT_BASE_DIRS.items()
        }
    
    @staticmethod
    def _normalize_language(language: str | None) -> str:
        """
        规范化语言代码
        
        Args:
            language: 语言代码或None
            
        Returns:
            规范化后的语言代码
        """
        if not language:
            return DEFAULT_LANGUAGE
        
        language = language.lower().strip()
        
        if language in SUPPORTED_LANGUAGES:
            return language
        
        # 如果不支持，返回默认语言（而不是抛异常，更友好）
        return DEFAULT_LANGUAGE
    
    def get_compliance_data_sources(self) -> Dict:
        """获取依从性报告的数据源配置"""
        return self.data_sources.get('compliance', {})
    
    def get_triage_data_sources(self) -> Dict:
        """获取分诊报告的数据源配置"""
        return self.data_sources.get('triage', {})
    
    def get_template_dir(self, module: str) -> Path:
        """
        获取指定模块的模板目录
        
        Args:
            module: 模块名（'compliance' 或 'triage'）
            
        Returns:
            模板目录路径
        """
        return self.template_dirs.get(module)
    
    def get_prompt_dir(self, module: str) -> Path:
        """
        获取指定模块的提示词目录
        
        Args:
            module: 模块名（'compliance' 或 'triage'）
            
        Returns:
            提示词目录路径
        """
        return self.prompt_dirs.get(module)
    
    @staticmethod
    def normalize_language(language: str | None) -> str:
        """
        静态方法：规范化语言代码（供外部调用）
        
        Args:
            language: 语言代码或None
            
        Returns:
            规范化后的语言代码
        """
        return LanguageConfig._normalize_language(language)


def get_language_config(language: str | None = None) -> LanguageConfig:
    """
    获取语言配置实例（便捷函数）
    
    Args:
        language: 语言代码，None时使用默认语言
        
    Returns:
        LanguageConfig实例
    """
    return LanguageConfig(language)

