# -*- coding: utf-8 -*-
"""
系统模型端客户端 - 与系统模型端交互
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any
import requests

from .config import (
    SYSTEM_BASE_URL,
    SYSTEM_API_KEY,
    MAX_RETRIES,
    RETRY_DELAY
)

logger = logging.getLogger(__name__)


class SystemClient:
    """系统模型端客户端"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        初始化系统模型端客户端
        
        Args:
            base_url: 系统模型端基础URL，默认使用配置中的值
            api_key: API密钥，默认使用配置中的值
        """
        self.base_url = (base_url or SYSTEM_BASE_URL).rstrip('/')
        if not self.base_url:
            raise ValueError("SYSTEM_BASE_URL 未配置，请设置环境变量或配置")
        
        self.api_key = api_key or SYSTEM_API_KEY
        # API Key 可选（Mock 服务器可能不需要）
        
        self.headers = {
            "Content-Type": "application/json"
        }
        # 只有在提供了 API Key 时才添加到 headers
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    def send_review_result(
        self,
        user_id: str,
        scenario_id: str,
        target_kind: str,
        target_id: str,
        annotation_json: Dict[str, Any],
        author_id: Optional[str] = None,
        override_json: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
        supersede_previous: bool = True
    ) -> dict:
        """
        向系统模型端发送医生审核结果
        
        Args:
            user_id: 用户ID
            scenario_id: 场景ID
            target_kind: 复核对象类型（如 "triage_result"）
            target_id: 复核对象ID（从bundle中提取的triage id）
            annotation_json: 医生标注内容（必填）
            author_id: 医生ID（可选）
            override_json: 对原输出的覆盖内容（可选）
            is_active: 是否为活动评审，默认True
            supersede_previous: 是否淘汰旧的活动评审，默认True
        
        Returns:
            响应字典，包含review_id等字段
        
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = f"{self.base_url}/v1/reviews/create"
        
        payload = {
            "user_id": user_id,
            "scenario_id": scenario_id,
            "target_kind": target_kind,
            "target_id": target_id,
            "annotation_json": annotation_json,
            "is_active": is_active,
            "supersede_previous": supersede_previous
        }
        
        # 可选字段
        if author_id:
            payload["author_id"] = author_id
        if override_json is not None:
            payload["override_json"] = override_json
        
        logger.info(
            f"发送审核结果到系统模型端: "
            f"user_id={user_id}, scenario_id={scenario_id}, "
            f"target_kind={target_kind}, target_id={target_id}"
        )
        
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
                
                review_id = result.get("review_id") or result.get("id")
                if review_id:
                    logger.info(f"✅ 审核结果发送成功: review_id={review_id}")
                    return result
                else:
                    logger.warning(f"⚠️ 审核结果发送响应格式异常: {result}")
                    # 即使没有review_id，如果状态码是200，也认为成功
                    return result
                    
            except requests.RequestException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"⚠️ 审核结果发送失败，{wait_time}秒后重试 "
                        f"(尝试 {attempt + 1}/{MAX_RETRIES}): {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 审核结果发送最终失败: {e}")
                    raise
        
        raise last_exception or requests.RequestException("审核结果发送失败")


# 默认客户端实例
_default_client: Optional[SystemClient] = None


def get_default_client() -> Optional[SystemClient]:
    """获取默认的系统模型端客户端实例（如果已配置）"""
    global _default_client
    # 只检查 SYSTEM_BASE_URL，不要求 SYSTEM_API_KEY（Mock 服务器可能不需要）
    if _default_client is None and SYSTEM_BASE_URL:
        try:
            _default_client = SystemClient()
            logger.info(f"✅ 系统模型端客户端初始化成功: {SYSTEM_BASE_URL}")
        except ValueError as e:
            logger.warning(f"⚠️ 系统模型端客户端初始化失败: {e}")
            return None
    return _default_client
