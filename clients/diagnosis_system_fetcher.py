# -*- coding: utf-8 -*-
"""
诊断系统数据拉取器 - 封装完整的数据拉取流程
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import logging

from .diagnosis_system_client import DiagnosisSystemClient
from .diagnosis_system_utils import (
    calculate_signal_time_range,
    extract_conv_start_ts,
    DEFAULT_LOOKBACK_DAYS
)

logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    """数据拉取错误"""
    pass


def fetch_diagnosis_data(
    client: DiagnosisSystemClient,
    user_id: str,
    scenario_id: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    validate: bool = True
) -> Dict[str, Any]:
    """
    从zhikai系统拉取完整的数据（ehr, bundle, signals）
    
    Args:
        client: 诊断系统客户端（FixtureDiagnosisSystemClient 或 LiveDiagnosisSystemClient）
        user_id: 用户ID
        scenario_id: 场景ID
        lookback_days: 往前回看的天数，默认30天
        validate: 是否验证数据完整性，默认True
    
    Returns:
        包含以下字段的字典：
        - ehr: 用户EHR数据
        - bundle: 场景聚合数据
        - signals: 信号数据
        - scenario: 场景基本信息（从bundle中提取）
        - time_range: 时间范围信息 {"start": "...", "end": "..."}
    
    Raises:
        DataFetchError: 数据拉取失败时抛出
    """
    try:
        # 1. 拉取EHR
        logger.info(f"📥 拉取EHR数据: user_id={user_id}")
        ehr = client.get_user_ehr(user_id)
        if not ehr:
            raise DataFetchError(f"EHR数据为空: user_id={user_id}")
        logger.info(f"✅ EHR数据拉取成功")
        
        # 2. 拉取场景聚合（bundle）
        logger.info(f"📥 拉取场景聚合: scenario_id={scenario_id}")
        bundle = client.get_scenario_bundle(scenario_id, include_reviews=True, include_signals=True)
        if not bundle:
            raise DataFetchError(f"场景聚合数据为空: scenario_id={scenario_id}")
        logger.info(f"✅ 场景聚合数据拉取成功")
        
        # 3. 从bundle中提取conv_start_ts并计算时间范围
        conv_start_ts = extract_conv_start_ts(bundle)
        if not conv_start_ts:
            raise DataFetchError(f"无法从bundle中提取conv_start_ts: scenario_id={scenario_id}")
        
        logger.info(f"📅 计算时间范围: conv_start_ts={conv_start_ts}, lookback_days={lookback_days}")
        start_iso, end_iso = calculate_signal_time_range(conv_start_ts, lookback_days)
        logger.info(f"✅ 时间范围计算完成: {start_iso} ~ {end_iso}")
        
        # 4. 拉取signals（带时间范围）
        logger.info(f"📥 拉取信号数据: user_id={user_id}, start={start_iso}, end={end_iso}")
        signals = client.get_user_signals(
            user_id=user_id,
            start=start_iso,
            end=end_iso,
            order="desc",  # 降序，最新的在前
            limit=500  # 最大限制
        )
        if not signals:
            raise DataFetchError(f"信号数据为空: user_id={user_id}")
        logger.info(f"✅ 信号数据拉取成功")
        
        # 5. 验证数据完整性（可选）
        if validate:
            _validate_data(ehr, bundle, signals, user_id, scenario_id)
        
        # 6. 提取scenario基本信息（从bundle中）
        scenario = bundle.get("scenario", {})
        
        return {
            "ehr": ehr,
            "bundle": bundle,
            "signals": signals,
            "scenario": scenario,
            "time_range": {
                "start": start_iso,
                "end": end_iso,
                "conv_start_ts": conv_start_ts
            }
        }
        
    except DataFetchError:
        raise
    except Exception as e:
        logger.error(f"❌ 数据拉取失败: {e}", exc_info=True)
        raise DataFetchError(f"数据拉取失败: {str(e)}") from e


def _validate_data(ehr: dict, bundle: dict, signals: dict, user_id: str, scenario_id: str):
    """
    验证数据完整性
    
    Raises:
        DataFetchError: 数据验证失败时抛出
    """
    # 验证EHR
    if not isinstance(ehr, dict):
        raise DataFetchError(f"EHR数据格式错误: 期望dict，实际{type(ehr)}")
    
    # 验证bundle
    if not isinstance(bundle, dict):
        raise DataFetchError(f"Bundle数据格式错误: 期望dict，实际{type(bundle)}")
    
    bundle_scenario = bundle.get("scenario", {})
    if not isinstance(bundle_scenario, dict):
        raise DataFetchError(f"Bundle中缺少scenario字段")
    
    # 验证scenario_id匹配
    if bundle_scenario.get("scenario_id") != scenario_id:
        raise DataFetchError(
            f"scenario_id不匹配: 期望{scenario_id}, "
            f"实际{bundle_scenario.get('scenario_id')}"
        )
    
    # 验证user_id匹配
    if bundle_scenario.get("user_id") != user_id:
        raise DataFetchError(
            f"user_id不匹配: 期望{user_id}, "
            f"实际{bundle_scenario.get('user_id')}"
        )
    
    # 验证signals
    if not isinstance(signals, dict):
        raise DataFetchError(f"Signals数据格式错误: 期望dict，实际{type(signals)}")
    
    signals_data = signals.get("data", [])
    if not isinstance(signals_data, list):
        raise DataFetchError(f"Signals中缺少data字段或格式错误")
    
    logger.info(f"✅ 数据验证通过: user_id={user_id}, scenario_id={scenario_id}, signals_count={len(signals_data)}")


