/**
 * NHIMS Analytics Dashboard – ApexCharts Initialization
 * All charts in dark theme with smooth animations
 */
(function() {
    'use strict';

    // ── Check if ApexCharts is loaded ──
    if (typeof ApexCharts === 'undefined') {
        console.error('ApexCharts library not loaded. Charts will not render.');
        document.querySelectorAll('.chart-container').forEach(container => {
            container.innerHTML = '<div class="text-center text-gray-400 py-4">Chart library not loaded</div>';
        });
        return;
    }

    // ── Dark theme palette ──
    const colors = ['#2563EB', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#EC4899'];

    // ── Global ApexCharts options ──
    const defaultOptions = {
        theme: {
            mode: 'dark',
            palette: 'palette1'
        },
        chart: {
            background: 'transparent',
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            },
            toolbar: {
                show: false
            },
            fontFamily: 'Inter, sans-serif'
        },
        grid: {
            borderColor: 'rgba(255,255,255,0.05)',
            strokeDashArray: 3,
            show: true,
            position: 'back'
        },
        tooltip: {
            theme: 'dark',
            style: {
                fontSize: '12px',
                fontFamily: 'Inter, sans-serif'
            },
            x: {
                show: true
            }
        },
        legend: {
            labels: {
                colors: '#94A3B8',
                fontFamily: 'Inter, sans-serif'
            },
            itemMargin: {
                horizontal: 10,
                vertical: 5
            }
        }
    };

    // ── Chart data (static example – replace with real data) ──
    const monthLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const patientData = [120, 135, 150, 170, 190, 210, 230, 250, 270, 290, 310, 330];
    const appointmentData = [80, 95, 110, 125, 140, 160, 175, 190, 210, 225, 240, 260];
    const revenueData = [45000, 52000, 49000, 58000, 62000, 71000, 68000, 75000, 82000, 79000, 88000, 92000];
    const hospitalData = [
        { name: 'Dhaka Medical', patients: 1200 },
        { name: 'Square Hospital', patients: 980 },
        { name: 'Apollo', patients: 780 },
        { name: 'United Hospital', patients: 650 },
        { name: 'Chittagong Med', patients: 540 }
    ];
    const deptData = [
        { label: 'Cardiology', value: 35 },
        { label: 'Neurology', value: 28 },
        { label: 'Pediatrics', value: 22 },
        { label: 'Orthopedics', value: 18 },
        { label: 'Others', value: 12 }
    ];
    const genderData = [
        { label: 'Male', value: 55 },
        { label: 'Female', value: 45 }
    ];
    const ageData = [
        { label: '0-18', value: 20 },
        { label: '19-35', value: 45 },
        { label: '36-50', value: 60 },
        { label: '51-65', value: 40 },
        { label: '65+', value: 25 }
    ];
    const stockData = [
        { label: 'In Stock', value: 65 },
        { label: 'Low Stock', value: 20 },
        { label: 'Out of Stock', value: 10 },
        { label: 'Expired', value: 5 }
    ];

    // ── Helper to create a chart ──
    function createChart(elementId, config) {
        const el = document.querySelector('#' + elementId);
        if (!el) {
            console.warn('Chart container not found:', elementId);
            return null;
        }
        try {
            const chart = new ApexCharts(el, config);
            chart.render();
            // Store reference for download
            if (!window.charts) window.charts = {};
            window.charts[elementId] = chart;
            return chart;
        } catch (e) {
            console.error('Error rendering chart:', elementId, e);
            return null;
        }
    }

    // ── 1. Patient Registration Trend (Area) ──
    function initPatientsTrend() {
        const config = {
            ...defaultOptions,
            series: [{
                name: 'Patients',
                data: patientData
            }],
            chart: {
                ...defaultOptions.chart,
                type: 'area',
                height: 220,
                zoom: { enabled: false }
            },
            stroke: {
                curve: 'smooth',
                width: 2
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.4,
                    opacityTo: 0.05
                }
            },
            xaxis: {
                categories: monthLabels,
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } }
            },
            colors: ['#2563EB']
        };
        createChart('patientsTrend', config);
    }

    // ── 2. Appointment Trend (Column) ──
    function initAppointmentsTrend() {
        const config = {
            ...defaultOptions,
            series: [{
                name: 'Appointments',
                data: appointmentData
            }],
            chart: {
                ...defaultOptions.chart,
                type: 'bar',
                height: 220
            },
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    columnWidth: '50%'
                }
            },
            xaxis: {
                categories: monthLabels,
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } }
            },
            colors: ['#2563EB']
        };
        createChart('appointmentsTrend', config);
    }

    // ── 3. Revenue Analytics (Line) ──
    function initRevenueChart() {
        const config = {
            ...defaultOptions,
            series: [{
                name: 'Revenue (BDT)',
                data: revenueData
            }],
            chart: {
                ...defaultOptions.chart,
                type: 'line',
                height: 220,
                zoom: { enabled: false }
            },
            stroke: {
                curve: 'smooth',
                width: 2
            },
            xaxis: {
                categories: monthLabels,
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#94A3B8', fontSize: '10px' }, formatter: function(v) { return 'BDT ' + v.toLocaleString(); } }
            },
            colors: ['#22C55E']
        };
        createChart('revenueChart', config);
    }

    // ── 4. Hospital Performance (Horizontal Bar) ──
    function initHospitalPerformance() {
        const config = {
            ...defaultOptions,
            series: [{
                name: 'Patients',
                data: hospitalData.map(d => d.patients)
            }],
            chart: {
                ...defaultOptions.chart,
                type: 'bar',
                height: 220
            },
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    horizontal: true,
                    barHeight: '60%'
                }
            },
            xaxis: {
                categories: hospitalData.map(d => d.name),
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } }
            },
            colors: ['#8B5CF6']
        };
        createChart('hospitalPerformance', config);
    }

    // ── 5. Department Distribution (Donut) ──
    function initDepartmentDist() {
        const config = {
            ...defaultOptions,
            series: deptData.map(d => d.value),
            chart: {
                ...defaultOptions.chart,
                type: 'donut',
                height: 220
            },
            labels: deptData.map(d => d.label),
            colors: ['#2563EB', '#22C55E', '#F59E0B', '#8B5CF6', '#EC4899'],
            legend: {
                ...defaultOptions.legend,
                position: 'bottom',
                fontSize: '10px'
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '65%'
                    }
                }
            }
        };
        createChart('departmentDist', config);
    }

    // ── 6. Gender Distribution (Pie) ──
    function initGenderDist() {
        const config = {
            ...defaultOptions,
            series: genderData.map(d => d.value),
            chart: {
                ...defaultOptions.chart,
                type: 'pie',
                height: 220
            },
            labels: genderData.map(d => d.label),
            colors: ['#2563EB', '#EC4899'],
            legend: {
                ...defaultOptions.legend,
                position: 'bottom',
                fontSize: '10px'
            }
        };
        createChart('genderDist', config);
    }

    // ── 7. Age Group Distribution (Bar) ──
    function initAgeGroup() {
        const config = {
            ...defaultOptions,
            series: [{
                name: 'Patients',
                data: ageData.map(d => d.value)
            }],
            chart: {
                ...defaultOptions.chart,
                type: 'bar',
                height: 220
            },
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    columnWidth: '50%'
                }
            },
            xaxis: {
                categories: ageData.map(d => d.label),
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#94A3B8', fontSize: '10px' } }
            },
            colors: ['#06B6D4']
        };
        createChart('ageGroup', config);
    }

    // ── 8. Medicine Stock (Radial Progress) ──
    function initMedicineStock() {
        const total = stockData.reduce((sum, d) => sum + d.value, 0);
        const inStock = stockData.find(d => d.label === 'In Stock').value;
        const percent = Math.round((inStock / total) * 100);
        const config = {
            ...defaultOptions,
            series: [percent],
            chart: {
                ...defaultOptions.chart,
                type: 'radialBar',
                height: 220,
                offsetY: -10
            },
            plotOptions: {
                radialBar: {
                    startAngle: -135,
                    endAngle: 135,
                    hollow: {
                        size: '60%'
                    },
                    track: {
                        background: 'rgba(255,255,255,0.05)',
                        strokeWidth: '90%'
                    },
                    dataLabels: {
                        name: {
                            show: true,
                            fontSize: '13px',
                            color: '#94A3B8',
                            offsetY: -10
                        },
                        value: {
                            fontSize: '20px',
                            fontWeight: 700,
                            color: '#F8FAFC',
                            offsetY: 5,
                            formatter: function(v) { return v + '%'; }
                        }
                    }
                }
            },
            labels: ['In Stock'],
            colors: ['#22C55E']
        };
        createChart('medicineStock', config);
    }

    // ── Initialize all charts ──
    function initAllCharts() {
        // Ensure all chart containers exist before initializing
        if (document.getElementById('patientsTrend')) initPatientsTrend();
        if (document.getElementById('appointmentsTrend')) initAppointmentsTrend();
        if (document.getElementById('revenueChart')) initRevenueChart();
        if (document.getElementById('hospitalPerformance')) initHospitalPerformance();
        if (document.getElementById('departmentDist')) initDepartmentDist();
        if (document.getElementById('genderDist')) initGenderDist();
        if (document.getElementById('ageGroup')) initAgeGroup();
        if (document.getElementById('medicineStock')) initMedicineStock();
        console.log('All charts initialized successfully.');
    }

    // ── Run when DOM ready ──
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllCharts);
    } else {
        initAllCharts();
    }
})();