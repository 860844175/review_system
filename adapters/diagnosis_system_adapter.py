# -*- coding: utf-8 -*-
"""
诊断系统适配器 - 将对方JSON转换为本地view model
"""

from __future__ import annotations

from typing import Optional
import logging

logger = logging.getLogger(__name__)

def _dig(d: dict, path: list[str], default=None):
    """
    深度访问嵌套字典，避免 KeyError
    Args:
        d: 字典对象
        path: 路径列表，如 ["bundle", "data", "triage"]
        default: 默认值
    Returns:
        找到的值或默认值
    """
    if not isinstance(d, dict):
        return default
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is None:
            return default
    return cur


def build_view_model(scenario: dict, bundle: dict, ehr: dict, signals: dict) -> dict:
    """
    构建前端用的view model
    
    Args:
        scenario: scenarios/get 返回的数据
        bundle: scenarios/bundle 返回的数据
        ehr: users/ehr 返回的数据
        signals: users/signals 返回的数据
    
    Returns:
        view model字典，包含scenario/triage/patient/signals/suggestions/resources
    """
    try:
        # 1. 提取scenario基本信息
        scenario_info = {
            "scenario_id": scenario.get("scenario_id", ""),
            "user_id": scenario.get("user_id", "")
        }
        
        # 2. 提取triage信息（宽松匹配多种路径）
        triage_data = (
            _dig(bundle, ["bundle", "data", "triage"], {}) or
            _dig(bundle, ["bundle", "triage"], {}) or
            _dig(bundle, ["data", "triage"], {}) or
            bundle.get("triage", {})
        )
        
        # triage_output 可能是 output_json 字段，也可能直接就是输出
        if isinstance(triage_data, dict):
            triage_output = triage_data.get("output_json", triage_data)
        else:
            triage_output = {}
        
        urgency_level = triage_output.get("urgency_level", "") if isinstance(triage_output, dict) else ""
        next_operation = triage_output.get("next_operation", "") if isinstance(triage_output, dict) else ""
        
        esi_level, path = derive_esi_and_path(urgency_level, next_operation)
        
        triage_info = {
            "urgency_level": urgency_level,
            "next_operation": next_operation,
            "rationale": triage_output.get("rationale", "") if isinstance(triage_output, dict) else "",
            "likely_causes": triage_output.get("likely_causes", []) if isinstance(triage_output, dict) else [],
            "esi_level": esi_level,   # 我方派生字段（仅用于UI）
            "path": path              # 我方派生字段（仅用于UI）
        }
        
        # 3. 提取patient信息（从ehr）
        # 兼容两种格式：
        # 1. 新格式：{user_id, schema_version, ehr: {demographics, meds, ...}, ...}
        # 2. 旧格式：{demographics, meds, baseline_vitals, ...}
        ehr_data = ehr.get("ehr", ehr) if isinstance(ehr, dict) else {}
        
        demographics = ehr_data.get("demographics", {}) or {}
        
        # meds 可能是数组（旧格式）或对象（新格式，包含药物清单等）
        meds = ehr_data.get("meds", []) or []
        if isinstance(meds, dict):
            # 新格式：提取药物清单
            meds = meds.get("药物清单", [])
        
        baseline_vitals = ehr_data.get("baseline_vitals", {}) or {}
        
        # 提取medical_history（疾病信息）
        medical_history_list = ehr_data.get("medical_history", [])
        diagnoses = []
        if medical_history_list and isinstance(medical_history_list, list):
            for item in medical_history_list:
                if isinstance(item, dict):
                    disease = item.get("疾病", "")
                    duration = item.get("病程原文", "")
                    if disease:
                        if duration:
                            diagnoses.append(f"{disease}（{duration}）")
                        else:
                            diagnoses.append(disease)
        
        # 提取allergy_history（过敏信息）
        allergy_history = ehr_data.get("allergy_history", {}) or {}
        
        patient_info = {
            "demographics": demographics,
            "meds": meds,
            "baseline_vitals": baseline_vitals,
            "medical_history": {
                "diagnoses": diagnoses,
                "diagnoses_str": "、".join(diagnoses) if diagnoses else "无"
            },
            "allergy_history": allergy_history
        }
        
        # 4. 提取signals信息（兼容两种形态）
        signals_list = signals.get("data") or signals.get("signals") or []
        
        # 从第一个 signal 中提取 metrics_json
        metrics = {}
        if signals_list and isinstance(signals_list[0], dict):
            first_signal = signals_list[0]
            # 路径：signals.data[0].metrics_json.output_json.metrics_json
            metrics = (
                _dig(first_signal, ["metrics_json", "output_json", "metrics_json"], {}) or
                first_signal.get("metrics", {}) or
                {}
            )
        
        signals_info = {
            "summary_text": (
                signals_list[0].get("summary_text", "") 
                if signals_list and isinstance(signals_list[0], dict) 
                else ""
            ) or "",
            "metrics": metrics,
            "signals_list": signals_list  # 保存完整列表，用于后续提取
        }
        
        # 5. 提取suggestions（宽松匹配多种路径）
        suggestions_data = (
            _dig(bundle, ["bundle", "data", "suggestions"], {}) or
            _dig(bundle, ["bundle", "suggestions"], {}) or
            _dig(bundle, ["data", "suggestions"], {}) or
            bundle.get("suggestions", {}) or
            {}
        )
        
        suggestions_info = {
            "patient": suggestions_data.get("patient", []) or [],
            "doctor": suggestions_data.get("doctor", []) or []
        }
        
        # 6. 提取resources（从suggestions文字中提取）
        resources = extract_resources_from_text(suggestions_info.get("doctor", []))
        
        return {
            "scenario": scenario_info,
            "triage": triage_info,
            "patient": patient_info,
            "signals": signals_info,
            "suggestions": suggestions_info,
            "resources": resources
        }
    except Exception as e:
        logger.error(f"构建view model失败: {e}", exc_info=True)
        # 返回默认结构而不是抛异常，保证系统可用性
        return {
            "scenario": {"scenario_id": "", "user_id": ""},
            "triage": {"urgency_level": "", "next_operation": "", "rationale": "", "likely_causes": [], "esi_level": 5, "path": "home"},
            "patient": {"demographics": {}, "meds": [], "baseline_vitals": {}},
            "signals": {"summary_text": "", "metrics": {}},
            "suggestions": {"patient": [], "doctor": []},
            "resources": []
        }


