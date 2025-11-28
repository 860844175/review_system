# 任务分配模块实现说明

## 实现概述

任务分配模块已实现基于负载均衡的任务分配策略，根据医生的未审核任务数量（cnt）和医生ID进行排序分配。

## 核心功能

### 1. 测试医生数据

**文件位置**: `data/test_doctors.json`

创建了3个测试医生，格式仿照 `requests_md/审核系统方.md` 中的接口规范：

- **张医生** (doctor001): 主任医师，有2个未审核任务
- **李医生** (doctor002): 副主任医师，有1个未审核任务  
- **王医生** (doctor003): 主治医师，有0个未审核任务

每个医生数据包含：
- 基本信息：id, name, phone, occupation, hospitalId, hospitalName
- 任务列表：tasks 字段，包含任务详情和状态（status: 0=未审核, 1=已审核）

### 2. 分配逻辑

**排序规则**: `(cnt, id)`

1. **cnt（任务数量）**: 优先按未审核任务数量升序排序
   - 只统计 `status=0` 的任务
   - 任务数量少的医生优先分配

2. **id（医生ID）**: 当任务数量相同时，按医生ID升序排序
   - 确保排序的稳定性和可预测性

### 3. 实现细节

#### ApprovalPlatformClient (`task_assignment/client.py`)

- ✅ `get_doctors()`: 从测试数据文件读取医生列表
- ✅ `get_doctors_with_task_counts()`: 获取医生列表并计算未审核任务数量
- ✅ `get_doctor_with_tasks()`: 获取指定医生的详细信息及任务列表
- ✅ 支持 `use_test_data` 模式，开发阶段使用本地测试数据

#### TaskAssigner (`task_assignment/assigner.py`)

- ✅ `assign_task()`: 分配任务给医生
- ✅ `_assign_with_load_balance()`: 负载均衡分配策略实现
  - 获取所有医生及其任务数量
  - 按 `(task_count, id)` 排序
  - 选择任务数量最少的医生
- ✅ 返回 `AssignmentResult`，包含医生ID、分配理由和策略名称

## 使用示例

```python
from task_assignment import TaskAssigner

# 创建分配器
assigner = TaskAssigner(strategy="load_balance")

# 分配任务
result = assigner.assign_task(
    user_id="user001",
    scenario_id="scenario001",
    task_id="task999",
    hospital_id=None  # 可选，指定医院ID
)

print(f"分配医生ID: {result.doctor_id}")
print(f"分配理由: {result.assignment_reason}")
print(f"使用策略: {result.strategy_used}")
```

## 测试验证

### 测试文件

1. **test_task_assignment.py**: 基础功能测试
2. **test_task_assignment_edge_cases.py**: 边缘情况测试（相同任务数量时的排序）

### 测试结果

✅ 所有测试通过

- ✅ 正确读取测试医生数据
- ✅ 正确计算未审核任务数量（只统计 status=0 的任务）
- ✅ 排序逻辑正确：先按任务数量，再按ID
- ✅ 分配逻辑正确：选择任务数量最少的医生

### 测试输出示例

```
排序结果（按 task_count, id）:
  1. 王医生 (ID: doctor003): cnt=0
  2. 李医生 (ID: doctor002): cnt=1
  3. 张医生 (ID: doctor001): cnt=2

分配结果: doctor003
分配理由: 负载均衡分配：医生 王医生 当前未审核任务数为 0，在所有可用医生中任务数量最少
```

## 数据结构

### 医生数据结构

```json
{
  "id": "doctor001",
  "name": "张医生",
  "occupation": "主任医师",
  "hospitalId": "hospital001",
  "hospitalName": "测试医院",
  "tasks": [
    {
      "id": "task001",
      "customerId": "patient001",
      "customerName": "患者A",
      "kind": "分诊评估",
      "url": "http://localhost:5001/review/triage?task_id=task001",
      "status": 0,  // 0=未审核, 1=已审核
      "createAt": "2025-01-20T10:00:00+08:00",
      "updateAt": "2025-01-20T10:00:00+08:00"
    }
  ]
}
```

### AssignmentResult

```python
@dataclass
class AssignmentResult:
    doctor_id: str              # 分配的医生ID
    assignment_reason: str      # 分配理由
    strategy_used: str          # 使用的策略名称
```

## 下一步

1. [ ] 集成到任务创建流程（`simple_server.py` 的 `create_review_task_from_system`）
2. [ ] 实现真实API调用（替代测试数据）
3. [ ] 支持更多分配策略（round_robin、urgent_match等）
4. [ ] 添加分配历史记录功能
5. [ ] 支持医院过滤和医生过滤

## 注意事项

- 当前使用测试数据模式（`use_test_data=True`）
- 任务数量只统计未审核任务（`status=0`）
- 排序逻辑确保稳定性和可预测性
- 所有测试数据格式遵循审核系统API规范

