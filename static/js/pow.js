/**
 * CigarBox Proof-of-Work (POW) Challenge Solver
 *
 * Unified module for solving POW challenges across the application.
 * Uses main thread SHA-256 hashing with periodic UI updates.
 * Supports both secure (crypto.subtle) and non-secure (fallback) contexts.
 */

(function() {
  'use strict';

  // Check if crypto.subtle is available (HTTPS or localhost only)
  const hasCryptoSubtle = typeof crypto !== 'undefined' &&
                          typeof crypto.subtle !== 'undefined';

  // Fallback SHA-256 implementation for non-secure contexts (HTTP)
  // Based on js-sha256 by Chen, Yi-Cyuan (MIT License)
  function sha256Fallback(message) {
    var K = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];

    function sha256_asm(message) {
      var h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
      var w = new Array(64);

      var blocks = [];
      var bytes = new TextEncoder().encode(message);
      var len = bytes.length;
      var bitLen = len * 8;

      // Padding
      var msgLen = len + 1 + 8;
      var blockCount = Math.ceil(msgLen / 64);
      var totalLen = blockCount * 64;
      var padding = new Uint8Array(totalLen);
      padding.set(bytes);
      padding[len] = 0x80;

      // Length in bits as big-endian 64-bit integer
      for (var i = 0; i < 8; i++) {
        padding[totalLen - 1 - i] = bitLen & 0xff;
        bitLen >>>= 8;
      }

      // Process blocks
      for (var i = 0; i < blockCount; i++) {
        var offset = i * 64;

        // Prepare message schedule
        for (var j = 0; j < 16; j++) {
          w[j] = (padding[offset + j * 4] << 24) | (padding[offset + j * 4 + 1] << 16) |
                 (padding[offset + j * 4 + 2] << 8) | padding[offset + j * 4 + 3];
        }

        for (var j = 16; j < 64; j++) {
          var s0 = ((w[j-15] >>> 7) | (w[j-15] << 25)) ^ ((w[j-15] >>> 18) | (w[j-15] << 14)) ^ (w[j-15] >>> 3);
          var s1 = ((w[j-2] >>> 17) | (w[j-2] << 15)) ^ ((w[j-2] >>> 19) | (w[j-2] << 13)) ^ (w[j-2] >>> 10);
          w[j] = (w[j-16] + s0 + w[j-7] + s1) >>> 0;
        }

        var a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];

        for (var j = 0; j < 64; j++) {
          var S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
          var ch = (e & f) ^ (~e & g);
          var temp1 = (hh + S1 + ch + K[j] + w[j]) >>> 0;
          var S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
          var maj = (a & b) ^ (a & c) ^ (b & c);
          var temp2 = (S0 + maj) >>> 0;

          hh = g;
          g = f;
          f = e;
          e = (d + temp1) >>> 0;
          d = c;
          c = b;
          b = a;
          a = (temp1 + temp2) >>> 0;
        }

        h[0] = (h[0] + a) >>> 0;
        h[1] = (h[1] + b) >>> 0;
        h[2] = (h[2] + c) >>> 0;
        h[3] = (h[3] + d) >>> 0;
        h[4] = (h[4] + e) >>> 0;
        h[5] = (h[5] + f) >>> 0;
        h[6] = (h[6] + g) >>> 0;
        h[7] = (h[7] + hh) >>> 0;
      }

      return h.map(n => n.toString(16).padStart(8, '0')).join('');
    }

    return sha256_asm(message);
  }

  // SHA-256 hash function - uses Web Crypto API or fallback
  async function sha256(message) {
    if (hasCryptoSubtle) {
      // Secure context - use Web Crypto API
      const msgBuffer = new TextEncoder().encode(message);
      const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } else {
      // Non-secure context (HTTP) - use fallback
      return sha256Fallback(message);
    }
  }

  // Validate return URL is relative (security)
  function validateReturnUrl(url) {
    if (!url || url === '') {
      return '/';
    }
    // Must be relative URL (starts with /)
    if (!url.startsWith('/')) {
      console.warn('[POW] Invalid return URL (not relative):', url);
      return '/';
    }
    // Reject protocol-relative URLs (//example.com)
    if (url.startsWith('//')) {
      console.warn('[POW] Invalid return URL (protocol-relative):', url);
      return '/';
    }
    return url;
  }

  // Main POW solver
  async function solvePowChallenge(options) {
    const baseUrl = window.CIGARBOX_SITEURL || '';
    const statusTextId = options.statusTextId || 'pow-status-text';
    const attemptsTextId = options.attemptsTextId || 'pow-hash-attempts';
    const returnUrl = validateReturnUrl(options.returnUrl || window.location.href);

    const statusText = document.getElementById(statusTextId);
    const attemptsText = document.getElementById(attemptsTextId);

    if (!statusText) {
      console.error('[POW] Status element not found:', statusTextId);
      return;
    }

    try {
      // Step 1: Fetch challenge from server
      statusText.textContent = 'Fetching challenge...';
      if (attemptsText) attemptsText.textContent = '';

      const response = await fetch(baseUrl + '/pow/challenge');
      if (!response.ok) {
        throw new Error('Failed to fetch challenge');
      }
      const data = await response.json();

      console.log('[POW] Challenge received:', data.challenge.substring(0, 8) + '... difficulty=' + data.difficulty);

      // Step 2: Solve POW puzzle
      statusText.textContent = 'Solving puzzle...';
      let nonce = 0;
      let hash;
      let attempts = 0;
      const startTime = Date.now();

      while (true) {
        const input = data.challenge + nonce;
        hash = await sha256(input);
        attempts++;

        // Update UI every 1000 attempts
        if (attempts % 1000 === 0) {
          const elapsed = (Date.now() - startTime) / 1000;
          if (attemptsText) {
            attemptsText.textContent = attempts + ' attempts (' + elapsed.toFixed(1) + 's)';
          }
          // Allow UI update (prevent browser freeze)
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        // Check if solution found
        if (hash.startsWith('0'.repeat(data.difficulty))) {
          console.log('[POW] Solution found! nonce=' + nonce + ' attempts=' + attempts);
          break;
        }
        nonce++;
      }

      // Step 3: Submit solution to server
      statusText.textContent = 'Verifying solution...';
      const submitResponse = await fetch(baseUrl + '/pow/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          challenge: data.challenge,
          nonce: nonce,
          return_url: returnUrl
        })
      });

      if (!submitResponse.ok) {
        const error = await submitResponse.json();
        throw new Error(error.error || 'Verification failed');
      }

      const result = await submitResponse.json();
      if (result.success) {
        statusText.textContent = 'Verified! ✓';
        if (attemptsText) {
          const elapsed = (Date.now() - startTime) / 1000;
          attemptsText.textContent = attempts + ' attempts (' + elapsed.toFixed(1) + 's) - Success!';
        }

        // Redirect to original page
        console.log('[POW] Redirecting to:', returnUrl);
        setTimeout(() => {
          window.location.href = returnUrl;
        }, 500);
      } else {
        throw new Error('Invalid solution');
      }

    } catch (error) {
      console.error('[POW] Error:', error);
      statusText.textContent = 'Verification failed: ' + error.message;
      statusText.style.color = 'var(--bs-danger)';

      // Offer retry
      setTimeout(() => {
        if (confirm('Verification failed. Retry?')) {
          window.location.reload();
        }
      }, 2000);
    }
  }

  // Export to global namespace
  window.CigarboxPOW = {
    solve: solvePowChallenge
  };

})();
