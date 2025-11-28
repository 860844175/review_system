# -*- coding: utf-8 -*-
"""
诊断系统客户端 - 支持fixture和live两种模式
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import os
import json
try:
    import requests  # 预留 live 用
except ImportError:
    requests = None

class DiagnosisSystemClient:
    """诊断系统客户端基类"""
    
    def get_scenario(self, scenario_id: str) -> dict:
        raise NotImplementedError
    
    def get_scenario_bundle(self, scenario_id: str, include_reviews: bool = True) -> dict:
        raise NotImplementedError
    
    def get_user_ehr(self, user_id: str, fields: Optional[list[str]] = None) -> dict:
        raise NotImplementedError
    
    def get_user_signals(self, user_id: str, **kwargs) -> dict:
        raise NotImplementedError
    
    def get_user_scenarios(self, user_id: str, **kwargs) -> dict:
        """获取用户的场景列表"""
        raise NotImplementedError


def _read_json(path: Path) -> dict:
    """读取JSON文件，兼容BOM和错误处理"""
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    try:
        # 兼容 BOM (utf-8-sig)
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")


class FixtureDiagnosisSystemClient(DiagnosisSystemClient):
    """
    测试模式：从本地JSON文件读取
    
    支持两种数据组织方式：
    1. 基于scenario_id的目录结构（新方式，推荐）
       - 目录名 = scenario_id
       - 例如：data/diagnosis_system_fixtures/S29VChQyexr7a6GkxETbmq/
    
    2. 基于fixture_dir的目录结构（旧方式，向后兼容）
       - 目录名 = "emergent" 或 "nonurgent"
       - 例如：data/diagnosis_system_fixtures/emergent/
    """
    
    def __init__(
        self, 
        scenario_id: Optional[str] = None,
        fixture_dir: Optional[str] = None
    ):
        """
        初始化Fixture客户端
        
        Args:
            scenario_id: 场景ID（新方式），如果提供则优先使用基于scenario_id的目录
            fixture_dir: 固定目录名（旧方式，向后兼容），"emergent" 或 "nonurgent"
        
        如果同时提供scenario_id和fixture_dir，优先使用scenario_id方式。
        """
        fixtures_base = Path("data/diagnosis_system_fixtures")
        
        # 优先尝试基于scenario_id的目录（新方式）
        if scenario_id:
            scenario_based_dir = fixtures_base / scenario_id
            if scenario_based_dir.exists():
                self.fixture_base = scenario_based_dir
                self._init_mode = "scenario_id"
                return
        
        # 回退到基于fixture_dir的目录（旧方式，向后兼容）
        if fixture_dir:
            legacy_dir = fixtures_base / fixture_dir
            if legacy_dir.exists():
                self.fixture_base = legacy_dir
                self._init_mode = "fixture_dir"
                return
        
        # 如果都不存在，尝试默认值
        default_dir = fixtures_base / "emergent"
        if default_dir.exists():
            self.fixture_base = default_dir
            self._init_mode = "legacy_default"
            return
        
        # 都找不到，报错
        raise FileNotFoundError(
            f"Fixture directory not found. Tried:\n"
            f"  - scenario_id based: {fixtures_base / scenario_id if scenario_id else 'N/A'}\n"
            f"  - fixture_dir based: {fixtures_base / fixture_dir if fixture_dir else 'N/A'}\n"
            f"  - default: {default_dir}"
        )
    
    def get_scenario(self, scenario_id: str) -> dict:
        """获取场景信息"""
        return _read_json(self.fixture_base / "scenarios_get.json")
    
    def get_scenario_bundle(self, scenario_id: str, include_reviews: bool = True) -> dict:
        """获取场景聚合数据"""
        return _read_json(self.fixture_base / "scenarios_bundle.json")
    
    def get_user_ehr(self, user_id: str, fields: Optional[list[str]] = None) -> dict:
        """获取用户EHR数据"""
        return _read_json(self.fixture_base / "users_ehr.json")
    
    def get_user_signals(self, user_id: str, **kwargs) -> dict:
        """
        获取用户信号列表（fixture模式）
        
        注意：fixture模式下，时间参数会被忽略，直接返回整个文件
        但在实际使用中，应该根据bundle中的links来筛选相关的signal
        """
        return _read_json(self.fixture_base / "users_signals.json")
    
    def get_user_scenarios(self, user_id: str, **kwargs) -> dict:
        """获取用户场景列表"""
        return _read_json(self.fixture_base / "users_scenarios.json")


class LiveDiagnosisSystemClient(DiagnosisSystemClient):
    """生产模式：从真实API读取"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def _post(self, path: str, payload: dict) -> dict:
        """统一POST请求方法"""
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self.headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()
    
    def get_scenario(self, scenario_id: str) -> dict:
        """获取场景详情"""
        payload = {"scenario_id": scenario_id}
        return self._post("/scenarios/get", payload)
    
    def get_scenario_bundle(self, scenario_id: str, include_reviews: bool = True) -> dict:
        """获取场景聚合"""
        payload = {
            "scenario_id": scenario_id,
            "include_reviews": include_reviews
        }
        return self._post("/scenarios/bundle", payload)
    
    def get_user_ehr(self, user_id: str, fields: Optional[list[str]] = None) -> dict:
        """获取用户EHR"""
        payload = {"user_id": user_id}
        if fields:
            payload["fields"] = fields
        return self._post("/users/ehr", payload)
    
    def get_user_signals(self, user_id: str, **kwargs) -> dict:
        """
        获取用户信号列表
        
        Args:
            user_id: 用户ID
            **kwargs: 可选参数
                - start: 开始时间（ISO-8601格式）
                - end: 结束时间（ISO-8601格式）
                - window_kind: 窗口类型数组
                - order: 排序方式（asc/desc）
                - limit: 限制数量
        """
        payload = {"user_id": user_id}
        
        # 添加可选参数
        if "start" in kwargs:
            payload["start"] = kwargs["start"]
        if "end" in kwargs:
            payload["end"] = kwargs["end"]
        if "window_kind" in kwargs:
            payload["window_kind"] = kwargs["window_kind"]
        if "order" in kwargs:
            payload["order"] = kwargs["order"]
        if "limit" in kwargs:
            payload["limit"] = kwargs["limit"]
        
        return self._post("/users/signals", payload)
    
    def get_user_scenarios(self, user_id: str, **kwargs) -> dict:
        """
        获取用户的场景列表
        
        Args:
            user_id: 用户ID
            **kwargs: 可选参数
                - status: 状态（open/completed/all）
                - scenario_type: 场景类型
                - start: 开始时间（ISO-8601格式）
                - end: 结束时间（ISO-8601格式）
                - order: 排序方式（asc/desc）
                - limit: 限制数量
        """
        payload = {"user_id": user_id}
        
        # 添加可选参数
        if "status" in kwargs:
            payload["status"] = kwargs["status"]
        if "scenario_type" in kwargs:
            payload["scenario_type"] = kwargs["scenario_type"]
        if "start" in kwargs:
            payload["start"] = kwargs["start"]
        if "end" in kwargs:
            payload["end"] = kwargs["end"]
        if "order" in kwargs:
            payload["order"] = kwargs["order"]
        if "limit" in kwargs:
            payload["limit"] = kwargs["limit"]
        
        return self._post("/users/scenarios", payload)

