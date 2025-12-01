// Internationalization (i18n) JavaScript Helper
class I18nHelper {
    constructor() {
        this.currentLanguage = this.getCurrentLanguage();
        this.translations = {};
        this.loadedLanguages = new Set();
        this.init();
    }

    init() {
        this.loadTranslations(this.currentLanguage);
        this.setupLanguageDetection();
        this.setupDynamicTranslation();
    }

    getCurrentLanguage() {
        // Try to get language from various sources
        const sources = [
            localStorage.getItem('language'),
            document.documentElement.getAttribute('lang'),
            navigator.language.split('-')[0],
            'en' // fallback
        ];
        
        return sources.find(lang => lang && lang.length === 2) || 'en';
    }

    async loadTranslations(language) {
        if (this.loadedLanguages.has(language)) {
            return;
        }

        try {
            const response = await fetch(`/i18n/js_translations?language=${language}`);
            if (response.ok) {
                const translations = await response.json();
                this.translations[language] = translations;
                this.loadedLanguages.add(language);
            }
        } catch (error) {
            console.error('Failed to load translations:', error);
        }
    }

    translate(key, variables = {}) {
        const translation = this.getTranslation(key, this.currentLanguage);
        return this.interpolate(translation, variables);
    }

    getTranslation(key, language) {
        const keys = key.split('.');
        let translation = this.translations[language];
        
        for (const k of keys) {
            if (translation && typeof translation === 'object') {
                translation = translation[k];
            } else {
                return key; // Return key if translation not found
            }
        }
        
        return translation || key;
    }

    interpolate(text, variables) {
        if (typeof text !== 'string') {
            return text;
        }

        return text.replace(/\{(\w+)\}/g, (match, variable) => {
            return variables[variable] !== undefined ? variables[variable] : match;
        });
    }

    async setLanguage(language) {
        if (language === this.currentLanguage) {
            return;
        }

        try {
            const response = await fetch('/i18n/set_language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    language_code: language
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.currentLanguage = language;
                localStorage.setItem('language', language);
                document.documentElement.setAttribute('lang', language);
                
                // Load new translations
                await this.loadTranslations(language);
                
                // Update all translated elements
                this.updateAllTranslations();
                
                // Update language switcher
                this.updateLanguageSwitcher(language);
                
                // Trigger language change event
                document.dispatchEvent(new CustomEvent('languageChanged', {
                    detail: { language: language }
                }));
                
                return true;
            } else {
                console.error('Failed to set language:', result.error);
                return false;
            }
        } catch (error) {
            console.error('Error setting language:', error);
            return false;
        }
    }

    setupLanguageDetection() {
        // Auto-detect language from browser
        const browserLang = navigator.language.split('-')[0];
        if (browserLang !== this.currentLanguage && this.isLanguageSupported(browserLang)) {
            this.setLanguage(browserLang);
        }
    }

    setupDynamicTranslation() {
        // Set up mutation observer for dynamic content
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.translateElement(node);
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial translation of all elements
        this.updateAllTranslations();
    }

