document.addEventListener('DOMContentLoaded', () => {
    const analyticsEl = document.getElementById('analytics-data');
    if (!analyticsEl) {
        return;
    }

    let analytics;
    try {
        analytics = JSON.parse(analyticsEl.textContent || '{}');
    } catch (error) {
        console.warn('Failed to parse analytics payload:', error);
        return;
    }

    const charts = {};

    hydrateStatsCounters();
    charts.mood = renderMoodBreakdownChart(analytics.mood_chart);
    charts.trend = renderMoodTrendChart(analytics.trend);
    buildHeatmap(analytics.heatmap);
    hydrateKeywordPills();
    revealAnalyticsCards();
    updateConsistencyRings();

    handleThemeChanges(charts);
    loadAdsIfPresent();
});

function hydrateStatsCounters() {
    const counters = document.querySelectorAll('.count-up');
    if (!counters.length) {
        return;
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    counters.forEach(counter => {
        const targetValue = Number(counter.dataset.target || '0');
        const decimals = Number.parseInt(counter.dataset.decimals || counter.dataset.precision || '0', 10) || 0;
        const factor = Math.pow(10, decimals);

        const formatValue = (value) => {
            if (!Number.isFinite(value)) {
                return counter.dataset.target || '0';
            }
            if (decimals > 0) {
                return (Math.round(value * factor) / factor).toFixed(decimals);
            }
            return Math.round(value).toString();
        };

        if (!Number.isFinite(targetValue)) {
            counter.textContent = counter.dataset.target || '0';
            return;
        }

        if (prefersReducedMotion) {
            counter.textContent = formatValue(targetValue);
            return;
        }

        counter.textContent = formatValue(0);
        const duration = 800;
        const startTime = performance.now();

        function update(now) {
            const progress = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = formatValue(eased * targetValue);
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    });
}

function renderMoodBreakdownChart(moodChart) {
    const ctx = document.getElementById('moodChart');
    if (!ctx || !moodChart || !moodChart.labels || !moodChart.data || !moodChart.data.length) {
        const card = document.querySelector('[data-analytics="mood-breakdown"]');
        if (card) {
            card.classList.add('is-empty');
            const body = card.querySelector('.card-body');
            if (body) {
                body.innerHTML = '<p class="text-muted mb-0">Not enough data yet — start journaling to see your mood breakdown.</p>';
            }
        }
        return null;
    }

    const palette = ['#0d6efd', '#198754', '#fd7e14', '#dc3545', '#6610f2', '#20c997', '#ffc107'];
    const dataset = {
        data: moodChart.data,
        backgroundColor: moodChart.data.map((_, index) => palette[index % palette.length]),
        borderWidth: 1,
        borderColor: '#ffffff'
    };

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: moodChart.labels,
            datasets: [dataset]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color')
                    }
                }
            }
        }
    });
}

function renderMoodTrendChart(trend) {
    const ctx = document.getElementById('moodTrendChart');
    if (!ctx || !trend || !trend.labels || !trend.labels.length) {
        const card = document.querySelector('[data-analytics="trend"]');
        if (card) {
            card.classList.add('is-empty');
            const body = card.querySelector('.card-body');
            if (body) {
                body.innerHTML = '<p class="text-muted mb-0">Keep writing to unlock mood trends.</p>';
            }
        }
        return null;
    }

    const palette = ['#0d6efd', '#198754', '#fd7e14', '#dc3545', '#6610f2', '#20c997', '#ffc107'];
    const datasets = (trend.datasets || []).map((dataset, index) => {
        const color = palette[index % palette.length];
        return {
            label: dataset.label,
            data: dataset.data,
            borderColor: color,
            backgroundColor: hexWithOpacity(color, 0.15),
            tension: 0.35,
            fill: true,
            spanGaps: true,
            pointRadius: 2,
            borderWidth: 2
        };
    });

    if (!datasets.length) {
        return null;
    }

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.labels,
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-color'),
                        maxTicksLimit: 6
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    ticks: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-color'),
                        precision: 0
                    },
                    grid: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-border-color')
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color')
                    }
                }
            }
        }
    });
}

