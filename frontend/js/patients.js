// 患者管理模块

class PatientsManager {
    constructor() {
        this.patients = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.searchQuery = '';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadPatients();
    }

    setupEventListeners() {
        // 添加患者表单
        const patientForm = document.getElementById('patientForm');
        if (patientForm) {
            patientForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handlePatientSubmit(e.target);
            });
        }

        // 搜索患者
        const patientSearch = document.getElementById('patientSearch');
        if (patientSearch) {
            patientSearch.addEventListener('input', Utils.debounce((e) => {
                this.searchPatients(e.target.value);
            }, 300));
        }

        // 批量操作
        document.getElementById('bulkExport')?.addEventListener('click', () => {
            this.bulkExport();
        });

        document.getElementById('bulkDelete')?.addEventListener('click', () => {
            this.bulkDelete();
        });

        // 导入患者数据
        document.getElementById('importPatients')?.addEventListener('change', (e) => {
            this.importPatients(e.target.files[0]);
        });
    }

    async loadPatients() {
        try {
            // 模拟加载患者数据
            this.patients = await this.fetchPatients();
            this.renderPatientsTable();
            this.updatePagination();
        } catch (error) {
            console.error('Failed to load patients:', error);
            window.app.showNotification('加载患者数据失败', 'error');
        }
    }

    async fetchPatients() {
        // 模拟API调用
        return new Promise(resolve => {
            setTimeout(() => {
                const samplePatients = [
                    {
                        id: 'P001',
                        name: '张三',
                        age: 65,
                        gender: '男',
                        diagnosis: '2型糖尿病,高血压',
                        phone: '13812345678',
                        email: 'zhangsan@example.com',
                        status: 'active',
                        riskLevel: 'medium',
                        lastVisit: '2024-01-15',
                        createdAt: '2023-12-01'
                    },
                    {
                        id: 'P002',
                        name: '李四',
                        age: 58,
                        gender: '女',
                        diagnosis: '高血压,冠心病',
                        phone: '13987654321',
                        email: 'lisi@example.com',
                        status: 'active',
                        riskLevel: 'high',
                        lastVisit: '2024-01-14',
                        createdAt: '2023-11-15'
                    },
                    {
                        id: 'P003',
                        name: '王五',
                        age: 72,
                        gender: '男',
                        diagnosis: '慢性肾病,糖尿病',
                        phone: '13456789012',
                        email: 'wangwu@example.com',
                        status: 'inactive',
                        riskLevel: 'low',
                        lastVisit: '2024-01-10',
                        createdAt: '2023-10-20'
                    }
                ];
                resolve(samplePatients);
            }, 500);
        });
    }

    renderPatientsTable() {
        const tbody = document.querySelector('#patientsTable tbody');
        if (!tbody) return;

        const filteredPatients = this.getFilteredPatients();
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pagePatients = filteredPatients.slice(startIndex, endIndex);

        if (pagePatients.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center">
                        <div class="empty-state">
                            <i class="fas fa-users"></i>
                            <h3>暂无患者数据</h3>
                            <p>点击"添加患者"开始管理您的患者信息</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = pagePatients.map(patient => `
            <tr>
                <td>
                    <input type="checkbox" class="patient-checkbox" data-patient-id="${patient.id}">
                </td>
                <td>
                    <div>
                        <strong>${patient.id}</strong>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${patient.name}</strong>
                        <div class="text-sm text-gray-500">${patient.age}岁 ${patient.gender}</div>
                    </div>
                </td>
                <td>${patient.diagnosis}</td>
                <td>
                    <div>${patient.phone}</div>
                    <div class="text-sm text-gray-500">${patient.email}</div>
                </td>
                <td>
                    <span class="status-badge ${patient.status}">
                        ${patient.status === 'active' ? '活跃' : '非活跃'}
                    </span>
                </td>
                <td>
                    <span class="status-badge ${patient.riskLevel}">
                        ${this.getRiskLevelText(patient.riskLevel)}
                    </span>
                </td>
                <td>${Utils.formatDate(patient.lastVisit)}</td>
                <td>
                    <div class="flex gap-2">
                        <button class="btn btn-sm btn-outline" onclick="patientsManager.editPatient('${patient.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="patientsManager.viewPatient('${patient.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="patientsManager.deletePatient('${patient.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // 设置checkbox事件
        tbody.querySelectorAll('.patient-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateBulkActions();
            });
        });
    }

    getFilteredPatients() {
        if (!this.searchQuery) return this.patients;

        return this.patients.filter(patient => 
            patient.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
            patient.id.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
            patient.diagnosis.toLowerCase().includes(this.searchQuery.toLowerCase())
        );
    }

    getRiskLevelText(level) {
        const texts = {
            high: '高风险',
            medium: '中风险',
            low: '低风险'
        };
        return texts[level] || level;
    }

    updatePagination() {
        const filteredPatients = this.getFilteredPatients();
        const totalPages = Math.ceil(filteredPatients.length / this.pageSize);
        
        const pagination = document.querySelector('.pagination');
        if (!pagination) return;

        let paginationHTML = `
            <button class="btn btn-outline" ${this.currentPage === 1 ? 'disabled' : ''} 
                    onclick="patientsManager.goToPage(${this.currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHTML += `
                    <button class="btn ${i === this.currentPage ? 'btn-primary' : 'btn-outline'}"
                            onclick="patientsManager.goToPage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        paginationHTML += `
            <button class="btn btn-outline" ${this.currentPage === totalPages ? 'disabled' : ''}
                    onclick="patientsManager.goToPage(${this.currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;

        pagination.innerHTML = paginationHTML;
    }

    goToPage(page) {
        const filteredPatients = this.getFilteredPatients();
        const totalPages = Math.ceil(filteredPatients.length / this.pageSize);
        
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderPatientsTable();
            this.updatePagination();
        }
    }

    searchPatients(query) {
        this.searchQuery = query;
        this.currentPage = 1;
        this.renderPatientsTable();
        this.updatePagination();
    }

    handlePatientSubmit(form) {
        const formData = new FormData(form);
        const patient = {
            id: formData.get('patientId') || this.generatePatientId(),
            name: formData.get('name'),
            age: parseInt(formData.get('age')),
            gender: formData.get('gender'),
            diagnosis: formData.get('diagnosis'),
            phone: formData.get('phone'),
            email: formData.get('email'),
            status: 'active',
            riskLevel: formData.get('riskLevel') || 'low',
            lastVisit: new Date().toISOString().split('T')[0],
            createdAt: new Date().toISOString().split('T')[0]
        };

        // 验证表单
        if (!this.validatePatientData(patient)) {
            return;
        }

        // 检查是否是编辑还是新增
        const existingIndex = this.patients.findIndex(p => p.id === patient.id);
        
        if (existingIndex >= 0) {
            this.patients[existingIndex] = patient;
            window.app.showNotification('患者信息更新成功', 'success');
        } else {
            this.patients.push(patient);
            window.app.showNotification('患者添加成功', 'success');
        }

        // 重新渲染表格
        this.renderPatientsTable();
        this.updatePagination();

        // 关闭模态框并重置表单
        window.app.closeAllModals();
        form.reset();
    }

    validatePatientData(patient) {
        if (!patient.name || !patient.age || !patient.gender) {
            window.app.showNotification('请填写必要的患者信息', 'error');
            return false;
        }

        if (patient.email && !Utils.validateEmail(patient.email)) {
            window.app.showNotification('请输入有效的邮箱地址', 'error');
            return false;
        }

        if (patient.phone && !Utils.validatePhone(patient.phone)) {
            window.app.showNotification('请输入有效的手机号码', 'error');
            return false;
        }

        return true;
    }

    generatePatientId() {
        const prefix = 'P';
        const number = (this.patients.length + 1).toString().padStart(3, '0');
        return prefix + number;
    }

    editPatient(patientId) {
        const patient = this.patients.find(p => p.id === patientId);
        if (!patient) return;

        // 填充表单数据
        const form = document.getElementById('patientForm');
        if (form) {
            Object.keys(patient).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = patient[key];
                }
            });
        }

        // 打开模态框
        window.app.openModal('patientModal');
    }

    viewPatient(patientId) {
        const patient = this.patients.find(p => p.id === patientId);
        if (!patient) return;

        // 显示患者详细信息
        const content = `
            <div class="patient-detail">
                <h4>${patient.name} (${patient.id})</h4>
                <div class="detail-grid">
                    <div><strong>年龄:</strong> ${patient.age}岁</div>
                    <div><strong>性别:</strong> ${patient.gender}</div>
                    <div><strong>诊断:</strong> ${patient.diagnosis}</div>
                    <div><strong>电话:</strong> ${patient.phone}</div>
                    <div><strong>邮箱:</strong> ${patient.email}</div>
                    <div><strong>风险等级:</strong> ${this.getRiskLevelText(patient.riskLevel)}</div>
                    <div><strong>最后就诊:</strong> ${Utils.formatDate(patient.lastVisit)}</div>
                    <div><strong>创建时间:</strong> ${Utils.formatDate(patient.createdAt)}</div>
                </div>
            </div>
        `;

        // 创建临时模态框显示详情
        this.showPatientDetail(content);
    }

    showPatientDetail(content) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>患者详情</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
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

    deletePatient(patientId) {
        if (confirm('确定要删除这个患者吗？此操作不可恢复。')) {
            this.patients = this.patients.filter(p => p.id !== patientId);
            this.renderPatientsTable();
            this.updatePagination();
            window.app.showNotification('患者删除成功', 'success');
        }
    }

    updateBulkActions() {
        const checkboxes = document.querySelectorAll('.patient-checkbox:checked');
        const bulkActions = document.querySelector('.bulk-actions');
        
        if (bulkActions) {
            bulkActions.style.display = checkboxes.length > 0 ? 'flex' : 'none';
        }
    }

    bulkExport() {
        const selected = this.getSelectedPatients();
        if (selected.length === 0) {
            window.app.showNotification('请选择要导出的患者', 'warning');
            return;
        }

        const csvContent = this.convertToCsv(selected);
        Utils.downloadFile(csvContent, 'patients_export.csv', 'text/csv');
        window.app.showNotification(`已导出 ${selected.length} 个患者的数据`, 'success');
    }

    bulkDelete() {
        const selected = this.getSelectedPatients();
        if (selected.length === 0) {
            window.app.showNotification('请选择要删除的患者', 'warning');
            return;
        }

        if (confirm(`确定要删除 ${selected.length} 个患者吗？此操作不可恢复。`)) {
            const selectedIds = selected.map(p => p.id);
            this.patients = this.patients.filter(p => !selectedIds.includes(p.id));
            this.renderPatientsTable();
            this.updatePagination();
            window.app.showNotification(`已删除 ${selected.length} 个患者`, 'success');
        }
    }

    getSelectedPatients() {
        const checkboxes = document.querySelectorAll('.patient-checkbox:checked');
        const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.patientId);
        return this.patients.filter(p => selectedIds.includes(p.id));
    }

    convertToCsv(patients) {
        const headers = ['ID', '姓名', '年龄', '性别', '诊断', '电话', '邮箱', '状态', '风险等级', '最后就诊', '创建时间'];
        const rows = patients.map(p => [
            p.id, p.name, p.age, p.gender, p.diagnosis, 
            p.phone, p.email, p.status, p.riskLevel, 
            p.lastVisit, p.createdAt
        ]);

        return [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\n');
    }

    async importPatients(file) {
        if (!file) return;

        try {
            const text = await file.text();
            const patients = this.parseCsvData(text);
            
            // 验证和导入数据
            let imported = 0;
            for (const patient of patients) {
                if (this.validatePatientData(patient)) {
                    // 检查是否已存在
                    const existingIndex = this.patients.findIndex(p => p.id === patient.id);
                    if (existingIndex >= 0) {
                        this.patients[existingIndex] = patient;
                    } else {
                        this.patients.push(patient);
                    }
                    imported++;
                }
            }

            this.renderPatientsTable();
            this.updatePagination();
            window.app.showNotification(`成功导入 ${imported} 个患者`, 'success');
            
        } catch (error) {
            console.error('Import failed:', error);
            window.app.showNotification('导入失败，请检查文件格式', 'error');
        }
    }

    parseCsvData(csvText) {
        const lines = csvText.split('\n');
        const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim());
        
        return lines.slice(1).map(line => {
            if (!line.trim()) return null;
            
            const values = line.split(',').map(v => v.replace(/"/g, '').trim());
            const patient = {};
            
            headers.forEach((header, index) => {
                switch(header) {
                    case 'ID':
                        patient.id = values[index];
                        break;
                    case '姓名':
                        patient.name = values[index];
                        break;
                    case '年龄':
                        patient.age = parseInt(values[index]);
                        break;
                    case '性别':
                        patient.gender = values[index];
                        break;
                    case '诊断':
                        patient.diagnosis = values[index];
                        break;
                    case '电话':
                        patient.phone = values[index];
                        break;
                    case '邮箱':
                        patient.email = values[index];
                        break;
                    case '状态':
                        patient.status = values[index];
                        break;
                    case '风险等级':
                        patient.riskLevel = values[index];
                        break;
                    case '最后就诊':
                        patient.lastVisit = values[index];
                        break;
                    case '创建时间':
                        patient.createdAt = values[index];
                        break;
                }
            });
            
            return patient;
        }).filter(p => p && p.name);
    }
}

// 导出
window.PatientsManager = PatientsManager;