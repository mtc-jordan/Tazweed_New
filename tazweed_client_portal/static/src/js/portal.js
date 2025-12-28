/* Tazweed Client Portal JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize portal functionality
    TazweedPortal.init();
});

const TazweedPortal = {
    init: function() {
        this.initNotifications();
        this.initRealTimeUpdates();
        this.initTooltips();
        this.initModals();
    },

    // Notification System
    initNotifications: function() {
        const notificationBell = document.querySelector('.portal-notification-bell');
        if (notificationBell) {
            notificationBell.addEventListener('click', this.toggleNotificationDropdown.bind(this));
            this.loadNotifications();
            
            // Poll for new notifications every 30 seconds
            setInterval(() => this.loadNotifications(), 30000);
        }
    },

    toggleNotificationDropdown: function(e) {
        e.preventDefault();
        const dropdown = document.querySelector('.portal-notification-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    },

    loadNotifications: async function() {
        try {
            const response = await this.jsonRpc('/api/portal/notifications', {});
            if (response.notifications) {
                this.renderNotifications(response.notifications);
                this.updateNotificationBadge(response.unread_count);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    },

    renderNotifications: function(notifications) {
        const container = document.querySelector('.portal-notification-list');
        if (!container) return;

        if (notifications.length === 0) {
            container.innerHTML = '<div class="portal-notification-empty">No notifications</div>';
            return;
        }

        container.innerHTML = notifications.map(n => `
            <div class="portal-notification-item ${n.is_read ? '' : 'unread'}" 
                 data-id="${n.id}" 
                 onclick="TazweedPortal.handleNotificationClick(${n.id}, '${n.action_url}')">
                <div class="notification-icon" style="color: ${n.color}">
                    <i class="fa ${n.icon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${n.title}</div>
                    <div class="notification-message">${n.message}</div>
                    <div class="notification-time">${this.formatTime(n.date)}</div>
                </div>
            </div>
        `).join('');
    },

    updateNotificationBadge: function(count) {
        const badge = document.querySelector('.portal-notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        }
    },

    handleNotificationClick: async function(id, actionUrl) {
        // Mark as read
        await this.jsonRpc('/api/portal/notifications/mark-read', { notification_id: id });
        
        // Navigate to action URL
        if (actionUrl) {
            window.location.href = actionUrl;
        }
    },

    markAllNotificationsRead: async function() {
        await this.jsonRpc('/api/portal/notifications/mark-all-read', {});
        this.loadNotifications();
    },

    // Real-time Updates
    initRealTimeUpdates: function() {
        // Update dashboard data periodically
        if (document.querySelector('.portal-dashboard')) {
            setInterval(() => this.refreshDashboard(), 60000);
        }
    },

    refreshDashboard: async function() {
        try {
            const response = await this.jsonRpc('/api/portal/dashboard', {});
            if (response.summary) {
                this.updateDashboardKPIs(response.summary);
            }
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
        }
    },

    updateDashboardKPIs: function(summary) {
        // Update KPI values with animation
        Object.keys(summary).forEach(key => {
            const element = document.querySelector(`[data-kpi="${key}"]`);
            if (element) {
                this.animateValue(element, parseInt(element.textContent) || 0, summary[key], 500);
            }
        });
    },

    animateValue: function(element, start, end, duration) {
        const range = end - start;
        const startTime = performance.now();
        
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const value = Math.floor(start + range * progress);
            element.textContent = value.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    },

    // Candidate Actions
    approveCandidate: async function(candidateId, notes = '') {
        try {
            const response = await this.jsonRpc('/api/portal/candidates/approve', {
                candidate_id: candidateId,
                notes: notes
            });
            
            if (response.success) {
                this.showToast('Candidate approved successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                this.showToast(response.error || 'Error approving candidate', 'error');
            }
        } catch (error) {
            this.showToast('Error approving candidate', 'error');
        }
    },

    rejectCandidate: async function(candidateId, reason = '') {
        try {
            const response = await this.jsonRpc('/api/portal/candidates/reject', {
                candidate_id: candidateId,
                reason: reason
            });
            
            if (response.success) {
                this.showToast('Candidate rejected', 'warning');
                setTimeout(() => location.reload(), 1000);
            } else {
                this.showToast(response.error || 'Error rejecting candidate', 'error');
            }
        } catch (error) {
            this.showToast('Error rejecting candidate', 'error');
        }
    },

    // Message System
    sendMessage: async function(subject, body, category = 'general') {
        try {
            const response = await this.jsonRpc('/api/portal/messages/send', {
                subject: subject,
                body: body,
                category: category
            });
            
            if (response.success) {
                this.showToast('Message sent successfully', 'success');
                return response.message_id;
            } else {
                this.showToast(response.error || 'Error sending message', 'error');
                return null;
            }
        } catch (error) {
            this.showToast('Error sending message', 'error');
            return null;
        }
    },

    // Document Actions
    acknowledgeDocument: async function(documentId) {
        try {
            const response = await this.jsonRpc('/api/portal/documents/acknowledge', {
                document_id: documentId
            });
            
            if (response.success) {
                this.showToast('Document acknowledged', 'success');
                location.reload();
            }
        } catch (error) {
            this.showToast('Error acknowledging document', 'error');
        }
    },

    // UI Helpers
    initTooltips: function() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(el => {
            el.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'portal-tooltip';
                tooltip.textContent = this.dataset.tooltip;
                document.body.appendChild(tooltip);
                
                const rect = this.getBoundingClientRect();
                tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
            });
            
            el.addEventListener('mouseleave', function() {
                const tooltip = document.querySelector('.portal-tooltip');
                if (tooltip) tooltip.remove();
            });
        });
    },

    initModals: function() {
        // Close modal on backdrop click
        document.querySelectorAll('.portal-modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.closest('.portal-modal').classList.remove('show');
                }
            });
        });
    },

    showModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
        }
    },

    hideModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    },

    showToast: function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `portal-toast portal-toast-${type}`;
        toast.innerHTML = `
            <i class="fa ${this.getToastIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    getToastIcon: function(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    },

    formatTime: function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = (now - date) / 1000;
        
        if (diff < 60) return 'Just now';
        if (diff < 3600) return Math.floor(diff / 60) + ' min ago';
        if (diff < 86400) return Math.floor(diff / 3600) + ' hours ago';
        if (diff < 604800) return Math.floor(diff / 86400) + ' days ago';
        
        return date.toLocaleDateString();
    },

    // JSON-RPC Helper
    jsonRpc: async function(url, params) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000)
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error.message || 'Unknown error');
        }
        
        return data.result;
    }
};

// Export for global access
window.TazweedPortal = TazweedPortal;