function buildHeatmap(heatmap) {
    const heatmapCard = document.querySelector('[data-analytics="heatmap"]');
    const grid = heatmapCard ? heatmapCard.querySelector('.heatmap-grid') : null;
    if (!heatmapCard || !grid || !heatmap || !Array.isArray(heatmap.points)) {
        return;
    }

    grid.innerHTML = '';
    const points = heatmap.points;
    const max = Math.max(1, Number(heatmap.max) || 0);

    if (!points.length || max === 0) {
        heatmapCard.classList.add('is-empty');
        const body = heatmapCard.querySelector('.card-body');
        if (body) {
            body.innerHTML = '<p class="text-muted mb-0">Write a little more to light up your heatmap.</p>';
        }
        return;
    }

    const palette = ['#eef4ff', '#cfe1ff', '#9bc6ff', '#5ba3f7', '#1c7cd6'];
    points.forEach(point => {
        const value = Number(point.count) || 0;
        const intensityIndex = value === 0 ? 0 : Math.min(palette.length - 1, Math.round((value / max) * (palette.length - 1)));
        const cell = document.createElement('span');
        cell.className = 'heatmap-cell';
        cell.style.setProperty('--heatmap-color', palette[intensityIndex]);
        cell.title = `${point.date}: ${value} entr${value === 1 ? 'y' : 'ies'}`;
        cell.dataset.count = value;
        grid.appendChild(cell);
    });
}

function hydrateKeywordPills() {
    const pills = document.querySelectorAll('.keyword-pill');
    if (!pills.length) {
        return;
    }

    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            const keyword = pill.dataset.keyword;
            if (!keyword) {
                return;
            }
            const url = new URL(window.location.href);
            url.searchParams.set('search', keyword);
            url.searchParams.delete('page');
            window.location.href = url.toString();
        });
    });
}

function revealAnalyticsCards() {
    document.querySelectorAll('.analytics-card').forEach(card => {
        card.classList.remove('is-loading');
        card.querySelectorAll('.skeleton').forEach(skeleton => skeleton.remove());
        card.dataset.animate = card.dataset.animate || 'fade';
    });
}

function updateConsistencyRings() {
    const rings = document.querySelectorAll('[data-consistency-ring]');
    if (!rings.length) {
        return;
    }

    rings.forEach(ring => {
        const rawValue = Number(ring.dataset.consistencyRing || ring.getAttribute('aria-valuenow') || 0);
        const clamped = Math.max(0, Math.min(100, Number.isFinite(rawValue) ? rawValue : 0));
        const degrees = clamped * 3.6;
        ring.setAttribute('aria-valuenow', clamped.toString());
        ring.dataset.consistencyRing = clamped.toString();
        ring.style.background = `conic-gradient(var(--consistency-color, #0d6efd) 0deg ${degrees}deg, var(--consistency-track, rgba(13, 110, 253, 0.12)) ${degrees}deg 360deg)`;
    });
}

function handleThemeChanges(charts) {
    document.addEventListener('themeChange', () => {
        const bodyColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color');
        const secondaryColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-color');
        const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-border-color');

        if (charts.mood) {
            charts.mood.options.plugins.legend.labels.color = bodyColor;
            charts.mood.update();
        }

        if (charts.trend) {
            charts.trend.options.plugins.legend.labels.color = bodyColor;
            charts.trend.options.scales.x.ticks.color = secondaryColor;
            charts.trend.options.scales.y.ticks.color = secondaryColor;
            charts.trend.options.scales.y.grid.color = borderColor;
            charts.trend.update();
        }
    });
}

function loadAdsIfPresent() {
    if (window.adsbygoogle && document.querySelector('.adsbygoogle')) {
        try {
            (adsbygoogle = window.adsbygoogle || []).push({});
        } catch (error) {
            console.warn('AdSense load failed:', error);
        }
    }
}

function hexWithOpacity(hex, opacity) {
    if (!hex.startsWith('#')) {
        return hex;
    }

    let normalized = hex.replace('#', '');
    if (normalized.length === 3) {
        normalized = normalized.split('').map(char => `${char}${char}`).join('');
    }

    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}
