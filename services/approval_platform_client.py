# -*- coding: utf-8 -*-
"""
审核平台客户端 - 与审核任务平台交互
"""

from __future__ import annotations

import logging
import time
from typing import Optional
import requests

from .config import (
    APPROVAL_PLATFORM_BASE_URL,
    APPROVAL_PLATFORM_API_KEY,
    MAX_RETRIES,
    RETRY_DELAY
)

logger = logging.getLogger(__name__)


class ApprovalPlatformClient:
    """审核平台客户端"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        初始化审核平台客户端
        
        Args:
            base_url: 审核平台基础URL，默认使用配置中的值
            api_key: API密钥（Token），默认使用配置中的值
        """
        self.base_url = (base_url or APPROVAL_PLATFORM_BASE_URL).rstrip('/')
        self.api_key = api_key or APPROVAL_PLATFORM_API_KEY
        self.headers = {
            "Token": self.api_key,
            "Content-Type": "application/json"
        }
    
    def register_add_task(
        self,
        task_id: str,
        user_id: str,
        review_page_url: str,
        doctor_id: Optional[str] = None,
        kind: str = "分诊评估"
    ) -> dict:
        """
        注册审核任务到审核平台
        
        Args:
            task_id: 本地生成的任务ID
            user_id: 用户ID（患者ID）
            review_page_url: 审核页面URL
            doctor_id: 医生ID，默认None（待对齐后传入）
            kind: 审核类型，默认"分诊评估"
        
        Returns:
            响应字典，包含success、message、data字段
        
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = f"{self.base_url}/openapi/doctor/approve/add"
        
        payload = {
            "id": task_id,
            "doctorId": doctor_id,  # 暂时传null，待对齐
            "customerId": user_id,
            "kind": kind,
            "url": review_page_url
        }
        
        logger.info(f"注册审核任务到平台: task_id={task_id}, user_id={user_id}")
        
        # 带重试的请求
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("success"):
                    logger.info(f"✅ 任务注册成功: task_id={task_id}")
                    return result
                else:
                    error_msg = result.get("message", "未知错误")
                    logger.warning(f"⚠️ 任务注册返回失败: {error_msg}")
                    raise requests.RequestException(f"平台返回失败: {error_msg}")
                    
            except requests.RequestException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"⚠️ 任务注册失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 任务注册最终失败: {e}")
                    raise
        
        raise last_exception or requests.RequestException("任务注册失败")
    
    def submit_task(self, task_id: str) -> dict:
        """
        通知审核平台任务已完成
        
        Args:
            task_id: 任务ID
        
        Returns:
            响应字典，包含success、message、data字段
        
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = f"{self.base_url}/openapi/doctor/approve/submit"
        
        payload = {
            "id": task_id
        }
        
        logger.info(f"通知审核平台任务完成: task_id={task_id}")
        
        # 带重试的请求
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("success"):
                    logger.info(f"✅ 任务完成通知成功: task_id={task_id}")
                    return result
                else:
                    error_msg = result.get("message", "未知错误")
                    logger.warning(f"⚠️ 任务完成通知返回失败: {error_msg}")
                    raise requests.RequestException(f"平台返回失败: {error_msg}")
                    
            except requests.RequestException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"⚠️ 任务完成通知失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 任务完成通知最终失败: {e}")
                    raise
        
        raise last_exception or requests.RequestException("任务完成通知失败")


# 默认客户端实例
_default_client: Optional[ApprovalPlatformClient] = None


def get_default_client() -> ApprovalPlatformClient:
    """获取默认的审核平台客户端实例"""
    global _default_client
    if _default_client is None:
        _default_client = ApprovalPlatformClient()
    return _default_client

