// Analytics Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Get analytics data from JSON script tag
    const analyticsScript = document.getElementById('analytics-data');
    let analyticsData = {};
    
    if (analyticsScript) {
        try {
            analyticsData = JSON.parse(analyticsScript.textContent);
        } catch (e) {
            console.error('Error parsing analytics data:', e);
        }
    }
    
    // Initialize all analytics components
    initializeMoodChart(analyticsData.mood_chart);
    initializeTrendChart(analyticsData.trend);
    initializeHeatmap(analyticsData.heatmap);
    initializeKeywordCloud(analyticsData.keywords);
    animateCounters();
});

// Mood Chart
function initializeMoodChart(moodData) {
    const ctx = document.getElementById('moodChart');
    if (!ctx) return;

    // Use provided data or fallback
    const data = moodData && moodData.labels ? moodData : {
        labels: ['Happy', 'Neutral', 'Sad', 'Excited', 'Anxious'],
        data: [15, 8, 3, 12, 2]
    };

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data || data.labels,
                backgroundColor: [
                    '#28a745',
                    '#6c757d', 
                    '#dc3545',
                    '#ffc107',
                    '#17a2b8'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                }
            }
        }
    });
}

// Writing Trends Chart
function initializeTrendChart(trendData) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    const data = trendData && trendData.labels ? trendData : {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        data: [2, 1, 3, 2, 0, 1, 2]
    };

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Entries',
                data: data.data || data.labels,
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Activity Heatmap
function initializeHeatmap(heatmapData) {
    const container = document.getElementById('activityHeatmap');
    if (!container) return;

    // Use provided data or fallback
    const data = heatmapData && Array.isArray(heatmapData) ? heatmapData : [];
    
    // If no data, show empty state
    if (data.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4"><i class="bi bi-calendar-x fs-1 mb-3 d-block"></i><p>No activity data available yet</p><small>Start writing to see your activity heatmap!</small></div>';
        return;
    }
    
    let html = '<div class="heatmap-calendar">';
    html += '<div class="heatmap-legend mb-2">';
    html += '<span class="text-muted">Less</span>';
    html += '<div class="heatmap-scale">';
    for (let i = 0; i < 5; i++) {
        html += `<div class="heatmap-cell intensity-${i}"></div>`;
    }
    html += '</div>';
    html += '<span class="text-muted">More</span>';
    html += '</div>';
    
    html += '<div class="heatmap-grid">';
    data.forEach(day => {
        const count = day.count || day.entries || 0;
        const intensity = Math.min(4, Math.floor(count / 2));
        const date = day.date || day.day || '';
        html += `<div class="heatmap-cell intensity-${intensity}" title="${date}: ${count} entries"></div>`;
    });
    html += '</div></div>';
    
    container.innerHTML = html;
}

// Keyword Cloud
function initializeKeywordCloud(keywordData) {
    const container = document.getElementById('keywordCloud');
    if (!container) return;

    const keywords = keywordData && keywordData.top_topics ? keywordData.top_topics : [
        { word: 'work', count: 15 },
        { word: 'family', count: 12 },
        { word: 'health', count: 8 },
        { word: 'friends', count: 6 },
        { word: 'travel', count: 4 }
    ];

    let html = '<div class="keyword-cloud-wrapper">';
    keywords.forEach(keyword => {
        const size = 0.8 + (keyword.count / keywords[0].count) * 0.8;
        html += `<span class="keyword-cloud-item" style="font-size: ${size}rem;">${keyword.word}</span>`;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// Animate Counters
function animateCounters() {
    const counters = document.querySelectorAll('.count-up');
    
    counters.forEach(counter => {
        const target = parseInt(counter.dataset.target);
        const duration = 2000; // 2 seconds
        const increment = target / (duration / 16); // 60fps
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target;
            }
        };
        
        // Start animation when element is in view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(counter);
    });
}

// Helper function to generate sample heatmap data
function generateSampleHeatmapData() {
    const data = [];
    const today = new Date();
    
    for (let i = 29; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        
        data.push({
            date: date.toLocaleDateString(),
            count: Math.floor(Math.random() * 5)
        });
    }
    
    return data;
}

// Export functions for global access
window.analyticsDashboard = {
    initializeMoodChart,
    initializeTrendChart,
    initializeHeatmap,
    initializeKeywordCloud,
    animateCounters
};
