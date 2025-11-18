/**
 * CigarBox Editor Utilities
 * Shared functionality for authenticated editors
 */

(function() {
  'use strict';

  // Create global namespace
  window.CigarboxEditor = window.CigarboxEditor || {};

  /**
   * Load share count badge
   * @param {string} apiUrl - API endpoint to fetch share count (e.g., '/photos/123/shares')
   * @param {string} badgeId - ID of badge element to update
   * @param {string} adminUrl - URL to admin page when badge is clicked
   */
  function loadShareCount(apiUrl, badgeId, adminUrl) {
    fetch(apiUrl)
      .then(response => response.json())
      .then(data => {
        if (data.shares && data.shares.length > 0) {
          var badge = document.getElementById(badgeId);
          if (!badge) return;

          badge.textContent = data.shares.length;
          badge.style.display = 'inline';

          // Make badge clickable to go to admin shares page
          badge.style.cursor = 'pointer';
          badge.onclick = function(e) {
            e.stopPropagation(); // Don't trigger the modal
            window.location.href = adminUrl;
          };
        }
      })
      .catch(error => {
        console.error('Error loading share count:', error);
      });
  }

  /**
   * Setup Enter key to submit forms in modals
   * @param {string} selector - CSS selector for input elements (e.g., '#tagsModal input')
   */
  function setupModalEnterKey(selector) {
    var elements = document.querySelectorAll(selector);
    elements.forEach(function(el) {
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          el.closest('form').submit();
        }
      });
    });
  }

  /**
   * Setup auto-focus when modal opens
   * @param {string} modalId - ID of modal element (without #)
   * @param {string} inputSelector - CSS selector for input to focus
   */
  function setupModalFocus(modalId, inputSelector) {
    var modal = document.getElementById(modalId);
    if (!modal) return;

    // Bootstrap 5 modal events
    modal.addEventListener('shown.bs.modal', function() {
      var input = document.querySelector(inputSelector);
      if (input) {
        input.focus();
      }
    });
  }

  // Export public API
  window.CigarboxEditor.loadShareCount = loadShareCount;
  window.CigarboxEditor.setupModalEnterKey = setupModalEnterKey;
  window.CigarboxEditor.setupModalFocus = setupModalFocus;

})();
