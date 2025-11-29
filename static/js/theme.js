(function () {
    'use strict';

    const htmlEl = document.documentElement;
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const storedTheme = localStorage.getItem('theme') || 'system';
    const availableThemes = ['light', 'dark', 'high-contrast', 'blue', 'green', 'system'];
    let currentTheme = storedTheme;
    let isTransitioning = false;

    // Theme configurations with icons and colors
    const themeConfig = {
        'system': { icon: 'bi-laptop', color: '#6c757d' },
        'light': { icon: 'bi-brightness-high-fill', color: '#ffc107' },
        'dark': { icon: 'bi-moon-stars-fill', color: '#6f42c1' },
        'high-contrast': { icon: 'bi-circle-half', color: '#000000' },
        'blue': { icon: 'bi-droplet-fill', color: '#0066cc' },
        'green': { icon: 'bi-tree-fill', color: '#28a745' }
    };

    // Apply theme immediately to avoid flashes
    applyTheme(currentTheme);

    function applyTheme(theme) {
        if (isTransitioning) return;
        
        // If theme is 'system', use the system preference
        const effectiveTheme = theme === 'system' 
            ? (prefersDark.matches ? 'dark' : 'light')
            : theme;

        isTransitioning = true;
        
        // Add transition class for smooth theme change
        document.body.classList.add('theme-transitioning');
        
        // Update theme attribute
        htmlEl.setAttribute('data-bs-theme', effectiveTheme);
        currentTheme = theme;
        localStorage.setItem('theme', theme);
        
        // Sync with server if user is logged in
        syncThemeWithServer(theme);
        
        // Update the UI to reflect the current theme
        updateThemeUI(theme);
        updateThemeIcon(theme);
        
        // Apply theme-specific animations
        applyThemeAnimation(theme);
        
        // Dispatch event for any components that need to know about theme changes
        document.dispatchEvent(new CustomEvent('themeChange', { 
            detail: { 
                theme: effectiveTheme,
                themeName: theme,
                config: themeConfig[theme]
            } 
        }));
        
        // Remove transition class after animation
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
            isTransitioning = false;
        }, 300);
    }

    function syncThemeWithServer(theme) {
        // Only sync if user is logged in (check for login token or user data)
        if (document.querySelector('[data-user-logged-in="true"]') || 
            localStorage.getItem('userLoggedIn') === 'true') {
            
            fetch('/theme/set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ theme: theme })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.warn('Failed to sync theme with server:', data.message);
                }
            })
            .catch(error => {
                console.warn('Theme sync error:', error);
            });
        }
    }

    function getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    function updateThemeUI(theme) {
        // Update theme dropdown
        const themeDropdownItems = document.querySelectorAll('.theme-option');
        themeDropdownItems.forEach(item => {
            const itemTheme = item.dataset.theme;
            const checkIcon = item.querySelector('.theme-check');
            const optionIcon = item.querySelector('.theme-option-icon');
            
            if (itemTheme === theme) {
                item.classList.add('active');
                if (checkIcon) {
                    checkIcon.style.display = 'inline';
                    // Animate check appearance
                    checkIcon.style.animation = 'checkBounce 0.5s ease';
                }
                if (optionIcon) {
                    optionIcon.style.color = themeConfig[theme].color;
                }
            } else {
                item.classList.remove('active');
                if (checkIcon) checkIcon.style.display = 'none';
                if (optionIcon) optionIcon.style.color = '';
            }
        });
    }

    function updateThemeIcon(theme) {
        const themeIcon = document.querySelector('.theme-icon');
        const themeBtn = document.querySelector('.theme-toggle-btn');
        
        if (themeIcon && themeBtn) {
            const config = themeConfig[theme];
            
            // Update icon with animation
            themeIcon.style.transform = 'scale(0) rotate(180deg)';
            themeIcon.style.transition = 'transform 0.3s ease';
            
            setTimeout(() => {
                themeIcon.className = `bi ${config.icon} theme-icon me-1`;
                themeIcon.style.color = config.color;
                themeIcon.style.transform = 'scale(1) rotate(0deg)';
            }, 150);
            
            // Update button color
            themeBtn.style.borderColor = config.color;
            themeBtn.style.color = config.color;
        }
    }

    function applyThemeAnimation(theme) {
        // Create floating particles for theme change
        if (theme === 'dark' || theme === 'blue') {
            createThemeParticles('night');
        } else if (theme === 'green') {
            createThemeParticles('nature');
        } else if (theme === 'light') {
            createThemeParticles('light');
        } else if (theme === 'high-contrast') {
            createThemeParticles('contrast');
        }
    }

    function createThemeParticles(type) {
        const container = document.body;
        const particleCount = 15;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'theme-particle';
            
            // Set particle style based on theme type
            switch(type) {
                case 'night':
                    particle.style.background = 'radial-gradient(circle, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0) 70%)';
                    particle.style.width = Math.random() * 4 + 2 + 'px';
                    particle.style.height = particle.style.width;
                    break;
                case 'nature':
                    particle.style.background = 'radial-gradient(circle, rgba(40,167,69,0.6) 0%, rgba(40,167,69,0) 70%)';
                    particle.style.width = Math.random() * 6 + 3 + 'px';
                    particle.style.height = particle.style.width;
                    break;
                case 'light':
                    particle.style.background = 'radial-gradient(circle, rgba(255,193,7,0.8) 0%, rgba(255,193,7,0) 70%)';
                    particle.style.width = Math.random() * 8 + 4 + 'px';
                    particle.style.height = particle.style.width;
                    break;
                case 'contrast':
                    particle.style.background = 'radial-gradient(circle, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 70%)';
                    particle.style.width = Math.random() * 3 + 1 + 'px';
                    particle.style.height = particle.style.width;
                    break;
            }
            
            // Random position and animation
            particle.style.position = 'fixed';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.pointerEvents = 'none';
            particle.style.zIndex = '9999';
            particle.style.borderRadius = '50%';
            
            // Animate particle
            particle.style.animation = `floatParticle ${Math.random() * 3 + 2}s ease-out forwards`;
            
            container.appendChild(particle);
            
            // Remove particle after animation
            setTimeout(() => {
                particle.remove();
            }, 5000);
        }
    }

    function showThemeMenu() {
        const menu = document.getElementById('themeMenu');
        if (menu) {
            menu.classList.add('show');
            // Add slide animation
            menu.style.animation = 'slideDown 0.3s ease';
        }
    }

    function closeThemeMenu() {
        const menu = document.getElementById('themeMenu');
        if (menu) {
            menu.classList.remove('show');
        }
    }

    // Close theme menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.theme-selector')) {
            closeThemeMenu();
        }
    });

    // Handle system theme changes
    prefersDark.addEventListener('change', (e) => {
        if (currentTheme === 'system') {
            applyTheme('system');
        }
    });

    // Initialize theme UI when DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        // Theme selector dropdown
        const themeSelector = document.querySelector('.theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('click', (e) => {
                e.stopPropagation();
                showThemeMenu();
            });
        }

        // Theme menu items
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const theme = option.dataset.theme;
                if (theme && theme !== currentTheme) {
                    applyTheme(theme);
                }
                closeThemeMenu();
            });
            
            // Add hover effect
            option.addEventListener('mouseenter', () => {
                const icon = option.querySelector('.theme-option-icon');
                if (icon && !option.classList.contains('active')) {
                    icon.style.transform = 'scale(1.2)';
                    icon.style.transition = 'transform 0.2s ease';
                }
            });
            
            option.addEventListener('mouseleave', () => {
                const icon = option.querySelector('.theme-option-icon');
                if (icon && !option.classList.contains('active')) {
                    icon.style.transform = 'scale(1)';
                }
            });
        });

        // Initialize UI
        updateThemeUI(currentTheme);
        updateThemeIcon(currentTheme);
        
        document.body.classList.remove('theme-loading');
        document.body.classList.add('theme-loaded');
    });

    // Expose theme functions to window
    window.themeManager = {
        setTheme: applyTheme,
        getCurrentTheme: () => currentTheme,
        getAvailableThemes: () => [...availableThemes],
        getThemeConfig: () => themeConfig
    };
})();
