# -*- coding: utf-8 -*-
"""
请求上下文 - 统一管理请求级别的语言上下文
"""

from typing import Optional
from .language_config import LanguageConfig, get_language_config


class RequestContext:
    """
    请求上下文对象
    
    职责：
    - 统一管理请求级别的语言信息
    - 提供语言配置访问
    - 避免在函数间传递多个语言相关参数
    """
    
    def __init__(self, language: str | None = None, patient_id: str | None = None):
        """
        初始化请求上下文
        
        Args:
            language: 语言代码（'zh' 或 'en'），None时使用默认语言
            patient_id: 患者ID（可选）
        """
        self.language = LanguageConfig.normalize_language(language)
        self.patient_id = patient_id
        self.lang_config = get_language_config(self.language)
    
    @classmethod
    def from_request(cls, request) -> 'RequestContext':
        """
        从Flask请求对象创建上下文
        
        Args:
            request: Flask request对象
            
        Returns:
            RequestContext实例
        """
        # 从URL路径参数获取语言（如 /zh/patients）
        language = request.view_args.get('lang') if request.view_args else None
        
        # 从查询参数获取语言（如 ?lang=zh）
        if not language:
            language = request.args.get('lang')
        
        # 从请求头获取语言（可选，用于API调用）
        if not language:
            language = request.headers.get('X-Language')
        
        return cls(language=language)
    
    def get_data_sources(self, report_type: str):
        """
        获取指定报告类型的数据源配置
        
        Args:
            report_type: 报告类型（'compliance' 或 'triage'）
            
        Returns:
            数据源配置字典
        """
        if report_type == 'compliance':
            return self.lang_config.get_compliance_data_sources()
        elif report_type == 'triage':
            return self.lang_config.get_triage_data_sources()
        else:
            raise ValueError(f"Unknown report type: {report_type}")

