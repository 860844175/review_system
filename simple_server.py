#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版报告生成服务
提供基础的患者查找和报告生成功能
"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import sys
import traceback
from datetime import datetime, timedelta

# 添加当前目录到Python路径，确保能导入report_modules
sys.path.insert(0, str(Path(__file__).parent))

# 报告生成模块已移除
REPORT_SYSTEM_AVAILABLE = False

# 诊断系统模块导入
try:
    from clients.diagnosis_system_client import FixtureDiagnosisSystemClient, LiveDiagnosisSystemClient
    from adapters.diagnosis_system_adapter import build_view_model
    DIAGNOSIS_SYSTEM_AVAILABLE = True
    print("✅ 诊断系统模块加载成功")
except ImportError as e:
    print(f"⚠️ 诊断系统模块加载失败: {e}")
    DIAGNOSIS_SYSTEM_AVAILABLE = False

# 任务仓库模块导入
try:
    from repositories.tasks_repository import get_task_by_id, create_task, update_task, list_all_tasks, find_pending_task_by_ids, cleanup_duplicate_tasks
    TASKS_REPOSITORY_AVAILABLE = True
    print("✅ 任务仓库模块加载成功")
except ImportError as e:
    print(f"⚠️ 任务仓库模块加载失败: {e}")
    TASKS_REPOSITORY_AVAILABLE = False

# 服务模块导入
try:
    from services.approval_platform_client import get_default_client as get_approval_platform_client
    from services.system_client import get_default_client as get_system_client
    from services.config import LOCAL_BASE_URL, APPROVAL_PLATFORM_BASE_URL
    SERVICES_AVAILABLE = True
    print("✅ 服务模块加载成功")
    print(f"📍 审核平台URL: {APPROVAL_PLATFORM_BASE_URL}")
    if "localhost:5003" in APPROVAL_PLATFORM_BASE_URL:
        print("   ✅ 使用 Mock 审核平台")
    elif "med.bjknrt.com" in APPROVAL_PLATFORM_BASE_URL:
        print("   ⚠️  使用真实审核平台（生产环境）")
    else:
        print(f"   ℹ️  自定义审核平台地址")
except ImportError as e:
    print(f"⚠️ 服务模块加载失败: {e}")
    SERVICES_AVAILABLE = False
    get_approval_platform_client = None
    get_system_client = None
    LOCAL_BASE_URL = "http://localhost:5001"

# 任务分配模块导入
try:
    from task_assignment import TaskAssigner
    TASK_ASSIGNMENT_AVAILABLE = True
    print("✅ 任务分配模块加载成功")
except ImportError as e:
    print(f"⚠️ 任务分配模块加载失败: {e}")
    TASK_ASSIGNMENT_AVAILABLE = False

app = Flask(__name__)

# 手动添加CORS头
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 配置路径
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "report" / "output"

# ==================== 导入语言配置系统 ====================
from config.language_config import get_language_config, LanguageConfig
from config.request_context import RequestContext
from config.constants import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, REPORT_APPROVED_BASE, REPORT_OUTPUT_BASE

# ==================== 数据入口配置（向后兼容，逐步迁移到LanguageConfig） ====================
# 注意：现在使用 get_language_config('zh').data_sources 来获取数据源
# 这个变量保留用于向后兼容，但新代码应该使用 LanguageConfig
def get_data_sources(language: str | None = None):
    """获取数据源配置（通过LanguageConfig）"""
    lang_config = get_language_config(language)
    return lang_config.data_sources

# 向后兼容：默认使用中文配置
DATA_SOURCES = get_data_sources('zh')

# 患者ID映射到实际数据文件
PATIENT_MAPPING = {
    'P001': '0b389f61f90fcf6da613e08c64e06fdbaf05758cdd9e6b5ae730f1b8a8a654e4',
    'P002': '6e84e63ded176d781f2a6e6a8d3e2cc82de94c2b360bee96209ddd24dabf3f3a',
    'P003': '7cb394d6e1c52e050ef41a9caa3c186d6a6a71fe2172fa8f901783973404285a'
}

# 反向映射：hash ID -> P001格式（用于分诊数据）
HASH_TO_TRIAGE_ID = {
    '0b389f61f90fcf6da613e08c64e06fdbaf05758cdd9e6b5ae730f1b8a8a654e4': 'p001',
    '6e84e63ded176d781f2a6e6a8d3e2cc82de94c2b360bee96209ddd24dabf3f3a': 'p002',
    '7cb394d6e1c52e050ef41a9caa3c186d6a6a71fe2172fa8f901783973404285a': 'p003'
}

# Approval相关配置
APPROVED_REPORTS_DIR = BASE_DIR / "report" / "approved"  # 完成报告目录
try:
    APPROVED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️ 无法创建目录 {APPROVED_REPORTS_DIR}: {e}")

# 患者信息数据库（可以从实际数据源读取）
PATIENT_INFO = {}

def check_available_report_types(patient_id: str, language: str | None = None) -> list:
    """
    检查病人可用的报告类型
    数据入口：统一从 LanguageConfig 配置读取数据路径
    
    Args:
        patient_id: 患者ID
        language: 语言代码，None时使用默认语言（zh）
    """
    lang_config = get_language_config(language)
    data_sources = lang_config.data_sources
    available_types = []
    
    # 检查依从性报告：从配置的数据源查找memory文件
    compliance_config = data_sources['compliance']
    for mem_dir in compliance_config['memory']:
        if mem_dir.exists():
            mem_file = mem_dir / compliance_config['memory_file_pattern'].format(patient_id=patient_id)
            if mem_file.exists():
                available_types.append("compliance")
                break
    
    # 检查分诊报告：从配置的数据源查找文件
    triage_config = data_sources['triage']
    triage_dir = triage_config['data_dir']
    if triage_dir.exists():
        # 首先尝试直接匹配
        triage_file = triage_dir / triage_config['file_pattern'].format(patient_id=patient_id)
        if triage_file.exists():
            available_types.append("triage")
        else:
            # 尝试通过映射查找（hash ID -> p001）
            triage_id = HASH_TO_TRIAGE_ID.get(patient_id, None)
            if triage_id:
                triage_file = triage_dir / f"{triage_id}.json"
                if triage_file.exists():
                    available_types.append("triage")
    
    return available_types if available_types else []

