// 主JavaScript文件 - 应用程序控制器

class App {
    constructor() {
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDashboard();
        this.updateStats();
    }

    setupEventListeners() {
        // 导航菜单事件
        document.querySelectorAll('.nav-item a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('href').replace('#', '');
                this.navigateToSection(section);
            });
        });

        // 模态框事件
        document.querySelectorAll('[data-modal]').forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = trigger.getAttribute('data-modal');
                this.openModal(modalId);
            });
        });

        document.querySelectorAll('.modal-close, .modal-backdrop').forEach(closer => {
            closer.addEventListener('click', () => {
                this.closeAllModals();
            });
        });

        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });

        // 快速操作按钮
        document.getElementById('quickAddPatient')?.addEventListener('click', () => {
            this.openModal('patientModal');
        });

        document.getElementById('quickGenerateReport')?.addEventListener('click', () => {
            this.navigateToSection('reports');
            setTimeout(() => this.openModal('reportModal'), 100);
        });

        // 搜索功能
        document.getElementById('globalSearch')?.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        // 文件上传
        this.setupFileUpload();
    }

    navigateToSection(sectionId) {
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[href="#${sectionId}"]`)?.parentElement.classList.add('active');

        // 显示对应的内容区域
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionId)?.classList.add('active');

        this.currentSection = sectionId;

        // 根据不同section加载对应数据
        switch(sectionId) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'patients':
                window.patientsManager?.loadPatients();
                break;
            case 'reports':
                window.reportsManager?.loadReports();
                break;
            case 'feedback':
                window.feedbackManager?.loadFeedback();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
        document.body.style.overflow = '';
    }

    async updateStats() {
        try {
            // 模拟API调用
            const stats = await this.fetchStats();
            
            // 更新统计数据
            document.getElementById('totalPatients').textContent = stats.totalPatients;
            document.getElementById('totalReports').textContent = stats.totalReports;
            document.getElementById('pendingFeedback').textContent = stats.pendingFeedback;
            document.getElementById('completionRate').textContent = `${stats.completionRate}%`;
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }

    async fetchStats() {
        // 模拟数据，实际应该调用后端API
        return new Promise(resolve => {
            setTimeout(() => {
                resolve({
                    totalPatients: 156,
                    totalReports: 423,
                    pendingFeedback: 12,
                    completionRate: 87
                });
            }, 500);
        });
    }

    loadDashboard() {
        this.updateRecentActivity();
        this.updateQuickActions();
    }

    updateRecentActivity() {
        const activities = [
            {
                icon: 'fas fa-file-medical',
                text: '为患者张三生成了服药依从性报告',
                time: '2分钟前'
            },
            {
                icon: 'fas fa-comment-medical',
                text: '收到了李医生对患者李四报告的反馈',
                time: '15分钟前'
            },
            {
                icon: 'fas fa-user-plus',
                text: '新增患者王五的基本信息',
                time: '1小时前'
            },
            {
                icon: 'fas fa-chart-line',
                text: '生成了本月的分析报告',
                time: '2小时前'
            }
        ];

        const activityList = document.querySelector('.activity-list');
        if (activityList) {
            activityList.innerHTML = activities.map(activity => `
                <div class="activity-item">
                    <i class="${activity.icon}"></i>
                    <span>${activity.text}</span>
                    <time>${activity.time}</time>
                </div>
            `).join('');
        }
    }

    updateQuickActions() {
        // 快速操作功能已在HTML中定义，这里可以添加动态内容
        console.log('Quick actions updated');
    }

    handleSearch(query) {
        if (query.length < 2) return;

        // 根据当前页面进行搜索
        switch(this.currentSection) {
            case 'patients':
                window.patientsManager?.searchPatients(query);
                break;
            case 'reports':
                window.reportsManager?.searchReports(query);
                break;
            case 'feedback':
                window.feedbackManager?.searchFeedback(query);
                break;
            default:
                this.globalSearch(query);
        }
    }

    globalSearch(query) {
        // 全局搜索逻辑
        console.log('Global search for:', query);
    }

    setupFileUpload() {
        const uploadAreas = document.querySelectorAll('.file-upload');
        
        uploadAreas.forEach(area => {
            area.addEventListener('click', () => {
                const input = area.querySelector('input[type="file"]');
                input?.click();
            });

            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });

            area.addEventListener('dragleave', () => {
                area.classList.remove('dragover');
            });

            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                this.handleFileUpload(files, area);
            });

            const input = area.querySelector('input[type="file"]');
            if (input) {
                input.addEventListener('change', (e) => {
                    this.handleFileUpload(e.target.files, area);
                });
            }
        });
    }

    handleFileUpload(files, uploadArea) {
        Array.from(files).forEach(file => {
            console.log('Uploading file:', file.name);
            this.uploadFile(file, uploadArea);
        });
    }

    async uploadFile(file, uploadArea) {
        try {
            // 显示上传进度
            this.showUploadProgress(uploadArea, 0);
            
            // 模拟文件上传
            for (let progress = 0; progress <= 100; progress += 10) {
                await new Promise(resolve => setTimeout(resolve, 100));
                this.showUploadProgress(uploadArea, progress);
            }

            this.showNotification('文件上传成功', 'success');
        } catch (error) {
            console.error('File upload failed:', error);
            this.showNotification('文件上传失败', 'error');
        }
    }

    showUploadProgress(uploadArea, progress) {
        let progressBar = uploadArea.querySelector('.progress');
        
        if (!progressBar && progress > 0) {
            progressBar = document.createElement('div');
            progressBar.className = 'progress';
            progressBar.innerHTML = '<div class="progress-bar" style="width: 0%"></div>';
            uploadArea.appendChild(progressBar);
        }

        if (progressBar) {
            const bar = progressBar.querySelector('.progress-bar');
            bar.style.width = `${progress}%`;

            if (progress === 100) {
                setTimeout(() => {
                    progressBar.remove();
                }, 1000);
            }
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;

        const container = document.querySelector('.content-panel');
        container.insertBefore(notification, container.firstChild);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }

    loadAnalytics() {
        // 加载分析页面
        console.log('Loading analytics...');
        this.loadCharts();
    }

    loadCharts() {
        // 创建示例图表
        this.createChart('reportsChart', 'line', '报告生成趋势');
        this.createChart('patientsChart', 'bar', '患者分布');
        this.createChart('feedbackChart', 'doughnut', '反馈统计');
    }

    createChart(canvasId, type, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        // 这里应该使用Chart.js或其他图表库
        // 暂时用简单的占位符
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#f3f4f6';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#374151';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(title, canvas.width / 2, canvas.height / 2);
    }

    loadSettings() {
        console.log('Loading settings...');
        this.loadSystemSettings();
        this.loadUserSettings();
    }

    loadSystemSettings() {
        // 加载系统设置
        const settings = {
            aiModel: 'qwen-plus',
            reportTypes: ['compliance', 'triage'],
            exportFormats: ['html', 'pdf', 'json'],
            autoBackup: true,
            notificationEmail: true
        };

        // 更新UI
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = settings[key];
                } else {
                    element.value = settings[key];
                }
            }
        });
    }

    loadUserSettings() {
        // 加载用户设置
        console.log('User settings loaded');
    }
}

// 工具函数
const Utils = {
    formatDate(date) {
        return new Intl.DateTimeFormat('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    },

    generateId() {
        return Math.random().toString(36).substr(2, 9);
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    async fetchJSON(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    },

    downloadFile(content, filename, type = 'text/plain') {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        
        URL.revokeObjectURL(url);
    },

    validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    validatePhone(phone) {
        return /^1[3-9]\d{9}$/.test(phone);
    }
};

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    
    // 加载其他管理器
    if (typeof PatientsManager !== 'undefined') {
        window.patientsManager = new PatientsManager();
    }
    
    if (typeof ReportsManager !== 'undefined') {
        window.reportsManager = new ReportsManager();
    }
    
    if (typeof FeedbackManager !== 'undefined') {
        window.feedbackManager = new FeedbackManager();
    }
});

// 导出到全局
window.App = App;
window.Utils = Utils;