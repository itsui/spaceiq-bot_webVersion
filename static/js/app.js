// SpaceIQ Bot Web Interface JavaScript

// Global variables
let currentStatus = {};
let statusCheckInterval;
let autoScroll = true;

// Toast notification system
function showToast(message, type = 'info', title = null) {
    const toastEl = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');
    const toast = new bootstrap.Toast(toastEl);

    // Set content
    toastTitle.textContent = title || (type.charAt(0).toUpperCase() + type.slice(1));
    toastBody.textContent = message;

    // Set styling
    toastEl.className = `toast ${type}`;

    // Show toast
    toast.show();
}

// API helper functions
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`/api${endpoint}`, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || 'API call failed');
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// Bot control functions
async function startBot() {
    try {
        const result = await apiCall('/start', 'POST', {
            headless: true,
            auto_mode: true
        });

        if (result.success) {
            showToast('Bot started successfully!', 'success');
            // Update UI immediately
            setTimeout(checkStatus, 500);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        // Error already shown in apiCall
    }
}

async function stopBot() {
    try {
        const result = await apiCall('/stop', 'POST');

        if (result.success) {
            showToast('Bot stopped successfully!', 'success');
            // Update UI immediately
            setTimeout(checkStatus, 500);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        // Error already shown in apiCall
    }
}

// Status checking functions
async function checkStatus() {
    try {
        const result = await apiCall('/status');
        currentStatus = result;
        updateStatusDisplay(result);
        updateLogs(result.logs || []);
    } catch (error) {
        // Error already shown in apiCall
        updateStatusDisplay({ running: false, error: error.message });
    }
}

function calculateUptime(startTime) {
    const start = new Date(startTime);
    const now = new Date();
    const diff = now - start;

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

// Logs management
function updateLogs(logs) {
    const logsContent = document.getElementById('logs-content');

    if (!logs || logs.length === 0) {
        logsContent.innerHTML = `
            <div class="text-muted text-center p-3">
                <i class="bi bi-hourglass-split"></i> Waiting for logs...
            </div>
        `;
        return;
    }

    // Build log HTML
    const logHtml = logs.map(log => {
        const timestamp = new Date(log.timestamp).toLocaleTimeString();
        const logClass = getLogClass(log.message);

        return `
            <div class="log-entry ${logClass}">
                <span class="log-timestamp">[${timestamp}]</span>
                <span class="log-message">${escapeHtml(log.message)}</span>
            </div>
        `;
    }).join('');

    logsContent.innerHTML = logHtml;

    // Auto-scroll to bottom if enabled
    if (autoScroll) {
        const logsContainer = document.querySelector('.logs-container');
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

function getLogClass(message) {
    const msgLower = message.toLowerCase();
    if (msgLower.includes('success') || msgLower.includes('booked')) {
        return 'success';
    } else if (msgLower.includes('error') || msgLower.includes('failed')) {
        return 'error';
    } else if (msgLower.includes('warning') || msgLower.includes('warn')) {
        return 'warning';
    }
    return 'info';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearLogs() {
    if (confirm('Are you sure you want to clear the logs display?')) {
        currentStatus.logs = [];
        updateLogs([]);
        showToast('Logs cleared', 'info');
    }
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const btn = event.target.closest('button');
    if (autoScroll) {
        btn.innerHTML = '<i class="bi bi-arrow-down-up"></i> Auto-scroll';
        showToast('Auto-scroll enabled', 'info');
    } else {
        btn.innerHTML = '<i class="bi bi-arrow-down-up"></i> Manual scroll';
        showToast('Auto-scroll disabled', 'info');
    }
}

function refreshStatus() {
    checkStatus();
    showToast('Status refreshed', 'info');
}

// Configuration management
async function loadConfiguration() {
    try {
        const config = await apiCall('/config');
        displayConfiguration(config);
    } catch (error) {
        // Error already shown in apiCall
    }
}

function displayConfiguration(config) {
    // Basic settings
    document.getElementById('building').value = config.building || '';
    document.getElementById('floor').value = config.floor || '';

    // Desk preferences
    document.getElementById('desk-prefix').value = config.desk_preferences?.prefix || '';

    // Dates
    displayDates(config.dates_to_try || []);

    // Booking days
    const weekdays = config.booking_days?.weekdays || [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox) {
            checkbox.checked = weekdays.includes(i);
        }
    }

    // Priority ranges
    displayPriorityRanges(config.desk_preferences?.priority_ranges || []);

    // Wait times
    document.getElementById('wait-early').value = config.wait_times?.rounds_1_to_5?.seconds || 60;
    document.getElementById('wait-mid').value = config.wait_times?.rounds_6_to_15?.seconds || 120;
    document.getElementById('wait-late').value = config.wait_times?.rounds_16_plus?.seconds || 180;

    // Browser settings
    document.getElementById('browser-restart').value = config.browser_restart?.restart_every_n_rounds || 50;

    // Update dashboard preview
    updateConfigPreview(config);
}

function updateConfigPreview(config) {
    // Update dashboard configuration preview
    const buildingEl = document.getElementById('config-building');
    const deskPrefixEl = document.getElementById('config-desk-prefix');
    const datesEl = document.getElementById('config-dates');
    const daysEl = document.getElementById('config-days');

    if (buildingEl) buildingEl.textContent = `${config.building || ''} / Floor ${config.floor || ''}`;
    if (deskPrefixEl) deskPrefixEl.textContent = config.desk_preferences?.prefix || 'Not set';
    if (datesEl) datesEl.textContent = (config.dates_to_try || []).length + ' dates configured';
    if (daysEl) {
        const weekdays = config.booking_days?.weekdays || [];
        const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const selectedDays = weekdays.map(day => dayNames[day]).join(', ') || 'None';
        daysEl.textContent = selectedDays;
    }
}

async function saveConfiguration() {
    try {
        const formData = new FormData(document.getElementById('config-form'));
        const config = {
            building: formData.get('building'),
            floor: formData.get('floor'),
            desk_preferences: {
                prefix: formData.get('desk_prefix'),
                priority_ranges: collectPriorityRanges()
            },
            dates_to_try: collectDates(),
            booking_days: {
                weekdays: collectWeekdays()
            },
            wait_times: {
                rounds_1_to_5: { seconds: parseInt(formData.get('wait_early')) },
                rounds_6_to_15: { seconds: parseInt(formData.get('wait_mid')) },
                rounds_16_plus: { seconds: parseInt(formData.get('wait_late')) }
            },
            browser_restart: {
                restart_every_n_rounds: parseInt(formData.get('browser_restart'))
            }
        };

        const result = await apiCall('/config', 'POST', config);

        if (result.success) {
            showToast('Configuration saved successfully!', 'success');
            updateConfigPreview(config);
        }
    } catch (error) {
        // Error already shown in apiCall
    }
}

// Date management
function displayDates(dates) {
    const container = document.getElementById('dates-rows');
    container.innerHTML = '';

    dates.forEach((date, index) => {
        addDateRow(date);
    });
}

function addDateRow(date = '') {
    const container = document.getElementById('dates-rows');
    const row = document.createElement('div');
    row.className = 'col-md-6 mb-2';
    row.innerHTML = `
        <div class="input-group">
            <input type="date" class="form-control date-input" value="${date}">
            <button class="btn btn-outline-danger" type="button" onclick="removeDateRow(this)">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;
    container.appendChild(row);
}

function removeDateRow(button) {
    button.closest('.col-md-6').remove();
}

function collectDates() {
    const dateInputs = document.querySelectorAll('.date-input');
    return Array.from(dateInputs)
        .map(input => input.value)
        .filter(date => date); // Remove empty values
}

function generateAutoDates() {
    // Generate dates for next 4 weeks based on selected weekdays
    const selectedDays = collectWeekdays();
    if (selectedDays.length === 0) {
        showToast('Please select at least one weekday first', 'warning');
        return;
    }

    const dates = [];
    const today = new Date();
    const maxDate = new Date(today.getTime() + (28 * 24 * 60 * 60 * 1000)); // 4 weeks

    for (let d = new Date(today); d <= maxDate; d.setDate(d.getDate() + 1)) {
        if (selectedDays.includes(d.getDay())) {
            dates.push(d.toISOString().split('T')[0]);
        }
    }

    // Clear existing dates and add new ones
    document.getElementById('dates-rows').innerHTML = '';
    dates.forEach(date => addDateRow(date));

    showToast(`Generated ${dates.length} dates for the next 4 weeks`, 'success');
}

// Priority range management
function displayPriorityRanges(ranges) {
    const container = document.getElementById('priority-ranges');
    container.innerHTML = '';

    ranges.forEach(range => {
        addPriorityRange(range);
    });
}

function addPriorityRange(range = {}) {
    const container = document.getElementById('priority-ranges');
    const priority = container.children.length + 1;

    const rangeDiv = document.createElement('div');
    rangeDiv.className = 'priority-range-item';
    rangeDiv.innerHTML = `
        <span class="priority-badge">Priority ${priority}</span>
        <div class="row align-items-center">
            <div class="col-md-4">
                <input type="text" class="form-control" placeholder="e.g., 2.24.01-2.24.20"
                       value="${range.range || ''}" data-field="range">
            </div>
            <div class="col-md-6">
                <input type="text" class="form-control" placeholder="Description"
                       value="${range.reason || ''}" data-field="reason">
            </div>
            <div class="col-md-2">
                <button class="btn btn-outline-danger btn-sm w-100" type="button" onclick="removePriorityRange(this)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    container.appendChild(rangeDiv);
}

function removePriorityRange(button) {
    button.closest('.priority-range-item').remove();
    // Update priority badges
    updatePriorityBadges();
}

function updatePriorityBadges() {
    const items = document.querySelectorAll('.priority-range-item');
    items.forEach((item, index) => {
        const badge = item.querySelector('.priority-badge');
        if (badge) {
            badge.textContent = `Priority ${index + 1}`;
        }
    });
}

function collectPriorityRanges() {
    const ranges = [];
    const items = document.querySelectorAll('.priority-range-item');

    items.forEach((item, index) => {
        const range = item.querySelector('[data-field="range"]').value;
        const reason = item.querySelector('[data-field="reason"]').value;

        if (range) {
            ranges.push({
                range: range,
                priority: index + 1,
                reason: reason || `Priority ${index + 1}`
            });
        }
    });

    return ranges;
}

// Weekday collection
function collectWeekdays() {
    const weekdays = [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox && checkbox.checked) {
            weekdays.push(i);
        }
    }
    return weekdays;
}

// Configuration page functions
function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
        location.reload();
    }
}

function cancelEdit() {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
        location.href = '/';
    }
}

// Booking history functions
async function loadBookingHistory() {
    try {
        const history = await apiCall('/history');
        bookingHistory = history;
        filteredHistory = history;
        displayHistory();
        updateStatistics();
    } catch (error) {
        // Error already shown in apiCall
    }
}

function displayHistory() {
    const tbody = document.getElementById('history-tbody');
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = filteredHistory.slice(start, end);

    if (pageData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    No booking history found
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = pageData.map(booking => `
        <tr>
            <td>${booking.date}</td>
            <td>${booking.desk}</td>
            <td>${booking.time}</td>
            <td>
                <span class="booking-status ${booking.status}">
                    ${booking.status}
                </span>
            </td>
            <td>${booking.details || '-'}</td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="viewBookingDetails('${booking.id || booking.date}')">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');

    updatePagination();
}

function updatePagination() {
    const totalPages = Math.ceil(filteredHistory.length / itemsPerPage);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let paginationHtml = '';

    // Previous button
    paginationHtml += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>
        </li>
    `;

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            paginationHtml += `
                <li class="page-item disabled">
                    <a class="page-link" href="#">...</a>
                </li>
            `;
        }
    }

    // Next button
    paginationHtml += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>
        </li>
    `;

    pagination.innerHTML = paginationHtml;
}

function changePage(page) {
    const totalPages = Math.ceil(filteredHistory.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;

    currentPage = page;
    displayHistory();
}

function updateStatistics() {
    const stats = {
        success: 0,
        failed: 0,
        pending: 0,
        total: filteredHistory.length
    };

    filteredHistory.forEach(booking => {
        stats[booking.status] = (stats[booking.status] || 0) + 1;
    });

    document.getElementById('stat-success').textContent = stats.success;
    document.getElementById('stat-failed').textContent = stats.failed;
    document.getElementById('stat-pending').textContent = stats.pending;
    document.getElementById('stat-total').textContent = stats.total;
}

function filterHistory() {
    const status = document.getElementById('filter-status').value;
    const dateFrom = document.getElementById('filter-date-from').value;
    const dateTo = document.getElementById('filter-date-to').value;

    filteredHistory = bookingHistory.filter(booking => {
        if (status && booking.status !== status) return false;
        if (dateFrom && booking.date < dateFrom) return false;
        if (dateTo && booking.date > dateTo) return false;
        return true;
    });

    currentPage = 1;
    displayHistory();
    updateStatistics();
}

function clearFilters() {
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-date-from').value = '';
    document.getElementById('filter-date-to').value = '';

    filteredHistory = bookingHistory;
    currentPage = 1;
    displayHistory();
    updateStatistics();
}

function sortHistory(field) {
    if (sortField === field) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortField = field;
        sortDirection = 'asc';
    }

    filteredHistory.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];

        if (field === 'date' || field === 'time') {
            aVal = new Date(`${a.date} ${a.time}`);
            bVal = new Date(`${b.date} ${b.time}`);
        }

        if (sortDirection === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });

    displayHistory();
}

function viewBookingDetails(bookingId) {
    // This would show detailed booking information in a modal
    showToast('Booking details feature coming soon!', 'info');
}

function refreshHistory() {
    loadBookingHistory();
    showToast('History refreshed', 'info');
}

function exportHistory() {
    // Export history to CSV
    const csv = [
        ['Date', 'Desk', 'Time', 'Status', 'Details'],
        ...filteredHistory.map(booking => [
            booking.date,
            booking.desk,
            booking.time,
            booking.status,
            booking.details || ''
        ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `booking-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);

    showToast('History exported successfully', 'success');
}

