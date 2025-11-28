# -*- coding: utf-8 -*-
"""
多语言配置常量 - 统一管理所有语言相关的路径配置
"""

from pathlib import Path

# 支持的语言列表
SUPPORTED_LANGUAGES = ['zh', 'en']
DEFAULT_LANGUAGE = 'zh'

# 项目根目录（从config目录向上）
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# ==================== 语言数据源配置 ====================
# 注意：目前只配置zh，en的配置等有数据后再添加
LANGUAGE_DATA_SOURCES = {
    'zh': {
        'compliance': {
            'profiles': [
                DATA_DIR / "zh" / "output_llm_enhanced" / "patient_profiles",
                DATA_DIR / "zh" / "output" / "patient_profiles"
            ],
            'memory': [
                DATA_DIR / "zh" / "output_llm_enhanced" / "memory_data",
                DATA_DIR / "zh" / "output" / "memory"
            ],
            'memory_file_pattern': '{patient_id}_memory.json'
        },
        'triage': {
            'data_dir': DATA_DIR / "zh" / "triage",
            'file_pattern': '{patient_id}.json'
        }
    },
    'en': {
        'compliance': {
            'profiles': [
                DATA_DIR / "en" / "output_llm_enhanced" / "patient_profiles",
                DATA_DIR / "en" / "output" / "patient_profiles"
            ],
            'memory': [
                DATA_DIR / "en" / "output_llm_enhanced" / "memory_data",
                DATA_DIR / "en" / "output" / "memory"
            ],
            'memory_file_pattern': '{patient_id}_memory.json'
        },
        'triage': {
            'data_dir': DATA_DIR / "en" / "triage",
            'file_pattern': '{patient_id}.json'
        }
    }
}

# 模板和提示词基础目录
TEMPLATE_BASE_DIRS = {
    'compliance': BASE_DIR / "report_modules" / "compliance" / "templates",
    'triage': BASE_DIR / "report_modules" / "triage" / "templates"
}

PROMPT_BASE_DIRS = {
    'compliance': BASE_DIR / "report_modules" / "compliance" / "prompts",
    'triage': BASE_DIR / "report_modules" / "triage" / "prompts"
}

# 报告输出目录
REPORT_OUTPUT_BASE = BASE_DIR / "report" / "output"
REPORT_APPROVED_BASE = BASE_DIR / "report" / "approved"

