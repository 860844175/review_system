# -*- coding: utf-8 -*-
"""
任务仓库 - 管理task_id与diagnosis数据的映射关系
"""

from __future__ import annotations

import json
import secrets
import string
from pathlib import Path
from typing import Optional
from datetime import datetime

# 任务映射文件路径
TASKS_MAP_FILE = Path("data/tasks_map.json")


def _load_tasks_map() -> list[dict]:
    """加载任务映射表"""
    if not TASKS_MAP_FILE.exists():
        return []
    try:
        with open(TASKS_MAP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ 加载tasks_map.json失败: {e}")
        return []


def _save_tasks_map(tasks: list[dict]) -> bool:
    """保存任务映射表"""
    try:
        TASKS_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_MAP_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"⚠️ 保存tasks_map.json失败: {e}")
        return False


def get_task_by_id(task_id: str) -> Optional[dict]:
    """
    根据task_id获取任务信息
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务字典，包含 user_id, scenario_id, fixture 等
        如果不存在则返回 None
    """
    tasks = _load_tasks_map()
    for task in tasks:
        if task.get("task_id") == task_id:
            return task
    return None


def _generate_task_id(length: int = 22) -> str:
    """
    生成随机task_id，格式类似API文档中的ID（22个字符，大小写字母+数字）
    
    Args:
        length: ID长度，默认22
    
    Returns:
        随机生成的task_id
    """
    # 使用大小写字母和数字生成随机字符串
    alphabet = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_task(
    user_id: str,
    scenario_id: str,
    fixture: str = "nonurgent",
    source: str = "fixture",
    task_id_length: int = 22
) -> str:
    """
    创建新任务并返回task_id
    
    Args:
        user_id: 用户ID
        scenario_id: 场景ID
        fixture: fixture类型（"emergent" 或 "nonurgent"）
        source: 数据来源（"fixture" 或 "live"），默认 "fixture"
        task_id_length: task_id长度，默认22（与API文档中的ID格式一致）
    
    Returns:
        生成的task_id（格式类似：YZerVgaQTCuSHtEkZyguV5）
    """
    # 生成随机task_id（类似API文档格式：22个字符，大小写字母+数字）
    task_id = _generate_task_id(task_id_length)
    
    # 创建任务记录
    task_record = {
        "task_id": task_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "fixture": fixture,
        "source": source,  # 数据来源：fixture 或 live
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "pending",  # 任务状态: pending(待分配) -> assigned(已分配) -> completed(已完成)
        "doctor_id": None,  # 分配的医生ID
        "assigned_at": None,  # 分配时间
        "completed_at": None  # 完成时间
    }
    
    # 加载现有任务列表
    tasks = _load_tasks_map()
    
    # 检查task_id是否已存在（理论上不应该，但做防护）
    existing = get_task_by_id(task_id)
    if existing:
        print(f"⚠️ task_id {task_id} 已存在，重新生成...")
        return create_task(user_id, scenario_id, fixture, source, task_id_length)
    
    # 追加新任务
    tasks.append(task_record)
    
    # 保存
    if _save_tasks_map(tasks):
        print(f"✅ 任务创建成功: {task_id}")
        return task_id
    else:
        raise RuntimeError(f"保存任务失败: {task_id}")


def find_task_by_ids(
    user_id: str,
    scenario_id: str
) -> Optional[dict]:
    """
    根据user_id和scenario_id查找任务
    
    Args:
        user_id: 用户ID
        scenario_id: 场景ID
    
    Returns:
        任务字典，如果不存在则返回 None
    """
    tasks = _load_tasks_map()
    for task in tasks:
        if (task.get("user_id") == user_id and
            task.get("scenario_id") == scenario_id):
            return task
    return None


def find_pending_task_by_ids(
    user_id: str,
    scenario_id: str
) -> Optional[dict]:
    """
    根据user_id和scenario_id查找待处理任务（状态为pending或None）
    
    Args:
        user_id: 用户ID
        scenario_id: 场景ID
    
    Returns:
        待处理任务字典，如果不存在则返回 None
    """
    tasks = _load_tasks_map()
    for task in tasks:
        if (task.get("user_id") == user_id and
            task.get("scenario_id") == scenario_id):
            status = task.get("status")
            # 如果状态是pending或None（旧数据可能没有status字段），认为是pending
            if status is None or status == "pending":
                return task
    return None


def list_all_tasks() -> list[dict]:
    """
    获取所有任务列表
    
    Returns:
        任务列表
    """
    return _load_tasks_map()


def update_task(task_id: str, **fields) -> Optional[dict]:
    """
    更新任务字段
    
    Args:
        task_id: 任务ID
        **fields: 要更新的字段（如 status, completed_at 等）
    
    Returns:
        更新后的任务字典，如果任务不存在则返回 None
    """
    tasks = _load_tasks_map()
    
    # 查找任务
    task_index = None
    for i, task in enumerate(tasks):
        if task.get("task_id") == task_id:
            task_index = i
            break
    
    if task_index is None:
        return None
    
    # 更新字段
    tasks[task_index].update(fields)
    
    # 保存
    if _save_tasks_map(tasks):
        print(f"✅ 任务更新成功: {task_id}")
        return tasks[task_index]
    else:
        raise RuntimeError(f"保存任务更新失败: {task_id}")


def cleanup_duplicate_tasks() -> dict:
    """
    清理重复任务：对于相同的user_id + scenario_id组合，
    保留最新的pending任务（如果存在），否则保留最新的completed任务，删除其他重复任务
    
    Returns:
        清理统计信息：{"removed": 数量, "kept": 数量}
    """
    tasks = _load_tasks_map()
    
    # 按 (user_id, scenario_id) 分组
    task_groups = {}
    for task in tasks:
        key = (task.get("user_id"), task.get("scenario_id"))
        if key not in task_groups:
            task_groups[key] = []
        task_groups[key].append(task)
    
    # 找出需要保留的任务
    tasks_to_keep = []
    removed_count = 0
    
    for key, group_tasks in task_groups.items():
        if len(group_tasks) == 1:
            # 只有一个任务，直接保留
            tasks_to_keep.append(group_tasks[0])
        else:
            # 多个任务，需要选择保留哪个
            # 优先保留pending任务，按创建时间倒序
            pending_tasks = [t for t in group_tasks if t.get("status") in (None, "pending")]
            completed_tasks = [t for t in group_tasks if t.get("status") == "completed"]
            
            if pending_tasks:
                # 有pending任务，保留最新的pending任务
                pending_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                tasks_to_keep.append(pending_tasks[0])
                removed_count += len(pending_tasks) - 1
                removed_count += len(completed_tasks)
            elif completed_tasks:
                # 只有completed任务，保留最新的completed任务
                completed_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                tasks_to_keep.append(completed_tasks[0])
                removed_count += len(completed_tasks) - 1
            else:
                # 其他情况，保留最新的
                group_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                tasks_to_keep.append(group_tasks[0])
                removed_count += len(group_tasks) - 1
    
    # 保存清理后的任务列表
    if _save_tasks_map(tasks_to_keep):
        print(f"✅ 清理重复任务完成: 保留 {len(tasks_to_keep)} 个任务，删除 {removed_count} 个重复任务")
        return {"removed": removed_count, "kept": len(tasks_to_keep)}
    else:
        raise RuntimeError("保存清理后的任务列表失败")

