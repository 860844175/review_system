# -*- coding: utf-8 -*-
"""
服务配置 - 外部系统API配置
"""

import os
from pathlib import Path

# ======================== 审核平台配置 ========================
# 默认使用 Mock 审核平台（开发/测试环境）
# 生产环境请通过环境变量设置真实平台地址
APPROVAL_PLATFORM_BASE_URL = os.getenv(
    "APPROVAL_PLATFORM_BASE_URL",
    "http://localhost:5003"  # 默认使用 Mock 平台
)
APPROVAL_PLATFORM_API_KEY = os.getenv(
    "APPROVAL_PLATFORM_API_KEY",
    "test_key"  # Mock 平台的默认token，可通过环境变量覆盖
)

# ======================== 系统模型端配置 ========================
# 默认使用 Mock Zhikai 服务器（开发/测试环境）
# 生产环境请通过环境变量设置真实系统地址
DIAGNOSIS_SYSTEM_BASE_URL = os.getenv("DIAGNOSIS_SYSTEM_BASE_URL", "http://localhost:5002")  # 默认使用 Mock Zhikai
DIAGNOSIS_SYSTEM_API_KEY = os.getenv("DIAGNOSIS_SYSTEM_API_KEY", "")  # Mock Zhikai 暂不需要 API Key，生产环境需要设置

# ======================== 本地服务配置 ========================
LOCAL_BASE_URL = os.getenv(
    "LOCAL_BASE_URL",
    "http://localhost:5001"
)

# ======================== 重试配置 ========================
MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "5"))  # seconds

