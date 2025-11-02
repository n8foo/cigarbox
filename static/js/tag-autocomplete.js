/**
 * Tag Autocomplete Component with Pill UI
 *
 * Provides tag autocomplete functionality with visual pill badges:
 * - Tab to accept autocomplete suggestion
 * - Space or Comma to create pill badge
 * - Click X to remove pill
 * - Backspace to remove last pill
 * - Paste support (splits on comma/space)
 * - Automatic lowercase conversion
 *
 * Usage:
 *   initTagAutocomplete('#tags', ['vacation', 'beach', 'summer']);
 */

function initTagAutocomplete(inputSelector, allTags) {
  // Accept either a CSS selector string or a DOM element
  var originalInput = typeof inputSelector === 'string' ? document.querySelector(inputSelector) : inputSelector;
  if (!originalInput) return;

  // Array to store current tags
  var tags = [];

  // Parse initial value from input
  var initialValue = originalInput.value.trim();
  if (initialValue) {
    tags = initialValue.split(/[,\s]+/).filter(function(t) { return t.trim(); });
  }

  // Hide original input but keep it for form submission
  originalInput.style.display = 'none';

  // Create pill container with Bootstrap form-control class for automatic dark mode support
  var pillContainer = document.createElement('div');
  pillContainer.className = 'tag-pill-container form-control';
  pillContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 4px; min-height: 38px; cursor: text; align-items: center;';

  // Create inline input for typing
  var inlineInput = document.createElement('input');
  inlineInput.type = 'text';
  inlineInput.style.cssText = 'border: none; outline: none; flex: 1; min-width: 80px; font-size: 1rem; padding: 0; background: transparent; color: inherit;';
  inlineInput.placeholder = tags.length === 0 ? (originalInput.placeholder || 'Type tags...') : '';

  // Insert pill container after original input
  originalInput.parentNode.insertBefore(pillContainer, originalInput.nextSibling);

  // Create wrapper for dropdown positioning
  var wrapper = document.createElement('div');
  wrapper.style.cssText = 'position: relative; display: flex; flex: 1; min-width: 80px; align-items: center;';
  wrapper.appendChild(inlineInput);

  // Create suggestion dropdown
  var dropdown = document.createElement('div');
  dropdown.className = 'dropdown-menu';
  dropdown.style.cssText = 'position: absolute; top: 100%; left: 0; right: 0; max-height: 150px; overflow-y: auto; z-index: 1000; display: none; font-size: 12px; margin-top: 2px;';
  wrapper.appendChild(dropdown);

  var currentSuggestion = null;

  // Create pill badge element
  function createPill(tag) {
    var pill = document.createElement('span');
    pill.className = 'badge bg-secondary tag-pill';
    pill.style.cssText = 'display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; cursor: default; user-select: none;';
    pill.dataset.tag = tag;

    var tagText = document.createElement('span');
    tagText.textContent = tag;
    pill.appendChild(tagText);

    var removeBtn = document.createElement('span');
    removeBtn.innerHTML = '&times;';
    removeBtn.className = 'tag-pill-remove';
    removeBtn.style.cssText = 'cursor: pointer; font-weight: bold; margin-left: 2px; opacity: 0.7; font-size: 1.2em; line-height: 1;';
    removeBtn.onmouseover = function() { this.style.opacity = '1'; };
    removeBtn.onmouseout = function() { this.style.opacity = '0.7'; };
    removeBtn.onclick = function(e) {
      e.stopPropagation();
      removePill(tag);
    };
    pill.appendChild(removeBtn);

    return pill;
  }

  // Add a tag pill
  function addPill(tag) {
    tag = tag.toLowerCase().trim();
    if (!tag || tags.indexOf(tag) !== -1) return; // Skip empty or duplicates

    tags.push(tag);
    var pill = createPill(tag);
    pillContainer.insertBefore(pill, wrapper);
    syncToOriginal();
    inlineInput.placeholder = '';
  }

  // Remove a tag pill
  function removePill(tag) {
    var index = tags.indexOf(tag);
    if (index === -1) return;

    tags.splice(index, 1);

    // Remove pill element
    var pills = pillContainer.querySelectorAll('.tag-pill');
    for (var i = 0; i < pills.length; i++) {
      if (pills[i].dataset.tag === tag) {
        pillContainer.removeChild(pills[i]);
        break;
      }
    }

    syncToOriginal();
    if (tags.length === 0) {
      inlineInput.placeholder = originalInput.placeholder || 'Type tags...';
    }
    inlineInput.focus();
  }

  // Sync tags array back to original input
  function syncToOriginal() {
    originalInput.value = tags.join(' ');
    // Trigger change event for bulk editor change tracking
    var event = new Event('change', { bubbles: true });
    originalInput.dispatchEvent(event);
  }

  // Add inline input wrapper to container FIRST
  pillContainer.appendChild(wrapper);

  // Then initialize pills from existing tags (insertBefore needs wrapper to be in container)
  tags.forEach(function(tag) {
    var pill = createPill(tag);
    pillContainer.insertBefore(pill, wrapper);
  });

  // Update autocomplete suggestion
  function updateSuggestion() {
    var value = inlineInput.value.trim();

    if (value.length > 0) {
      // Find matching tags
      var matches = allTags.filter(function(tag) {
        return tag.toLowerCase().startsWith(value.toLowerCase()) && tags.indexOf(tag) === -1;
      });

      if (matches.length > 0) {
        currentSuggestion = matches[0];
        dropdown.innerHTML = '<div class="dropdown-item" style="padding: 4px 8px;"><strong>' +
                             value + '</strong>' +
                             matches[0].substring(value.length) +
                             ' <span class="text-muted">(tab to accept)</span></div>';
        dropdown.style.display = 'block';
      } else {
        currentSuggestion = null;
        dropdown.style.display = 'none';
      }
    } else {
      currentSuggestion = null;
      dropdown.style.display = 'none';
    }
  }

  // Accept current input as pill
  function acceptCurrentInput() {
    var value = inlineInput.value.trim();
    if (value) {
      addPill(value);
      inlineInput.value = '';
      currentSuggestion = null;
      dropdown.style.display = 'none';
    }
  }

  // Input event - lowercase and update suggestions
  inlineInput.addEventListener('input', function(e) {
    // Convert to lowercase
    var start = this.selectionStart;
    var end = this.selectionEnd;
    this.value = this.value.toLowerCase().replace(/,/g, ' ');
    this.setSelectionRange(start, end);

    updateSuggestion();
  });

  // Keydown event - handle Tab, Space, Comma, Backspace
  inlineInput.addEventListener('keydown', function(e) {
    // Tab ONLY accepts autocomplete suggestion (opt-in)
    if (e.key === 'Tab') {
      if (currentSuggestion) {
        e.preventDefault();
        addPill(currentSuggestion);
        inlineInput.value = '';
        currentSuggestion = null;
        dropdown.style.display = 'none';
      }
      // If no suggestion, let Tab do its default thing (focus next field)
    }
    // Space or Comma creates pill from what you typed (ignores suggestions)
    else if (e.key === ' ' || e.key === ',') {
      if (inlineInput.value.trim()) {
        e.preventDefault();
        acceptCurrentInput();
        inlineInput.value = '';
        currentSuggestion = null;
        dropdown.style.display = 'none';
      }
    }
    // Backspace removes last pill if input is empty
    else if (e.key === 'Backspace' && !inlineInput.value) {
      e.preventDefault();
      if (tags.length > 0) {
        removePill(tags[tags.length - 1]);
      }
    }
    // Enter accepts current input (don't prevent default - let form submit)
    else if (e.key === 'Enter') {
      if (inlineInput.value.trim()) {
        acceptCurrentInput();
      }
    }
  });

  // Paste event - split and create pills
  inlineInput.addEventListener('paste', function(e) {
    e.preventDefault();
    var pastedText = e.clipboardData.getData('text');
    var pastedTags = pastedText.split(/[,\s]+/).filter(function(t) { return t.trim(); });
    pastedTags.forEach(function(tag) {
      addPill(tag);
    });
    inlineInput.value = '';
    currentSuggestion = null;
    dropdown.style.display = 'none';
  });

  // Blur event - accept current input and hide dropdown
  inlineInput.addEventListener('blur', function() {
    // Accept current input if any
    if (inlineInput.value.trim()) {
      acceptCurrentInput();
    }

    // Hide dropdown after delay (allows clicking)
    setTimeout(function() {
      dropdown.style.display = 'none';
    }, 200);
  });

  // Click on container focuses inline input
  pillContainer.addEventListener('click', function() {
    inlineInput.focus();
  });

  // Focus styles - add focus class to trigger Bootstrap's form-control:focus styles
  inlineInput.addEventListener('focus', function() {
    pillContainer.classList.add('focus');
    pillContainer.style.borderColor = '#86b7fe';
    pillContainer.style.boxShadow = '0 0 0 0.25rem rgba(13, 110, 253, 0.25)';
  });

  inlineInput.addEventListener('blur', function() {
    setTimeout(function() {
      pillContainer.classList.remove('focus');
      pillContainer.style.borderColor = '';
      pillContainer.style.boxShadow = '';
    }, 200);
  });

  return {
    getTags: function() {
      return tags.slice(); // Return copy
    },
    addTag: function(tag) {
      addPill(tag);
    },
    removeTag: function(tag) {
      removePill(tag);
    },
    focus: function() {
      inlineInput.focus();
    },
    destroy: function() {
      if (pillContainer && pillContainer.parentNode) {
        pillContainer.parentNode.removeChild(pillContainer);
        originalInput.style.display = '';
      }
    }
  };
}