def derive_esi_and_path(urgency_level: Optional[str], _next_operation: Optional[str] = None) -> tuple[Optional[int], str]:
    """
    严格按 triage.urgency_level 映射：
      - 紧急 / urgent / emergent / 急诊 → ESI=3, path="immediate"
      - 关注 / 可关注 / 关注级 → ESI=4, path="home"
      - 非紧急 / 稳定 / non-urgent / nonurgent → ESI=5, path="home"
    未识别值 → (None, "home")
    """
    text = (urgency_level or "").strip().lower()
    
    # 归一化（去空格与连字符）
    norm = text.replace(" ", "").replace("-", "")
    
    # 高优先：先匹配"非紧急"与 non-urgent，以免误判成"紧急"
    if norm in ("非紧急", "稳定", "nonurgent"):
        return 5, "home"
    
    # 关注级（介于非紧急与紧急之间）
    if norm in ("关注", "可关注", "关注级"):
        return 4, "home"
    
    # 紧急
    if norm in ("紧急", "急诊", "urgent", "emergent"):
        return 3, "immediate"
    
    # 兜底：仍然按保守策略走居家路径，不给 ESI
    return None, "home"


def extract_resources_from_text(suggestions_doctor: list) -> list[dict]:
    """
    从医生建议文字中提取资源列表（如"心电图"、"超声"等）
    
    Args:
        suggestions_doctor: doctor suggestions列表
    
    Returns:
        资源列表，格式：[{"id": "...", "name": "...", "evidence": "..."}]
    """
    # 简单关键词映射（可根据实际需求扩展）
    resource_keywords = {
        "心电图": {"id": "DX-ECG-001", "name": "12导联心电图"},
        "超声": {"id": "DX-US-001", "name": "超声检查"},
        "血压监测": {"id": "DX-BP-001", "name": "动态血压监测"},
        "肌钙蛋白": {"id": "DX-TROP-001", "name": "肌钙蛋白检查"},
        "心脏彩超": {"id": "DX-ECHO-001", "name": "心脏彩超"},
    }
    
    resources = []
    seen_ids = set()
    
    def extract_text_from_output_json(output_json) -> str:
        """
        从output_json中提取文字，兼容多种格式：
        1. 字符串格式（旧格式）
        2. 数组格式，包含 {category, advice: []} 结构（新格式）
        """
        if not output_json:
            return ""
        
        # 如果是字符串，直接返回
        if isinstance(output_json, str):
            return output_json
        
        # 如果是数组，提取所有advice文字
        if isinstance(output_json, list):
            texts = []
            for item in output_json:
                if isinstance(item, dict):
                    # 新格式：{category: "...", advice: ["...", "..."]}
                    advice_list = item.get("advice", [])
                    if isinstance(advice_list, list):
                        texts.extend(advice_list)
                    elif isinstance(advice_list, str):
                        texts.append(advice_list)
                elif isinstance(item, str):
                    texts.append(item)
            return " ".join(texts)
        
        # 其他格式，转为字符串
        return str(output_json)
    
    for item in suggestions_doctor or []:
        # 从output_json中提取文字（兼容数组/字符串）
        output_json = item.get("output_json", "")
        text = extract_text_from_output_json(output_json).lower()
        
        for keyword, resource_info in resource_keywords.items():
            if keyword in text and resource_info["id"] not in seen_ids:
                resources.append({
                    "id": resource_info["id"],
                    "name": resource_info["name"],
                    "evidence": f"建议中出现'{keyword}'"
                })
                seen_ids.add(resource_info["id"])
    
    return resources

