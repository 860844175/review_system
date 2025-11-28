// 工具函数库

// API 相关工具
const ApiUtils = {
    baseUrl: 'http://localhost:8000/api',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    async get(endpoint) {
        return this.request(endpoint);
    },

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    },

    async uploadFile(endpoint, file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', `${this.baseUrl}${endpoint}`);
            xhr.send(formData);
        });
    }
};

// 本地存储工具
const StorageUtils = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
        }
    },

    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to read from localStorage:', error);
            return defaultValue;
        }
    },

    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Failed to remove from localStorage:', error);
        }
    },

    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Failed to clear localStorage:', error);
        }
    }
};

// 数据验证工具
const ValidationUtils = {
    isEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    isPhone(phone) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        return phoneRegex.test(phone);
    },

    isIdCard(idCard) {
        const idCardRegex = /^\d{17}[\dX]$/;
        return idCardRegex.test(idCard);
    },

    isRequired(value) {
        return value !== null && value !== undefined && value.toString().trim() !== '';
    },

    isNumber(value) {
        return !isNaN(value) && isFinite(value);
    },

    isPositiveNumber(value) {
        return this.isNumber(value) && parseFloat(value) > 0;
    },

    isInRange(value, min, max) {
        const num = parseFloat(value);
        return this.isNumber(num) && num >= min && num <= max;
    },

    validateForm(form, rules) {
        const errors = {};
        
        Object.keys(rules).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;
            
            const value = field.value;
            const fieldRules = rules[fieldName];
            
            for (const rule of fieldRules) {
                if (rule.required && !this.isRequired(value)) {
                    errors[fieldName] = rule.message || `${fieldName}是必填项`;
                    break;
                }
                
                if (rule.type === 'email' && value && !this.isEmail(value)) {
                    errors[fieldName] = rule.message || '请输入有效的邮箱地址';
                    break;
                }
                
                if (rule.type === 'phone' && value && !this.isPhone(value)) {
                    errors[fieldName] = rule.message || '请输入有效的手机号码';
                    break;
                }
                
                if (rule.minLength && value.length < rule.minLength) {
                    errors[fieldName] = rule.message || `最少需要${rule.minLength}个字符`;
                    break;
                }
                
                if (rule.maxLength && value.length > rule.maxLength) {
                    errors[fieldName] = rule.message || `最多允许${rule.maxLength}个字符`;
                    break;
                }
                
                if (rule.pattern && !rule.pattern.test(value)) {
                    errors[fieldName] = rule.message || '格式不正确';
                    break;
                }
            }
        });
        
        return errors;
    }
};

// 日期时间工具
const DateUtils = {
    format(date, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!date) return '';
        
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },

    formatRelative(date) {
        if (!date) return '';
        
        const now = new Date();
        const target = new Date(date);
        const diffMs = now - target;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        if (diffDays < 7) return `${diffDays}天前`;
        
        return this.format(date, 'MM-DD HH:mm');
    },

    isToday(date) {
        const today = new Date();
        const target = new Date(date);
        
        return today.getDate() === target.getDate() &&
               today.getMonth() === target.getMonth() &&
               today.getFullYear() === target.getFullYear();
    },

    addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    },

    getDaysBetween(date1, date2) {
        const diffTime = Math.abs(new Date(date2) - new Date(date1));
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
};

// 数据导出工具
const ExportUtils = {
    toCSV(data, headers, filename = 'export.csv') {
        let csv = '';
        
        // 添加表头
        if (headers) {
            csv += headers.join(',') + '\n';
        }
        
        // 添加数据行
        data.forEach(row => {
            const csvRow = row.map(field => {
                // 处理包含逗号、引号或换行符的字段
                if (typeof field === 'string' && (field.includes(',') || field.includes('"') || field.includes('\n'))) {
                    return `"${field.replace(/"/g, '""')}"`;
                }
                return field;
            });
            csv += csvRow.join(',') + '\n';
        });
        
        this.downloadFile(csv, filename, 'text/csv');
    },

    toJSON(data, filename = 'export.json') {
        const json = JSON.stringify(data, null, 2);
        this.downloadFile(json, filename, 'application/json');
    },

    toExcel(data, headers, filename = 'export.xlsx') {
        // 这里需要使用 SheetJS 库来生成 Excel 文件
        console.warn('Excel export requires SheetJS library');
    },

    downloadFile(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
    }
};

