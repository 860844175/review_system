# -*- coding: utf-8 -*-
"""
服务模块 - 提供与外部系统的集成服务
"""

from .approval_platform_client import ApprovalPlatformClient
from .system_client import SystemClient

__all__ = ['ApprovalPlatformClient', 'SystemClient']