def check_report_approval_status(patient_id: str, report_type: str, language: str | None = None) -> bool:
    """
    检查报告是否已被approval（完成）
    返回True表示已完成，False表示未完成
    
    Args:
        patient_id: 患者ID
        report_type: 报告类型
        language: 语言代码，None时使用默认语言（zh）
    """
    lang_config = get_language_config(language)
    # 新路径：按语言组织
    approved_dir = REPORT_APPROVED_BASE / language / report_type
    
    # 旧路径兼容（不带语言）
    old_approved_dir = APPROVED_REPORTS_DIR / report_type
    
    # 查找该患者的已完成报告
    # 报告可能以 patient_id 或 data_id 命名
    possible_names = [patient_id]
    
    # 如果是hash ID，也尝试查找对应的P001格式
    if patient_id in HASH_TO_TRIAGE_ID:
        possible_names.append(HASH_TO_TRIAGE_ID[patient_id])
    
    # 如果是P001格式，也尝试查找对应的hash ID
    reverse_mapping = {v: k for k, v in HASH_TO_TRIAGE_ID.items()}
    if patient_id in reverse_mapping:
        possible_names.append(reverse_mapping[patient_id])
    
    # 先在新路径查找
    if approved_dir.exists():
        for name in possible_names:
            approved_reports = list(approved_dir.glob(f"{name}*"))
            if approved_reports:
                return True
    
    # 旧路径兼容查找
    if old_approved_dir.exists():
        for name in possible_names:
            approved_reports = list(old_approved_dir.glob(f"{name}*"))
            if approved_reports:
                return True
    
    return False

def load_patient_from_profile(patient_id: str, language: str | None = None):
    """
    从patient_profiles目录加载病人信息
    数据入口：从 LanguageConfig 配置的目录加载
    
    Args:
        patient_id: 患者ID
        language: 语言代码，None时使用默认语言（zh）
    """
    lang_config = get_language_config(language)
    data_sources = lang_config.data_sources
    
    # 从配置的数据源加载
    compliance_config = data_sources['compliance']
    for profile_dir in compliance_config['profiles']:
        profile_file = profile_dir / f"{patient_id}.json"
        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                basic_info = profile_data.get('basic_info', {})
                disease_info = profile_data.get('disease_info', {})
                
                # 提取主要疾病名称
                primary_diseases = disease_info.get('primary_diseases', [])
                disease_names = [d.get('disease_name', '') for d in primary_diseases if d.get('disease_name')]
                
                # 根据语言设置文本
                if language == 'en':
                    default_name = f"Patient {patient_id[:8]}"
                    unknown_text = "Unknown"
                    gender_map = {'M': 'Male', 'F': 'Female', '男': 'Male', '女': 'Female'}
                    diagnosis = ', '.join(disease_names) if disease_names else 'Chronic Disease Management'
                else:
                    default_name = f"患者{patient_id[:8]}"
                    unknown_text = "未知"
                    gender_map = {'M': '男', 'F': '女', 'Male': '男', 'Female': '女'}
                    diagnosis = ', '.join(disease_names) if disease_names else '未知'
                
                # 检查可用的报告类型
                available_reports = check_available_report_types(patient_id, language)
                
                # 检查每个报告的approval状态
                report_status = {}
                for report_type in available_reports:
                    report_status[report_type] = check_report_approval_status(patient_id, report_type, language)
                
                # 判断整体状态：如果有可用报告，检查是否全部完成
                if available_reports:
                    all_approved = all(report_status.get(rt, False) for rt in available_reports)
                    status = 'completed' if all_approved else 'pending'
                else:
                    status = 'no_data'  # 无可用数据
                
                # 处理性别
                sex = basic_info.get('sex', '')
                gender = gender_map.get(sex, unknown_text) if sex else unknown_text
                
                return {
                    'id': patient_id,
                    'name': basic_info.get('name') or default_name,
                    'age': basic_info.get('age', unknown_text),
                    'gender': gender,
                    'diagnosis': diagnosis,
                    'dataFile': patient_id,
                    'status': status,  # completed, pending, no_data
                    'report_status': report_status,  # 每个报告类型的完成状态
                    'profile_data': profile_data,
                    'available_reports': available_reports
                }
            except Exception as e:
                print(f"⚠️ 读取病人档案失败 {profile_file}: {e}")
                continue
    return None

