# -*- coding: utf-8 -*-
"""
诊断系统工具函数 - 时间计算和数据拉取
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dateutil import parser as date_parser


# 默认回看天数（超参数）
DEFAULT_LOOKBACK_DAYS = 30


def calculate_signal_time_range(conv_start_ts: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> Tuple[str, str]:
    """
    从conv_start_ts计算信号查询的时间范围
    
    Args:
        conv_start_ts: 对话开始时间，ISO-8601格式（如 "2025-11-03T08:31:01.081201-05:00"）
        lookback_days: 往前回看的天数，默认30天
    
    Returns:
        (start_iso, end_iso): 时间范围的开始和结束，ISO-8601格式（UTC，Z结尾）
        例如: ("2025-10-04T00:00:00Z", "2025-11-03T23:59:59Z")
    """
    try:
        # 解析ISO-8601时间字符串（支持UTC和时区偏移）
        conv_datetime = date_parser.parse(conv_start_ts)
        
        # 如果时间没有时区信息，假设为UTC
        if conv_datetime.tzinfo is None:
            conv_datetime = conv_datetime.replace(tzinfo=timezone.utc)
        
        # 提取日期部分（忽略时间）
        conv_date = conv_datetime.date()
        
        # 计算end：该日期的23:59:59（UTC）
        end_datetime = datetime.combine(conv_date, datetime.max.time().replace(microsecond=0))
        # 转换为UTC时区
        if end_datetime.tzinfo is None:
            end_datetime = end_datetime.replace(tzinfo=timezone.utc)
        else:
            # 如果原时间有时区，先转换到UTC
            end_datetime = conv_datetime.replace(hour=23, minute=59, second=59, microsecond=0)
            end_datetime = end_datetime.astimezone(timezone.utc)
        
        # 计算start：往前推lookback_days天的00:00:00（UTC）
        start_date = conv_date - timedelta(days=lookback_days)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        # 转换为UTC时区
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        else:
            start_datetime = start_datetime.astimezone(timezone.utc)
        
        # 格式化为ISO-8601格式（UTC，Z结尾）
        start_iso = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return start_iso, end_iso
        
    except Exception as e:
        raise ValueError(f"时间计算失败: {e}, conv_start_ts={conv_start_ts}")


def extract_conv_start_ts(bundle: dict) -> Optional[str]:
    """
    从bundle中提取conv_start_ts
    
    Args:
        bundle: scenarios/bundle返回的数据
    
    Returns:
        conv_start_ts字符串，如果找不到则返回None
    """
    # 尝试多种路径
    scenario = bundle.get("scenario", {})
    if isinstance(scenario, dict):
        conv_start_ts = scenario.get("conv_start_ts")
        if conv_start_ts:
            return conv_start_ts
    
    # 如果bundle直接包含scenario字段
    if "conv_start_ts" in bundle:
        return bundle["conv_start_ts"]
    
    return None


