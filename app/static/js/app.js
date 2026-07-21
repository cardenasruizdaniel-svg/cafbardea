/**
 * CAFBARDLA - Premium Restaurant POS System
 * JavaScript Utilities & Interactions
 */

// ===================================================================
// NOTIFICATION SYSTEM
// ===================================================================
class NotificationManager {
    constructor() {
        this.container = null;
        this.init();
    }
    
    init() {
        if (!document.querySelector('.toast-container')) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }
    
    show(title, message = '', type = 'info', duration = 4000) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || '•'}</span>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                ${message ? `<div class="toast-message">${message}</div>` : ''}
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(toast);
        
        if (duration > 0) {
            setTimeout(() => toast.remove(), duration);
        }
        
        return toast;
    }
    
    success(title, message = '') {
        return this.show(title, message, 'success');
    }
    
    error(title, message = '') {
        return this.show(title, message, 'error');
    }
    
    warning(title, message = '') {
        return this.show(title, message, 'warning');
    }
    
    info(title, message = '') {
        return this.show(title, message, 'info');
    }
}

// Instancia global
const notify = new NotificationManager();

// ===================================================================
// MODAL SYSTEM
// ===================================================================
class Modal {
    constructor(title, content, options = {}) {
        this.title = title;
        this.content = content;
        this.options = {
            size: 'md',
            closable: true,
            ...options
        };
        this.element = null;
        this.backdrop = null;
    }
    
    open() {
        // Crear backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'modal-backdrop';
        this.backdrop.onclick = (e) => {
            if (e.target === this.backdrop && this.options.closable) {
                this.close();
            }
        };
        
        // Crear modal
        this.element = document.createElement('div');
        this.element.className = `modal modal-${this.options.size}`;
        this.element.innerHTML = `
            <div class="modal-header">
                <h2 class="modal-title">${this.title}</h2>
                ${this.options.closable ? '<button class="modal-close" onclick="this.closest(\'.modal-backdrop\").remove()">×</button>' : ''}
            </div>
            <div class="modal-body">
                ${this.content}
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="this.closest(\'.modal-backdrop\').remove()">Cancelar</button>
                <button class="btn btn-primary" onclick="document.dispatchEvent(new CustomEvent('modalConfirm'))">Confirmar</button>
            </div>
        `;
        
        this.backdrop.appendChild(this.element);
        document.body.appendChild(this.backdrop);
        
        return this;
    }
    
    close() {
        if (this.backdrop) {
            this.backdrop.remove();
        }
    }
    
    setContent(content) {
        if (this.element) {
            this.element.querySelector('.modal-body').innerHTML = content;
        }
        return this;
    }
}

// ===================================================================
// FORM UTILITIES
// ===================================================================
class FormHelper {
    static validate(formElement) {
        let isValid = true;
        const errors = [];
        
        formElement.querySelectorAll('[required]').forEach(field => {
            if (!field.value || field.value.trim() === '') {
                isValid = false;
                errors.push(`${field.name} es requerido`);
                this.setFieldError(field, true);
            } else {
                this.setFieldError(field, false);
            }
        });
        
        return { isValid, errors };
    }
    
    static setFieldError(field, hasError) {
        if (hasError) {
            field.classList.add('error');
            field.setAttribute('aria-invalid', 'true');
        } else {
            field.classList.remove('error');
            field.setAttribute('aria-invalid', 'false');
        }
    }
    
    static serialize(formElement) {
        const formData = new FormData(formElement);
        const data = {};
        for (const [key, value] of formData) {
            data[key] = value;
        }
        return data;
    }
    
    static reset(formElement) {
        formElement.reset();
        formElement.querySelectorAll('.form-control').forEach(field => {
            this.setFieldError(field, false);
        });
    }
}

// ===================================================================
// TABLE UTILITIES
// ===================================================================
class TableHelper {
    static sort(tableElement, columnIndex, direction = 'asc') {
        const tbody = tableElement.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent;
            const bValue = b.cells[columnIndex].textContent;
            
            if (direction === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    }
    
    static filter(tableElement, searchText) {
        const rows = tableElement.querySelectorAll('tbody tr');
        let visibleCount = 0;
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(searchText.toLowerCase())) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
        
        return visibleCount;
    }
    
    static exportToCSV(tableElement, filename = 'export.csv') {
        let csv = [];
        const rows = tableElement.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const csvRow = Array.from(cols).map(col => col.textContent).join(',');
            csv.push(csvRow);
        });
        
        const csvContent = csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
    }
}

