/**
 * Justified Gallery Layout
 * Creates rows of photos that fill container width while maintaining aspect ratios
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    targetRowHeight: 250,        // Target height for rows (will vary based on aspect ratios)
    targetRowHeightMobile: 150,  // Smaller target for mobile
    rowGap: 4,                   // Gap between photos (pixels)
    containerPadding: 0,         // Container padding
    debounceDelay: 250,          // Debounce window resize
    mobileBreakpoint: 768        // Switch to mobile mode below this width
  };

  class JustifiedGallery {
    constructor(container) {
      this.container = container;
      // Handle both direct .jg-item and .jg-item-wrapper > .jg-item
      this.items = Array.from(container.querySelectorAll('.jg-item, .jg-item-wrapper'));
      this.resizeTimeout = null;
      this.loadedCount = 0;
      this.totalPhotos = this.items.length;
      this.lastWidth = 0; // Track last container width to prevent unnecessary relayouts

      this.init();
    }

    init() {
      // Wait for images to load
      this.items.forEach((item, index) => {
        const img = item.querySelector('img');

        if (img.complete && img.naturalWidth > 0) {
          // Already loaded
          this.handleImageLoad(item, img);
        } else {
          // Wait for load
          img.addEventListener('load', () => this.handleImageLoad(item, img));
          img.addEventListener('error', () => this.handleImageError(item, img));
        }
      });

      // Handle window resize
      window.addEventListener('resize', () => this.handleResize());
    }

    handleImageLoad(item, img) {
      // Store aspect ratio as data attribute
      const aspectRatio = img.naturalWidth / img.naturalHeight;
      item.dataset.aspectRatio = aspectRatio;
      item.dataset.loaded = 'true';

      this.loadedCount++;

      // Layout when all images loaded, or do progressive layout
      if (this.loadedCount === this.totalPhotos) {
        this.layout();
      }
    }

    handleImageError(item, img) {
      // Use fallback aspect ratio for broken images
      item.dataset.aspectRatio = 1.5; // Default landscape
      item.dataset.loaded = 'true';
      this.loadedCount++;

      if (this.loadedCount === this.totalPhotos) {
        this.layout();
      }
    }

    layout() {
      const containerWidth = this.container.clientWidth;

      // Only relayout if width changed significantly (more than 10px)
      if (Math.abs(containerWidth - this.lastWidth) < 10) {
        return;
      }
      this.lastWidth = containerWidth;

      const isMobile = window.innerWidth < CONFIG.mobileBreakpoint;
      const targetHeight = isMobile ? CONFIG.targetRowHeightMobile : CONFIG.targetRowHeight;

      // Get only loaded photos with aspect ratios
      const loadedPhotos = this.items.filter(item => item.dataset.loaded === 'true');

      if (loadedPhotos.length === 0) return;

      // Group photos into rows
      const rows = this.calculateRows(loadedPhotos, containerWidth, targetHeight);

      // Apply layout
      this.applyLayout(rows);
    }

    calculateRows(photos, containerWidth, targetHeight) {
      const rows = [];
      let currentRow = [];
      let currentRowWidth = 0;

      photos.forEach((item, index) => {
        const aspectRatio = parseFloat(item.dataset.aspectRatio);
        const photoWidth = targetHeight * aspectRatio;

        // Look ahead: would adding this photo overflow too much?
        const potentialWidth = currentRowWidth + photoWidth + (currentRow.length > 0 ? CONFIG.rowGap : 0);
        const isLastPhoto = index === photos.length - 1;

        // Break row if:
        // 1. We have at least 2 photos AND adding this would be way over (130%+)
        // 2. This is the last photo
        const wayTooWide = potentialWidth > containerWidth * 1.3 && currentRow.length >= 2;

        if (wayTooWide && !isLastPhoto) {
          // Don't add this photo, finalize current row
          rows.push({
            photos: currentRow,
            originalWidth: currentRowWidth,
            isLastRow: false
          });

          // Start new row with this photo
          currentRow = [{
            item: item,
            aspectRatio: aspectRatio,
            width: photoWidth
          }];
          currentRowWidth = photoWidth;
        } else {
          // Add photo to current row
          currentRow.push({
            item: item,
            aspectRatio: aspectRatio,
            width: photoWidth
          });
          currentRowWidth = potentialWidth;
        }

        // Finalize row if this is the last photo
        if (isLastPhoto && currentRow.length > 0) {
          rows.push({
            photos: currentRow,
            originalWidth: currentRowWidth,
            isLastRow: true
          });
        }
      });

      return rows;
    }

    applyLayout(rows) {
      // Use clientWidth which is the inner width (excludes scrollbar but includes padding)
      const containerWidth = this.container.clientWidth;

      rows.forEach((row, rowIndex) => {
        const isLastRow = row.isLastRow;
        const numPhotos = row.photos.length;

        // Calculate total gap space for this row
        const totalGapWidth = (numPhotos - 1) * CONFIG.rowGap;
        const availableWidth = containerWidth - totalGapWidth;

        // Calculate row height that makes photos fill the row width exactly
        const totalAspectRatio = row.photos.reduce((sum, p) => sum + p.aspectRatio, 0);
        const rowHeight = availableWidth / totalAspectRatio;

        // Apply styles to each photo in the row
        let accumulatedWidth = 0;
        row.photos.forEach((photo, photoIndex) => {
          let photoWidth = rowHeight * photo.aspectRatio;

          // For the last photo in each row, adjust width to fill exactly (handles rounding errors)
          if (photoIndex === numPhotos - 1) {
            photoWidth = availableWidth - accumulatedWidth;
          } else {
            accumulatedWidth += photoWidth;
          }
          const item = photo.item;
          const img = item.querySelector('img');

          // Set item dimensions
          item.style.width = `${photoWidth}px`;
          item.style.height = `${rowHeight}px`;
          item.style.marginRight = photoIndex < numPhotos - 1 ? `${CONFIG.rowGap}px` : '0';
          item.style.marginBottom = `${CONFIG.rowGap}px`;
          item.style.display = 'inline-block';
          item.style.overflow = 'hidden';
          item.style.position = 'relative';

          // Set image styles
          img.style.width = '100%';
          img.style.height = '100%';
          img.style.objectFit = 'cover';
          img.style.display = 'block';
        });
      });
    }

    handleResize() {
      clearTimeout(this.resizeTimeout);
      this.resizeTimeout = setTimeout(() => {
        this.layout();
      }, CONFIG.debounceDelay);
    }
  }

  // Initialize galleries when DOM is ready
  function initGalleries() {
    const galleries = document.querySelectorAll('.justified-gallery');
    galleries.forEach(gallery => {
      new JustifiedGallery(gallery);
    });
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGalleries);
  } else {
    initGalleries();
  }
})();
