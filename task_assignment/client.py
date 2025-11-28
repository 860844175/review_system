# -*- coding: utf-8 -*-
"""
Approval Platform Client for Task Assignment
任务分配相关的审核平台客户端

用于从审核平台获取医生信息、任务列表等数据。
"""

from __future__ import annotations
from typing import Optional
import logging
import json
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class ApprovalPlatformClient:
    """
    审核平台客户端（用于任务分配）
    
    负责与审核平台API交互，获取医生信息等数据。
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_test_data: bool = True
    ):
        """
        初始化客户端
        
        Args:
            base_url: 审核平台基础URL
            api_key: API密钥
            use_test_data: 是否使用测试数据（默认True，开发阶段使用）
        """
        self.base_url = base_url
        self.api_key = api_key
        self.use_test_data = use_test_data
        self.test_data_path = Path(__file__).parent.parent / "data" / "test_doctors.json"
    
    def get_doctors(self, hospital_id: Optional[str] = None) -> list[dict]:
        """
        获取医生列表（包含任务信息）
        
        Args:
            hospital_id: 医院ID（可选），如果提供则只返回该医院的医生
        
        Returns:
            医生列表，每个医生包含 tasks 字段
        """
        if self.use_test_data:
            return self._get_doctors_from_test_data(hospital_id)
        
        # 从审核平台API获取
        return self._get_doctors_from_api(hospital_id)
    
    def _get_doctors_from_test_data(self, hospital_id: Optional[str] = None) -> list[dict]:
        """
        从测试数据文件读取医生列表
        
        Args:
            hospital_id: 医院ID（可选）
        
        Returns:
            医生列表
        """
        try:
            with open(self.test_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            doctors = data.get("data", [])
            
            # 如果指定了医院ID，进行过滤
            if hospital_id:
                doctors = [d for d in doctors if d.get("hospitalId") == hospital_id]
            
            logger.info(f"从测试数据读取到 {len(doctors)} 位医生")
            return doctors
            
        except FileNotFoundError:
            logger.error(f"测试数据文件不存在: {self.test_data_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析测试数据文件失败: {e}")
            return []
        except Exception as e:
            logger.error(f"读取测试数据失败: {e}")
            return []
    
    def _get_doctors_from_api(self, hospital_id: Optional[str] = None) -> list[dict]:
        """
        从审核平台API获取医生列表
        
        Args:
            hospital_id: 医院ID（可选）
        
        Returns:
            医生列表
        """
        if not self.base_url:
            logger.error("审核平台 base_url 未配置")
            return []
        
        url = f"{self.base_url}/openapi/doctor/list"
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Token"] = self.api_key
        
        payload = {}
        if hospital_id:
            payload["hospitalId"] = hospital_id
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                doctors = result.get("data", [])
                logger.info(f"从审核平台API获取到 {len(doctors)} 位医生")
                return doctors
            else:
                logger.error(f"审核平台API返回失败: {result.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"调用审核平台API失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取医生列表失败: {e}")
            return []
    
    def get_doctor_with_tasks(self, doctor_id: str) -> dict:
        """
        获取医生信息及其所有任务
        
        Args:
            doctor_id: 医生ID
        
        Returns:
            医生信息及任务列表，格式：
            {
                "id": "...",
                "name": "...",
                "tasks": [...]
            }
        """
        if self.use_test_data:
            doctors = self._get_doctors_from_test_data()
            for doctor in doctors:
                if doctor.get("id") == doctor_id:
                    return doctor
            raise ValueError(f"医生ID不存在: {doctor_id}")
        
        # 从审核平台API获取
        return self._get_doctor_from_api(doctor_id)
    
    def _get_doctor_from_api(self, doctor_id: str) -> dict:
        """
        从审核平台API获取医生信息及其任务
        
        Args:
            doctor_id: 医生ID
        
        Returns:
            医生信息及任务列表
        """
        if not self.base_url:
            raise ValueError("审核平台 base_url 未配置")
        
        url = f"{self.base_url}/openapi/doctor/get"
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Token"] = self.api_key
        
        payload = {"id": doctor_id}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                data = result.get("data", [])
                if data and len(data) > 0:
                    return data[0]  # 返回第一个医生信息
                else:
                    raise ValueError(f"医生ID不存在: {doctor_id}")
            else:
                raise ValueError(f"获取医生信息失败: {result.get('message', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"调用审核平台API失败: {e}")
        except Exception as e:
            raise ValueError(f"获取医生信息失败: {e}")
    
    def get_doctors_with_task_counts(self, hospital_id: Optional[str] = None) -> list[dict]:
        """
        获取医生列表及其未审核任务数量
        
        Args:
            hospital_id: 医院ID（可选）
        
        Returns:
            医生列表，每个医生包含：
            - 所有原有字段
            - tasks: 任务列表
            - task_count: 未审核任务数量（status=0的任务数）
        """
        doctors = self.get_doctors(hospital_id)
        
        result = []
        for doctor in doctors:
            tasks = doctor.get("tasks", [])
            # 统计未审核任务数量（status=0）
            task_count = sum(1 for task in tasks if task.get("status") == 0)
            
            doctor_copy = doctor.copy()
            doctor_copy["task_count"] = task_count
            result.append(doctor_copy)
        
        return result
    
    def get_hospitals(self) -> list[dict]:
        """
        获取所有医院列表
        
        Returns:
            医院列表
        """
        if not self.base_url:
            logger.error("审核平台 base_url 未配置")
            return []
        
        url = f"{self.base_url}/openapi/hospital/list"
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Token"] = self.api_key
        
        try:
            response = requests.post(url, headers=headers, json={}, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                hospitals = result.get("data", [])
                logger.info(f"从审核平台API获取到 {len(hospitals)} 个医院")
                return hospitals
            else:
                logger.error(f"审核平台API返回失败: {result.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"调用审核平台API失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取医院列表失败: {e}")
            return []