// Recent bookings for dashboard
async function loadRecentBookings() {
    try {
        const history = await apiCall('/history');
        const recentBookings = history.slice(0, 5); // Last 5 bookings

        const container = document.getElementById('recent-bookings');
        if (!container) return; // Exit if element doesn't exist

        if (recentBookings.length === 0) {
            container.innerHTML = `
                <div class="text-muted text-center">
                    <i class="bi bi-calendar-x"></i>
                    <p class="mb-0 mt-2">No recent bookings</p>
                </div>
            `;
            return;
        }

        container.innerHTML = recentBookings.map(booking => `
            <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                <div>
                    <div class="fw-bold">${booking.date}</div>
                    <small class="text-muted">${booking.desk} at ${booking.time}</small>
                </div>
                <span class="booking-status ${booking.status}">${booking.status}</span>
            </div>
        `).join('');
    } catch (error) {
        const container = document.getElementById('recent-bookings');
        if (container) {
            container.innerHTML = `
                <div class="text-muted text-center">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mb-0 mt-2">Failed to load recent bookings</p>
                </div>
            `;
        }
        console.error('Failed to load recent bookings:', error);
    }
}

// Log management functions
function viewFullLogs() {
    window.location.href = '/logs';
}

function downloadSessionLog() {
    // Try to download the most recent session log
    downloadMostRecentSessionLog();
}

