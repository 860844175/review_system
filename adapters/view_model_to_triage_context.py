# -*- coding: utf-8 -*-
"""
View Model 到 Triage Context 适配器
将诊断系统的 view_model 转换为 TriageHTMLGenerator 需要的 context 格式
"""

from __future__ import annotations

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def convert_view_model_to_triage_context(
    view_model: Dict[str, Any],
    user_id: str,
    scenario_id: str,
    language: str = 'zh',
    bundle: Dict[str, Any] = None,
    ehr: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    将 view_model 转换为 TriageHTMLGenerator 需要的 context 格式
    
    Args:
        view_model: build_view_model 返回的 view model
        user_id: 用户ID
        scenario_id: 场景ID
        language: 语言代码，'zh' 或 'en'
    
    Returns:
        TriageHTMLGenerator 需要的 context 字典
    """
    try:
        patient = view_model.get("patient", {})
        triage = view_model.get("triage", {})
        signals_info = view_model.get("signals", {})
        suggestions = view_model.get("suggestions", {})
        resources = view_model.get("resources", [])
        
        # 提取患者信息
        demographics = patient.get("demographics", {})
        baseline_vitals = patient.get("baseline_vitals", {})
        meds = patient.get("meds", [])
        
        # 构建 patient_info
        patient_info = {
            "age": demographics.get("年龄"),
            "sex": demographics.get("性别", ""),
            "chief_complaint": _extract_chief_complaint(view_model, bundle, language)
        }
        
        # 构建 vital_signs
        # 优先从 signals 中提取实时生命体征，如果没有则使用 baseline_vitals
        vital_signs = _extract_vital_signs(signals_info, baseline_vitals, triage)
        
        # 构建 medical_history（从 ehr 中提取完整信息）
        medical_history = _extract_medical_history(ehr, meds, language)
        
        # 判断决策路径
        # 根据 next_operation 和 path 判断
        next_operation = triage.get("next_operation", "")
        path = triage.get("path", "home")
        
        # 如果 next_operation 包含"就医"、"医院"等关键词，或 path 是 "immediate"，则建议立即就医
        go_to_hospital_chose = "yes" if (
            "就医" in next_operation or 
            "医院" in next_operation or 
            path == "immediate" or
            triage.get("esi_level") in [1, 2, 3]  # ESI 1-3 通常需要立即就医
        ) else "no"
        
        go_to_hospital = {
            "chose": go_to_hospital_chose,
            "evidence": triage.get("rationale", "")
        }
        
        decision_path = "immediate_care" if go_to_hospital_chose == "yes" else "home_observation"
        
        # 提取系统推荐资源
        system_resources = [r.get("id") for r in resources if r.get("id")]
        
        # 构建对话记录总结（从 bundle 的 questions 和 symptoms 提取）
        pre_triage_summary = _extract_pre_triage_summary(bundle, signals_info, triage, language)
        
        # 提取对话消息列表（用于聊天界面展示）
        dialogue_messages = _extract_dialogue_messages(bundle, language)
        
        # 提取异常标签（从 signals 的 anomalies）
        anomaly_tags = _extract_anomaly_tags(signals_info)
        
        # 提取并分组建议（按category分组）
        patient_suggestions = _extract_suggestions_by_category(suggestions.get("patient", []))
        doctor_suggestions = _extract_suggestions_by_category(suggestions.get("doctor", []))
        
        # 提取时间序列数据（用于Section 3图表）
        signals_timeseries_data = _extract_signals_timeseries(signals_info)
        anomaly_periods = _extract_anomaly_periods(signals_info)
        
        # 提取触发上下文
        trigger_context = _extract_trigger_context(bundle, signals_info)

        # 构建 context
        context = {
            "trigger_context": trigger_context,
            "patient_id": user_id,
            "patient_info": patient_info,
            "vital_signs": vital_signs,
            "medical_history": medical_history,
            "pre_triage_summary": pre_triage_summary,
            "dialogue_messages": dialogue_messages,
            "anomaly_tags": anomaly_tags,
            "go_to_hospital": go_to_hospital,
            "decision_path": decision_path,
            "urgency_level": triage.get("urgency_level", ""),
            "next_operation": triage.get("next_operation", ""),
            "rationale": triage.get("rationale", ""),
            "likely_causes": triage.get("likely_causes", []),
            "patient_suggestions": patient_suggestions,
            "doctor_suggestions": doctor_suggestions,
            "signals_timeseries_data": signals_timeseries_data,
            "anomaly_periods": anomaly_periods,
            "system_resources": system_resources,
            "resource_details": [
                {"id": r.get("id"), "name": r.get("name", "")}
                for r in resources
            ],
            # immediate_care 相关数据
            "max_time_to_doctor": {
                "chose": "30",  # 默认30分钟
                "evidence": triage.get("rationale", "")
            },
            "deterioration_risk": {
                "chose": _map_urgency_to_risk(triage.get("urgency_level", "")),
                "evidence": triage.get("rationale", "")
            },
            "hospital_recommendation": {},  # 医院推荐（暂时为空，后续可以扩展）
            # home_observation 相关数据
            "followup_time": {
                "chose": "24",  # 默认24小时
                "evidence": ""
            },
            "care_measures": {
                "chose": _extract_care_measures(suggestions.get("patient", [])),
                "evidence": ""
            },
            "warning_signs": {
                "chose": [],
                "evidence": ""
            },
            "home_deterioration_risk": {
                "chose": "低",
                "evidence": ""
            }
        }
        
        return context
        
    except Exception as e:
        logger.error(f"转换 view_model 到 triage context 失败: {e}", exc_info=True)
        # 返回最小可用的 context
        return {
            "patient_id": user_id,
            "patient_info": {"age": None, "sex": "", "chief_complaint": ""},
            "vital_signs": {"temperature": None, "heartrate": None, "resprate": None, 
                          "o2sat": None, "sbp": None, "dbp": None, "pain": None, "esi": None},
            "medical_history": {"diagnoses_str": "无", "allergies_str": "无过敏史", 
                               "medications_str": "无", "family_history": "无特殊家族史",
                               "social_history": {"tobacco": "未知", "alcohol": "未知"}},
            "pre_triage_summary": "",
            "go_to_hospital": {"chose": "no", "evidence": ""},
            "decision_path": "home_observation",
            "system_resources": [],
            "resource_details": []
        }


def _extract_vital_signs(signals_info: Dict[str, Any], baseline_vitals: Dict[str, Any], triage: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 signals 和 baseline_vitals 中提取生命体征
    
    使用 bundle.data.signals[0].metrics_json 中的:
    - detection_summary: 触发异常时刻的生理指标（window_length: 600s = 10分钟）
    - overall_summary: 整个事件窗口的生理指标（window_length: 3600s = 1小时）
    
    返回三组数据：触发时刻值、前1小时范围、基线值
    """
    signals_list = signals_info.get("signals_list", [])
    
    # 获取最近一次signal
    latest_signal = signals_list[0] if signals_list and isinstance(signals_list[0], dict) else None
    
    # 提取最近一次测量的时间
    latest_measurement_time = None
    if latest_signal:
        start_ts = latest_signal.get("start_ts", "")
        if start_ts:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                latest_measurement_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                latest_measurement_time = start_ts[:16]
    
    # 从 metrics_json 中提取 detection_summary 和 overall_summary
    detection_summary = {}
    overall_summary = {}
    if latest_signal:
        metrics_json = latest_signal.get("metrics_json", {})
        if isinstance(metrics_json, dict):
            detection_summary = metrics_json.get("detection_summary", {})
            overall_summary = metrics_json.get("overall_summary", {})
    
    # 提取心率
    # 触发时刻值（from detection_summary）
    hr_detection = detection_summary.get("心率", {})
    hr_trigger = hr_detection.get("mean") if isinstance(hr_detection, dict) else None
    
    # 前1小时范围（from overall_summary）
    hr_overall = overall_summary.get("心率", {})
    hr_range_min = hr_overall.get("min") if isinstance(hr_overall, dict) else None
    hr_range_max = hr_overall.get("max") if isinstance(hr_overall, dict) else None
    
    # 基线值
    hr_baseline = baseline_vitals.get("心率")
    
    # 提取血压
    # 触发时刻值
    bp_detection = detection_summary.get("血压", {})
    sbp_detection = bp_detection.get("收缩压", {}) if isinstance(bp_detection, dict) else {}
    dbp_detection = bp_detection.get("舒张压", {}) if isinstance(bp_detection, dict) else {}
    sbp_trigger = sbp_detection.get("mean") if isinstance(sbp_detection, dict) else None
    dbp_trigger = dbp_detection.get("mean") if isinstance(dbp_detection, dict) else None
    
    # 前1小时范围
    bp_overall = overall_summary.get("血压", {})
    sbp_overall = bp_overall.get("收缩压", {}) if isinstance(bp_overall, dict) else {}
    dbp_overall = bp_overall.get("舒张压", {}) if isinstance(bp_overall, dict) else {}
    sbp_range_min = sbp_overall.get("min") if isinstance(sbp_overall, dict) else None
    sbp_range_max = sbp_overall.get("max") if isinstance(sbp_overall, dict) else None
    dbp_range_min = dbp_overall.get("min") if isinstance(dbp_overall, dict) else None
    dbp_range_max = dbp_overall.get("max") if isinstance(dbp_overall, dict) else None
    
    # 基线值
    bp_baseline = baseline_vitals.get("血压", {})
    sbp_baseline = bp_baseline.get("收缩压") if isinstance(bp_baseline, dict) else None
    dbp_baseline = bp_baseline.get("舒张压") if isinstance(bp_baseline, dict) else None
    
    # 提取血氧
    spo2_detection = detection_summary.get("血氧饱和度", {})
    spo2_trigger = spo2_detection.get("mean") if isinstance(spo2_detection, dict) else None
    
    spo2_overall = overall_summary.get("血氧饱和度", {})
    spo2_range_min = spo2_overall.get("min") if isinstance(spo2_overall, dict) else None
    spo2_range_max = spo2_overall.get("max") if isinstance(spo2_overall, dict) else None
    
    # 提取体温（保持℃）
    temp_detection = detection_summary.get("体温", {})
    temp_trigger = temp_detection.get("mean") if isinstance(temp_detection, dict) else None
    
    temp_overall = overall_summary.get("体温", {})
    temp_range_min = temp_overall.get("min") if isinstance(temp_overall, dict) else None
    temp_range_max = temp_overall.get("max") if isinstance(temp_overall, dict) else None
    
    temp_baseline = baseline_vitals.get("体温")
    
    return {
        # 触发时刻值（用于显示"当前值"）
        "heartrate": hr_trigger,
        "sbp": sbp_trigger,
        "dbp": dbp_trigger,
        "o2sat": spo2_trigger,
        "temperature": temp_trigger,
        "resprate": None,
        "pain": None,
        "esi": triage.get("esi_level"),
        "measurement_time": latest_measurement_time,
        
        # 前1小时范围（新增字段）
        "ranges": {
            "heart_rate": {"min": hr_range_min, "max": hr_range_max} if hr_range_min is not None else None,
            "blood_pressure": {
                "systolic": {"min": sbp_range_min, "max": sbp_range_max} if sbp_range_min is not None else None,
                "diastolic": {"min": dbp_range_min, "max": dbp_range_max} if dbp_range_min is not None else None
            },
            "spo2": {"min": spo2_range_min, "max": spo2_range_max} if spo2_range_min is not None else None,
            "temperature": {"min": temp_range_min, "max": temp_range_max} if temp_range_min is not None else None
        },
        
        # 基线值（从 EHR）
        "baselines": {
            "heart_rate": hr_baseline,
            "blood_pressure": {"systolic": sbp_baseline, "diastolic": dbp_baseline},
            "temperature": temp_baseline
        }
    }


def _extract_chief_complaint(view_model: Dict[str, Any], bundle: Dict[str, Any] = None, language: str = 'zh') -> str:
    """
    从 bundle 的 symptoms 中提取主诉（user_feedback）
    
    优先从 bundle.data.symptoms[0].user_feedback 提取
    """
    # 优先从 bundle 的 symptoms 中提取 user_feedback
    if bundle:
        bundle_data = bundle.get("bundle", {}).get("data", {}) or bundle.get("data", {})
        symptoms = bundle_data.get("symptoms", [])
        if symptoms and isinstance(symptoms, list) and len(symptoms) > 0:
            first_symptom = symptoms[0]
            if isinstance(first_symptom, dict):
                user_feedback = first_symptom.get("user_feedback", [])
                if user_feedback and isinstance(user_feedback, list):
                    # 将数组转换为字符串
                    complaint = "、".join([str(item) for item in user_feedback if item])
                    if complaint:
                        return complaint
    
    # 备选：从 triage 的 rationale 中提取（不再使用 signals.summary_text，因为可能包含无关的历史信号）
    triage = view_model.get("triage", {})
    rationale = triage.get("rationale", "")
    if rationale:
        return rationale[:100]
    
    return ""


def _map_urgency_to_risk(urgency_level: str) -> str:
    """
    将 urgency_level 映射到恶化风险等级
    """
    urgency_lower = (urgency_level or "").lower()
    
    if "紧急" in urgency_level or "urgent" in urgency_lower or "emergent" in urgency_lower:
        return "高"
    elif "关注" in urgency_level or "attention" in urgency_lower:
        return "中"
    else:
        return "低"


def _extract_pre_triage_summary(bundle: Dict[str, Any], signals_info: Dict[str, Any], triage: Dict[str, Any], language: str = 'zh') -> str:
    """
    从 bundle 中提取问诊摘要（包含 symptoms 和 questions 的对话记录）
    """
    summary_parts = []
    
    # 1. 从 bundle 提取 symptoms 和 questions
    if bundle:
        bundle_data = bundle.get("bundle", {}).get("data", {}) or bundle.get("data", {})
        
        # 提取 symptoms
        symptoms = bundle_data.get("symptoms", [])
        if symptoms and isinstance(symptoms, list):
            for symptom in symptoms:
                if isinstance(symptom, dict):
                    # 提取 output_json（系统识别的症状）
                    output_json = symptom.get("output_json", [])
                    if output_json and isinstance(output_json, list):
                        symptom_list = [str(s) for s in output_json if s]
                        if symptom_list:
                            summary_parts.append(f"系统识别症状：{', '.join(symptom_list)}")
                    
                    # 提取 user_feedback（患者反馈的症状）
                    user_feedback = symptom.get("user_feedback", [])
                    if user_feedback and isinstance(user_feedback, list):
                        feedback_list = [str(f) for f in user_feedback if f]
                        if feedback_list:
                            summary_parts.append(f"患者主诉：{', '.join(feedback_list)}")
        
        # 提取 questions 的对话记录
        questions = bundle_data.get("questions", [])
        if questions and isinstance(questions, list):
            qa_pairs = []
            for question in questions:
                if isinstance(question, dict):
                    # 提取问题
                    output_json = question.get("output_json", {})
                    if isinstance(output_json, dict):
                        q_list = output_json.get("questions", [])
                        if q_list:
                            for q_item in q_list:
                                if isinstance(q_item, dict):
                                    q_text = q_item.get("question", "")
                                    if q_text:
                                        qa_pairs.append(f"问：{q_text}")
                    
                    # 提取回答
                    user_feedback = question.get("user_feedback", [])
                    if user_feedback and isinstance(user_feedback, list):
                        for feedback_item in user_feedback:
                            if isinstance(feedback_item, dict):
                                answer = feedback_item.get("answer", "")
                                if answer:
                                    qa_pairs.append(f"答：{answer}")
                            elif isinstance(feedback_item, str):
                                qa_pairs.append(f"答：{feedback_item}")
            
            if qa_pairs:
                summary_parts.append("对话记录：\n" + "\n".join(qa_pairs))
    
    # 2. 如果没有从 bundle 提取到内容，使用 signals 的 summary_text
    if not summary_parts:
        signals_summary = signals_info.get("summary_text", "")
        if signals_summary:
            summary_parts.append(signals_summary)
    
    # 3. 如果还是没有，使用 triage 的 rationale
    if not summary_parts:
        rationale = triage.get("rationale", "")
        if rationale:
            summary_parts.append(rationale)
    
    return "\n\n".join(summary_parts) if summary_parts else ("暂无问诊摘要" if language == 'zh' else "No consultation summary available")


def _extract_dialogue_messages(bundle: Dict[str, Any], language: str = 'zh') -> List[Dict[str, Any]]:
    """
    从 bundle 中提取对话消息列表，用于聊天界面展示
    返回格式: [{"type": "ai"|"patient", "content": "...", "time": "HH:MM", "target_path": "...", "question_index": int, "question_id": "..."}, ...]
    """
    messages = []
    
    if not bundle:
        return messages
    
    bundle_data = bundle.get("bundle", {}).get("data", {}) or bundle.get("data", {})
    
    def _format_time(ts: str) -> str:
        """格式化时间戳为 HH:MM 格式"""
        if not ts:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except:
            # 尝试简单截取
            if len(ts) >= 16:
                return ts[11:16]  # 提取 HH:MM
            return ""
    
    # 1. 提取 symptoms（AI的初始询问）
    symptoms = bundle_data.get("symptoms", [])
    if symptoms and isinstance(symptoms, list):
        for symptom_index, symptom in enumerate(symptoms):
            if isinstance(symptom, dict):
                symptom_id = symptom.get("id", "")
                # AI的询问（从 presented_json 提取）
                presented_json = symptom.get("presented_json", {})
                if isinstance(presented_json, dict):
                    ai_content = presented_json.get("content", "")
                    if ai_content:
                        created_at = symptom.get("created_at", "")
                        messages.append({
                            "type": "ai",
                            "content": ai_content,
                            "time": _format_time(created_at),
                            "target_path": f"bundle.data.symptoms[{symptom_index}].presented_json.content",
                            "symptom_id": symptom_id,
                            "symptom_index": symptom_index
                        })
                
                # 患者的反馈（从 user_feedback 提取）
                user_feedback = symptom.get("user_feedback", [])
                if user_feedback and isinstance(user_feedback, list):
                    # 提取文本内容：如果是字典，提取 text 或 symptom_name；如果是字符串，直接使用
                    feedback_texts = []
                    for f in user_feedback:
                        if not f:
                            continue
                        if isinstance(f, dict):
                            # 优先使用 text，如果没有则使用 symptom_name
                            text = f.get("text") or f.get("symptom_name", "")
                            if text:
                                feedback_texts.append(str(text))
                        elif isinstance(f, str):
                            feedback_texts.append(f)
                    
                    patient_content = ", ".join(feedback_texts)
                    if patient_content:
                        created_at = symptom.get("created_at", "")
                        messages.append({
                            "type": "patient",
                            "content": patient_content,
                            "time": _format_time(created_at),
                            "target_path": f"bundle.data.symptoms[{symptom_index}].user_feedback",
                            "symptom_id": symptom_id,
                            "symptom_index": symptom_index
                        })
    
    # 2. 提取 questions（问答对）- 关键：保留turn_index
    questions = bundle_data.get("questions", [])
    if questions and isinstance(questions, list):
        for question_index, question in enumerate(questions):
            if isinstance(question, dict):
                created_at = question.get("created_at", "")
                question_id = question.get("id", "")
                # 获取turn_index（从context中）
                context = question.get("context", {})
                turn_index = context.get("turn_index", question_index)  # 如果没有turn_index，使用数组索引
                
                # AI的问题（从 output_json.questions 提取）
                output_json = question.get("output_json", {})
                if isinstance(output_json, dict):
                    # 提取 reason（AI 决策理由）
                    reason = output_json.get("reason", "")
                    q_list = output_json.get("questions", [])
                    if q_list:
                        for q_item_index, q_item in enumerate(q_list):
                            if isinstance(q_item, dict):
                                q_text = q_item.get("question", "")
                                if q_text:
                                    messages.append({
                                        "type": "ai",
                                        "content": q_text,
                                        "time": _format_time(created_at),
                                        "target_path": f"bundle.data.questions[{turn_index}].output_json.questions[{q_item_index}].question",
                                        "question_id": question_id,
                                        "question_index": question_index,
                                        "turn_index": turn_index,
                                        "q_item_index": q_item_index,
                                        "reason": reason  # AI 决策理由
                                    })
                
                # 患者的回答（从 user_feedback 提取）
                user_feedback = question.get("user_feedback", [])
                if user_feedback and isinstance(user_feedback, list):
                    for feedback_index, feedback_item in enumerate(user_feedback):
                        if isinstance(feedback_item, dict):
                            answer = feedback_item.get("answer", "")
                            if answer:
                                messages.append({
                                    "type": "patient",
                                    "content": answer,
                                    "time": _format_time(created_at),
                                    "target_path": f"bundle.data.questions[{turn_index}].user_feedback[{feedback_index}].answer",
                                    "question_id": question_id,
                                    "question_index": question_index,
                                    "turn_index": turn_index,
                                    "feedback_index": feedback_index
                                })
                        elif isinstance(feedback_item, str) and feedback_item:
                            messages.append({
                                "type": "patient",
                                "content": feedback_item,
                                "time": _format_time(created_at),
                                "target_path": f"bundle.data.questions[{turn_index}].user_feedback[{feedback_index}]",
                                "question_id": question_id,
                                "question_index": question_index,
                                "turn_index": turn_index,
                                "feedback_index": feedback_index
                            })
    
    return messages


def _extract_anomaly_tags(signals_info: Dict[str, Any]) -> List[str]:
    """
    从 signals 中提取异常标签
    signals.data[0].metrics_json.output_json.anomalies 或 state_tags
    """
    anomaly_tags = []
    
    # 从 signals_list 的第一个信号中提取
    signals_list = signals_info.get("signals_list", [])
    if signals_list and isinstance(signals_list[0], dict):
        first_signal = signals_list[0]
        metrics_json = first_signal.get("metrics_json", {})
        if isinstance(metrics_json, dict):
            output_json = metrics_json.get("output_json", {})
            if isinstance(output_json, dict):
                # 提取 anomalies（中文描述）
                anomalies = output_json.get("anomalies", [])
                if anomalies and isinstance(anomalies, list):
                    anomaly_tags.extend([str(a) for a in anomalies if a])
                
                # 如果没有 anomalies，尝试提取 state_tags
                if not anomaly_tags:
                    state_tags = output_json.get("state_tags", [])
                    if state_tags and isinstance(state_tags, list):
                        anomaly_tags.extend([str(tag) for tag in state_tags if tag])
    
    return anomaly_tags


def _extract_symptoms_data(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 bundle 中提取症状数据（系统识别 + 患者自述）
    
    返回格式：
    {
        "system_identified": ["恶心/呕吐", "胸闷", ...],  # 系统识别的症状列表
        "patient_feedback": ["无明显症状"]  # 患者自述
    }
    """
    bundle_data = bundle.get("bundle", {}).get("data", {}) or bundle.get("data", {})
    symptoms = bundle_data.get("symptoms", [])
    
    system_identified = []
    patient_feedback = []
    
    if symptoms and isinstance(symptoms, list):
        for symptom in symptoms:
            if isinstance(symptom, dict):
                # 提取系统识别的症状（output_json.symptoms）
                output_json = symptom.get("output_json", {})
                if isinstance(output_json, dict):
                    # 新的数据格式：output_json 是对象，symptoms 在其中
                    symptoms_list = output_json.get("symptoms", [])
                    if symptoms_list and isinstance(symptoms_list, list):
                        system_identified.extend([str(s) for s in symptoms_list if s])
                elif isinstance(output_json, list):
                    # 兼容旧的数据格式：output_json 直接是列表
                    system_identified.extend([str(s) for s in output_json if s])
                
                # 提取患者自述（user_feedback）
                user_feedback = symptom.get("user_feedback", [])
                if user_feedback and isinstance(user_feedback, list):
                    for fb in user_feedback:
                        if isinstance(fb, dict):
                            # 新格式：user_feedback 是对象列表
                            text = fb.get("text") or fb.get("symptom_name", "")
                            if text:
                                patient_feedback.append(str(text))
                        elif fb:
                            # 旧格式：直接是字符串
                            patient_feedback.append(str(fb))
    
    return {
        "system_identified": system_identified,
        "patient_feedback": patient_feedback
    }


def _extract_trigger_context(bundle: Dict[str, Any], signals_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取触发上下文信息（触发类型、原因、患者反馈、AI推理详情）
    """
    context = {
        "trigger_type": "unknown",
        "trigger_reason": [],
        "patient_feedback": "",
        "ai_exclusions": [],
        "ai_risks": []
    }
    
    if not bundle:
        return context
        
    # 提取 trigger_type
    # bundle 可能直接包含 scenario，或者在 bundle.scenario
    scenario = bundle.get("scenario", {})
    if not scenario:
        scenario = bundle.get("bundle", {}).get("scenario", {})
        
    context["trigger_type"] = scenario.get("trigger_type", "unknown")
    
    # 提取症状和推理信息
    bundle_data = bundle.get("bundle", {}).get("data", {}) or bundle.get("data", {})
    symptoms = bundle_data.get("symptoms", [])
    
    if symptoms and isinstance(symptoms, list) and len(symptoms) > 0:
        first_symptom = symptoms[0]
        if isinstance(first_symptom, dict):
            output_json = first_symptom.get("output_json", {})
            
            # 1. 提取 Trigger Reason (优先使用 anchors.signals)
            reasoning = output_json.get("reasoning", {}) if isinstance(output_json, dict) else {}
            anchors = reasoning.get("anchors", {})
            if "signals" in anchors and isinstance(anchors["signals"], list):
                context["trigger_reason"] = anchors["signals"]
            
            # 如果没有 anchors.signals，尝试使用 signals_info 中的 anomalies
            if not context["trigger_reason"]:
                context["trigger_reason"] = _extract_anomaly_tags(signals_info)
                
            # 2. 提取 AI Exclusions
            context["ai_exclusions"] = reasoning.get("exclusions", [])
            
            # 3. 提取 AI Risks
            context["ai_risks"] = anchors.get("risks", [])
            
            # 4. 提取 Patient Feedback
            user_feedback = first_symptom.get("user_feedback", [])
            feedback_texts = []
            if isinstance(user_feedback, list):
                for fb in user_feedback:
                    if isinstance(fb, dict):
                        text = fb.get("text") or fb.get("symptom_name")
                        if text: feedback_texts.append(str(text))
                    elif isinstance(fb, str):
                        feedback_texts.append(fb)
            context["patient_feedback"] = "、".join(feedback_texts) if feedback_texts else ""
            
    return context


def _extract_suggestions_by_category(suggestions_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    从 suggestions 列表中提取建议，并按 category 分组
    
    suggestions 结构：
    [
        {
            "output_json": [
                {"category": "诊断与评估", "advice": ["建议1", "建议2"]},
                {"category": "检查与辅助", "advice": ["建议3"]}
            ]
        }
    ]
    """
    categorized = {}
    
    for suggestion in suggestions_list:
        if not isinstance(suggestion, dict):
            continue
        
        # 提取 output_json
        output_json = suggestion.get("output_json", [])
        if not isinstance(output_json, list):
            continue
        
        for item in output_json:
            if not isinstance(item, dict):
                continue
            
            category = item.get("category", "其他")
            advice_list = item.get("advice", [])
            
            if category not in categorized:
                categorized[category] = []
            
            if isinstance(advice_list, list):
                categorized[category].extend([str(a) for a in advice_list if a])
    
    return categorized


def _extract_signals_timeseries(signals_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 signals 中提取时间序列数据，用于图表展示（带状图）
    每个signal作为一个时间点，提取min/max/mean值
    
    返回格式：
    {
        "heart_rate": {
            "labels": [...], 
            "mean": [...], 
            "min": [...], 
            "max": [...]
        },
        "blood_pressure": {
            "labels": [...],
            "systolic": {"mean": [...], "min": [...], "max": [...]},
            "diastolic": {"mean": [...], "min": [...], "max": [...]}
        },
        "spo2": {
            "labels": [...], 
            "mean": [...], 
            "min": [...], 
            "max": [...]
        },
        "temperature": {
            "labels": [...], 
            "mean": [...], 
            "min": [...], 
            "max": [...]
        }
    }
    """
    timeseries_data = {}
    signals_list = signals_info.get("signals_list", [])
    
    if not signals_list:
        return timeseries_data
    
    # 提取所有信号的时间序列数据（按时间顺序，从早到晚）
    # signals_list通常是降序的（最新的在前），我们需要反转以便图表从左到右显示时间
    signals_list_sorted = sorted(signals_list, key=lambda x: x.get("start_ts", ""), reverse=False) if signals_list else []
    
    # 心率数据
    hr_mean = []
    hr_min = []
    hr_max = []
    
    # 血压数据
    sbp_mean = []
    sbp_min = []
    sbp_max = []
    dbp_mean = []
    dbp_min = []
    dbp_max = []
    
    # 血氧数据
    spo2_mean = []
    spo2_min = []
    spo2_max = []
    
    # 体温数据
    temp_mean = []
    temp_min = []
    temp_max = []
    
    labels = []
    
    for signal in signals_list_sorted:
        if not isinstance(signal, dict):
            continue
        
        # 提取时间标签（使用整点时间，便于快速阅读）
        start_ts = signal.get("start_ts", "")
        end_ts = signal.get("end_ts", "")
        if start_ts:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                # 使用整点时间，如 "02:00", "03:00"（取开始时间的整点）
                # 如果开始时间不是整点，显示开始时间的小时:分钟
                hour = start_dt.hour
                minute = start_dt.minute
                # 如果分钟接近0或20或40，显示整点或20分或40分
                if minute < 10:
                    labels.append(f"{hour:02d}:00")
                elif minute < 30:
                    labels.append(f"{hour:02d}:20")
                elif minute < 50:
                    labels.append(f"{hour:02d}:40")
                else:
                    # 接近下一个整点，显示下一个整点
                    next_hour = (hour + 1) % 24
                    labels.append(f"{next_hour:02d}:00")
            except:
                labels.append(start_ts[:16])  # 截取前16个字符
        else:
            labels.append("")
        
        # 提取metrics
        metrics_json = signal.get("metrics_json", {})
        output_json = metrics_json.get("output_json", {}) if isinstance(metrics_json, dict) else {}
        metrics = output_json.get("metrics_json", {}) if isinstance(output_json, dict) else {}
        
        if isinstance(metrics, dict):
            # 心率（提取min/max/mean）
            hr = metrics.get("heart_rate", {})
            if isinstance(hr, dict):
                hr_mean.append(hr.get("mean"))
                hr_min.append(hr.get("min"))
                hr_max.append(hr.get("max"))
            else:
                hr_mean.append(None)
                hr_min.append(None)
                hr_max.append(None)
            
            # 血压（提取min/max/mean）
            bp = metrics.get("blood_pressure", {})
            if isinstance(bp, dict):
                systolic = bp.get("systolic", {})
                diastolic = bp.get("diastolic", {})
                
                if isinstance(systolic, dict):
                    sbp_mean.append(systolic.get("mean"))
                    sbp_min.append(systolic.get("min"))
                    sbp_max.append(systolic.get("max"))
                else:
                    sbp_mean.append(None)
                    sbp_min.append(None)
                    sbp_max.append(None)
                
                if isinstance(diastolic, dict):
                    dbp_mean.append(diastolic.get("mean"))
                    dbp_min.append(diastolic.get("min"))
                    dbp_max.append(diastolic.get("max"))
                else:
                    dbp_mean.append(None)
                    dbp_min.append(None)
                    dbp_max.append(None)
            else:
                sbp_mean.append(None)
                sbp_min.append(None)
                sbp_max.append(None)
                dbp_mean.append(None)
                dbp_min.append(None)
                dbp_max.append(None)
            
            # 血氧（提取min/max/mean）
            spo2 = metrics.get("spo2", {})
            if isinstance(spo2, dict):
                spo2_mean.append(spo2.get("mean"))
                spo2_min.append(spo2.get("min"))
                spo2_max.append(spo2.get("max"))
            else:
                spo2_mean.append(None)
                spo2_min.append(None)
                spo2_max.append(None)
            
            # 体温（保持°C，提取min/max/mean）
            temp = metrics.get("temperature", {})
            if isinstance(temp, dict):
                temp_c_mean = temp.get("mean")
                temp_c_min = temp.get("min")
                temp_c_max = temp.get("max")
                if temp_c_mean is not None:
                    temp_mean.append(round(temp_c_mean, 1))
                else:
                    temp_mean.append(None)
                if temp_c_min is not None:
                    temp_min.append(round(temp_c_min, 1))
                else:
                    temp_min.append(None)
                if temp_c_max is not None:
                    temp_max.append(round(temp_c_max, 1))
                else:
                    temp_max.append(None)
            else:
                temp_mean.append(None)
                temp_min.append(None)
                temp_max.append(None)
        else:
            # 如果没有metrics，填充None
            hr_mean.append(None)
            hr_min.append(None)
            hr_max.append(None)
            sbp_mean.append(None)
            sbp_min.append(None)
            sbp_max.append(None)
            dbp_mean.append(None)
            dbp_min.append(None)
            dbp_max.append(None)
            spo2_mean.append(None)
            spo2_min.append(None)
            spo2_max.append(None)
            temp_mean.append(None)
            temp_min.append(None)
            temp_max.append(None)
    
    # 构建返回数据（只返回有数据的序列）
    if labels and any(v is not None for v in hr_mean):
        timeseries_data["heart_rate"] = {
            "labels": labels,
            "mean": hr_mean,
            "min": hr_min,
            "max": hr_max
        }
    
    if labels and (any(v is not None for v in sbp_mean) or any(v is not None for v in dbp_mean)):
        timeseries_data["blood_pressure"] = {
            "labels": labels,
            "systolic": {
                "mean": sbp_mean,
                "min": sbp_min,
                "max": sbp_max
            },
            "diastolic": {
                "mean": dbp_mean,
                "min": dbp_min,
                "max": dbp_max
            }
        }
    
    if labels and any(v is not None for v in spo2_mean):
        timeseries_data["spo2"] = {
            "labels": labels,
            "mean": spo2_mean,
            "min": spo2_min,
            "max": spo2_max
        }
    
    if labels and any(v is not None for v in temp_mean):
        timeseries_data["temperature"] = {
            "labels": labels,
            "mean": temp_mean,
            "min": temp_min,
            "max": temp_max
        }
    
    return timeseries_data


def _extract_anomaly_periods(signals_info: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    从 signals 中提取异常时间段
    
    返回格式：
    [
        {"start": "...", "end": "...", "anomaly_type": "..."},
        ...
    ]
    """
    periods = []
    signals_list = signals_info.get("signals_list", [])
    
    for signal in signals_list:
        if not isinstance(signal, dict):
            continue
        
        start_ts = signal.get("start_ts", "")
        end_ts = signal.get("end_ts", "")
        metrics_json = signal.get("metrics_json", {})
        output_json = metrics_json.get("output_json", {}) if isinstance(metrics_json, dict) else {}
        
        # 提取异常信息
        anomalies = output_json.get("anomalies", []) if isinstance(output_json, dict) else []
        
        if anomalies and start_ts and end_ts:
            # 简化时间显示
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_ts.replace('Z', '+00:00'))
                start_str = start_dt.strftime("%m-%d %H:%M")
                end_str = end_dt.strftime("%m-%d %H:%M")
            except:
                start_str = start_ts[:16]
                end_str = end_ts[:16]
            
            # 为每个异常创建一个时间段记录
            for anomaly in anomalies:
                if isinstance(anomaly, str) and anomaly:
                    periods.append({
                        "start": start_str,
                        "end": end_str,
                        "anomaly_type": anomaly
                    })
    
    return periods


def _extract_medical_history(ehr: Dict[str, Any], meds: list, language: str = 'zh') -> Dict[str, Any]:
    """
    从 ehr 中提取完整的既往史信息
    
    ehr 格式：
    - medical_history: [{"疾病": "...", "病程原文": "...", "病程年数": ..., ...}, ...]
    - allergy_history: {"药物": [...], "食物": [...], "环境": [...], ...}
    - family_history: {"母亲病史": [...], "父亲病史": [...], ...}
    """
    # 提取 ehr 数据（兼容新旧格式）
    ehr_data = ehr.get("ehr", ehr) if isinstance(ehr, dict) else {}
    
    # 提取既往疾病
    medical_history_list = ehr_data.get("medical_history", [])
    diagnoses = []
    diagnoses_str = "无"
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
        if diagnoses:
            diagnoses_str = "、".join(diagnoses)
    
    # 提取过敏史
    allergy_history = ehr_data.get("allergy_history", {})
    allergies = []
    allergies_str = "无过敏史" if language == 'zh' else "No known allergies"
    if isinstance(allergy_history, dict):
        # 提取所有类型的过敏
        drug_allergies = allergy_history.get("药物", [])
        food_allergies = allergy_history.get("食物", [])
        env_allergies = allergy_history.get("环境", [])
        other_allergies = allergy_history.get("其他", [])
        
        all_allergies = []
        if drug_allergies and isinstance(drug_allergies, list):
            all_allergies.extend([f"药物：{a}" for a in drug_allergies if a])
        if food_allergies and isinstance(food_allergies, list):
            all_allergies.extend([f"食物：{a}" for a in food_allergies if a])
        if env_allergies and isinstance(env_allergies, list):
            all_allergies.extend([f"环境：{a}" for a in env_allergies if a])
        if other_allergies and isinstance(other_allergies, list):
            all_allergies.extend([f"其他：{a}" for a in other_allergies if a])
        
        if all_allergies:
            allergies = all_allergies
            allergies_str = "、".join(all_allergies)
    
    # 提取家族史
    family_history = ehr_data.get("family_history", {})
    family_history_str = "无特殊家族史" if language == 'zh' else "No significant family history"
    if isinstance(family_history, dict):
        family_items = []
        mother_history = family_history.get("母亲病史", [])
        father_history = family_history.get("父亲病史", [])
        sibling_history = family_history.get("兄弟姐妹病史", [])
        child_history = family_history.get("子女病史", [])
        
        if mother_history and isinstance(mother_history, list):
            family_items.append(f"母亲：{', '.join([str(h) for h in mother_history if h])}")
        if father_history and isinstance(father_history, list):
            family_items.append(f"父亲：{', '.join([str(h) for h in father_history if h])}")
        if sibling_history and isinstance(sibling_history, list):
            family_items.append(f"兄弟姐妹：{', '.join([str(h) for h in sibling_history if h])}")
        if child_history and isinstance(child_history, list):
            family_items.append(f"子女：{', '.join([str(h) for h in child_history if h])}")
        
        if family_items:
            family_history_str = "；".join(family_items)
    
    # 提取生活方式（从 ehr 的 lifestyle）
    lifestyle = ehr_data.get("lifestyle", {})
    social_history = {
        "tobacco": lifestyle.get("吸烟情况", "未知") if isinstance(lifestyle, dict) else "未知",
        "alcohol": lifestyle.get("饮酒情况", "未知") if isinstance(lifestyle, dict) else "未知"
    }
    
    return {
        "diagnoses": diagnoses,
        "diagnoses_str": diagnoses_str,
        "surgeries": [],  # ehr 中没有手术史字段
        "surgeries_str": "无",
        "allergies": allergies,
        "allergies_str": allergies_str,
        "medications": meds if isinstance(meds, list) else [],
        "medications_str": "、".join(meds) if isinstance(meds, list) and meds else "无",
        "family_history": family_history_str,
        "social_history": social_history
    }


def _extract_care_measures(patient_suggestions: list) -> list:
    """
    从患者建议中提取护理措施
    """
    measures = []
    for suggestion in patient_suggestions:
        output_json = suggestion.get("output_json", [])
        if isinstance(output_json, list):
            for item in output_json:
                if isinstance(item, dict):
                    advice_list = item.get("advice", [])
                    if isinstance(advice_list, list):
                        measures.extend(advice_list)
    return measures[:5]  # 限制数量

