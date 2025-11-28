# 诊断系统客户端模块

## 功能
- `FixtureDiagnosisSystemClient`: 从本地JSON文件读取测试数据
- `LiveDiagnosisSystemClient`: 从真实API读取数据（待实现）

## 使用方法
```python
from clients.diagnosis_system_client import FixtureDiagnosisSystemClient

# 使用紧急测试数据
client = FixtureDiagnosisSystemClient(fixture_dir="emergent")
scenario = client.get_scenario("S_EMG_001")
bundle = client.get_scenario_bundle("S_EMG_001")
ehr = client.get_user_ehr("U_EMG_001")
signals = client.get_user_signals("U_EMG_001")
```

## 测试数据位置
- `data/diagnosis_system_fixtures/emergent/` - 紧急场景
- `data/diagnosis_system_fixtures/nonurgent/` - 非紧急场景

## API 端点
通过 Flask 路由 `/api/diagnosis-system/triage-view` 访问。