async function downloadMostRecentSessionLog() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Find the most recent session log
        const sessionLogs = data.logs.filter(log => log.type === 'session');
        if (sessionLogs.length > 0) {
            const mostRecent = sessionLogs[0]; // Already sorted by modification time
            window.location.href = `/api/logs/${encodeURIComponent(mostRecent.name)}`;
        } else {
            showToast('No session logs found to download', 'warning');
        }
    } catch (error) {
        console.error('Failed to download session log:', error);
        showToast(`Failed to download session log: ${error.message}`, 'error');
    }
}

// Update session log download button visibility
function updateSessionLogButton(status) {
    const downloadBtn = document.getElementById('download-log-btn');
    if (downloadBtn) {
        if (status.running) {
            downloadBtn.style.display = 'inline-block';
            downloadBtn.title = 'Download Current Session Log';
        } else {
            downloadBtn.style.display = 'none';
        }
    }
}

// Update configuration preview in dashboard
function updateConfigPreview(config) {
    // Update dashboard configuration preview
    const buildingEl = document.getElementById('config-building');
    const deskPrefixEl = document.getElementById('config-desk-prefix');
    const datesEl = document.getElementById('config-dates');
    const daysEl = document.getElementById('config-days');

    if (buildingEl) buildingEl.textContent = `${config.building || 'N/A'} / Floor ${config.floor || 'N/A'}`;
    if (deskPrefixEl) deskPrefixEl.textContent = config.desk_preferences?.prefix || 'Not set';
    if (datesEl) datesEl.textContent = (config.dates_to_try || []).length + ' dates configured';
    if (daysEl) {
        const weekdays = config.booking_days?.weekdays || [];
        const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const selectedDays = weekdays.map(day => dayNames[day]).join(', ') || 'None';
        daysEl.textContent = selectedDays;
    }
}