// 图表工具
const ChartUtils = {
    defaultColors: [
        '#4f46e5', '#06b6d4', '#10b981', '#f59e0b',
        '#ef4444', '#8b5cf6', '#f97316', '#84cc16'
    ],

    createLineChart(canvas, data, options = {}) {
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    ...dataset,
                    borderColor: dataset.borderColor || this.defaultColors[index % this.defaultColors.length],
                    backgroundColor: dataset.backgroundColor || this.defaultColors[index % this.defaultColors.length] + '20'
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                ...options
            }
        };
        
        // 这里需要使用 Chart.js 库
        console.warn('Chart creation requires Chart.js library');
        return null;
    },

    createBarChart(canvas, data, options = {}) {
        return this.createLineChart(canvas, data, { ...options, type: 'bar' });
    },

    createPieChart(canvas, data, options = {}) {
        return this.createLineChart(canvas, data, { ...options, type: 'pie' });
    }
};

// 通知工具
const NotificationUtils = {
    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getIcon(type)}"></i>
                <span>${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        // 添加样式
        this.addNotificationStyles();
        
        // 添加到页面
        const container = this.getNotificationContainer();
        container.appendChild(notification);
        
        // 自动关闭
        setTimeout(() => {
            this.remove(notification);
        }, duration);
        
        // 手动关闭
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.remove(notification);
        });
    },

    remove(notification) {
        notification.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    },

    getIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    },

    getNotificationContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
        return container;
    },

    addNotificationStyles() {
        if (document.getElementById('notification-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification-container {
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            
            .notification {
                min-width: 300px;
                max-width: 500px;
                padding: 16px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                animation: slideIn 0.3s ease-out forwards;
            }
            
            .notification-success {
                background: #d1fae5;
                border-left: 4px solid #10b981;
                color: #065f46;
            }
            
            .notification-error {
                background: #fee2e2;
                border-left: 4px solid #ef4444;
                color: #991b1b;
            }
            
            .notification-warning {
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                color: #92400e;
            }
            
            .notification-info {
                background: #dbeafe;
                border-left: 4px solid #3b82f6;
                color: #1e40af;
            }
            
            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                margin-left: auto;
                opacity: 0.7;
            }
            
            .notification-close:hover {
                opacity: 1;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        
        document.head.appendChild(styles);
    }
};

// 字符串工具
const StringUtils = {
    truncate(str, length = 50, suffix = '...') {
        if (!str) return '';
        if (str.length <= length) return str;
        return str.substring(0, length) + suffix;
    },

    capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    camelCase(str) {
        return str.replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ''));
    },

    kebabCase(str) {
        return str.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
    },

    removeHtml(str) {
        return str.replace(/<[^>]*>/g, '');
    },

    highlight(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
};

// 数组工具
const ArrayUtils = {
    unique(arr, key = null) {
        if (key) {
            const seen = new Set();
            return arr.filter(item => {
                const value = item[key];
                if (seen.has(value)) {
                    return false;
                }
                seen.add(value);
                return true;
            });
        }
        return [...new Set(arr)];
    },

    groupBy(arr, key) {
        return arr.reduce((groups, item) => {
            const group = item[key];
            if (!groups[group]) {
                groups[group] = [];
            }
            groups[group].push(item);
            return groups;
        }, {});
    },

    sortBy(arr, key, order = 'asc') {
        return arr.sort((a, b) => {
            let aVal = a[key];
            let bVal = b[key];
            
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }
            
            if (order === 'desc') {
                return bVal > aVal ? 1 : bVal < aVal ? -1 : 0;
            }
            
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        });
    },

    paginate(arr, page = 1, pageSize = 10) {
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        
        return {
            data: arr.slice(startIndex, endIndex),
            pagination: {
                currentPage: page,
                pageSize,
                total: arr.length,
                totalPages: Math.ceil(arr.length / pageSize),
                hasNext: endIndex < arr.length,
                hasPrev: page > 1
            }
        };
    }
};

// 导出所有工具
window.ApiUtils = ApiUtils;
window.StorageUtils = StorageUtils;
window.ValidationUtils = ValidationUtils;
window.DateUtils = DateUtils;
window.ExportUtils = ExportUtils;
window.ChartUtils = ChartUtils;
window.NotificationUtils = NotificationUtils;
window.StringUtils = StringUtils;
window.ArrayUtils = ArrayUtils;