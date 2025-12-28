/* ============================================
   Tazweed Employee Portal - JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize Portal
    initPortal();
    
    // Initialize Dashboard
    if (document.querySelector('.tazweed-dashboard')) {
        initDashboard();
    }
    
    // Initialize Attendance
    if (document.querySelector('#attendance-btn')) {
        initAttendance();
    }
    
    // Initialize Forms
    initForms();
    
    // Initialize Notifications
    initNotifications();
});

/**
 * Initialize Portal
 */
function initPortal() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Add loading states to buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
            }
        });
    });
    
    // Initialize tooltips
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
    });
}

/**
 * Initialize Dashboard
 */
function initDashboard() {
    // Animate stat cards on scroll
    const statCards = document.querySelectorAll('.stat-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.1 });
    
    statCards.forEach(card => observer.observe(card));
    
    // Auto-refresh dashboard data
    if (window.dashboardAutoRefresh) {
        setInterval(refreshDashboard, 60000); // Refresh every minute
    }
}

/**
 * Initialize Attendance
 */
function initAttendance() {
    const attendanceBtn = document.querySelector('#attendance-btn');
    
    if (attendanceBtn) {
        // Get current location for attendance
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    // Store location for form submission
                    const form = attendanceBtn.closest('form');
                    if (form) {
                        let latInput = form.querySelector('input[name="latitude"]');
                        let lngInput = form.querySelector('input[name="longitude"]');
                        
                        if (!latInput) {
                            latInput = document.createElement('input');
                            latInput.type = 'hidden';
                            latInput.name = 'latitude';
                            form.appendChild(latInput);
                        }
                        if (!lngInput) {
                            lngInput = document.createElement('input');
                            lngInput.type = 'hidden';
                            lngInput.name = 'longitude';
                            form.appendChild(lngInput);
                        }
                        
                        latInput.value = lat;
                        lngInput.value = lng;
                    }
                },
                (error) => {
                    console.log('Location not available:', error.message);
                }
            );
        }
    }
    
    // Update current time display
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
}

/**
 * Update Current Time Display
 */
function updateCurrentTime() {
    const timeDisplay = document.querySelector('#current-time');
    if (timeDisplay) {
        const now = new Date();
        timeDisplay.textContent = now.toLocaleTimeString();
    }
}

/**
 * Initialize Forms
 */
function initForms() {
    // Date validation
    document.querySelectorAll('input[type="date"]').forEach(input => {
        input.addEventListener('change', validateDateRange);
    });
    
    // File upload preview
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', previewFile);
    });
    
    // Form validation
    document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', validateForm);
    });
}

/**
 * Validate Date Range
 */
function validateDateRange(e) {
    const input = e.target;
    const form = input.closest('form');
    
    if (form) {
        const dateFrom = form.querySelector('input[name="date_from"]');
        const dateTo = form.querySelector('input[name="date_to"]');
        
        if (dateFrom && dateTo && dateFrom.value && dateTo.value) {
            if (new Date(dateTo.value) < new Date(dateFrom.value)) {
                showNotification('End date cannot be before start date', 'error');
                dateTo.value = dateFrom.value;
            }
        }
    }
}

/**
 * Preview File
 */
function previewFile(e) {
    const input = e.target;
    const file = input.files[0];
    
    if (file) {
        // Check file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showNotification('File size exceeds 10MB limit', 'error');
            input.value = '';
            return;
        }
        
        // Show file name
        const fileNameDisplay = input.parentElement.querySelector('.file-name');
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }
        
        // Preview image
        if (file.type.startsWith('image/')) {
            const preview = input.parentElement.querySelector('.file-preview');
            if (preview) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.innerHTML = `<img src="${e.target.result}" class="img-thumbnail" style="max-height: 200px;">`;
                };
                reader.readAsDataURL(file);
            }
        }
    }
}

/**
 * Validate Form
 */
function validateForm(e) {
    const form = e.target;
    let isValid = true;
    
    // Check required fields
    form.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    if (!isValid) {
        e.preventDefault();
        showNotification('Please fill in all required fields', 'error');
    }
    
    return isValid;
}

/**
 * Initialize Notifications
 */
function initNotifications() {
    // Check for flash messages
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.classList.add('fade-out');
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
}

/**
 * Show Notification
 */
function showNotification(message, type = 'info') {
    const container = document.querySelector('.notification-container') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * Create Notification Container
 */
function createNotificationContainer() {
    const container = document.createElement('div');
    container.className = 'notification-container';
    container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    document.body.appendChild(container);
    return container;
}

/**
 * Refresh Dashboard
 */
function refreshDashboard() {
    fetch('/my/dashboard/data')
        .then(response => response.json())
        .then(data => {
            // Update stat cards
            if (data.leave_balance) {
                updateStatCard('leave-balance', data.leave_balance);
            }
            if (data.pending_requests) {
                updateStatCard('pending-requests', data.pending_requests);
            }
            // Add more updates as needed
        })
        .catch(error => console.error('Dashboard refresh failed:', error));
}

/**
 * Update Stat Card
 */
function updateStatCard(id, value) {
    const card = document.querySelector(`#${id}`);
    if (card) {
        const valueEl = card.querySelector('.stat-value');
        if (valueEl) {
            valueEl.textContent = value;
        }
    }
}

/**
 * Show Tooltip
 */
function showTooltip(e) {
    const el = e.target;
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = el.dataset.tooltip;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 9999;
    `;
    
    const rect = el.getBoundingClientRect();
    tooltip.style.top = (rect.top - 30) + 'px';
    tooltip.style.left = (rect.left + rect.width / 2) + 'px';
    tooltip.style.transform = 'translateX(-50%)';
    
    document.body.appendChild(tooltip);
    el._tooltip = tooltip;
}

/**
 * Hide Tooltip
 */
function hideTooltip(e) {
    const el = e.target;
    if (el._tooltip) {
        el._tooltip.remove();
        delete el._tooltip;
    }
}

/**
 * Confirm Action
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Format Currency
 */
function formatCurrency(amount, currency = 'AED') {
    return new Intl.NumberFormat('en-AE', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format Date
 */
function formatDate(date, format = 'short') {
    const d = new Date(date);
    const options = format === 'long' 
        ? { year: 'numeric', month: 'long', day: 'numeric' }
        : { year: 'numeric', month: 'short', day: 'numeric' };
    return d.toLocaleDateString('en-AE', options);
}

// Export functions for external use
window.TazweedPortal = {
    showNotification,
    confirmAction,
    formatCurrency,
    formatDate
};
