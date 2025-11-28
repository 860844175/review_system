# Task Assignment Module

## 概述

任务分配模块负责将审核任务分配给合适的医生。

## 目录结构

```
task_assignment/
├── __init__.py           # 模块初始化
├── assigner.py           # 任务分配器核心类
├── client.py             # 审核平台客户端（用于获取医生信息）
├── strategies/           # 分配策略目录
│   └── __init__.py
└── README.md             # 本文档
```

## 设计目标

1. **独立性**：独立于任务生成模块，可单独测试和扩展
2. **可扩展性**：支持多种分配策略（轮询、负载均衡、专业匹配等）
3. **可配置性**：通过配置切换不同的分配策略

## 接口设计

### TaskAssigner

主要的分配器类，负责将任务分配给医生。

```python
from task_assignment import TaskAssigner

assigner = TaskAssigner(strategy="round_robin")
result = assigner.assign_task(
    user_id="...",
    scenario_id="...",
    task_id="..."
)
# result.doctor_id 包含分配的医生ID
```

### AssignmentResult

分配结果数据类：

- `doctor_id`: 分配的医生ID
- `assignment_reason`: 分配理由
- `strategy_used`: 使用的策略名称

## 待实现功能

- [ ] 轮询分配策略 (round_robin)
- [ ] 负载均衡策略 (load_balance)
- [ ] 从审核平台获取医生列表
- [ ] 获取医生当前任务负载
- [ ] 紧急任务优先匹配
- [ ] 专业领域匹配

## 使用示例

```python
from task_assignment import TaskAssigner

# 创建分配器
assigner = TaskAssigner(strategy="round_robin")

# 分配任务
result = assigner.assign_task(
    user_id="YZerVgaQTCuSHtEkZyguV5",
    scenario_id="S29VChQyexr7a6GkxETbmq",
    task_id="gfv93fX6aTGOby3ct0r2ha",
    urgency_level="urgent"  # 可选参数
)

print(f"分配的医生ID: {result.doctor_id}")
print(f"分配理由: {result.assignment_reason}")
```

## 集成点

任务分配模块将在以下位置被调用：

1. **任务创建流程** (`simple_server.py` 的 `create_review_task_from_system` 函数)
   - 任务创建后 → 分配医生 → 注册到审核平台

2. **未来可能的定时任务**
   - 自动重新分配未分配的任务

## 注意事项

- 当前版本为占位实现，具体策略需要后续开发
- 需要与审核平台API集成以获取医生信息
- 建议实现分配历史的记录功能，便于分析和优化