// Enhanced status checking with log button update
function updateStatusDisplay(status) {
    const statusLight = document.getElementById('status-light');
    const statusDisplay = document.getElementById('status-display');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const navbarStatus = document.getElementById('status-text');
    const navbarIndicator = document.querySelector('#status-indicator i');

    // Update status light
    if (status.running) {
        statusLight.className = 'status-light running';
        statusDisplay.textContent = `Running (PID: ${status.pid || 'Unknown'})`;
        startBtn.disabled = true;
        stopBtn.disabled = false;

        navbarStatus.textContent = 'Running';
        navbarIndicator.className = 'bi bi-circle-fill text-success';
    } else if (status.error) {
        statusLight.className = 'status-light error';
        statusDisplay.textContent = `Error: ${status.error}`;
        startBtn.disabled = false;
        stopBtn.disabled = true;

        navbarStatus.textContent = 'Error';
        navbarIndicator.className = 'bi bi-circle-fill text-warning';
    } else {
        statusLight.className = 'status-light stopped';
        statusDisplay.textContent = 'Stopped';
        startBtn.disabled = false;
        stopBtn.disabled = true;

        navbarStatus.textContent = 'Stopped';
        navbarIndicator.className = 'bi bi-circle-fill text-danger';
    }

    // Update session log download button
    updateSessionLogButton(status);

    // Update statistics
    document.getElementById('current-round').textContent = status.current_round || 0;
    document.getElementById('successful-bookings').textContent = status.successful_bookings || 0;
    document.getElementById('failed-attempts').textContent = status.failed_attempts || 0;

    // Update uptime
    if (status.started_at) {
        const uptime = calculateUptime(status.started_at);
        document.getElementById('uptime').textContent = uptime;
    } else {
        document.getElementById('uptime').textContent = '00:00';
    }
}

// Bot status for config page
async function checkBotStatus() {
    try {
        const status = await apiCall('/status');
        const statusEl = document.getElementById('config-status');

        if (status.running) {
            statusEl.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mb-0">Bot is currently running</p>
                    <small>Configuration changes will apply when the bot is restarted</small>
                </div>
            `;
        } else {
            statusEl.innerHTML = `
                <div class="alert alert-success mb-0">
                    <i class="bi bi-check-circle"></i>
                    <p class="mb-0">Bot is stopped</p>
                    <small>Configuration changes can be applied immediately</small>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('config-status').innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="bi bi-x-circle"></i>
                <p class="mb-0">Failed to check bot status</p>
            </div>
        `;
    }
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set up any global event listeners
    console.log('SpaceIQ Bot Web Interface initialized');
});