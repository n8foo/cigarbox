/**
 * CigarBox Utilities
 * Universal JavaScript functions used across the application
 */

(function() {
  'use strict';

  // Create global namespace
  window.Cigarbox = window.Cigarbox || {};

  // ============================================================================
  // DARK MODE TOGGLE
  // ============================================================================

  function initDarkMode() {
    const html = document.documentElement;
    const toggle = document.getElementById('darkModeToggle');
    const icon = document.getElementById('darkModeIcon');

    if (!toggle || !icon) {
      // Dark mode toggle not present on this page
      return;
    }

    // Get stored preference or detect from OS
    function getThemePreference() {
      const stored = localStorage.getItem('theme');
      if (stored) return stored;

      // No override stored - use OS preference
      return getOSPreference();
    }

    // Get OS preference
    function getOSPreference() {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
      return 'light';
    }

    // Apply theme
    function setTheme(theme) {
      if (theme === 'dark') {
        html.setAttribute('data-bs-theme', 'dark');
        icon.className = 'bi bi-sun-fill';
      } else {
        html.setAttribute('data-bs-theme', 'light');
        icon.className = 'bi bi-moon-fill';
      }

      // Smart storage: only save if overriding OS preference
      const osPreference = getOSPreference();
      if (theme === osPreference) {
        // Theme matches OS - remove override, go back to auto
        localStorage.removeItem('theme');
      } else {
        // Theme differs from OS - save override
        localStorage.setItem('theme', theme);
      }
    }

    // Toggle theme
    function toggleTheme() {
      const currentTheme = html.getAttribute('data-bs-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    }

    // Initialize
    setTheme(getThemePreference());

    // Add click handler
    toggle.addEventListener('click', toggleTheme);

    // Listen for OS theme changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        const newOSTheme = e.matches ? 'dark' : 'light';
        // Auto-switch if no override is stored (localStorage is empty)
        if (!localStorage.getItem('theme')) {
          setTheme(newOSTheme);
        }
      });
    }
  }

  // ============================================================================
  // COPY TO CLIPBOARD
  // ============================================================================

  /**
   * Copy text to clipboard with visual feedback
   * @param {string} text - Text to copy
   * @param {HTMLElement} buttonElement - Button that triggered the copy (optional, for visual feedback)
   */
  function copyToClipboard(text, buttonElement) {
    // Modern Clipboard API with fallback
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => showCopyFeedback(buttonElement))
        .catch(err => {
          console.error('Clipboard write failed:', err);
          fallbackCopy(text, buttonElement);
        });
    } else {
      fallbackCopy(text, buttonElement);
    }
  }

  /**
   * Fallback clipboard copy for older browsers
   */
  function fallbackCopy(text, buttonElement) {
    // Create temporary textarea
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999); // For mobile

    try {
      document.execCommand('copy');
      showCopyFeedback(buttonElement);
    } catch (err) {
      console.error('Copy failed:', err);
      alert('Failed to copy. Please copy manually: ' + text);
    } finally {
      document.body.removeChild(textarea);
    }
  }

  /**
   * Show visual feedback on button
   */
  function showCopyFeedback(buttonElement) {
    if (!buttonElement) return;

    const originalHTML = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="bi bi-check"></i> Copied!';

    setTimeout(() => {
      buttonElement.innerHTML = originalHTML;
    }, 2000);
  }

  /**
   * Copy from input element (helper for share modals)
   * Call from onclick: onclick="Cigarbox.copyShareLink()"
   */
  function copyShareLink() {
    const input = document.getElementById('shareUrlInput');
    if (!input) {
      console.error('shareUrlInput element not found');
      return;
    }

    const button = event.target.closest('button');
    copyToClipboard(input.value, button);
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  // Auto-initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDarkMode);
  } else {
    // DOM already loaded
    initDarkMode();
  }

  // Export public API
  window.Cigarbox.copyToClipboard = copyToClipboard;
  window.Cigarbox.copyShareLink = copyShareLink;

})();
