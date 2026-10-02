/**
 * IronPulse Gym Management System - Core Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const menuToggleBtn = document.getElementById('menuToggleBtn');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggleBtn && sidebar) {
        menuToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && sidebar.classList.contains('show') && !sidebar.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // 2. Auto Dismiss Flash Alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 6000);
    });

    // 3. Confirm Delete Prompts
    document.querySelectorAll('.delete-form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const itemName = form.dataset.item || 'this record';
            if (!confirm(`Are you sure you want to permanently delete ${itemName}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });

    // 4. Dynamic End Date Calculation in Member Forms
    const planSelect = document.getElementById('plan_id');
    const startDateInput = document.getElementById('membership_start');
    const endDateInput = document.getElementById('membership_end');

    function calculateEndDate() {
        if (!planSelect || !startDateInput || !endDateInput) return;
        
        const selectedOption = planSelect.options[planSelect.selectedIndex];
        if (!selectedOption) return;

        const durationMonths = parseInt(selectedOption.dataset.months || '1', 10);
        const startDateVal = startDateInput.value;

        if (startDateVal) {
            const start = new Date(startDateVal);
            if (!isNaN(start.getTime())) {
                const end = new Date(start);
                end.setMonth(end.getMonth() + durationMonths);
                
                // Format to YYYY-MM-DD
                const yyyy = end.getFullYear();
                const mm = String(end.getMonth() + 1).padStart(2, '0');
                const dd = String(end.getDate()).padStart(2, '0');
                endDateInput.value = `${yyyy}-${mm}-${dd}`;
            }
        }
    }

    if (planSelect && startDateInput && endDateInput) {
        planSelect.addEventListener('change', calculateEndDate);
        startDateInput.addEventListener('change', calculateEndDate);
        calculateEndDate();
    }

    // 5. Initialize Dashboard Charts (if elements present)
    initDashboardCharts();
});

/**
 * Initializes Chart.js on the dashboard
 */
function initDashboardCharts() {
    const statusCanvas = document.getElementById('membershipStatusChart');
    const revenueCanvas = document.getElementById('monthlyRevenueChart');

    if (statusCanvas && window.Chart) {
        try {
            const activeCount = parseInt(statusCanvas.dataset.active || '0', 10);
            const expiredCount = parseInt(statusCanvas.dataset.expired || '0', 10);
            const pendingCount = parseInt(statusCanvas.dataset.pending || '0', 10);
            const inactiveCount = parseInt(statusCanvas.dataset.inactive || '0', 10);

            new Chart(statusCanvas, {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'Expired', 'Pending', 'Inactive'],
                    datasets: [{
                        data: [activeCount, expiredCount, pendingCount, inactiveCount],
                        backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#64748b'],
                        borderColor: '#162033',
                        borderWidth: 3,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#94a3b8',
                                font: { family: 'Plus Jakarta Sans', size: 12 },
                                padding: 15
                            }
                        }
                    },
                    cutout: '72%'
                }
            });
        } catch (err) {
            console.error('Error rendering status chart:', err);
        }
    }

    if (revenueCanvas && window.Chart) {
        try {
            const rawLabels = revenueCanvas.dataset.labels || '[]';
            const rawData = revenueCanvas.dataset.data || '[]';
            
            const labels = JSON.parse(rawLabels);
            const dataValues = JSON.parse(rawData);

            new Chart(revenueCanvas, {
                type: 'line',
                data: {
                    labels: labels.length > 0 ? labels : ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'],
                    datasets: [{
                        label: 'Revenue (₹)',
                        data: dataValues.length > 0 ? dataValues : [28000, 34000, 42000, 39000, 51000, 68000],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.12)',
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#2563eb',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => ` Revenue: ₹${Number(context.raw).toLocaleString('en-IN')}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans' } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { family: 'Plus Jakarta Sans' },
                                callback: (val) => '₹' + val.toLocaleString('en-IN')
                            }
                        }
                    }
                }
            });
        } catch (err) {
            console.error('Error rendering revenue chart:', err);
        }
    }
}