@app.route('/api/patients', methods=['GET'])
@app.route('/<lang>/api/patients', methods=['GET'])
def get_all_patients(lang: str | None = None):
    """
    获取所有病人列表
    数据入口：统一从 LanguageConfig 配置扫描所有数据源
    
    Args:
        lang: 语言代码（从URL路径或查询参数获取）
    """
    try:
        # 创建请求上下文
        ctx = RequestContext.from_request(request) if 'request' in globals() else RequestContext(language=lang)
        language = ctx.language
        lang_config = ctx.lang_config
        data_sources = lang_config.data_sources
        
        patients = []
        patient_ids_seen = set()  # 避免重复
        
        # 数据入口1：扫描依从性数据的profile目录
        compliance_config = data_sources['compliance']
        for profile_dir in compliance_config['profiles']:
            if profile_dir.exists():
                for json_file in profile_dir.glob("*.json"):
                    patient_id = json_file.stem
                    if patient_id not in patient_ids_seen:
                        # 检查是否有可用的报告类型（triage或compliance）
                        available_reports = check_available_report_types(patient_id, language)
                        if available_reports:  # 只添加有可用报告的患者
                            patient_info = load_patient_from_profile(patient_id, language)
                            if patient_info:
                                # 确保available_reports与检查结果一致
                                patient_info['available_reports'] = available_reports
                                patients.append(patient_info)
                                patient_ids_seen.add(patient_id)
        
        # 数据入口2：扫描分诊数据目录
        triage_config = data_sources['triage']
        triage_dir = triage_config['data_dir']
        if triage_dir.exists():
            for json_file in triage_dir.glob("*.json"):
                # 跳过注释文件或非标准格式
                if json_file.name.startswith('//') or json_file.name.endswith('_zh.json'):
                    continue
                
                patient_id = json_file.stem
                if patient_id not in patient_ids_seen:
                    # 检查是否有可用的报告类型（triage或compliance）
                    available_reports = check_available_report_types(patient_id, language)
                    if not available_reports:  # 如果没有可用报告，跳过
                        continue
                    
                    # 检查是否已有profile（可能从依从性数据加载过）
                    patient_info = load_patient_from_profile(patient_id, language)
                    if not patient_info:
                        # 只有分诊数据，没有依从性数据，从分诊文件读取基本信息
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                triage_data = json.load(f)
                            hpi = triage_data.get('hpi', {})
                            meta = hpi.get('meta', {})
                            ed_snapshot = hpi.get('ed_snapshot', {})
                            
                            # 提取ESI等级
                            esi = ed_snapshot.get('ESI', None)
                            if esi is not None:
                                try:
                                    esi = float(esi)
                                except (ValueError, TypeError):
                                    esi = None
                            
                            # 检查分诊报告的approval状态
                            triage_approved = check_report_approval_status(patient_id, 'triage', language)
                            status = 'completed' if triage_approved else 'pending'
                            
                            # 根据语言设置文本
                            if language == 'en':
                                default_name = f"Patient {patient_id[:8]}"
                                unknown_text = "Unknown"
                                gender_map = {'M': 'Male', 'F': 'Female'}
                                diagnosis_text = "Triage Assessment"
                            else:
                                default_name = f"患者{patient_id[:8]}"
                                unknown_text = "未知"
                                gender_map = {'M': '男', 'F': '女'}
                                diagnosis_text = "分诊评估"
                            
                            patient_info = {
                                'id': patient_id,
                                'name': default_name,
                                'age': meta.get('age', unknown_text),
                                'gender': gender_map.get(meta.get('sex', '').upper(), unknown_text),
                                'diagnosis': diagnosis_text,
                                'dataFile': patient_id,
                                'status': status,
                                'report_status': {'triage': triage_approved},
                                'available_reports': available_reports,  # 使用检查结果
                                'esi': esi  # 添加ESI信息
                            }
                        except Exception as e:
                            print(f"⚠️ 读取分诊数据失败 {json_file}: {e}")
                            continue
                    else:
                        # 已有profile，更新可用报告类型（使用检查结果）
                        patient_info['available_reports'] = available_reports
                        
                        # 尝试从triage文件读取ESI信息
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                triage_data = json.load(f)
                            hpi = triage_data.get('hpi', {})
                            ed_snapshot = hpi.get('ed_snapshot', {})
                            esi = ed_snapshot.get('ESI', None)
                            if esi is not None:
                                try:
                                    esi = float(esi)
                                    patient_info['esi'] = esi
                                except (ValueError, TypeError):
                                    pass
                        except Exception as e:
                            print(f"⚠️ 读取分诊数据获取ESI失败 {json_file}: {e}")
                        
                        # 更新报告状态
                        if 'report_status' not in patient_info:
                            patient_info['report_status'] = {}
                        patient_info['report_status']['triage'] = check_report_approval_status(patient_id, 'triage', language)
                        
                        # 重新计算整体状态
                        available_reports = patient_info.get('available_reports', [])
                        if available_reports:
                            all_approved = all(
                                patient_info.get('report_status', {}).get(rt, False) 
                                for rt in available_reports
                            )
                            patient_info['status'] = 'completed' if all_approved else 'pending'
                    
                    patients.append(patient_info)
                    patient_ids_seen.add(patient_id)
        
        # 按ESI排序：低等级（高数字）放在最后，高等级（低数字）放在前面
        # ESI 1 (最紧急) -> ESI 5 (最不紧急)
        # 如果ESI为None，放在最后
        def sort_key(patient):
            esi = patient.get('esi')
            if esi is None:
                return (2, 999)  # None值放在最后
            try:
                esi_float = float(esi)
                return (1, esi_float)  # 有ESI值的按ESI排序
            except (ValueError, TypeError):
                return (2, 999)  # 无法转换的值放在最后
        
        patients.sort(key=sort_key)
        
        return jsonify({
            'success': True,
            'total': len(patients),
            'patients': patients
        })
    except Exception as e:
        print(f"❌ 获取病人列表失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/patients/count', methods=['GET'])
@app.route('/<lang>/api/patients/count', methods=['GET'])
def get_patients_count(lang: str | None = None):
    """
    动态统计系统中的病人数量
    
    Args:
        lang: 语言代码（从URL路径或查询参数获取）
    """
    try:
        # 创建请求上下文获取语言
        ctx = RequestContext.from_request(request) if 'request' in globals() else RequestContext(language=lang)
        language = ctx.language
        # 使用LanguageConfig获取数据源路径（优先新路径data/{lang}，兼容旧路径）
        lang_config = get_language_config(language)
        compliance_config = lang_config.get_compliance_data_sources()
        
        # 统计所有配置的profile目录
        total_count = 0
        output_count = 0
        enhanced_count = 0
        
        for profile_dir in compliance_config['profiles']:
            if profile_dir.exists():
                count = len(list(profile_dir.glob("*.json")))
                total_count += count
                # 判断是output还是output_llm_enhanced
                if 'output_llm_enhanced' in str(profile_dir):
                    enhanced_count += count
                elif 'output' in str(profile_dir) and 'llm_enhanced' not in str(profile_dir):
                    output_count += count
        
        # 向后兼容：如果新路径没有数据，尝试旧路径
        if total_count == 0:
            old_output_dir = DATA_DIR / "output" / "patient_profiles"
            old_enhanced_dir = DATA_DIR / "output_llm_enhanced" / "patient_profiles"
            if old_output_dir.exists():
                output_count = len(list(old_output_dir.glob("*.json")))
            if old_enhanced_dir.exists():
                enhanced_count = len(list(old_enhanced_dir.glob("*.json")))
            total_count = output_count + enhanced_count
        
        return jsonify({
            'success': True,
            'total': total_count,
            'output': output_count,
            'enhanced': enhanced_count,
            'registered': len(PATIENT_INFO)  # 已注册的病人数（硬编码的）
        })
    except Exception as e:
        print(f"❌ 统计病人数量失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/patients/<patient_id>', methods=['GET'])
@app.route('/<lang>/api/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id, lang: str | None = None):
    """
    获取患者信息（支持原始ID和映射ID）
    
    Args:
        patient_id: 患者ID
        lang: 语言代码（从URL路径或查询参数获取）
    """
    try:
        # 创建请求上下文获取语言
        ctx = RequestContext.from_request(request) if 'request' in globals() else RequestContext(language=lang)
        language = ctx.language
        
        # 首先尝试从硬编码的PATIENT_INFO查找（兼容P001等）
        patient_id_upper = patient_id.upper()
        if patient_id_upper in PATIENT_INFO:
            patient = PATIENT_INFO[patient_id_upper].copy()
            # 检查数据文件是否存在（优先新路径，兼容旧路径）
            lang_config = get_language_config(language)
            compliance_config = lang_config.get_compliance_data_sources()
            data_file = None
            # 尝试从配置的目录查找（新路径）
            for mem_dir in compliance_config.get('memory', []):
                dialogue_dir = mem_dir.parent / "dialogue_data"
                if dialogue_dir.exists():
                    data_file = dialogue_dir / f"{patient['dataFile']}_multiday.json"
                    if data_file.exists():
                        break
            # 向后兼容：如果新路径找不到，尝试旧路径
            if not data_file or not data_file.exists():
                data_file = DATA_DIR / "output" / "dialogue_data" / f"{patient['dataFile']}_multiday.json"
            patient['hasData'] = data_file.exists() if data_file else False
            return jsonify(patient)
        
        # 如果不在PATIENT_INFO中，尝试从patient_profiles目录加载
        patient_info = load_patient_from_profile(patient_id, language)
        if patient_info:
            # 检查数据文件是否存在（优先新路径，兼容旧路径）
            lang_config = get_language_config(language)
            compliance_config = lang_config.get_compliance_data_sources()
            data_file = None
            # 尝试从配置的目录查找（新路径）
            for mem_dir in compliance_config.get('memory', []):
                dialogue_dir = mem_dir.parent / "dialogue_data"
                if dialogue_dir.exists():
                    data_file = dialogue_dir / f"{patient_id}_multiday.json"
                    if data_file.exists():
                        break
            # 向后兼容：如果新路径找不到，尝试旧路径
            if not data_file or not data_file.exists():
                data_file = DATA_DIR / "output" / "dialogue_data" / f"{patient_id}_multiday.json"
            if not data_file.exists():
                data_file = DATA_DIR / "output_llm_enhanced" / "dialogue_data" / f"{patient_id}_multiday.json"
            
            patient_info['hasData'] = data_file.exists() if data_file else False
            return jsonify(patient_info)
        
        return jsonify({'error': f'患者 {patient_id} 不存在'}), 404
            
    except Exception as e:
        print(f"❌ 获取患者信息失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/approve-report', methods=['POST'])
@app.route('/<lang>/api/approve-report', methods=['POST'])
def approve_report(lang: str | None = None):
    """
    批准报告，将报告移动到完成文件夹
    
    Args:
        lang: 语言代码（从URL路径或请求参数获取）
    """
    try:
        # 创建请求上下文
        ctx = RequestContext.from_request(request) if 'request' in globals() else RequestContext(language=lang)
        language = ctx.language
        
        data = request.json
        patient_id = data.get('patientId', '').strip()
        report_type = data.get('reportType', '').strip()  # compliance 或 triage
        report_path = data.get('reportPath', '')  # 原始报告路径
        modifications = data.get('modifications', {})  # 医生做的修改
        
        # 请求中的语言参数优先
        if 'language' in data:
            language = LanguageConfig.normalize_language(data.get('language'))
            ctx = RequestContext(language=language, patient_id=patient_id)
        
        if not patient_id or not report_type:
            return jsonify({'error': '缺少必要参数'}), 400
        
        print(f"✅ 批准报告: {patient_id} - {report_type} (语言: {language})")
        
        # 创建完成文件夹结构：report/approved/{language}/{report_type}/
        from config.constants import REPORT_APPROVED_BASE
        approved_dir = REPORT_APPROVED_BASE / language / report_type
        approved_dir.mkdir(parents=True, exist_ok=True)
        
        # 从report_path解析原始报告文件
        # report_path格式：/api/reports/{language}/{data_id}/{report_dir}/{filename} 或 /api/reports/{data_id}/{report_dir}/{filename}（旧格式）
        if report_path.startswith('/api/reports/'):
            path_parts = report_path.replace('/api/reports/', '').split('/')
            
            # 判断是新格式（带语言）还是旧格式（不带语言）
            if len(path_parts) >= 3 and path_parts[0] in SUPPORTED_LANGUAGES:
                # 新格式：/api/reports/{language}/{data_id}/{report_dir}/{filename}
                path_language = path_parts[0]
                data_id = path_parts[1]
                report_dir_name = path_parts[2]
                filename = path_parts[3] if len(path_parts) > 3 else 'doctor_report.html'
            elif len(path_parts) >= 2:
                # 旧格式：/api/reports/{data_id}/{report_dir}/{filename}
                data_id = path_parts[0]
                report_dir_name = path_parts[1]
                filename = path_parts[2] if len(path_parts) > 2 else 'doctor_report.html'
                path_language = language  # 使用当前请求的语言
            else:
                return jsonify({'error': '报告路径格式错误'}), 400
            
            # 查找原始报告文件（先新路径，后旧路径）
            from config.constants import REPORT_OUTPUT_BASE
            original_report_dir_new = REPORT_OUTPUT_BASE / path_language / data_id / report_dir_name
            original_report_dir_old = REPORT_DIR / data_id / report_dir_name
            
            # 优先使用新路径，如果不存在则使用旧路径
            if original_report_dir_new.exists():
                original_report_dir = original_report_dir_new
            else:
                original_report_dir = original_report_dir_old
            
            original_report_file = original_report_dir / filename
            
            if original_report_file.exists():
                # Stateless mode: Do not save files locally
                print(f"✅ [Stateless] 报告已批准 (未保存到本地): {patient_id} - {report_type}")
                
                # 模拟生成文件名用于返回
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                target_filename = f"{patient_id}_{report_type}_{timestamp}.html"
                
                # 不再执行 shutil.copy2 和 json.dump
                
                return jsonify({
                    'success': True,
                    'message': '报告已批准 (Stateless Mode)',
                    'approved_path': f"/api/approved/{language}/{report_type}/{target_filename}"
                })
            else:
                return jsonify({'error': '原始报告文件不存在'}), 404
        else:
            return jsonify({'error': '无效的报告路径'}), 400
            
    except Exception as e:
        print(f"❌ 批准报告失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/<report_id>/urgency', methods=['PATCH'])
def adjust_urgency(report_id):
    """医生手动调整紧迫程度"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        new_level = data.get('new_level')
        reason = data.get('reason')
        adjusted_by = data.get('adjusted_by', 'doctor')
        adjusted_at = data.get('adjusted_at')
        
        # 验证参数
        if not all([patient_id, new_level, reason]):
            return jsonify({'error': '缺少必需参数'}), 400
        
        if new_level not in ['urgent', 'attention', 'stable']:
            return jsonify({'error': '无效的紧迫程度级别'}), 400
        
        # 这里应该保存到数据库，目前只是返回确认
        # TODO: 实现数据持久化
        
        print(f"✓ 紧迫程度调整: 患者={patient_id}, 报告={report_id}, 新级别={new_level}")
        print(f"  理由: {reason}")
        print(f"  操作者: {adjusted_by}, 时间: {adjusted_at}")
        
        response = {
            'success': True,
            'message': '紧迫程度已调整',
            'data': {
                'report_id': report_id,
                'patient_id': patient_id,
                'old_level': 'attention',  # 示例，应该从数据库读取
                'new_level': new_level,
                'reason': reason,
                'adjusted_by': adjusted_by,
                'adjusted_at': adjusted_at
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ 调整紧迫程度失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/urgency/stats', methods=['GET'])
def get_urgency_stats():
    """获取紧迫程度统计"""
    try:
        # TODO: 从实际报告数据中统计
        # 这里返回示例数据
        stats = {
            'urgent': 2,
            'attention': 5,
            'stable': 8,
            'total': 15,
            'last_updated': '2025-10-16T10:00:00'
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"❌ 获取统计失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    status = {
        'status': 'healthy',
        'message': '慢性病报告生成服务运行正常',
        'reportSystem': REPORT_SYSTEM_AVAILABLE
    }
    

    
    return jsonify(status)

@app.route('/api/diagnosis-system/triage-view', methods=['GET'])
def diagnosis_system_triage_view():
    """获取诊断系统的分诊视图数据"""
    if not DIAGNOSIS_SYSTEM_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "diagnosis system modules unavailable"
        }), 503
    
    # 获取参数
    user_id = request.args.get('user_id', '').strip()
    scenario_id = request.args.get('scenario_id', '').strip()
    source = request.args.get('source', 'fixture').strip()
    fixture_param = request.args.get('fixture', '').strip()  # 显式指定fixture目录
    
    if not user_id or not scenario_id:
        return jsonify({
            "success": False,
            "error": "missing user_id or scenario_id"
        }), 400
    
    try:
        fixture_dir = None
        if source == 'fixture':
            # 优先使用显式 fixture 参数，否则根据 user_id 推断
            if fixture_param in ('emergent', 'nonurgent'):
                fixture_dir = fixture_param
            
            # 优先使用scenario_id方式（新方式），如果不存在则回退到fixture_dir（旧方式）
            client = FixtureDiagnosisSystemClient(
                scenario_id=scenario_id,  # 新方式：基于scenario_id
                fixture_dir=fixture_dir   # 旧方式：向后兼容
            )
            
        elif source == 'live':
            base_url = os.getenv('DIAGNOSIS_SYSTEM_BASE_URL', '')
            api_key = os.getenv('DIAGNOSIS_SYSTEM_API_KEY', '')
            if not base_url or not api_key:
                return jsonify({
                    "success": False,
                    "error": "live mode requires DIAGNOSIS_SYSTEM_BASE_URL & DIAGNOSIS_SYSTEM_API_KEY"
                }), 400
            client = LiveDiagnosisSystemClient(base_url=base_url, api_key=api_key)
        else:
            return jsonify({
                "success": False,
                "error": f"invalid source: {source} (must be 'fixture' or 'live')"
            }), 400
        
        # 读取4个JSON
        scenario = client.get_scenario(scenario_id)
        bundle = client.get_scenario_bundle(scenario_id)
        ehr = client.get_user_ehr(user_id)
        signals = client.get_user_signals(user_id)
        
        # 构建view model
        view_model = build_view_model(scenario, bundle, ehr, signals)
        
        return jsonify({
            "success": True,
            "data": view_model,
            "source": source,
            "fixture_dir": fixture_dir
        })
        
    except FileNotFoundError as e:
        print(f"❌ Fixture文件不存在: {e}")
        return jsonify({
            "success": False,
            "error": f"Fixture file not found: {str(e)}"
        }), 404
    except ValueError as e:
        print(f"❌ JSON解析错误: {e}")
        return jsonify({
            "success": False,
            "error": f"Invalid JSON format: {str(e)}"
        }), 400
    except Exception as e:
        print(f"❌ 获取分诊视图失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/diagnosis-system/triage-view/by-task', methods=['GET'])
def diagnosis_system_triage_view_by_task():
    """通过task_id获取诊断系统的分诊视图数据"""
    if not DIAGNOSIS_SYSTEM_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "diagnosis system module unavailable"
        }), 503
    
    # 从URL参数获取 task_id, user_id, scenario_id
    task_id = request.args.get('task_id', '').strip()
    user_id = request.args.get('user_id', '').strip()
    scenario_id = request.args.get('scenario_id', '').strip()
    
    if not task_id:
        return jsonify({
            "success": False,
            "error": "missing task_id parameter"
        }), 400
    
    if not user_id or not scenario_id:
        return jsonify({
            "success": False,
            "error": "missing user_id or scenario_id parameter"
        }), 400
    
    try:
        # source 固定为 "live"（不再从 tasks_map.json 获取）
        source = "live"
        
        # Live 模式：从真实 API 读取
        base_url = os.getenv('DIAGNOSIS_SYSTEM_BASE_URL', '')
        api_key = os.getenv('DIAGNOSIS_SYSTEM_API_KEY', '')
        if not base_url or not api_key:
            return jsonify({
                "success": False,
                "error": "live mode requires DIAGNOSIS_SYSTEM_BASE_URL & DIAGNOSIS_SYSTEM_API_KEY"
            }), 400
        
        print(f"[{datetime.utcnow().isoformat()}Z] 📡 使用 live 模式拉取数据: {base_url}")
        client = LiveDiagnosisSystemClient(base_url=base_url, api_key=api_key)
        
        # 从 API 读取数据
        try:
            # 1. 只拉取场景聚合信息 (Bundle)
            print(f"[{datetime.utcnow().isoformat()}Z] 1️⃣ 拉取场景聚合信息: {scenario_id}")
            # scenario = client.get_scenario(scenario_id) # 不再单独拉取scenario
            bundle = client.get_scenario_bundle(scenario_id)
            
            # 从bundle中提取scenario信息
            scenario = bundle.get('scenario', {})
            
            # 2. 计算信号时间窗口
            # End: conv_start_ts
            conv_start_ts_str = scenario.get('conv_start_ts')
            
            # Start: End - 30 days
            signal_start_ts = None
            signal_end_ts = None
            
            if conv_start_ts_str:
                try:
                    # 解析时间字符串 (ISO format)
                    # 注意：Python 3.7+ fromisoformat 支持部分ISO格式，但最好处理一下 'Z'
                    if conv_start_ts_str.endswith('Z'):
                        conv_start_ts_str = conv_start_ts_str[:-1] + '+00:00'
                    
                    conv_start_dt = datetime.fromisoformat(conv_start_ts_str)
                    
                    signal_end_ts = conv_start_ts_str
                    signal_start_dt = conv_start_dt - timedelta(days=30)
                    signal_start_ts = signal_start_dt.isoformat()
                    
                    print(f"[{datetime.utcnow().isoformat()}Z] ⏱️ 计算信号时间窗口 (30天): {signal_start_ts} - {signal_end_ts}")
                except Exception as e:
                    print(f"⚠️ 时间解析失败: {e}, 将使用默认时间拉取信号")
            else:
                print(f"⚠️ 未找到 conv_start_ts, 将使用默认时间拉取信号")
            
            # 3. 拉取用户EHR
            print(f"[{datetime.utcnow().isoformat()}Z] 2️⃣ 拉取用户EHR: {user_id}")
            ehr = client.get_user_ehr(user_id)
            
            # 4. 拉取信号数据（使用计算出的时间窗口）
            print(f"[{datetime.utcnow().isoformat()}Z] 3️⃣ 拉取信号数据: {user_id}, window=[{signal_start_ts}, {signal_end_ts}]")
            signals_kwargs = {}
            if signal_start_ts:
                signals_kwargs['start'] = signal_start_ts
            if signal_end_ts:
                signals_kwargs['end'] = signal_end_ts
                
            signals = client.get_user_signals(user_id, **signals_kwargs)
            
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}Z] ❌ Live 模式数据拉取失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"Failed to fetch data from live API: {str(e)}"
            }), 500
        
        # 构建view model
        view_model = build_view_model(scenario, bundle, ehr, signals)
        
        # 提取对话历史（从bundle中）
        from adapters.view_model_to_triage_context import _extract_dialogue_messages
        dialogue_messages = _extract_dialogue_messages(bundle, language='zh')
        
        # 将对话历史添加到view_model中
        view_model["dialogue_messages"] = dialogue_messages
        
        # 提取triage_id和路径信息
        triage_id = None
        triage_data = (
            bundle.get("bundle", {}).get("data", {}).get("triage", {}) or
            bundle.get("bundle", {}).get("triage", {}) or
            bundle.get("data", {}).get("triage", {}) or
            bundle.get("triage", {})
        )
        if isinstance(triage_data, dict):
            triage_id = triage_data.get("id")
        
        # 添加triage_id和数据路径映射
        view_model["triage_id"] = triage_id
        view_model["data_paths"] = {
            "urgency_level": "bundle.data.triage.output_json.urgency_level",
            "next_operation": "bundle.data.triage.output_json.next_operation",
            "rationale": "bundle.data.triage.output_json.rationale",
            "likely_causes": "bundle.data.triage.output_json.likely_causes",
            "signals_summary": "signals.data[0].summary_text",
            "signals_metrics": "signals.data[0].metrics_json.output_json.metrics_json",
            "patient_recommendations": "bundle.data.suggestions.patient",
            "doctor_recommendations": "bundle.data.suggestions.doctor"
        }
        
        return jsonify({
            "success": True,
            "data": view_model,
            "task_id": task_id,
            "source": source
        })
        
    except Exception as e:
        print(f"❌ 通过task_id获取分诊视图失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/openapi/review/task/create', methods=['POST'])
def create_review_task_from_system():
    """
    系统模型端调用此接口创建审核任务
    
    流程：
    1. 生成 task_id 和 URL（URL中包含 user_id 和 scenario_id）
    2. 分配医生
    3. 注册到审核平台
    """
    if not SERVICES_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "services module unavailable"
        }), 503
    
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "missing request body"
            }), 400
        
        # 获取参数
        user_id = data.get('user_id', '').strip()
        scenario_id = data.get('scenario_id', '').strip()
        target_kind = data.get('target_kind', 'triage_result')
        target_id = data.get('target_id', '')
        
        # 校验必需参数
        if not user_id or not scenario_id:
            return jsonify({
                "success": False,
                "error": "missing user_id or scenario_id"
            }), 400
        
        # 生成 task_id（但不存储到本地）
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        task_id = ''.join(secrets.choice(alphabet) for _ in range(22))
        
        import time
        start_time = time.time()
        
        # 任务分配（Step 1）：分配医生（需要在生成URL之前完成）
        doctor_id = None
        assignment_result = None
        assignment_time = 0.0
        assignment_start_time = time.time()
        
        if TASK_ASSIGNMENT_AVAILABLE:
            try:
                print(f"[{datetime.utcnow().isoformat()}Z] 📋 开始分配医生...")
                
                from task_assignment.client import ApprovalPlatformClient
                from services.config import APPROVAL_PLATFORM_BASE_URL, APPROVAL_PLATFORM_API_KEY
                
                assignment_client = ApprovalPlatformClient(
                    base_url=APPROVAL_PLATFORM_BASE_URL,
                    api_key=APPROVAL_PLATFORM_API_KEY,
                    use_test_data=False
                )
                
                assigner = TaskAssigner(strategy="load_balance", client=assignment_client)
                hospital_id = data.get('hospital_id')
                assignment_result = assigner.assign_task(
                    user_id=user_id,
                    scenario_id=scenario_id,
                    task_id=task_id,
                    hospital_id=hospital_id
                )
                doctor_id = assignment_result.doctor_id
                assignment_time = time.time() - assignment_start_time
                print(f"[{datetime.utcnow().isoformat()}Z] ✅ 任务已分配给医生: doctor_id={doctor_id}")
                print(f"    分配理由: {assignment_result.assignment_reason}")
                print(f"    分配耗时: {assignment_time:.3f}秒")
                    
            except Exception as e:
                assignment_time = time.time() - assignment_start_time
                print(f"[{datetime.utcnow().isoformat()}Z] ⚠️ 任务分配失败（不影响任务创建）: {e}")
                print(f"    分配耗时: {assignment_time:.3f}秒")
                traceback.print_exc()
        else:
            print(f"[{datetime.utcnow().isoformat()}Z] ⚠️ 任务分配模块不可用，跳过医生分配")
        
        # 生成审核页面URL，将 task_id、user_id、scenario_id 和 doctor_id 编码到URL中
        from urllib.parse import urlencode
        params = {
            'task_id': task_id,
            'user_id': user_id,
            'scenario_id': scenario_id
        }
        # 如果分配了医生，添加到URL参数中
        if doctor_id:
            params['doctor_id'] = doctor_id
        review_page_url = f"{LOCAL_BASE_URL}/review/triage?{urlencode(params)}"
        
        # 调用审核平台注册任务（Step 2）
        platform_synced = False
        platform_time = 0.0
        platform_start_time = time.time()
        
        try:
            approval_client = get_approval_platform_client()
            if approval_client:
                print(f"[{datetime.utcnow().isoformat()}Z] 📤 开始注册任务到审核平台...")
                approval_client.register_add_task(
                    task_id=task_id,
                    user_id=user_id,
                    review_page_url=review_page_url,
                    doctor_id=doctor_id
                )
                platform_synced = True
                platform_time = time.time() - platform_start_time
                print(f"[{datetime.utcnow().isoformat()}Z] ✅ 任务已注册到审核平台: task_id={task_id}, doctor_id={doctor_id or 'None'}")
                print(f"    平台注册耗时: {platform_time:.3f}秒")
            else:
                print(f"[{datetime.utcnow().isoformat()}Z] ⚠️ 审核平台客户端未初始化，跳过注册")
        except Exception as e:
            platform_time = time.time() - platform_start_time if 'platform_start_time' in locals() else 0.0
            print(f"[{datetime.utcnow().isoformat()}Z] ⚠️ 注册到审核平台失败（不影响任务创建）: {e}")
            print(f"    平台注册耗时: {platform_time:.3f}秒")
        
        total_time = time.time() - start_time
        print(f"[{datetime.utcnow().isoformat()}Z] ⏱️  总耗时: {total_time:.3f}秒 (分配: {assignment_time:.3f}s, 注册: {platform_time:.3f}s)")
        
        result = {
            "success": True,
            "task_id": task_id,
            "review_url": review_page_url,
            "platform_synced": platform_synced
        }
        
        if assignment_result:
            result["doctor_id"] = assignment_result.doctor_id
            result["assignment_reason"] = assignment_result.assignment_reason
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ 创建审核任务失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/diagnosis-system/triage-review/submit', methods=['POST'])
def submit_triage_review():
    """
    提交分诊审核结果
    
    流程：
    1. 保存审核结果
    2. 通知审核平台任务完成
    3. 回传审核结果到系统模型端（zhikai）
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "missing request body"
            }), 400
        
        # 从请求参数获取（不再从 tasks_map.json）
        task_id = data.get('task_id', '').strip()
        user_id = data.get('user_id', '').strip()
        scenario_id = data.get('scenario_id', '').strip()
        decision = data.get('decision', {})
        modifications = data.get('modifications', [])
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": "missing task_id"
            }), 400
        
        if not user_id or not scenario_id:
            return jsonify({
                "success": False,
                "error": "missing user_id or scenario_id"
            }), 400
        
        # 注意：不再保存到本地 review_results，数据会发送给 zhikai (5002) 存储
        
        # Step 1: 通知审核平台任务完成（5003会更新任务状态）
        platform_synced = False
        if SERVICES_AVAILABLE and get_approval_platform_client:
            try:
                approval_client = get_approval_platform_client()
                if approval_client:
                    print(f"📤 [5001] 正在通知审核平台(5003)任务完成: task_id={task_id}")
                    result = approval_client.submit_task(task_id)
                    platform_synced = True
                    print(f"✅ [5001] 已通知审核平台任务完成: task_id={task_id}")
                    print(f"   平台响应: {result.get('message', 'N/A')}")
                else:
                    print(f"⚠️ [5001] 审核平台客户端未初始化，跳过通知")
            except Exception as e:
                print(f"❌ [5001] 通知审核平台失败: {e}")
                print(f"   错误类型: {type(e).__name__}")
                import traceback
                traceback.print_exc()
        
        # Step 2: 回传审核结果到系统模型端（zhikai）
        system_synced = False
        if SERVICES_AVAILABLE and get_system_client:
            try:
                system_client = get_system_client()
                if system_client:
                    # 尝试从bundle中获取triage_id和target_kind
                    target_id = None
                    target_kind = "triage_result"
                    
                    # 如果有diagnosis system可用，尝试获取bundle
                    if DIAGNOSIS_SYSTEM_AVAILABLE:
                        try:
                            base_url = os.getenv('DIAGNOSIS_SYSTEM_BASE_URL', '')
                            api_key = os.getenv('DIAGNOSIS_SYSTEM_API_KEY', '')
                            if base_url and api_key:
                                client = LiveDiagnosisSystemClient(base_url=base_url, api_key=api_key)
                                bundle = client.get_scenario_bundle(scenario_id)
                                
                                triage_data = (
                                    bundle.get("bundle", {}).get("data", {}).get("triage", {}) or
                                    bundle.get("triage", {})
                                )
                                if isinstance(triage_data, dict):
                                    target_id = triage_data.get("id")
                                    target_kind = triage_data.get("kind", "triage_result")
                        except Exception as e:
                            print(f"⚠️ 获取bundle失败，使用默认值: {e}")
                    
                    # 如果无法获取triage_id，使用scenario_id作为备选
                    if not target_id:
                        target_id = scenario_id
                    
                    # 构造annotation_json
                    annotation_json = {
                        "review_date": datetime.utcnow().isoformat() + "Z",
                        "task_id": task_id,
                        "modifications": modifications
                    }
                    
                    # 提取author_id
                    author_id = decision.get("reviewer_id") or decision.get("author_id")
                    
                    system_client.send_review_result(
                        user_id=user_id,
                        scenario_id=scenario_id,
                        target_kind=target_kind,
                        target_id=target_id,
                        annotation_json=annotation_json,
                        author_id=author_id
                    )
                    system_synced = True
                    print(f"✅ 已回传审核结果到系统模型端: task_id={task_id}")
                else:
                    print(f"⚠️ 系统模型端客户端未初始化，跳过回传")
            except Exception as e:
                print(f"⚠️ 回传系统模型端失败（不影响结果保存）: {e}")
                traceback.print_exc()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "platform_synced": platform_synced,
            "system_synced": system_synced
        })
        
    except Exception as e:
        print(f"❌ 提交审核结果失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/review/triage', methods=['GET'])
def triage_view_page():
    """分诊审核页面"""
    triage_file = BASE_DIR / "frontend" / "triage_view.html"
    if triage_file.exists():
        return send_file(triage_file, mimetype='text/html; charset=utf-8')
    else:
        return jsonify({'error': 'triage_view.html not found'}), 404



@app.route('/', methods=['GET'])
@app.route('/<lang>/', methods=['GET'])
def index(lang: str | None = None):
    """
    主页 - 提供前端页面
    
    Args:
        lang: 语言代码（从URL路径获取，可选）
    """
    # 直接返回API状态，不提供前端页面
    status = {
        'name': '慢性病报告生成服务 (Backend Only)',
        'version': '2.0.0',
        'status': 'running',
        'message': 'Frontend is disabled. This is a pure API server.',
        'endpoints': [
            'GET /api/health - 健康检查',
            'GET /api/patients/<patient_id> - 获取患者信息',
            'POST /api/generate-report - 生成报告',
            'GET /api/reports/<patient_id>/<filename> - 获取报告文件'
        ]
    }
    return jsonify(status)

@app.route('/api', methods=['GET'])
def api_docs():
    """API文档"""
    status = {
        'name': '慢性病报告生成服务',
        'version': '2.0.0',
        'reportSystemAvailable': REPORT_SYSTEM_AVAILABLE,
        'endpoints': [
            'GET /api/health - 健康检查',
            'GET /api/patients/<patient_id> - 获取患者信息',
            'POST /api/generate-report - 生成报告',
            'GET /api/reports/<patient_id>/<filename> - 获取报告文件'
        ],
        'testPatients': list(PATIENT_INFO.keys())
    }
    

    
    return jsonify(status)

def check_dependencies():
    """检查依赖文件"""
    required_dirs = [DATA_DIR, REPORT_DIR]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            print(f"创建目录: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # 检查数据文件（优先新路径，兼容旧路径）
    lang_config = get_language_config('zh')
    compliance_config = lang_config.get_compliance_data_sources()
    data_found = False
    # 检查新路径
    for mem_dir in compliance_config.get('memory', []):
        dialogue_dir = mem_dir.parent / "dialogue_data"
        if dialogue_dir.exists():
            data_found = True
            break
    # 向后兼容：检查旧路径
    if not data_found:
        data_dialogue_dir = DATA_DIR / "output" / "dialogue_data"
        if data_dialogue_dir.exists():
            data_found = True
        else:
            print(f"警告: 数据目录不存在（已检查新路径和旧路径）")
            return False
    
    return True

if __name__ == '__main__':
    print("正在启动慢性病报告生成服务...")

    port_number = 5001
    
    # 检查依赖
    if not check_dependencies():
        print("警告: 某些依赖文件缺失，服务可能无法正常工作")
    
    print("服务启动成功!")
    print(f"前端访问地址: http://localhost:{port_number}/")
    print(f"API文档: http://localhost:{port_number}/api")

    # 启动服务
    app.run(
        host='0.0.0.0',
        port=port_number,
        debug=True
    )