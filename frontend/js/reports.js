// 报告管理模块

class ReportsManager {
    constructor() {
        this.reports = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.searchQuery = '';
        this.filterType = 'all';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadReports();
    }

    setupEventListeners() {
        // 生成报告表单
        const reportForm = document.getElementById('reportForm');
        if (reportForm) {
            reportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleReportSubmit(e.target);
            });
        }

        // 搜索和过滤
        const reportSearch = document.getElementById('reportSearch');
        if (reportSearch) {
            reportSearch.addEventListener('input', Utils.debounce((e) => {
                this.searchReports(e.target.value);
            }, 300));
        }

        const reportFilter = document.getElementById('reportFilter');
        if (reportFilter) {
            reportFilter.addEventListener('change', (e) => {
                this.filterReports(e.target.value);
            });
        }

        // 批量操作
        document.getElementById('bulkExportReports')?.addEventListener('click', () => {
            this.bulkExportReports();
        });

        document.getElementById('bulkDeleteReports')?.addEventListener('click', () => {
            this.bulkDeleteReports();
        });
    }

    async loadReports() {
        try {
            this.reports = await this.fetchReports();
            this.renderReportsTable();
            this.updateReportsPagination();
        } catch (error) {
            console.error('Failed to load reports:', error);
            window.app.showNotification('加载报告数据失败', 'error');
        }
    }

    async fetchReports() {
        // 模拟API调用
        return new Promise(resolve => {
            setTimeout(() => {
                const sampleReports = [
                    {
                        id: 'R001',
                        patientId: 'P001',
                        patientName: '张三',
                        type: 'compliance',
                        title: '服药依从性评估报告',
                        status: 'completed',
                        createdAt: '2024-01-15T10:30:00',
                        completedAt: '2024-01-15T11:45:00',
                        aiScore: 85,
                        doctorFeedback: true,
                        exportFormats: ['html', 'pdf']
                    },
                    {
                        id: 'R002',
                        patientId: 'P002',
                        patientName: '李四',
                        type: 'triage',
                        title: '分诊评估报告',
                        status: 'processing',
                        createdAt: '2024-01-14T14:20:00',
                        completedAt: null,
                        aiScore: null,
                        doctorFeedback: false,
                        exportFormats: []
                    },
                    {
                        id: 'R003',
                        patientId: 'P001',
                        patientName: '张三',
                        type: 'compliance',
                        title: '健康监测报告',
                        status: 'pending_feedback',
                        createdAt: '2024-01-13T09:15:00',
                        completedAt: '2024-01-13T10:30:00',
                        aiScore: 92,
                        doctorFeedback: false,
                        exportFormats: ['html']
                    }
                ];
                resolve(sampleReports);
            }, 500);
        });
    }

    renderReportsTable() {
        const tbody = document.querySelector('#reportsTable tbody');
        if (!tbody) return;

        const filteredReports = this.getFilteredReports();
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageReports = filteredReports.slice(startIndex, endIndex);

        if (pageReports.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center">
                        <div class="empty-state">
                            <i class="fas fa-file-medical"></i>
                            <h3>暂无报告数据</h3>
                            <p>点击"生成报告"开始创建您的第一个报告</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = pageReports.map(report => `
            <tr>
                <td>
                    <input type="checkbox" class="report-checkbox" data-report-id="${report.id}">
                </td>
                <td>
                    <div>
                        <strong>${report.id}</strong>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${report.title}</strong>
                        <div class="text-sm text-gray-500">${report.patientName} (${report.patientId})</div>
                    </div>
                </td>
                <td>
                    <span class="status-badge ${report.type === 'compliance' ? 'info' : 'warning'}">
                        ${this.getReportTypeText(report.type)}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${this.getStatusClass(report.status)}">
                        ${this.getStatusText(report.status)}
                    </span>
                </td>
                <td>${Utils.formatDate(report.createdAt)}</td>
                <td>
                    ${report.aiScore ? `
                        <div class="flex items-center gap-2">
                            <span>${report.aiScore}/100</span>
                            <div class="progress" style="width: 60px;">
                                <div class="progress-bar" style="width: ${report.aiScore}%"></div>
                            </div>
                        </div>
                    ` : '-'}
                </td>
                <td>
                    ${report.doctorFeedback ? 
                        '<i class="fas fa-check text-green-500"></i>' : 
                        '<i class="fas fa-clock text-gray-400"></i>'
                    }
                </td>
                <td>
                    <div class="flex gap-2">
                        <button class="btn btn-sm btn-outline" onclick="reportsManager.viewReport('${report.id}')"
                                title="查看报告">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="reportsManager.downloadReport('${report.id}')"
                                title="下载报告" ${report.status !== 'completed' ? 'disabled' : ''}>
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="reportsManager.shareReport('${report.id}')"
                                title="分享报告" ${report.status !== 'completed' ? 'disabled' : ''}>
                            <i class="fas fa-share"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="reportsManager.deleteReport('${report.id}')"
                                title="删除报告">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // 设置checkbox事件
        tbody.querySelectorAll('.report-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateBulkReportActions();
            });
        });
    }

    getFilteredReports() {
        let filtered = this.reports;

        // 按搜索条件过滤
        if (this.searchQuery) {
            filtered = filtered.filter(report => 
                report.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                report.patientName.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                report.id.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        }

        // 按类型过滤
        if (this.filterType && this.filterType !== 'all') {
            filtered = filtered.filter(report => report.type === this.filterType);
        }

        return filtered;
    }

    getReportTypeText(type) {
        const types = {
            compliance: '依从性评估',
            triage: '分诊评估',
            monitoring: '健康监测'
        };
        return types[type] || type;
    }

    getStatusText(status) {
        const statuses = {
            pending: '待处理',
            processing: '处理中',
            completed: '已完成',
            pending_feedback: '待反馈',
            failed: '失败'
        };
        return statuses[status] || status;
    }

    getStatusClass(status) {
        const classes = {
            pending: 'warning',
            processing: 'info',
            completed: 'success',
            pending_feedback: 'warning',
            failed: 'danger'
        };
        return classes[status] || 'secondary';
    }

    updateReportsPagination() {
        const filteredReports = this.getFilteredReports();
        const totalPages = Math.ceil(filteredReports.length / this.pageSize);
        
        const pagination = document.querySelector('#reportsPagination');
        if (!pagination) return;

        let paginationHTML = `
            <button class="btn btn-outline" ${this.currentPage === 1 ? 'disabled' : ''} 
                    onclick="reportsManager.goToReportPage(${this.currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHTML += `
                    <button class="btn ${i === this.currentPage ? 'btn-primary' : 'btn-outline'}"
                            onclick="reportsManager.goToReportPage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        paginationHTML += `
            <button class="btn btn-outline" ${this.currentPage === totalPages ? 'disabled' : ''}
                    onclick="reportsManager.goToReportPage(${this.currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;

        pagination.innerHTML = paginationHTML;
    }

    goToReportPage(page) {
        const filteredReports = this.getFilteredReports();
        const totalPages = Math.ceil(filteredReports.length / this.pageSize);
        
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderReportsTable();
            this.updateReportsPagination();
        }
    }

    searchReports(query) {
        this.searchQuery = query;
        this.currentPage = 1;
        this.renderReportsTable();
        this.updateReportsPagination();
    }

    filterReports(type) {
        this.filterType = type;
        this.currentPage = 1;
        this.renderReportsTable();
        this.updateReportsPagination();
    }

    async handleReportSubmit(form) {
        const formData = new FormData(form);
        const reportData = {
            patientId: formData.get('patientId'),
            type: formData.get('reportType'),
            title: formData.get('title'),
            description: formData.get('description')
        };

        // 验证表单
        if (!reportData.patientId || !reportData.type || !reportData.title) {
            window.app.showNotification('请填写必要的报告信息', 'error');
            return;
        }

        try {
            // 显示生成进度
            const progressModal = this.showReportProgress();
            
            // 模拟报告生成过程
            await this.generateReport(reportData, progressModal);
            
            // 重新加载报告列表
            await this.loadReports();
            
            // 关闭模态框
            window.app.closeAllModals();
            form.reset();
            
        } catch (error) {
            console.error('Report generation failed:', error);
            window.app.showNotification('报告生成失败', 'error');
        }
    }

    showReportProgress() {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>正在生成报告</h3>
                </div>
                <div class="modal-body">
                    <div class="progress-container">
                        <div class="progress">
                            <div class="progress-bar" id="reportProgress" style="width: 0%"></div>
                        </div>
                        <div class="progress-text" id="progressText">准备中...</div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        return modal;
    }

    async generateReport(reportData, progressModal) {
        const progressBar = progressModal.querySelector('#reportProgress');
        const progressText = progressModal.querySelector('#progressText');
        
        const steps = [
            { text: '正在加载患者数据...', progress: 20 },
            { text: '正在分析健康指标...', progress: 40 },
            { text: '正在生成AI评估...', progress: 60 },
            { text: '正在编译报告内容...', progress: 80 },
            { text: '正在保存报告...', progress: 90 },
            { text: '报告生成完成！', progress: 100 }
        ];

        for (const step of steps) {
            progressText.textContent = step.text;
            progressBar.style.width = `${step.progress}%`;
            
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // 创建新报告记录
        const newReport = {
            id: this.generateReportId(),
            patientId: reportData.patientId,
            patientName: this.getPatientName(reportData.patientId),
            type: reportData.type,
            title: reportData.title,
            status: 'completed',
            createdAt: new Date().toISOString(),
            completedAt: new Date().toISOString(),
            aiScore: Math.floor(Math.random() * 30) + 70, // 70-100
            doctorFeedback: false,
            exportFormats: ['html', 'pdf']
        };

        this.reports.unshift(newReport);

        // 关闭进度模态框
        setTimeout(() => {
            progressModal.remove();
            window.app.showNotification('报告生成成功', 'success');
        }, 1000);
    }

    generateReportId() {
        const prefix = 'R';
        const number = (this.reports.length + 1).toString().padStart(3, '0');
        return prefix + number;
    }

    getPatientName(patientId) {
        // 这里应该从患者管理器获取患者信息
        const patientNames = {
            'P001': '张三',
            'P002': '李四',
            'P003': '王五'
        };
        return patientNames[patientId] || '未知患者';
    }

    viewReport(reportId) {
        const report = this.reports.find(r => r.id === reportId);
        if (!report) return;

        // 创建报告预览窗口
        this.openReportViewer(report);
    }

    openReportViewer(report) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px;">
                <div class="modal-header">
                    <h3>${report.title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="report-viewer">
                        <div class="report-meta">
                            <div><strong>患者:</strong> ${report.patientName} (${report.patientId})</div>
                            <div><strong>类型:</strong> ${this.getReportTypeText(report.type)}</div>
                            <div><strong>生成时间:</strong> ${Utils.formatDate(report.createdAt)}</div>
                            <div><strong>AI评分:</strong> ${report.aiScore || 'N/A'}</div>
                        </div>
                        <hr>
                        <div class="report-content">
                            <h4>报告摘要</h4>
                            <p>这是一个示例报告预览。在实际应用中，这里会显示完整的报告内容，包括患者健康数据分析、AI生成的建议以及医生反馈等信息。</p>
                            
                            <h4>主要发现</h4>
                            <ul>
                                <li>患者整体健康状况良好</li>
                                <li>血压控制在正常范围内</li>
                                <li>血糖水平需要持续监测</li>
                                <li>建议调整用药方案</li>
                            </ul>
                            
                            <h4>医生建议</h4>
                            <p>建议患者继续现有治疗方案，并定期复查相关指标。如有不适，及时就医。</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="reportsManager.downloadReport('${report.id}')">
                        <i class="fas fa-download"></i> 下载报告
                    </button>
                    <button class="btn btn-outline modal-close">关闭</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 添加关闭事件
        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.remove();
            });
        });
    }

    downloadReport(reportId) {
        const report = this.reports.find(r => r.id === reportId);
        if (!report || report.status !== 'completed') {
            window.app.showNotification('报告尚未完成或不存在', 'warning');
            return;
        }

        // 模拟下载报告
        const reportContent = this.generateReportContent(report);
        Utils.downloadFile(reportContent, `${report.id}_${report.title}.html`, 'text/html');
        window.app.showNotification('报告下载成功', 'success');
    }

    generateReportContent(report) {
        return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${report.title}</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; margin: 40px; }
        .header { border-bottom: 2px solid #4f46e5; padding-bottom: 20px; margin-bottom: 30px; }
        .meta { background: #f9fafb; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        h1 { color: #4f46e5; }
        h2 { color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>${report.title}</h1>
        <p>报告编号：${report.id}</p>
    </div>
    
    <div class="meta">
        <p><strong>患者姓名：</strong>${report.patientName}</p>
        <p><strong>患者ID：</strong>${report.patientId}</p>
        <p><strong>报告类型：</strong>${this.getReportTypeText(report.type)}</p>
        <p><strong>生成时间：</strong>${Utils.formatDate(report.createdAt)}</p>
        <p><strong>AI评分：</strong>${report.aiScore}/100</p>
    </div>
    
    <div class="section">
        <h2>执行摘要</h2>
        <p>本报告基于患者的健康数据和医疗记录，通过AI分析生成。报告包含了患者的健康状况评估、风险分析和个性化建议。</p>
    </div>
    
    <div class="section">
        <h2>主要发现</h2>
        <ul>
            <li>患者整体健康状况评估：良好</li>
            <li>慢性病管理依从性：${report.aiScore}%</li>
            <li>风险等级：中等</li>
            <li>需要特别关注的指标：血糖、血压</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>建议和后续行动</h2>
        <ol>
            <li>继续遵医嘱服药</li>
            <li>定期监测血糖和血压</li>
            <li>保持健康的生活方式</li>
            <li>按时复诊</li>
        </ol>
    </div>
    
    <div class="footer">
        <p style="color: #6b7280; font-size: 14px;">
            此报告由慢性病管理系统自动生成，仅供参考。如有疑问，请咨询专业医生。
        </p>
    </div>
</body>
</html>
        `;
    }

    shareReport(reportId) {
        const report = this.reports.find(r => r.id === reportId);
        if (!report || report.status !== 'completed') {
            window.app.showNotification('报告尚未完成或不存在', 'warning');
            return;
        }

        // 生成分享链接（模拟）
        const shareUrl = `${window.location.origin}/reports/${reportId}`;
        
        // 复制到剪贴板
        navigator.clipboard.writeText(shareUrl).then(() => {
            window.app.showNotification('分享链接已复制到剪贴板', 'success');
        }).catch(() => {
            window.app.showNotification('复制失败，请手动复制链接', 'warning');
        });
    }

    deleteReport(reportId) {
        if (confirm('确定要删除这个报告吗？此操作不可恢复。')) {
            this.reports = this.reports.filter(r => r.id !== reportId);
            this.renderReportsTable();
            this.updateReportsPagination();
            window.app.showNotification('报告删除成功', 'success');
        }
    }

    updateBulkReportActions() {
        const checkboxes = document.querySelectorAll('.report-checkbox:checked');
        const bulkActions = document.querySelector('.bulk-report-actions');
        
        if (bulkActions) {
            bulkActions.style.display = checkboxes.length > 0 ? 'flex' : 'none';
        }
    }

    bulkExportReports() {
        const selected = this.getSelectedReports();
        if (selected.length === 0) {
            window.app.showNotification('请选择要导出的报告', 'warning');
            return;
        }

        // 批量导出为ZIP文件（模拟）
        window.app.showNotification(`正在导出 ${selected.length} 个报告...`, 'info');
        
        setTimeout(() => {
            window.app.showNotification(`已导出 ${selected.length} 个报告`, 'success');
        }, 2000);
    }

    bulkDeleteReports() {
        const selected = this.getSelectedReports();
        if (selected.length === 0) {
            window.app.showNotification('请选择要删除的报告', 'warning');
            return;
        }

        if (confirm(`确定要删除 ${selected.length} 个报告吗？此操作不可恢复。`)) {
            const selectedIds = selected.map(r => r.id);
            this.reports = this.reports.filter(r => !selectedIds.includes(r.id));
            this.renderReportsTable();
            this.updateReportsPagination();
            window.app.showNotification(`已删除 ${selected.length} 个报告`, 'success');
        }
    }

    getSelectedReports() {
        const checkboxes = document.querySelectorAll('.report-checkbox:checked');
        const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.reportId);
        return this.reports.filter(r => selectedIds.includes(r.id));
    }
}

// 导出
window.ReportsManager = ReportsManager;