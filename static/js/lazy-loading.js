/**
 * Lazy Loading for Images
 * Uses IntersectionObserver to load images as they enter viewport
 */

(function() {
  'use strict';

  function initLazyLoading() {
    var lazyImages = document.querySelectorAll('img.lazy');

    if ('IntersectionObserver' in window) {
      var imageObserver = new IntersectionObserver(function(entries, observer) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            var img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            imageObserver.unobserve(img);
          }
        });
      }, {
        rootMargin: '200px'
      });

      lazyImages.forEach(function(img) {
        imageObserver.observe(img);
      });
    } else {
      // Fallback for older browsers
      lazyImages.forEach(function(img) {
        img.src = img.dataset.src;
      });
    }
  }

  // Auto-initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLazyLoading);
  } else {
    // DOM already loaded
    initLazyLoading();
  }

})();
