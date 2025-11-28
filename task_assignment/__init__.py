# -*- coding: utf-8 -*-
"""
Task Assignment Module
任务分配模块

此模块负责将审核任务分配给合适的医生。

主要功能：
- 任务分配策略管理
- 医生选择算法
- 负载均衡
"""

__version__ = "1.0.0"

from .assigner import TaskAssigner, AssignmentResult
from .client import ApprovalPlatformClient

__all__ = ['TaskAssigner', 'AssignmentResult', 'ApprovalPlatformClient']