// ===================================================================
// COLLAPSE / ACCORDION
// ===================================================================
class Collapse {
    constructor(element) {
        this.element = element;
        this.header = element.querySelector('.collapse-header');
        this.body = element.querySelector('.collapse-body');
        
        if (this.header) {
            this.header.addEventListener('click', () => this.toggle());
        }
    }
    
    toggle() {
        if (this.header.classList.contains('active')) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.header.classList.add('active');
        this.body.classList.add('active');
    }
    
    close() {
        this.header.classList.remove('active');
        this.body.classList.remove('active');
    }
}

// Inicializar collapses
document.querySelectorAll('.collapse').forEach(element => {
    new Collapse(element);
});

// ===================================================================
// LOADING STATES
// ===================================================================
class LoadingHelper {
    static show(message = 'Cargando...') {
        const loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.className = 'modal-backdrop';
        loader.style.cursor = 'wait';
        loader.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                <div class="spinner"></div>
                <p style="color: white;">${message}</p>
            </div>
        `;
        document.body.appendChild(loader);
    }
    
    static hide() {
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.remove();
        }
    }
}

// ===================================================================
// UTILITY FUNCTIONS
// ===================================================================

// Format currency
function formatCurrency(amount, currency = 'COP') {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Format date
function formatDate(date, format = 'es-CO') {
    return new Date(date).toLocaleDateString(format);
}

// Format time
function formatTime(date) {
    return new Date(date).toLocaleTimeString('es-CO');
}

// Deep clone
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// Debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ===================================================================
// LOCAL STORAGE HELPER
// ===================================================================
const Storage = {
    set(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    },
    
    get(key) {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
    },
    
    remove(key) {
        localStorage.removeItem(key);
    },
    
    clear() {
        localStorage.clear();
    }
};

// ===================================================================
// LAYOUT MANAGER (SIDEBAR + PLATFORM)
// ===================================================================
class LayoutManager {
    static init() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        const mobileBtn = document.getElementById('sidebarMobileBtn');
        const backdrop = document.getElementById('sidebarBackdrop');

        const collapseKey = 'cafbardla.sidebarCollapsed';
        const savedCollapsed = Storage.get(collapseKey);
        if (savedCollapsed === true && window.innerWidth > 1024) {
            document.body.classList.add('sidebar-collapsed');
        }

        const updateCollapseIcon = () => {
            if (!collapseBtn) return;
            const collapsed = document.body.classList.contains('sidebar-collapsed');
            collapseBtn.textContent = collapsed ? '⟩' : '⟨';
            collapseBtn.setAttribute('aria-label', collapsed ? 'Mostrar menú' : 'Ocultar menú');
        };

        const closeMobileSidebar = () => {
            document.body.classList.remove('sidebar-mobile-open');
        };

        collapseBtn?.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-collapsed');
            const collapsed = document.body.classList.contains('sidebar-collapsed');
            Storage.set(collapseKey, collapsed);
            updateCollapseIcon();
        });

        mobileBtn?.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-mobile-open');
        });

        backdrop?.addEventListener('click', closeMobileSidebar);

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeMobileSidebar();
            }
        });

        document.querySelectorAll('.nav-item').forEach((link) => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 1024) closeMobileSidebar();
            });
        });

        if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) {
            document.body.classList.add('platform-mobile-browser');
        }

        updateCollapseIcon();
    }
}

// ===================================================================
// FETCH HELPER
// ===================================================================
class API {
    static async get(url, options = {}) {
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    static async post(url, data = {}, options = {}) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...options.headers },
                body: JSON.stringify(data),
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    static async put(url, data = {}, options = {}) {
        try {
            const response = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...options.headers },
                body: JSON.stringify(data),
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    static async delete(url, options = {}) {
        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
}

// ===================================================================
// INICIALIZACIONES
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
    LayoutManager.init();

    // Agregar tooltips
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.style.cursor = 'help';
    });
    
    // Activar búsqueda en tiempo real
    const searchInput = document.querySelector('.header-search input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            console.log('Buscando:', e.target.value);
        }, 300));
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K: Abrir búsqueda
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput?.focus();
        }
        
        // Esc: Cerrar modales
        if (e.key === 'Escape') {
            document.querySelector('.modal-backdrop')?.remove();
        }
    });
});

// ===================================================================
// EXPORT
// ===================================================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NotificationManager,
        Modal,
        FormHelper,
        TableHelper,
        Collapse,
        LoadingHelper,
        formatCurrency,
        formatDate,
        formatTime,
        deepClone,
        debounce,
        throttle,
        Storage,
        API,
        LayoutManager
    };
}
