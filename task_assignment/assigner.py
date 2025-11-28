# -*- coding: utf-8 -*-
"""
Task Assigner
任务分配器

负责将审核任务分配给医生。
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
import logging

from .client import ApprovalPlatformClient

logger = logging.getLogger(__name__)


@dataclass
class AssignmentResult:
    """任务分配结果"""
    doctor_id: str
    assignment_reason: str
    strategy_used: str


class TaskAssigner:
    """
    任务分配器
    
    根据不同的策略将任务分配给医生。
    """
    
    def __init__(self, strategy: str = "load_balance", client: Optional[ApprovalPlatformClient] = None):
        """
        初始化任务分配器
        
        Args:
            strategy: 分配策略名称，默认 "load_balance"
            client: 审核平台客户端，如果为None则创建新实例
        """
        self.strategy = strategy
        self.client = client or ApprovalPlatformClient(use_test_data=True)
    
    def assign_task(
        self,
        user_id: str,
        scenario_id: str,
        task_id: str,
        hospital_id: Optional[str] = None,
        **kwargs
    ) -> AssignmentResult:
        """
        分配任务给医生
        
        Args:
            user_id: 用户ID（患者ID）
            scenario_id: 场景ID
            task_id: 任务ID
            hospital_id: 医院ID（可选），如果提供则只从该医院选择医生
            **kwargs: 其他可选参数（如紧急程度等）
        
        Returns:
            AssignmentResult: 分配结果，包含doctor_id和分配信息
        
        Raises:
            ValueError: 如果没有可用的医生
        """
        if self.strategy == "load_balance":
            return self._assign_with_load_balance(hospital_id, task_id)
        else:
            raise NotImplementedError(
                f"Assignment strategy '{self.strategy}' is not yet implemented."
            )
    
    def _assign_with_load_balance(
        self,
        hospital_id: Optional[str],
        task_id: str
    ) -> AssignmentResult:
        """
        使用负载均衡策略分配任务
        
        分配逻辑：
        1. 获取所有医生及其未审核任务数量
        2. 按 (task_count, id) 排序（任务数量优先，然后按ID）
        3. 选择任务数量最少的医生
        
        Args:
            hospital_id: 医院ID（可选）
            task_id: 任务ID（用于日志）
        
        Returns:
            AssignmentResult: 分配结果
        
        Raises:
            ValueError: 如果没有可用的医生
        """
        # 获取医生列表及其任务数量
        doctors_with_counts = self.client.get_doctors_with_task_counts(hospital_id)
        
        if not doctors_with_counts:
            raise ValueError("没有可用的医生")
        
        # 按 (task_count, id) 排序
        # task_count 小的在前，相同 task_count 时 id 小的在前
        sorted_doctors = sorted(
            doctors_with_counts,
            key=lambda d: (d.get("task_count", 0), d.get("id", ""))
        )
        
        # 选择任务数量最少的医生
        selected_doctor = sorted_doctors[0]
        doctor_id = selected_doctor["id"]
        doctor_name = selected_doctor.get("name", doctor_id)
        task_count = selected_doctor.get("task_count", 0)
        
        logger.info(
            f"任务 {task_id} 分配给医生 {doctor_id} ({doctor_name})，"
            f"当前未审核任务数: {task_count}"
        )
        
        return AssignmentResult(
            doctor_id=doctor_id,
            assignment_reason=(
                f"负载均衡分配：医生 {doctor_name} 当前未审核任务数为 {task_count}，"
                f"在所有可用医生中任务数量最少"
            ),
            strategy_used="load_balance"
        )
    
    def get_available_doctors(self, hospital_id: Optional[str] = None) -> list[dict]:
        """
        获取可用的医生列表（包含任务数量信息）
        
        Args:
            hospital_id: 医院ID（可选），如果提供则只返回该医院的医生
        
        Returns:
            医生列表，每个医生包含 task_count 字段
        """
        return self.client.get_doctors_with_task_counts(hospital_id)

