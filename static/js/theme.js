(function () {
    'use strict';

    const htmlEl = document.documentElement;
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const storedTheme = localStorage.getItem('theme');
    let currentTheme = storedTheme || (prefersDark.matches ? 'dark' : 'light');

    function setTheme(theme) {
        currentTheme = theme;
        htmlEl.setAttribute('data-bs-theme', theme);
        if (themeToggleElement) {
            themeToggleElement.classList.toggle('active', theme === 'dark');
        }
        document.dispatchEvent(new CustomEvent('themeChange', { detail: { theme } }));
    }

    function toggleTheme() {
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', nextTheme);
        setTheme(nextTheme);
    }

    function handleToggleKey(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleTheme();
        }
    }

    // Apply theme immediately to avoid flashes
    let themeToggleElement = null;
    setTheme(currentTheme);

    document.addEventListener('DOMContentLoaded', () => {
        themeToggleElement = document.getElementById('themeToggle');

        if (themeToggleElement) {
            themeToggleElement.addEventListener('click', toggleTheme);
            themeToggleElement.addEventListener('keydown', handleToggleKey);
        }

        document.body.classList.remove('theme-loading');
        document.body.classList.add('theme-loaded');
    });

    prefersDark.addEventListener('change', (event) => {
        if (!localStorage.getItem('theme')) {
            setTheme(event.matches ? 'dark' : 'light');
        }
    });

    window.themeManager = {
        setTheme,
        toggleTheme,
        getCurrentTheme: () => currentTheme
    };
})();
