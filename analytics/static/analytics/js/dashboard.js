/**
 * NHIMS Analytics Dashboard - UI Interactions
 * Sidebar toggle, global search, counter animation, charts init
 */
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // ----- Sidebar Toggle -----
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });
        document.addEventListener('click', function(e) {
            if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') sidebar.classList.remove('open');
        });
    }

    // ----- Global Search (Debounced) -----
    const searchInput = document.getElementById('globalSearchInput');
    const resultsContainer = document.getElementById('globalSearchResults');
    if (searchInput && resultsContainer) {
        let debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();
            if (query.length < 2) {
                resultsContainer.style.display = 'none';
                return;
            }
            debounceTimer = setTimeout(() => {
                fetch(`/analytics/search/?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.results) {
                            let html = '';
                            const sections = ['patients', 'doctors', 'appointments', 'prescriptions', 'medical_records', 'medicines'];
                            const labels = {
                                'patients': 'Patients',
                                'doctors': 'Doctors',
                                'appointments': 'Appointments',
                                'prescriptions': 'Prescriptions',
                                'medical_records': 'Medical Records',
                                'medicines': 'Medicines'
                            };
                            let hasResults = false;
                            sections.forEach(key => {
                                if (data.results[key] && data.results[key].length > 0) {
                                    hasResults = true;
                                    html += `<div class="dropdown-header text-muted small">${labels[key]}</div>`;
                                    data.results[key].forEach(item => {
                                        html += `<a href="${item.url}" class="dropdown-item">${item.name}</a>`;
                                    });
                                }
                            });
                            if (!hasResults) html = `<div class="dropdown-item text-muted">No results found</div>`;
                            resultsContainer.innerHTML = html;
                            resultsContainer.style.display = 'block';
                        }
                    })
                    .catch(() => resultsContainer.style.display = 'none');
            }, 350);
        });

        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    }

    // ----- Counter Animation (Stat Cards) -----
    const counters = document.querySelectorAll('.stat-value[data-count]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'), 10);
        if (isNaN(target)) return;
        let current = 0;
        const increment = Math.ceil(target / 40);
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.innerText = target;
                clearInterval(timer);
            } else {
                counter.innerText = current;
            }
        }, 25);
    });

    // ----- Refresh Button (simple) -----
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            this.querySelector('i').classList.add('fa-spin');
            setTimeout(() => {
                location.reload();
            }, 300);
        });
    }

    // ----- Charts Initialization (if Chart.js exists) -----
    if (typeof Chart !== 'undefined' && window.chartData) {
        const data = window.chartData;

        // Helper: create chart with dark theme
        function createChart(id, config) {
            const canvas = document.getElementById(id);
            if (!canvas) return null;
            const ctx = canvas.getContext('2d');
            return new Chart(ctx, config);
        }

        // ---- Chart IDs must match the ones in dashboard.html ----
        // 1. Patient Registration Trend (Line) - uses canvas id "patientsTrend"
        if (data.patients_per_month?.labels?.length) {
            createChart('patientsTrend', {
                type: 'line',
                data: {
                    labels: data.patients_per_month.labels,
                    datasets: [{
                        label: 'Patients',
                        data: data.patients_per_month.data,
                        borderColor: '#22C55E',
                        backgroundColor: 'rgba(34,197,94,0.1)',
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#22C55E',
                        pointBorderColor: '#22C55E',
                        pointBorderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#94A3B8', font: { size: 11 } } }
                    },
                    scales: {
                        y: { ticks: { color: '#94A3B8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { ticks: { color: '#94A3B8' }, grid: { display: false } }
                    }
                }
            });
        }

        // 2. Appointment Trend (Bar) - uses canvas id "appointmentsTrend"
        if (data.appointments_per_month?.labels?.length) {
            createChart('appointmentsTrend', {
                type: 'bar',
                data: {
                    labels: data.appointments_per_month.labels,
                    datasets: [{
                        label: 'Appointments',
                        data: data.appointments_per_month.data,
                        backgroundColor: 'rgba(37,99,235,0.6)',
                        borderColor: '#2563EB',
                        borderWidth: 2,
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#94A3B8', font: { size: 11 } } }
                    },
                    scales: {
                        y: { ticks: { color: '#94A3B8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { ticks: { color: '#94A3B8' }, grid: { display: false } }
                    }
                }
            });
        }

        // 3. Medicine Stock (Doughnut) - uses canvas id "medicineStock"
        const stockLabels = ['In Stock', 'Low Stock', 'Out of Stock', 'Expired'];
        const stockData = [65, 20, 10, 5];
        createChart('medicineStock', {
            type: 'doughnut',
            data: {
                labels: stockLabels,
                datasets: [{
                    data: stockData,
                    backgroundColor: ['#22C55E', '#F59E0B', '#EF4444', '#64748B'],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94A3B8', font: { size: 10 }, padding: 12, usePointStyle: true, pointStyle: 'circle' }
                    }
                },
                cutout: '65%',
            }
        });

        // 4. Revenue Overview (Line) - uses canvas id "revenueChart"
        const revenueLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
        const revenueData = [45000, 52000, 49000, 58000, 62000, 71000];
        createChart('revenueChart', {
            type: 'line',
            data: {
                labels: revenueLabels,
                datasets: [{
                    label: 'Revenue (BDT)',
                    data: revenueData,
                    borderColor: '#F59E0B',
                    backgroundColor: 'rgba(245,158,11,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#F59E0B',
                    pointBorderColor: '#F59E0B',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#94A3B8', font: { size: 11 } } }
                },
                scales: {
                    y: { ticks: { color: '#94A3B8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { ticks: { color: '#94A3B8' }, grid: { display: false } }
                }
            }
        });
    }
});