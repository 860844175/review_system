// 反馈管理模块

class FeedbackManager {
    constructor() {
        this.feedback = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.searchQuery = '';
        this.filterStatus = 'all';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFeedback();
    }

    setupEventListeners() {
        // 反馈表单
        const feedbackForm = document.getElementById('feedbackForm');
        if (feedbackForm) {
            feedbackForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFeedbackSubmit(e.target);
            });
        }

        // 搜索和过滤
        const feedbackSearch = document.getElementById('feedbackSearch');
        if (feedbackSearch) {
            feedbackSearch.addEventListener('input', Utils.debounce((e) => {
                this.searchFeedback(e.target.value);
            }, 300));
        }

        const feedbackFilter = document.getElementById('feedbackFilter');
        if (feedbackFilter) {
            feedbackFilter.addEventListener('change', (e) => {
                this.filterFeedback(e.target.value);
            });
        }

        // 批量操作
        document.getElementById('bulkMarkProcessed')?.addEventListener('click', () => {
            this.bulkMarkProcessed();
        });

        document.getElementById('bulkExportFeedback')?.addEventListener('click', () => {
            this.bulkExportFeedback();
        });
    }

    async loadFeedback() {
        try {
            this.feedback = await this.fetchFeedback();
            this.renderFeedbackTable();
            this.updateFeedbackPagination();
        } catch (error) {
            console.error('Failed to load feedback:', error);
            window.app.showNotification('加载反馈数据失败', 'error');
        }
    }

    async fetchFeedback() {
        // 模拟API调用
        return new Promise(resolve => {
            setTimeout(() => {
                const sampleFeedback = [
                    {
                        id: 'F001',
                        reportId: 'R001',
                        reportTitle: '服药依从性评估报告',
                        patientName: '张三',
                        doctorName: '李医生',
                        doctorId: 'D001',
                        type: 'review',
                        priority: 'high',
                        status: 'pending',
                        content: '患者的血糖控制情况需要进一步关注，建议调整胰岛素用量。',
                        createdAt: '2024-01-15T14:30:00',
                        processedAt: null,
                        tags: ['血糖', '胰岛素', '用量调整']
                    },
                    {
                        id: 'F002',
                        reportId: 'R003',
                        reportTitle: '健康监测报告',
                        patientName: '张三',
                        doctorName: '王医生',
                        doctorId: 'D002',
                        type: 'suggestion',
                        priority: 'medium',
                        status: 'processed',
                        content: '整体报告质量良好，建议增加生活方式指导部分。',
                        createdAt: '2024-01-14T16:45:00',
                        processedAt: '2024-01-15T09:20:00',
                        tags: ['生活方式', '指导', '报告优化']
                    },
                    {
                        id: 'F003',
                        reportId: 'R002',
                        reportTitle: '分诊评估报告',
                        patientName: '李四',
                        doctorName: '赵医生',
                        doctorId: 'D003',
                        type: 'correction',
                        priority: 'high',
                        status: 'in_progress',
                        content: '分诊建议过于保守，患者症状表明需要更积极的治疗方案。',
                        createdAt: '2024-01-13T11:15:00',
                        processedAt: null,
                        tags: ['分诊', '治疗方案', '症状评估']
                    }
                ];
                resolve(sampleFeedback);
            }, 500);
        });
    }

    renderFeedbackTable() {
        const tbody = document.querySelector('#feedbackTable tbody');
        if (!tbody) return;

        const filteredFeedback = this.getFilteredFeedback();
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageFeedback = filteredFeedback.slice(startIndex, endIndex);

        if (pageFeedback.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center">
                        <div class="empty-state">
                            <i class="fas fa-comments"></i>
                            <h3>暂无反馈数据</h3>
                            <p>还没有收到医生的反馈意见</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = pageFeedback.map(feedback => `
            <tr>
                <td>
                    <input type="checkbox" class="feedback-checkbox" data-feedback-id="${feedback.id}">
                </td>
                <td>
                    <div>
                        <strong>${feedback.id}</strong>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${feedback.reportTitle}</strong>
                        <div class="text-sm text-gray-500">报告ID: ${feedback.reportId}</div>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${feedback.patientName}</strong>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${feedback.doctorName}</strong>
                        <div class="text-sm text-gray-500">${feedback.doctorId}</div>
                    </div>
                </td>
                <td>
                    <span class="status-badge ${this.getFeedbackTypeClass(feedback.type)}">
                        ${this.getFeedbackTypeText(feedback.type)}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${feedback.priority}">
                        ${this.getPriorityText(feedback.priority)}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${this.getStatusClass(feedback.status)}">
                        ${this.getStatusText(feedback.status)}
                    </span>
                </td>
                <td>${Utils.formatDate(feedback.createdAt)}</td>
                <td>
                    <div class="flex gap-2">
                        <button class="btn btn-sm btn-outline" onclick="feedbackManager.viewFeedback('${feedback.id}')"
                                title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="feedbackManager.processFeedback('${feedback.id}')"
                                title="处理反馈" ${feedback.status === 'processed' ? 'disabled' : ''}>
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="feedbackManager.replyFeedback('${feedback.id}')"
                                title="回复">
                            <i class="fas fa-reply"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // 设置checkbox事件
        tbody.querySelectorAll('.feedback-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateBulkFeedbackActions();
            });
        });
    }

    getFilteredFeedback() {
        let filtered = this.feedback;

        // 按搜索条件过滤
        if (this.searchQuery) {
            filtered = filtered.filter(feedback => 
                feedback.reportTitle.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                feedback.patientName.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                feedback.doctorName.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                feedback.content.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        }

        // 按状态过滤
        if (this.filterStatus && this.filterStatus !== 'all') {
            filtered = filtered.filter(feedback => feedback.status === this.filterStatus);
        }

        return filtered;
    }

    getFeedbackTypeText(type) {
        const types = {
            review: '审核意见',
            suggestion: '改进建议',
            correction: '修正要求',
            question: '疑问反馈'
        };
        return types[type] || type;
    }

    getFeedbackTypeClass(type) {
        const classes = {
            review: 'info',
            suggestion: 'success',
            correction: 'warning',
            question: 'secondary'
        };
        return classes[type] || 'secondary';
    }

    getPriorityText(priority) {
        const priorities = {
            high: '高优先级',
            medium: '中优先级',
            low: '低优先级'
        };
        return priorities[priority] || priority;
    }

    getStatusText(status) {
        const statuses = {
            pending: '待处理',
            in_progress: '处理中',
            processed: '已处理',
            rejected: '已拒绝'
        };
        return statuses[status] || status;
    }

    getStatusClass(status) {
        const classes = {
            pending: 'warning',
            in_progress: 'info',
            processed: 'success',
            rejected: 'danger'
        };
        return classes[status] || 'secondary';
    }

    updateFeedbackPagination() {
        const filteredFeedback = this.getFilteredFeedback();
        const totalPages = Math.ceil(filteredFeedback.length / this.pageSize);
        
        const pagination = document.querySelector('#feedbackPagination');
        if (!pagination) return;

        let paginationHTML = `
            <button class="btn btn-outline" ${this.currentPage === 1 ? 'disabled' : ''} 
                    onclick="feedbackManager.goToFeedbackPage(${this.currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHTML += `
                    <button class="btn ${i === this.currentPage ? 'btn-primary' : 'btn-outline'}"
                            onclick="feedbackManager.goToFeedbackPage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        paginationHTML += `
            <button class="btn btn-outline" ${this.currentPage === totalPages ? 'disabled' : ''}
                    onclick="feedbackManager.goToFeedbackPage(${this.currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;

        pagination.innerHTML = paginationHTML;
    }

    goToFeedbackPage(page) {
        const filteredFeedback = this.getFilteredFeedback();
        const totalPages = Math.ceil(filteredFeedback.length / this.pageSize);
        
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderFeedbackTable();
            this.updateFeedbackPagination();
        }
    }

    searchFeedback(query) {
        this.searchQuery = query;
        this.currentPage = 1;
        this.renderFeedbackTable();
        this.updateFeedbackPagination();
    }

    filterFeedback(status) {
        this.filterStatus = status;
        this.currentPage = 1;
        this.renderFeedbackTable();
        this.updateFeedbackPagination();
    }

    viewFeedback(feedbackId) {
        const feedback = this.feedback.find(f => f.id === feedbackId);
        if (!feedback) return;

        this.showFeedbackDetail(feedback);
    }

    showFeedbackDetail(feedback) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3>反馈详情 - ${feedback.id}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="feedback-detail">
                        <div class="feedback-meta">
                            <div class="meta-grid">
                                <div><strong>相关报告:</strong> ${feedback.reportTitle}</div>
                                <div><strong>患者:</strong> ${feedback.patientName}</div>
                                <div><strong>医生:</strong> ${feedback.doctorName}</div>
                                <div><strong>类型:</strong> ${this.getFeedbackTypeText(feedback.type)}</div>
                                <div><strong>优先级:</strong> ${this.getPriorityText(feedback.priority)}</div>
                                <div><strong>状态:</strong> ${this.getStatusText(feedback.status)}</div>
                                <div><strong>创建时间:</strong> ${Utils.formatDate(feedback.createdAt)}</div>
                                ${feedback.processedAt ? `<div><strong>处理时间:</strong> ${Utils.formatDate(feedback.processedAt)}</div>` : ''}
                            </div>
                        </div>
                        
                        <div class="feedback-content">
                            <h4>反馈内容</h4>
                            <div class="content-box">
                                ${feedback.content}
                            </div>
                        </div>
                        
                        ${feedback.tags.length > 0 ? `
                            <div class="feedback-tags">
                                <h4>标签</h4>
                                <div class="tags">
                                    ${feedback.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="feedback-actions-detail">
                            <h4>处理记录</h4>
                            <div class="action-timeline">
                                <div class="timeline-item">
                                    <i class="fas fa-plus-circle text-blue-500"></i>
                                    <div>
                                        <strong>反馈创建</strong>
                                        <div class="text-sm text-gray-500">${Utils.formatDate(feedback.createdAt)}</div>
                                    </div>
                                </div>
                                ${feedback.status === 'processed' ? `
                                    <div class="timeline-item">
                                        <i class="fas fa-check-circle text-green-500"></i>
                                        <div>
                                            <strong>反馈已处理</strong>
                                            <div class="text-sm text-gray-500">${Utils.formatDate(feedback.processedAt)}</div>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    ${feedback.status !== 'processed' ? `
                        <button class="btn btn-primary" onclick="feedbackManager.processFeedback('${feedback.id}'); this.closest('.modal').remove();">
                            <i class="fas fa-check"></i> 标记为已处理
                        </button>
                    ` : ''}
                    <button class="btn btn-outline" onclick="feedbackManager.replyFeedback('${feedback.id}')">
                        <i class="fas fa-reply"></i> 回复
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

    processFeedback(feedbackId) {
        const feedback = this.feedback.find(f => f.id === feedbackId);
        if (!feedback || feedback.status === 'processed') return;

        // 更新反馈状态
        feedback.status = 'processed';
        feedback.processedAt = new Date().toISOString();

        // 重新渲染表格
        this.renderFeedbackTable();
        
        window.app.showNotification('反馈已标记为已处理', 'success');
    }

    replyFeedback(feedbackId) {
        const feedback = this.feedback.find(f => f.id === feedbackId);
        if (!feedback) return;

        // 创建回复模态框
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>回复反馈 - ${feedback.id}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="original-feedback">
                        <h4>原始反馈</h4>
                        <div class="content-box">
                            ${feedback.content}
                        </div>
                    </div>
                    
                    <form id="replyForm">
                        <div class="form-group">
                            <label for="replyContent">回复内容</label>
                            <textarea id="replyContent" class="form-control" rows="6" 
                                      placeholder="请输入您的回复..." required></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="feedbackManager.submitReply('${feedbackId}', this.closest('.modal'))">
                        <i class="fas fa-paper-plane"></i> 发送回复
                    </button>
                    <button class="btn btn-outline modal-close">取消</button>
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

    submitReply(feedbackId, modal) {
        const replyContent = modal.querySelector('#replyContent').value;
        
        if (!replyContent.trim()) {
            window.app.showNotification('请输入回复内容', 'warning');
            return;
        }

        // 模拟发送回复
        window.app.showNotification('回复发送成功', 'success');
        modal.remove();

        // 这里可以添加将回复内容保存到数据库的逻辑
        console.log('Reply sent for feedback:', feedbackId, 'Content:', replyContent);
    }

    handleFeedbackSubmit(form) {
        const formData = new FormData(form);
        const newFeedback = {
            id: this.generateFeedbackId(),
            reportId: formData.get('reportId'),
            reportTitle: formData.get('reportTitle'),
            patientName: formData.get('patientName'),
            doctorName: formData.get('doctorName'),
            doctorId: formData.get('doctorId'),
            type: formData.get('feedbackType'),
            priority: formData.get('priority'),
            status: 'pending',
            content: formData.get('content'),
            createdAt: new Date().toISOString(),
            processedAt: null,
            tags: formData.get('tags') ? formData.get('tags').split(',').map(tag => tag.trim()) : []
        };

        // 验证表单
        if (!newFeedback.reportId || !newFeedback.content) {
            window.app.showNotification('请填写必要的反馈信息', 'error');
            return;
        }

        // 添加到反馈列表
        this.feedback.unshift(newFeedback);
        
        // 重新渲染表格
        this.renderFeedbackTable();
        this.updateFeedbackPagination();

        // 关闭模态框并重置表单
        window.app.closeAllModals();
        form.reset();
        
        window.app.showNotification('反馈提交成功', 'success');
    }

    generateFeedbackId() {
        const prefix = 'F';
        const number = (this.feedback.length + 1).toString().padStart(3, '0');
        return prefix + number;
    }

    updateBulkFeedbackActions() {
        const checkboxes = document.querySelectorAll('.feedback-checkbox:checked');
        const bulkActions = document.querySelector('.bulk-feedback-actions');
        
        if (bulkActions) {
            bulkActions.style.display = checkboxes.length > 0 ? 'flex' : 'none';
        }
    }

    bulkMarkProcessed() {
        const selected = this.getSelectedFeedback();
        if (selected.length === 0) {
            window.app.showNotification('请选择要处理的反馈', 'warning');
            return;
        }

        const pending = selected.filter(f => f.status !== 'processed');
        if (pending.length === 0) {
            window.app.showNotification('选中的反馈已经处理完成', 'info');
            return;
        }

        if (confirm(`确定要将 ${pending.length} 个反馈标记为已处理吗？`)) {
            pending.forEach(feedback => {
                feedback.status = 'processed';
                feedback.processedAt = new Date().toISOString();
            });

            this.renderFeedbackTable();
            window.app.showNotification(`已处理 ${pending.length} 个反馈`, 'success');
        }
    }

    bulkExportFeedback() {
        const selected = this.getSelectedFeedback();
        if (selected.length === 0) {
            window.app.showNotification('请选择要导出的反馈', 'warning');
            return;
        }

        const csvContent = this.convertFeedbackToCsv(selected);
        Utils.downloadFile(csvContent, 'feedback_export.csv', 'text/csv');
        window.app.showNotification(`已导出 ${selected.length} 个反馈`, 'success');
    }

    getSelectedFeedback() {
        const checkboxes = document.querySelectorAll('.feedback-checkbox:checked');
        const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.feedbackId);
        return this.feedback.filter(f => selectedIds.includes(f.id));
    }

    convertFeedbackToCsv(feedbackList) {
        const headers = ['ID', '报告标题', '患者姓名', '医生姓名', '类型', '优先级', '状态', '内容', '创建时间', '处理时间'];
        const rows = feedbackList.map(f => [
            f.id, f.reportTitle, f.patientName, f.doctorName,
            this.getFeedbackTypeText(f.type), this.getPriorityText(f.priority),
            this.getStatusText(f.status), f.content, 
            Utils.formatDate(f.createdAt), f.processedAt ? Utils.formatDate(f.processedAt) : ''
        ]);

        return [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\n');
    }
}

// 导出
window.FeedbackManager = FeedbackManager;