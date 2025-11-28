// 紧迫程度管理模块

class UrgencyManager {
    constructor() {
        this.urgencyLevels = {
            'urgent': {
                text: '🔴 紧急级',
                class: 'urgency-urgent',
                color: '#dc2626',
                description: '需要医生立即介入决策'
            },
            'attention': {
                text: '🟡 关注级',
                class: 'urgency-attention',
                color: '#f59e0b',
                description: '需要医生定期审阅'
            },
            'stable': {
                text: '🟢 稳定级',
                class: 'urgency-stable',
                color: '#10b981',
                description: '病情稳定，AI建议即可'
            }
        };
    }

    /**
     * 渲染紧迫程度徽章
     */
    renderUrgencyBadge(level, riskScore = null) {
        const urgency = this.urgencyLevels[level] || this.urgencyLevels['attention'];
        
        return `
            <span class="urgency-badge ${urgency.class}" title="${urgency.description}">
                ${urgency.text}
                ${riskScore ? `<span class="risk-score-small">${riskScore}</span>` : ''}
            </span>
        `;
    }

    /**
     * 渲染紧迫程度卡片（用于患者列表）
     */
    renderUrgencyCard(urgencyData) {
        const urgency = this.urgencyLevels[urgencyData.level] || this.urgencyLevels['attention'];
        
        return `
            <div class="urgency-card ${urgency.class}">
                <div class="urgency-card-header">
                    <span class="urgency-icon">${urgency.text.split(' ')[0]}</span>
                    <div class="urgency-card-info">
                        <strong>${urgency.text}</strong>
                        <span class="risk-score-badge">${urgencyData.risk_score}/100</span>
                    </div>
                </div>
                <div class="urgency-card-body">
                    <p class="urgency-reasoning">${urgencyData.reasoning}</p>
                    ${urgencyData.key_concerns && urgencyData.key_concerns.length > 0 ? `
                        <div class="urgency-concerns">
                            <strong>关键关注：</strong>
                            <ul>
                                ${urgencyData.key_concerns.map(c => `<li>${c}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    <div class="urgency-actions">
                        <span><strong>建议：</strong>${urgencyData.suggested_action}</span>
                        <span><strong>随访：</strong>${urgencyData.follow_up_days}天后</span>
                    </div>
                </div>
                ${urgencyData.doctor_intervention_needed ? `
                    <div class="urgency-card-footer">
                        <button class="btn btn-sm btn-primary" onclick="urgencyManager.handleDoctorIntervention('${urgencyData.patient_id}')">
                            <i class="fas fa-user-md"></i> 医生介入
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * 获取紧迫程度颜色
     */
    getUrgencyColor(level) {
        return this.urgencyLevels[level]?.color || '#6b7280';
    }

    /**
     * 手动调整紧迫程度（医生操作）
     */
    async adjustUrgencyLevel(patientId, reportId, newLevel, reason) {
        try {
            // 调用API调整紧迫程度
            const response = await fetch(`/api/reports/${reportId}/urgency`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    patient_id: patientId,
                    new_level: newLevel,
                    reason: reason,
                    adjusted_by: 'doctor',
                    adjusted_at: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error('调整紧迫程度失败');
            }

            const data = await response.json();
            
            window.app.showNotification('紧迫程度已调整', 'success');
            
            // 刷新报告显示
            this.refreshReportView(reportId);
            
            return data;
        } catch (error) {
            console.error('调整紧迫程度失败:', error);
            window.app.showNotification('调整失败: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * 显示紧迫程度调整对话框
     */
    showAdjustDialog(patientId, reportId, currentLevel) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal urgency-adjust-modal">
                <div class="modal-header">
                    <h3>调整紧迫程度</h3>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <p>当前级别：${this.urgencyLevels[currentLevel].text}</p>
                    
                    <div class="form-group">
                        <label>调整为：</label>
                        <select id="newUrgencyLevel" class="form-control">
                            <option value="urgent" ${currentLevel === 'urgent' ? 'selected' : ''}>
                                🔴 紧急级 - 需要医生立即介入
                            </option>
                            <option value="attention" ${currentLevel === 'attention' ? 'selected' : ''}>
                                🟡 关注级 - 需要医生定期审阅
                            </option>
                            <option value="stable" ${currentLevel === 'stable' ? 'selected' : ''}>
                                🟢 稳定级 - AI建议即可
                            </option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>调整理由：<span class="text-danger">*</span></label>
                        <textarea id="adjustReason" class="form-control" rows="3" 
                                  placeholder="请说明调整理由..." required></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                        取消
                    </button>
                    <button class="btn btn-primary" onclick="urgencyManager.submitAdjustment('${patientId}', '${reportId}')">
                        确认调整
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    /**
     * 提交紧迫程度调整
     */
    async submitAdjustment(patientId, reportId) {
        const newLevel = document.getElementById('newUrgencyLevel').value;
        const reason = document.getElementById('adjustReason').value.trim();
        
        if (!reason) {
            window.app.showNotification('请填写调整理由', 'warning');
            return;
        }
        
        try {
            await this.adjustUrgencyLevel(patientId, reportId, newLevel, reason);
            document.querySelector('.modal-overlay').remove();
        } catch (error) {
            // 错误已在adjustUrgencyLevel中处理
        }
    }

    /**
     * 处理医生介入操作
     */
    async handleDoctorIntervention(patientId) {
        // 可以实现跳转到医生工作台、发送通知等
        console.log('医生介入处理:', patientId);
        
        // 示例：跳转到患者详情页
        window.location.href = `patients.html?id=${patientId}&action=intervention`;
        
        // 或者显示快捷操作菜单
        // this.showInterventionMenu(patientId);
    }

    /**
     * 刷新报告视图
     */
    refreshReportView(reportId) {
        // 重新加载报告数据
        if (window.reportsManager) {
            window.reportsManager.loadReports();
        }
        
        // 如果在报告详情页，重新加载详情
        const reportFrame = document.getElementById('reportFrame');
        if (reportFrame && reportFrame.src.includes(reportId)) {
            reportFrame.src = reportFrame.src; // 重新加载iframe
        }
    }

    /**
     * 获取紧迫程度统计
     */
    getUrgencyStats(reports) {
        const stats = {
            urgent: 0,
            attention: 0,
            stable: 0,
            total: 0
        };

        reports.forEach(report => {
            if (report.urgency && report.urgency.level) {
                stats[report.urgency.level]++;
                stats.total++;
            }
        });

        return stats;
    }

    /**
     * 渲染紧迫程度统计图表
     */
    renderUrgencyStatsChart(stats) {
        return `
            <div class="urgency-stats">
                <div class="urgency-stat-item urgency-urgent">
                    <span class="urgency-stat-icon">🔴</span>
                    <div class="urgency-stat-info">
                        <span class="urgency-stat-label">紧急级</span>
                        <span class="urgency-stat-value">${stats.urgent}</span>
                    </div>
                </div>
                <div class="urgency-stat-item urgency-attention">
                    <span class="urgency-stat-icon">🟡</span>
                    <div class="urgency-stat-info">
                        <span class="urgency-stat-label">关注级</span>
                        <span class="urgency-stat-value">${stats.attention}</span>
                    </div>
                </div>
                <div class="urgency-stat-item urgency-stable">
                    <span class="urgency-stat-icon">🟢</span>
                    <div class="urgency-stat-info">
                        <span class="urgency-stat-label">稳定级</span>
                        <span class="urgency-stat-value">${stats.stable}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 按紧迫程度排序报告列表
     */
    sortReportsByUrgency(reports) {
        const urgencyOrder = { urgent: 0, attention: 1, stable: 2 };
        
        return reports.sort((a, b) => {
            const levelA = urgencyOrder[a.urgency?.level] ?? 3;
            const levelB = urgencyOrder[b.urgency?.level] ?? 3;
            
            if (levelA !== levelB) {
                return levelA - levelB;
            }
            
            // 同级别按风险评分降序
            const scoreA = a.urgency?.risk_score ?? 0;
            const scoreB = b.urgency?.risk_score ?? 0;
            return scoreB - scoreA;
        });
    }

    /**
     * 过滤特定紧迫程度的报告
     */
    filterReportsByUrgency(reports, level) {
        if (!level || level === 'all') {
            return reports;
        }
        
        return reports.filter(report => report.urgency?.level === level);
    }
}

// 创建全局实例
window.urgencyManager = new UrgencyManager();