    translateElement(element) {
        const elementsToTranslate = element.querySelectorAll('[data-i18n]');
        
        elementsToTranslate.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const variables = el.getAttribute('data-i18n-variables');
            
            let vars = {};
            if (variables) {
                try {
                    vars = JSON.parse(variables);
                } catch (e) {
                    console.error('Invalid i18n variables:', variables);
                }
            }
            
            const translation = this.translate(key, vars);
            
            // Handle different element types
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                if (el.type === 'submit' || el.type === 'button') {
                    el.value = translation;
                } else {
                    el.placeholder = translation;
                }
            } else {
                el.textContent = translation;
            }
        });
    }

    updateAllTranslations() {
        this.translateElement(document);
    }

    updateLanguageSwitcher(language) {
        const switcher = document.querySelector('.language-switcher');
        if (switcher) {
            // Update switcher display
            const flag = switcher.querySelector('.flag');
            const name = switcher.querySelector('.language-name');
            
            if (flag && name) {
                // Reload switcher component or update manually
                this.reloadLanguageSwitcher();
            }
        }
    }

    async reloadLanguageSwitcher() {
        try {
            const response = await fetch('/i18n/language_switcher');
            if (response.ok) {
                const html = await response.text();
                const switcherContainer = document.querySelector('.language-switcher-container');
                if (switcherContainer) {
                    switcherContainer.innerHTML = html;
                }
            }
        } catch (error) {
            console.error('Failed to reload language switcher:', error);
        }
    }

    formatNumber(number, format = 'decimal') {
        try {
            const locale = this.getLocaleCode();
            
            switch (format) {
                case 'decimal':
                    return new Intl.NumberFormat(locale).format(number);
                case 'currency':
                    return new Intl.NumberFormat(locale, {
                        style: 'currency',
                        currency: 'USD'
                    }).format(number);
                case 'percent':
                    return new Intl.NumberFormat(locale, {
                        style: 'percent'
                    }).format(number);
                default:
                    return new Intl.NumberFormat(locale).format(number);
            }
        } catch (error) {
            console.error('Error formatting number:', error);
            return number.toString();
        }
    }

    formatDate(date, format = 'medium') {
        try {
            const locale = this.getLocaleCode();
            const dateObj = new Date(date);
            
            const options = {
                short: { dateStyle: 'short' },
                medium: { dateStyle: 'medium' },
                long: { dateStyle: 'long' },
                full: { dateStyle: 'full' }
            };
            
            return new Intl.DateTimeFormat(locale, options[format] || options.medium).format(dateObj);
        } catch (error) {
            console.error('Error formatting date:', error);
            return date.toString();
        }
    }

    formatTime(date, format = '24h') {
        try {
            const locale = this.getLocaleCode();
            const dateObj = new Date(date);
            
            const options = {
                '12h': { hour: '2-digit', minute: '2-digit', hour12: true },
                '24h': { hour: '2-digit', minute: '2-digit', hour12: false }
            };
            
            return new Intl.DateTimeFormat(locale, options[format] || options['24h']).format(dateObj);
        } catch (error) {
            console.error('Error formatting time:', error);
            return date.toString();
        }
    }

    formatRelativeTime(date) {
        try {
            const locale = this.getLocaleCode();
            const dateObj = new Date(date);
            const now = new Date();
            const diffInSeconds = Math.floor((now - dateObj) / 1000);
            
            const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
            
            if (diffInSeconds < 60) {
                return rtf.format(-diffInSeconds, 'second');
            } else if (diffInSeconds < 3600) {
                return rtf.format(-Math.floor(diffInSeconds / 60), 'minute');
            } else if (diffInSeconds < 86400) {
                return rtf.format(-Math.floor(diffInSeconds / 3600), 'hour');
            } else {
                return rtf.format(-Math.floor(diffInSeconds / 86400), 'day');
            }
        } catch (error) {
            console.error('Error formatting relative time:', error);
            return date.toString();
        }
    }

    getLocaleCode() {
        const localeMap = {
            'en': 'en-US',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'de': 'de-DE',
            'it': 'it-IT',
            'pt': 'pt-BR',
            'ru': 'ru-RU',
            'ja': 'ja-JP',
            'zh': 'zh-CN',
            'ko': 'ko-KR',
            'ar': 'ar-SA'
        };
        
        return localeMap[this.currentLanguage] || 'en-US';
    }

    isLanguageSupported(language) {
        // This should be synchronized with backend supported languages
        const supportedLanguages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', 'ko', 'ar'];
        return supportedLanguages.includes(language);
    }

    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    // Utility method to translate template strings
    t(key, variables = {}) {
        return this.translate(key, variables);
    }

    // Method to add translations dynamically
    addTranslations(language, translations) {
        if (!this.translations[language]) {
            this.translations[language] = {};
        }
        
        Object.assign(this.translations[language], translations);
        this.loadedLanguages.add(language);
    }
}

// Initialize i18n helper
window.i18n = new I18nHelper();

// Global translation function for convenience
window.t = function(key, variables) {
    return window.i18n.translate(key, variables);
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = I18nHelper;
}
