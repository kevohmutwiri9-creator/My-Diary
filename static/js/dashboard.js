document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('moodChart');
    if (!ctx) {
        return;
    }

    const metaEl = document.getElementById('moodChart-data');
    let chartLabels = [];
    let chartData = [];

    if (metaEl) {
        try {
            const chartMeta = JSON.parse(metaEl.textContent || '{}');
            chartLabels = Array.isArray(chartMeta.labels) ? chartMeta.labels : [];
            chartData = Array.isArray(chartMeta.data) ? chartMeta.data : [];
        } catch (error) {
            console.warn('Failed to parse mood chart data:', error);
        }
    }

    if (!chartLabels.length || !chartData.length) {
        return;
    }

    const chartConfig = {
        type: 'doughnut',
        data: {
            labels: chartLabels,
            datasets: [
                {
                    data: chartData,
                    backgroundColor: [
                        '#0d6efd', '#198754', '#fd7e14', '#dc3545', '#6610f2', '#20c997', '#ffc107'
                    ],
                    borderWidth: 1,
                    borderColor: '#ffffff'
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color')
                    }
                }
            }
        }
    };

    window.moodChart = new Chart(ctx, chartConfig);

    document.addEventListener('themeChange', () => {
        if (!window.moodChart) {
            return;
        }
        const legendLabels = window.moodChart.options.plugins.legend.labels;
        legendLabels.color = getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color');
        window.moodChart.update();
    });

    if (window.adsbygoogle && document.querySelector('.adsbygoogle')) {
        try {
            (adsbygoogle = window.adsbygoogle || []).push({});
        } catch (error) {
            console.warn('AdSense load failed:', error);
        }
    }
});
