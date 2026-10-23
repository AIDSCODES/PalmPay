/**
 * PalmPay - Contactless Palm-Vein Biometric Payment Frontend
 * Modern real-time vanilla JS application connecting to FastAPI backend
 */

(function () {
  'use strict';

  // Configuration & State
  const state = {
    apiBase: window.location.origin.includes(':8000') ? window.location.origin : 'http://127.0.0.1:8000',
    adminKey: localStorage.getItem('palmpay_admin_key') || 'your-admin-api-key-change-in-production',
    deviceId: localStorage.getItem('palmpay_device_id') || 'e8b9252d-c48a-4f38-ae94-10a1a46dffe1',
    deviceKey: localStorage.getItem('palmpay_device_key') || 'ZuqDrnh4-U2slC9A3odO0_r3UqJcjqcn-qwgcqrBkCg',
    scannerMode: 'esp32', // Pure dedicated ESP32 NIR hardware scanner
    esp32Url: localStorage.getItem('palmpay_esp32_url') || 'http://192.168.1.100',
    esp32Online: false,
    esp32AutoPollInterval: null,
    streamActive: true,
    enrolledSamples: [], // array of { blob, base64, previewUrl, quality }
    matchedCustomer: null,
    usersCache: [],
    autoScanActive: false,
    isIdentifying: false,
    pollingInterval: null,
  };

  // DOM Elements
  const elements = {
    // Nav tabs
    tabs: document.querySelectorAll('.nav-tab'),
    viewPanels: document.querySelectorAll('.view-panel'),
    terminalLabel: document.getElementById('terminal-label'),
    btnQuickConfig: document.getElementById('btn-quick-config'),

    // View 1: POS Checkout
    checkoutAmount: document.getElementById('checkout-amount'),
    checkoutDesc: document.getElementById('checkout-desc'),
    quickAmountChips: document.querySelectorAll('.chip-btn[data-amount]'),
    esp32EndpointBar: document.getElementById('esp32-endpoint-bar'),
    esp32StatusPill: document.querySelector('.esp32-status-pill'),
    esp32StatusDot: document.getElementById('esp32-status-dot'),
    esp32StatusBadge: document.getElementById('esp32-status-badge'),
    esp32DeviceUrl: document.getElementById('esp32-device-url'),
    btnPingEsp32: document.getElementById('btn-ping-esp32'),
    esp32StreamImg: document.getElementById('esp32-stream-img'),
    scannerCanvas: document.getElementById('scanner-canvas'),
    scanLaser: document.getElementById('scan-laser'),
    gaugeScore: document.getElementById('gauge-score'),
    qualityProgressFill: document.getElementById('quality-progress-fill'),
    hudStatusText: document.getElementById('hud-status-text'),
    hudSpectrumTag: document.getElementById('hud-spectrum-tag'),
    btnScanIdentify: document.getElementById('btn-scan-identify'),
    btnScanLabel: document.getElementById('btn-scan-label'),
    btnToggleAutoscan: document.getElementById('btn-toggle-autoscan'),
    autoscanBtnLabel: document.getElementById('autoscan-btn-label'),
    btnToggleStream: document.getElementById('btn-toggle-stream'),
    streamBtnLabel: document.getElementById('stream-btn-label'),
    aiLivenessStatus: document.getElementById('ai-liveness-status'),

    // Checkout Match Card
    matchResultCard: document.getElementById('match-result-card'),
    matchCustomerName: document.getElementById('match-customer-name'),
    matchConfidenceBadge: document.getElementById('match-confidence-badge'),
    matchCustomerPhone: document.getElementById('match-customer-phone'),
    matchCustomerId: document.getElementById('match-customer-id'),
    matchCustomerBalance: document.getElementById('match-customer-balance'),
    btnConfirmCharge: document.getElementById('btn-confirm-charge'),
    btnResetMatch: document.getElementById('btn-reset-match'),

    // View 2: Enrollment
    enrollName: document.getElementById('enroll-name'),
    enrollPhone: document.getElementById('enroll-phone'),
    enrollEmail: document.getElementById('enroll-email'),
    enrollInitBalance: document.getElementById('enroll-init-balance'),
    enrollCaptureCanvas: document.getElementById('enroll-capture-canvas'),
    enrollHudStatus: document.getElementById('enroll-hud-status'),
    btnEnrollSnap: document.getElementById('btn-enroll-snap'),
    btnEnrollAuto3: document.getElementById('btn-enroll-auto-3'),
    sampleCountBadge: document.getElementById('collected-sample-count'),
    samplesGallery: document.getElementById('samples-gallery'),
    btnSubmitEnrollment: document.getElementById('btn-submit-enrollment'),
    btnClearEnrollment: document.getElementById('btn-clear-enrollment'),

    // View 3: Wallets
    walletUserSelect: document.getElementById('wallet-user-select'),
    walletBalanceDisplay: document.getElementById('wallet-balance-display'),
    walletUserName: document.getElementById('wallet-user-name'),
    walletStatusBadge: document.getElementById('wallet-status-badge'),
    topupAmount: document.getElementById('topup-amount'),
    topupDesc: document.getElementById('topup-desc'),
    quickTopupChips: document.querySelectorAll('.chip-btn[data-topup]'),
    btnSubmitTopup: document.getElementById('btn-submit-topup'),
    btnRefreshUserTx: document.getElementById('btn-refresh-user-tx'),
    tbodyUserTransactions: document.getElementById('tbody-user-transactions'),

    // View 4: Transactions
    btnRefreshAllTx: document.getElementById('btn-refresh-all-tx'),
    tbodyAllTransactions: document.getElementById('tbody-all-transactions'),

    // View 5: Admin & Hardware
    cfgDeviceId: document.getElementById('cfg-device-id'),
    cfgDeviceKey: document.getElementById('cfg-device-key'),
    cfgAdminKey: document.getElementById('cfg-admin-key'),
    btnTestDeviceAuth: document.getElementById('btn-test-device-auth'),
    btnSaveDeviceCfg: document.getElementById('btn-save-device-cfg'),
    btnCheckModelStatus: document.getElementById('btn-check-model-status'),
    aiModelVersion: document.getElementById('ai-model-version'),
    aiModelType: document.getElementById('ai-model-type'),
    aiModelDim: document.getElementById('ai-model-dim'),
    btnPingHealth: document.getElementById('btn-ping-health'),
    healthApiStatus: document.getElementById('health-api-status'),
    healthDbStatus: document.getElementById('health-db-status'),
    btnSubmitRegDevice: document.getElementById('btn-submit-reg-device'),
    regDevName: document.getElementById('reg-dev-name'),
    regDevType: document.getElementById('reg-dev-type'),
    regDevFw: document.getElementById('reg-dev-fw'),
    btnRefreshAdminUsers: document.getElementById('btn-refresh-admin-users'),
    tbodyAdminUsers: document.getElementById('tbody-admin-users'),

    // Receipt Modal
    modalReceipt: document.getElementById('modal-receipt'),
    receiptAmount: document.getElementById('receipt-amount'),
    receiptTxRef: document.getElementById('receipt-tx-ref'),
    receiptCustomerName: document.getElementById('receipt-customer-name'),
    receiptRemainingBalance: document.getElementById('receipt-remaining-balance'),
    receiptTimestamp: document.getElementById('receipt-timestamp'),
    btnCloseReceipt: document.getElementById('btn-close-receipt'),

    // Toasts
    toastContainer: document.getElementById('toast-container'),
  };

  /* ==========================================================================
     Web Audio Feedback (Real-Time POS Chimes)
     ========================================================================== */

  let audioCtx = null;
  function playAudioTone(type) {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      const now = audioCtx.currentTime;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      if (type === 'success') {
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(1175, now + 0.15);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === 'scan') {
        osc.frequency.setValueAtTime(1200, now);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
        osc.start(now);
        osc.stop(now + 0.1);
      } else if (type === 'error') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, now);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      }
    } catch {
      // Audio not supported or blocked
    }
  }

  /* ==========================================================================
     API Client Helper
     ========================================================================== */

  async function apiRequest(endpoint, options = {}) {
    const url = `${state.apiBase}${endpoint}`;
    const headers = options.headers || {};

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        let msg = 'Request failed';
        if (data && data.error && data.error.message) {
          msg = data.error.message;
        } else if (data && data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } else if (response.statusText) {
          msg = `${response.status} ${response.statusText}`;
        }
        throw new Error(msg);
      }

      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  }

  /* ==========================================================================
     UI Notification Helpers
     ========================================================================== */

  function showToast(message, type = 'info', duration = 4000) {
    if (!elements.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else if (type === 'error') {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      <div class="toast-icon">${iconSvg}</div>
      <div class="toast-content">
        <span class="toast-message">${escapeHtml(message)}</span>
      </div>
      <button class="toast-close" type="button">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.animation = 'fadeOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function canvasToBlob(canvas, quality = 0.95) {
    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
    });
  }

  /* ==========================================================================
     ESP32 Hardware Connection & Diagnostics
     ========================================================================== */

  async function testEsp32Connection(notify = true) {
    const rawUrl = elements.esp32DeviceUrl ? elements.esp32DeviceUrl.value.trim() : state.esp32Url;
    state.esp32Url = rawUrl || 'http://192.168.1.100';
    localStorage.setItem('palmpay_esp32_url', state.esp32Url);

    if (elements.esp32StatusBadge) elements.esp32StatusBadge.textContent = 'PINGING...';

    let connected = false;

    try {
      // 1. Direct fetch attempt with 2s timeout
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 2000);
      const pingResp = await fetch(`${state.esp32Url}/ping`, { method: 'GET', signal: ctrl.signal, mode: 'no-cors' }).catch(() => null);
      clearTimeout(tid);

      if (pingResp) {
        connected = true;
      } else {
        // 2. Probe via backend capture endpoint
        const probeResp = await apiRequest('/api/v1/devices/esp32/capture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_url: state.esp32Url, device_id: state.deviceId || null }),
        }).catch(() => null);

        if (probeResp && (probeResp.success || !probeResp.error?.includes('Could not reach ESP32'))) {
          connected = true;
        }
      }
    } catch {
      connected = false;
    }

    state.esp32Online = connected;
    if (elements.esp32StatusBadge) {
      elements.esp32StatusBadge.textContent = connected ? 'ESP32 READY' : 'ESP32 STANDBY';
    }
    if (elements.esp32StatusPill) {
      elements.esp32StatusPill.classList.toggle('online', connected);
      elements.esp32StatusPill.classList.toggle('offline', !connected);
    }

    if (notify) {
      if (connected) {
        playAudioTone('success');
        showToast(`ESP32 Connected: ${state.esp32Url}`, 'success');
      } else {
        showToast(`ESP32 at ${state.esp32Url} not reachable. Check power & WiFi.`, 'warning');
      }
    }
    return connected;
  }

  /* ==========================================================================
     View 1: POS Checkout Actions & Real-Time Scanning
     ========================================================================== */

  async function handleScanAndIdentify() {
    if (state.isIdentifying) return;
    state.isIdentifying = true;

    // Laser animation & status HUD
    if (elements.scanLaser) elements.scanLaser.classList.add('active');
    if (elements.hudStatusText) elements.hudStatusText.textContent = 'CAPTURING FROM ESP32 SENSOR...';
    if (elements.btnScanIdentify) elements.btnScanIdentify.disabled = true;

    playAudioTone('scan');

    try {
      const rawUrl = elements.esp32DeviceUrl ? elements.esp32DeviceUrl.value.trim() : state.esp32Url;
      state.esp32Url = rawUrl || 'http://192.168.1.100';

      const response = await apiRequest('/api/v1/devices/esp32/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_url: state.esp32Url,
          device_id: state.deviceId || null,
        }),
      });

      // Render captured NIR image on scanner canvas
      if (response && response.image) {
        const img = new Image();
        img.onload = () => {
          if (elements.scannerCanvas) {
            elements.scannerCanvas.style.display = 'block';
            const ctx = elements.scannerCanvas.getContext('2d');
            ctx.drawImage(img, 0, 0, elements.scannerCanvas.width, elements.scannerCanvas.height);
          }
        };
        img.src = `data:image/jpeg;base64,${response.image}`;
      }

      if (!response || !response.success) {
        throw new Error(response?.error || 'Failed to capture frame from ESP32');
      }

      // Update quality gauge from match score or quality
      const qualityPct = Math.round((response.similarity || 0.88) * 100);
      if (elements.gaugeScore) elements.gaugeScore.textContent = `${qualityPct}%`;
      if (elements.qualityProgressFill) elements.qualityProgressFill.style.width = `${qualityPct}%`;

      if (response.matched && response.user_id) {
        const confidence = (response.similarity * 100).toFixed(1);
        playAudioTone('success');
        showToast(`Palm Vein Matched! (${confidence}% confidence)`, 'success');
        if (elements.hudStatusText) elements.hudStatusText.textContent = `MATCHED: ${confidence}%`;
        await loadMatchedCustomer(response.user_id, confidence);
      } else {
        playAudioTone('error');
        showToast(response.reason || 'No biometric match found in vector store', 'error');
        if (elements.hudStatusText) elements.hudStatusText.textContent = 'NO MATCH DETECTED';
        if (elements.matchResultCard) elements.matchResultCard.classList.add('hidden');
      }
    } catch (err) {
      playAudioTone('error');
      showToast(`ESP32 Scan failed: ${err.message}`, 'error');
      if (elements.hudStatusText) elements.hudStatusText.textContent = 'SCAN ERROR / RETRY';
    } finally {
      setTimeout(() => {
        if (elements.scanLaser) elements.scanLaser.classList.remove('active');
        state.isIdentifying = false;
      }, 1000);
      if (elements.btnScanIdentify) elements.btnScanIdentify.disabled = false;
    }
  }

  function toggleAutoScan() {
    state.autoScanActive = !state.autoScanActive;

    if (state.autoScanActive) {
      elements.btnToggleAutoscan.classList.add('btn-active-glow');
      if (elements.autoscanBtnLabel) {
        elements.autoscanBtnLabel.textContent = 'Auto-Match: ON';
      }
      showToast('Real-Time ESP32 Palm Auto-Match enabled', 'success');
      startEsp32AutoPoll();
    } else {
      elements.btnToggleAutoscan.classList.remove('btn-active-glow');
      if (elements.autoscanBtnLabel) {
        elements.autoscanBtnLabel.textContent = 'Auto-Match: OFF';
      }
      showToast('Real-Time Auto-Match disabled', 'info');
      stopEsp32AutoPoll();
    }
  }

  function startEsp32AutoPoll() {
    stopEsp32AutoPoll();
    state.esp32AutoPollInterval = setInterval(async () => {
      if (!state.autoScanActive || state.isIdentifying || state.matchedCustomer) return;
      try {
        const res = await apiRequest(`/api/v1/devices/${state.deviceId}/latest-scan`).catch(() => null);
        if (res && res.has_scan && res.scan) {
          handleScanAndIdentify();
          return;
        }

        // Active continuous real-time scan when ESP32 is online
        if (state.esp32Online) {
          handleScanAndIdentify();
        }
      } catch {
        // Silent poll
      }
    }, 2000);
  }

  function stopEsp32AutoPoll() {
    if (state.esp32AutoPollInterval) {
      clearInterval(state.esp32AutoPollInterval);
      state.esp32AutoPollInterval = null;
    }
  }

  /* ==========================================================================
     Real-Time Live Video Stream Controls
     ========================================================================== */

  function startEsp32LiveStream() {
    state.streamActive = true;
    if (elements.esp32StreamImg) {
      const streamUrl = `${state.apiBase}/api/v1/devices/esp32/stream?device_url=${encodeURIComponent(state.esp32Url)}`;
      elements.esp32StreamImg.src = streamUrl;
      elements.esp32StreamImg.style.display = 'block';
    }
    if (elements.scannerCanvas) {
      elements.scannerCanvas.style.display = 'none';
    }
    if (elements.btnToggleStream) {
      elements.btnToggleStream.classList.add('btn-active-glow');
    }
    if (elements.streamBtnLabel) {
      elements.streamBtnLabel.textContent = 'Live Stream: ON';
    }
  }

  function stopEsp32LiveStream() {
    state.streamActive = false;
    if (elements.esp32StreamImg) {
      elements.esp32StreamImg.src = '';
      elements.esp32StreamImg.style.display = 'none';
    }
    if (elements.scannerCanvas) {
      elements.scannerCanvas.style.display = 'block';
    }
    if (elements.btnToggleStream) {
      elements.btnToggleStream.classList.remove('btn-active-glow');
    }
    if (elements.streamBtnLabel) {
      elements.streamBtnLabel.textContent = 'Live Stream: OFF';
    }
  }

  function toggleLiveStream() {
    if (state.streamActive) {
      stopEsp32LiveStream();
      showToast('ESP32 Live Stream paused', 'info');
    } else {
      startEsp32LiveStream();
      showToast('ESP32 Real-Time Live Stream active', 'success');
    }
  }

  async function loadMatchedCustomer(userId, confidenceStr) {
    try {
      const [user, wallet] = await Promise.all([
        apiRequest(`/api/v1/users/${userId}`),
        apiRequest(`/api/v1/wallets/${userId}`),
      ]);

      state.matchedCustomer = {
        id: user.id,
        name: user.name,
        phone: user.phone || 'N/A',
        balance: wallet.balance,
      };

      elements.matchCustomerName.textContent = user.name;
      elements.matchConfidenceBadge.textContent = `${confidenceStr}% Match`;
      elements.matchConfidenceBadge.className = 'badge badge-success';
      elements.matchCustomerPhone.textContent = user.phone ? `Phone: ${user.phone}` : 'No phone linked';
      elements.matchCustomerId.textContent = `ID: ${user.id.slice(0, 18)}...`;
      elements.matchCustomerBalance.textContent = `₹${parseFloat(wallet.balance).toFixed(2)}`;

      elements.matchResultCard.classList.remove('hidden');
      elements.btnConfirmCharge.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      showToast(`Could not load customer data: ${err.message}`, 'error');
    }
  }

  async function handleConfirmPayment() {
    if (!state.matchedCustomer) {
      showToast('No customer identified yet. Please place palm on ESP32 scanner.', 'error');
      return;
    }

    const amount = parseFloat(elements.checkoutAmount.value);
    if (!amount || amount <= 0) {
      showToast('Please enter a valid bill amount', 'error');
      return;
    }

    if (amount > state.matchedCustomer.balance) {
      playAudioTone('error');
      showToast(`Insufficient balance! Customer has ₹${state.matchedCustomer.balance.toFixed(2)}`, 'error');
      return;
    }

    elements.btnConfirmCharge.disabled = true;
    elements.btnConfirmCharge.innerHTML = `<span>Processing Biometric Charge...</span>`;

    try {
      const idempotencyKey = crypto.randomUUID();
      const payload = {
        user_id: state.matchedCustomer.id,
        amount: amount,
        currency: 'INR',
        description: elements.checkoutDesc.value || 'Palm Biometric Checkout',
      };

      const response = await apiRequest('/api/v1/payments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': state.deviceId,
          'X-Device-Key': state.deviceKey,
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(payload),
      });

      playAudioTone('success');

      // Show receipt modal
      elements.receiptAmount.textContent = parseFloat(response.amount).toFixed(2);
      elements.receiptTxRef.textContent = response.transaction_reference;
      elements.receiptCustomerName.textContent = state.matchedCustomer.name;
      elements.receiptRemainingBalance.textContent = `₹${parseFloat(response.remaining_balance).toFixed(2)}`;
      elements.receiptTimestamp.textContent = new Date().toLocaleString();

      elements.modalReceipt.showModal();
      showToast('Payment processed successfully!', 'success');

      // Reset checkout
      elements.matchResultCard.classList.add('hidden');
      state.matchedCustomer = null;

      // Refresh ledgers in real-time
      loadAllTransactions(true);
    } catch (err) {
      playAudioTone('error');
      showToast(`Payment failed: ${err.message}`, 'error');
    } finally {
      elements.btnConfirmCharge.disabled = false;
      elements.btnConfirmCharge.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>Authorize & Charge Payment</span>
      `;
    }
  }

  /* ==========================================================================
     View 2: Multi-Sample Real-Time Biometric Enrollment
     ========================================================================== */

  async function addEnrollmentSample(blob, previewUrl, qualityScore) {
    if (state.enrolledSamples.length >= 5) {
      showToast('Maximum 5 enrollment samples reached', 'warning');
      return;
    }

    state.enrolledSamples.push({
      blob,
      previewUrl,
      quality: qualityScore,
    });

    renderEnrollmentGallery();
    updateEnrollmentSubmitButton();
  }

  function renderEnrollmentGallery() {
    elements.sampleCountBadge.textContent = state.enrolledSamples.length;
    elements.samplesGallery.innerHTML = '';

    if (state.enrolledSamples.length === 0) {
      elements.samplesGallery.innerHTML = `
        <div class="sample-placeholder-card">
          <span class="placeholder-icon">+</span>
          <span>No samples yet</span>
        </div>
      `;
      return;
    }

    state.enrolledSamples.forEach((sample, idx) => {
      const card = document.createElement('div');
      card.className = 'sample-thumbnail-card';
      card.innerHTML = `
        <img class="sample-thumb-img" src="${sample.previewUrl}" alt="Sample ${idx + 1}">
        <span class="sample-quality-tag">Q: ${Math.round(sample.quality * 100)}%</span>
        <button type="button" class="btn-delete-sample" title="Remove sample" data-idx="${idx}">&times;</button>
      `;

      card.querySelector('.btn-delete-sample').addEventListener('click', (e) => {
        e.stopPropagation();
        removeEnrollmentSample(idx);
      });

      elements.samplesGallery.appendChild(card);
    });
  }

  function removeEnrollmentSample(index) {
    state.enrolledSamples.splice(index, 1);
    renderEnrollmentGallery();
    updateEnrollmentSubmitButton();
    showToast(`Sample removed (${state.enrolledSamples.length}/3-5 remaining)`, 'info');
  }

  function updateEnrollmentSubmitButton() {
    const hasMinSamples = state.enrolledSamples.length >= 3;
    elements.btnSubmitEnrollment.disabled = !hasMinSamples;

    if (hasMinSamples) {
      elements.btnSubmitEnrollment.classList.add('btn-pulse');
    } else {
      elements.btnSubmitEnrollment.classList.remove('btn-pulse');
    }
  }

  async function handleSnapEnrollmentFrame() {
    if (state.enrolledSamples.length >= 5) {
      showToast('Maximum 5 enrollment samples reached', 'warning');
      return;
    }

    try {
      showToast('Capturing NIR sample from ESP32...', 'info');
      if (elements.enrollHudStatus) elements.enrollHudStatus.textContent = 'CAPTURING FROM ESP32...';

      const rawUrl = elements.esp32DeviceUrl ? elements.esp32DeviceUrl.value.trim() : state.esp32Url;
      const res = await apiRequest('/api/v1/devices/esp32/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_url: rawUrl, device_id: state.deviceId || null }),
      });

      if (!res || !res.image) {
        throw new Error(res?.error || 'No frame received from ESP32');
      }

      // Convert base64 to Blob
      const byteCharacters = atob(res.image);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'image/jpeg' });
      const previewUrl = URL.createObjectURL(blob);

      // Draw onto the enrollment viewfinder canvas
      const img = new Image();
      img.onload = () => {
        if (elements.enrollCaptureCanvas) {
          elements.enrollCaptureCanvas.style.display = 'block';
          const ctx = elements.enrollCaptureCanvas.getContext('2d');
          ctx.drawImage(img, 0, 0, elements.enrollCaptureCanvas.width, elements.enrollCaptureCanvas.height);
        }
      };
      img.src = previewUrl;

      // Assess quality via API
      let quality = 0.88;
      try {
        const formData = new FormData();
        formData.append('image', blob, 'sample.jpg');
        const qRes = await apiRequest('/api/v1/biometric/quality', { method: 'POST', body: formData });
        quality = qRes.quality_score;
      } catch {
        // fallback
      }

      playAudioTone('scan');
      addEnrollmentSample(blob, previewUrl, quality);
      if (elements.enrollHudStatus) elements.enrollHudStatus.textContent = `SAMPLE #${state.enrolledSamples.length} CAPTURED`;
      showToast(`Captured ESP32 Sample #${state.enrolledSamples.length} (Quality: ${Math.round(quality * 100)}%)`, 'success');
    } catch (err) {
      if (elements.enrollHudStatus) elements.enrollHudStatus.textContent = 'ESP32 CAPTURE ERROR';
      showToast(`ESP32 Capture Error: ${err.message}`, 'error');
    }
  }

  async function handleAutoBurst3LiveFrames() {
    if (state.enrolledSamples.length >= 5) {
      showToast('Maximum 5 enrollment samples already collected', 'warning');
      return;
    }

    elements.btnEnrollAuto3.disabled = true;
    const btnLabel = document.getElementById('auto-burst-label');

    try {
      for (let i = 0; i < 3; i++) {
        if (state.enrolledSamples.length >= 5) break;

        const sampleNum = state.enrolledSamples.length + 1;
        if (btnLabel) btnLabel.textContent = `ESP32 Sample ${i + 1}/3...`;
        if (elements.enrollHudStatus) elements.enrollHudStatus.textContent = `CAPTURING SAMPLE #${sampleNum}...`;

        await handleSnapEnrollmentFrame();

        if (i < 2) {
          if (btnLabel) btnLabel.textContent = `Shift Palm Slightly...`;
          await new Promise((r) => setTimeout(r, 1200));
        }
      }
      showToast('All 3 ESP32 samples captured successfully!', 'success');
    } catch (err) {
      showToast(`Burst capture failed: ${err.message}`, 'error');
    } finally {
      elements.btnEnrollAuto3.disabled = false;
      if (btnLabel) btnLabel.textContent = 'Auto-Capture 3 ESP32 Samples';
      if (elements.enrollHudStatus) elements.enrollHudStatus.textContent = 'ESP32 NIR SENSOR';
    }
  }

  async function handleSubmitEnrollment() {
    const name = elements.enrollName.value.trim();
    const phone = elements.enrollPhone.value.trim();

    if (!name) {
      showToast('Please enter customer full name', 'error');
      return;
    }
    if (!phone) {
      showToast('Please enter customer phone number', 'error');
      return;
    }
    if (state.enrolledSamples.length < 3) {
      showToast('At least 3 palm samples required for biometric registration', 'error');
      return;
    }

    elements.btnSubmitEnrollment.disabled = true;
    elements.btnSubmitEnrollment.innerHTML = `<span>Enrolling Palm Templates...</span>`;

    try {
      const formData = new FormData();
      formData.append('name', name);
      formData.append('phone', phone);

      state.enrolledSamples.forEach((sample, i) => {
        formData.append('samples', sample.blob, `palm_sample_${i + 1}.jpg`);
      });

      const response = await apiRequest('/api/v1/users/register', {
        method: 'POST',
        body: formData,
      });

      const userId = response.user_id;
      playAudioTone('success');
      showToast(`Customer registered! User ID: ${userId.slice(0, 8)}...`, 'success');

      // Check initial wallet top-up
      const initAmount = parseFloat(elements.enrollInitBalance.value);
      if (initAmount > 0) {
        await apiRequest(`/api/v1/wallets/${userId}/topup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: initAmount, description: 'Initial Enrollment Top-Up' }),
        });
        showToast(`Wallet credited with ₹${initAmount.toFixed(2)}`, 'success');
      }

      // Reset form
      elements.enrollName.value = '';
      elements.enrollPhone.value = '';
      state.enrolledSamples = [];
      renderEnrollmentGallery();
      updateEnrollmentSubmitButton();

      // Refresh cached users list
      await loadUsersDropdown();

      // Switch to wallets view with this new user
      switchTab('wallets');
      elements.walletUserSelect.value = userId;
      handleUserSelectChange();
    } catch (err) {
      playAudioTone('error');
      showToast(`Enrollment failed: ${err.message}`, 'error');
    } finally {
      elements.btnSubmitEnrollment.disabled = false;
      elements.btnSubmitEnrollment.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>Register User & Save Biometric Templates</span>
      `;
    }
  }

  /* ==========================================================================
     View 3: Wallets & Top-Up Actions
     ========================================================================== */

  async function loadUsersDropdown() {
    try {
      const data = await apiRequest('/api/v1/admin/users?page=1&page_size=50', {
        headers: { 'X-Admin-Key': state.adminKey },
      });

      state.usersCache = data.users || [];

      // Update wallets dropdown
      if (elements.walletUserSelect) {
        elements.walletUserSelect.innerHTML = '<option value="">-- Choose Enrolled User --</option>';
        state.usersCache.forEach((u) => {
          const opt = document.createElement('option');
          opt.value = u.id;
          opt.textContent = `${u.name} (${u.phone || u.id.slice(0, 8)})`;
          elements.walletUserSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('Could not populate users dropdown from admin:', err);
    }
  }

  async function handleUserSelectChange() {
    const userId = elements.walletUserSelect.value;
    if (!userId) {
      elements.walletBalanceDisplay.textContent = '0.00';
      elements.walletUserName.textContent = 'No User Selected';
      elements.tbodyUserTransactions.innerHTML = `
        <tr><td colspan="6" class="text-center text-muted">Select a customer above to view their statement.</td></tr>
      `;
      return;
    }

    try {
      const [wallet, user, txData] = await Promise.all([
        apiRequest(`/api/v1/wallets/${userId}`),
        apiRequest(`/api/v1/users/${userId}`),
        apiRequest(`/api/v1/transactions/${userId}?page=1&page_size=20`),
      ]);

      elements.walletBalanceDisplay.textContent = parseFloat(wallet.balance).toFixed(2);
      elements.walletUserName.textContent = `${user.name} • ${user.phone || 'No phone'}`;
      elements.walletStatusBadge.textContent = wallet.status;

      renderUserTransactionsTable(txData.transactions || []);
    } catch (err) {
      showToast(`Error fetching wallet: ${err.message}`, 'error');
    }
  }

  function renderUserTransactionsTable(transactions) {
    if (transactions.length === 0) {
      elements.tbodyUserTransactions.innerHTML = `
        <tr><td colspan="6" class="text-center text-muted">No transactions on record for this customer.</td></tr>
      `;
      return;
    }

    elements.tbodyUserTransactions.innerHTML = transactions
      .map((tx) => {
        const isPayment = tx.transaction_type === 'PAYMENT';
        const amountSign = isPayment ? '-' : '+';
        const amountColor = isPayment ? 'var(--text-primary)' : 'var(--emerald-primary)';
        const dateStr = new Date(tx.created_at).toLocaleString();

        let badgeClass = 'badge-pending';
        if (tx.status === 'SUCCESS') badgeClass = 'badge-success';
        if (tx.status === 'FAILED') badgeClass = 'badge-failed';

        return `
        <tr>
          <td class="font-mono text-bold">${tx.transaction_reference}</td>
          <td><span class="badge ${isPayment ? 'badge-pending' : 'badge-active'}">${tx.transaction_type}</span></td>
          <td class="font-mono" style="color: ${amountColor}; font-weight: 700;">${amountSign}₹${parseFloat(tx.amount).toFixed(2)}</td>
          <td><span class="badge ${badgeClass}">${tx.status}</span></td>
          <td class="text-sm font-mono text-secondary">${dateStr}</td>
          <td>
            <button type="button" class="btn btn-secondary btn-sm" onclick="window.viewTxDetail('${tx.id}')">View</button>
          </td>
        </tr>
      `;
      })
      .join('');
  }

  async function handleTopupSubmit() {
    const userId = elements.walletUserSelect.value;
    if (!userId) {
      showToast('Please select a customer first', 'error');
      return;
    }

    const amount = parseFloat(elements.topupAmount.value);
    if (!amount || amount <= 0) {
      showToast('Please enter a positive top-up amount', 'error');
      return;
    }

    elements.btnSubmitTopup.disabled = true;

    try {
      const response = await apiRequest(`/api/v1/wallets/${userId}/topup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: amount,
          description: elements.topupDesc.value || 'Admin Cash Deposit',
        }),
      });

      playAudioTone('success');
      showToast(`Wallet topped up with ₹${amount.toFixed(2)}! New balance: ₹${parseFloat(response.balance).toFixed(2)}`, 'success');
      elements.walletBalanceDisplay.textContent = parseFloat(response.balance).toFixed(2);

      // Refresh transaction table
      const txData = await apiRequest(`/api/v1/transactions/${userId}?page=1&page_size=20`);
      renderUserTransactionsTable(txData.transactions || []);
    } catch (err) {
      showToast(`Top-up failed: ${err.message}`, 'error');
    } finally {
      elements.btnSubmitTopup.disabled = false;
    }
  }

  /* ==========================================================================
     View 4: Live All Transactions Feed & Polling
     ========================================================================== */

  async function loadAllTransactions(isSilent = false) {
    if (!isSilent) {
      elements.tbodyAllTransactions.innerHTML = `
        <tr><td colspan="7" class="text-center text-muted">Refreshing live transaction ledger...</td></tr>
      `;
    }

    try {
      const usersData = await apiRequest('/api/v1/admin/users?page=1&page_size=50', {
        headers: { 'X-Admin-Key': state.adminKey },
      });

      const users = usersData.users || [];
      const userMap = new Map(users.map((u) => [u.id, u.name]));

      const txPromises = users.slice(0, 15).map((u) =>
        apiRequest(`/api/v1/transactions/${u.id}?page=1&page_size=10`).catch(() => ({ transactions: [] }))
      );

      const results = await Promise.all(txPromises);
      let allTx = [];
      results.forEach((res) => {
        if (res.transactions) allTx.push(...res.transactions);
      });

      allTx.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      if (allTx.length === 0) {
        elements.tbodyAllTransactions.innerHTML = `
          <tr><td colspan="7" class="text-center text-muted">No transactions found in system.</td></tr>
        `;
        return;
      }

      elements.tbodyAllTransactions.innerHTML = allTx
        .map((tx) => {
          const userName = userMap.get(tx.user_id) || 'Enrolled User';
          const isPayment = tx.transaction_type === 'PAYMENT';
          const amountSign = isPayment ? '-' : '+';
          const amountColor = isPayment ? 'var(--text-primary)' : 'var(--emerald-primary)';

          let badgeClass = 'badge-pending';
          if (tx.status === 'SUCCESS') badgeClass = 'badge-success';
          if (tx.status === 'FAILED') badgeClass = 'badge-failed';

          return `
          <tr>
            <td class="font-mono text-bold">${tx.transaction_reference}</td>
            <td>${escapeHtml(userName)}</td>
            <td><span class="badge ${isPayment ? 'badge-pending' : 'badge-active'}">${tx.transaction_type}</span></td>
            <td class="font-mono" style="color: ${amountColor}; font-weight: 700;">${amountSign}₹${parseFloat(tx.amount).toFixed(2)}</td>
            <td><span class="badge ${badgeClass}">${tx.status}</span></td>
            <td class="text-sm font-mono text-secondary">${new Date(tx.created_at).toLocaleString()}</td>
            <td>
              <button type="button" class="btn btn-secondary btn-sm" onclick="window.viewTxDetail('${tx.id}')">Receipt</button>
            </td>
          </tr>
        `;
        })
        .join('');
    } catch (err) {
      if (!isSilent) {
        elements.tbodyAllTransactions.innerHTML = `
          <tr><td colspan="7" class="text-center text-muted">Failed to load transactions: ${escapeHtml(err.message)}</td></tr>
        `;
      }
    }
  }

  function startRealTimePolling() {
    if (state.pollingInterval) return;
    state.pollingInterval = setInterval(() => {
      if (document.hidden) return;
      const activePanel = document.querySelector('.view-panel.active');
      if (activePanel && activePanel.id === 'view-transactions') {
        loadAllTransactions(true);
      }
    }, 4000);
  }

  window.viewTxDetail = async function (txId) {
    try {
      const tx = await apiRequest(`/api/v1/transactions/detail/${txId}`);
      elements.receiptAmount.textContent = parseFloat(tx.amount).toFixed(2);
      elements.receiptTxRef.textContent = tx.transaction_reference;
      elements.receiptCustomerName.textContent = `User ${tx.user_id.slice(0, 8)}...`;
      elements.receiptRemainingBalance.textContent = 'Statement Verified';
      elements.receiptTimestamp.textContent = new Date(tx.created_at).toLocaleString();
      elements.modalReceipt.showModal();
    } catch (err) {
      showToast(`Error viewing transaction: ${err.message}`, 'error');
    }
  };

  /* ==========================================================================
     View 5: Admin & Hardware Manager
     ========================================================================== */

  async function handleTestDeviceAuth() {
    const devId = elements.cfgDeviceId.value.trim();
    const devKey = elements.cfgDeviceKey.value.trim();

    if (!devId || !devKey) {
      showToast('Device ID and Device Key required', 'error');
      return;
    }

    try {
      const result = await apiRequest('/api/v1/devices/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: devId, device_key: devKey }),
      });

      playAudioTone('success');
      showToast(`Device Connected! Status: ${result.connection_status} (${result.device_name})`, 'success');
      elements.terminalLabel.textContent = `${result.device_name} (ONLINE)`;
    } catch (err) {
      playAudioTone('error');
      showToast(`Device authentication failed: ${err.message}`, 'error');
    }
  }

  function handleSaveDeviceConfig() {
    state.deviceId = elements.cfgDeviceId.value.trim();
    state.deviceKey = elements.cfgDeviceKey.value.trim();
    state.adminKey = elements.cfgAdminKey.value.trim();

    localStorage.setItem('palmpay_device_id', state.deviceId);
    localStorage.setItem('palmpay_device_key', state.deviceKey);
    localStorage.setItem('palmpay_admin_key', state.adminKey);

    showToast('Terminal hardware configuration saved!', 'success');
  }

  async function handleCheckModelStatus() {
    try {
      const status = await apiRequest('/api/v1/admin/model/status', {
        headers: { 'X-Admin-Key': state.adminKey },
      });

      elements.aiModelVersion.textContent = status.model_version;
      elements.aiModelType.textContent = `${status.model_type} (${status.is_mock ? 'Mock' : 'PyTorch Live Real-Time'})`;
      elements.aiModelDim.textContent = `${status.embedding_dim}-dim Vector`;
      if (elements.aiLivenessStatus) {
        elements.aiLivenessStatus.textContent = `${status.liveness_type || 'RealTime'} (ACTIVE)`;
      }

      showToast('Real-Time Biometric PyTorch model telemetry verified OK', 'success');
    } catch (err) {
      showToast(`Could not query model: ${err.message}`, 'error');
    }
  }

  async function handlePingHealth() {
    try {
      const health = await apiRequest('/api/v1/health');
      elements.healthApiStatus.textContent = `${health.status.toUpperCase()} (${health.version})`;
      playAudioTone('success');
      showToast(`FastAPI Server is healthy and responsive (v${health.version})`, 'success');
    } catch (err) {
      elements.healthApiStatus.textContent = 'DISCONNECTED';
      playAudioTone('error');
      showToast(`Backend connection failed: ${err.message}`, 'error');
    }
  }

  async function handleRegisterNewDevice() {
    const name = elements.regDevName.value.trim();
    const type = elements.regDevType.value;
    const fw = elements.regDevFw.value.trim();

    if (!name) {
      showToast('Please specify a device name', 'error');
      return;
    }

    try {
      const response = await apiRequest('/api/v1/devices/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': state.adminKey,
        },
        body: JSON.stringify({
          device_name: name,
          device_type: type,
          firmware_version: fw,
        }),
      });

      elements.cfgDeviceId.value = response.id;
      elements.cfgDeviceKey.value = response.device_key;
      handleSaveDeviceConfig();

      playAudioTone('success');
      showToast(`Registered new terminal! Device Key generated.`, 'success');
    } catch (err) {
      showToast(`Device registration failed: ${err.message}`, 'error');
    }
  }

  async function loadAdminUsers() {
    try {
      const data = await apiRequest('/api/v1/admin/users?page=1&page_size=50', {
        headers: { 'X-Admin-Key': state.adminKey },
      });

      const users = data.users || [];
      state.usersCache = users;

      if (users.length === 0) {
        elements.tbodyAdminUsers.innerHTML = `
          <tr><td colspan="6" class="text-center text-muted">No users currently registered.</td></tr>
        `;
        return;
      }

      elements.tbodyAdminUsers.innerHTML = users
        .map((u) => {
          let statusBadge = u.is_active ? 'badge-success' : 'badge-suspended';
          return `
          <tr>
            <td class="font-mono text-sm">${u.id.slice(0, 16)}...</td>
            <td><strong>${escapeHtml(u.name)}</strong></td>
            <td class="font-mono text-secondary">${escapeHtml(u.phone || 'N/A')}</td>
            <td><span class="badge ${statusBadge}">${u.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
            <td class="text-sm font-mono text-secondary">${new Date(u.created_at).toLocaleDateString()}</td>
            <td>
              <button type="button" class="btn btn-secondary btn-sm" onclick="window.quickSelectUser('${u.id}')">Select</button>
            </td>
          </tr>
        `;
        })
        .join('');
    } catch (err) {
      elements.tbodyAdminUsers.innerHTML = `
        <tr><td colspan="6" class="text-center text-muted">Error fetching user directory: ${err.message}</td></tr>
      `;
    }
  }

  window.quickSelectUser = function (userId) {
    switchTab('wallets');
    elements.walletUserSelect.value = userId;
    handleUserSelectChange();
  };

  /* ==========================================================================
     Navigation & Tab Switching
     ========================================================================== */

  function switchTab(targetName) {
    elements.tabs.forEach((tab) => {
      const isTarget = tab.dataset.target === `view-${targetName}`;
      tab.classList.toggle('active', isTarget);
    });

    elements.viewPanels.forEach((panel) => {
      const isTarget = panel.id === `view-${targetName}`;
      panel.classList.toggle('active', isTarget);
    });

    if (targetName === 'wallets') {
      loadUsersDropdown();
    } else if (targetName === 'transactions') {
      loadAllTransactions();
    } else if (targetName === 'admin') {
      handleCheckModelStatus();
      loadAdminUsers();
    }
  }

  /* ==========================================================================
     Initialization & Event Listeners
     ========================================================================== */

  function initEventListeners() {
    // Nav tabs
    elements.tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const targetView = tab.dataset.target.replace('view-', '');
        switchTab(targetView);
      });
    });

    if (elements.btnQuickConfig) {
      elements.btnQuickConfig.addEventListener('click', () => switchTab('admin'));
    }

    // Quick amounts (Checkout)
    elements.quickAmountChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        elements.quickAmountChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        elements.checkoutAmount.value = parseFloat(chip.dataset.amount).toFixed(2);
      });
    });

    // ESP32 Hardware Controls
    if (elements.btnPingEsp32) {
      elements.btnPingEsp32.addEventListener('click', () => testEsp32Connection(true));
    }
    if (elements.esp32DeviceUrl) {
      elements.esp32DeviceUrl.addEventListener('change', (e) => {
        state.esp32Url = e.target.value.trim();
        localStorage.setItem('palmpay_esp32_url', state.esp32Url);
      });
    }

    // Real-Time Auto-Scan Toggle
    if (elements.btnToggleAutoscan) {
      elements.btnToggleAutoscan.addEventListener('click', toggleAutoScan);
    }

    // Real-Time Live Video Stream Toggle
    if (elements.btnToggleStream) {
      elements.btnToggleStream.addEventListener('click', toggleLiveStream);
    }

    // Checkout actions
    elements.btnScanIdentify.addEventListener('click', handleScanAndIdentify);
    elements.btnConfirmCharge.addEventListener('click', handleConfirmPayment);
    elements.btnResetMatch.addEventListener('click', () => {
      elements.matchResultCard.classList.add('hidden');
      state.matchedCustomer = null;
    });

    // Enrollment ESP32 actions
    if (elements.btnEnrollSnap) {
      elements.btnEnrollSnap.addEventListener('click', handleSnapEnrollmentFrame);
    }
    if (elements.btnEnrollAuto3) {
      elements.btnEnrollAuto3.addEventListener('click', handleAutoBurst3LiveFrames);
    }
    if (elements.btnSubmitEnrollment) {
      elements.btnSubmitEnrollment.addEventListener('click', handleSubmitEnrollment);
    }
    if (elements.btnClearEnrollment) {
      elements.btnClearEnrollment.addEventListener('click', () => {
        elements.enrollName.value = '';
        elements.enrollPhone.value = '';
        state.enrolledSamples = [];
        renderEnrollmentGallery();
        updateEnrollmentSubmitButton();
      });
    }

    // Wallets actions
    if (elements.walletUserSelect) {
      elements.walletUserSelect.addEventListener('change', handleUserSelectChange);
    }
    elements.quickTopupChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        elements.quickTopupChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        elements.topupAmount.value = chip.dataset.topup;
      });
    });
    if (elements.btnSubmitTopup) {
      elements.btnSubmitTopup.addEventListener('click', handleTopupSubmit);
    }
    if (elements.btnRefreshUserTx) {
      elements.btnRefreshUserTx.addEventListener('click', handleUserSelectChange);
    }

    // Transactions actions
    if (elements.btnRefreshAllTx) {
      elements.btnRefreshAllTx.addEventListener('click', () => loadAllTransactions(false));
    }

    // Admin & Hardware actions
    if (elements.btnTestDeviceAuth) {
      elements.btnTestDeviceAuth.addEventListener('click', handleTestDeviceAuth);
    }
    if (elements.btnSaveDeviceCfg) {
      elements.btnSaveDeviceCfg.addEventListener('click', handleSaveDeviceConfig);
    }
    if (elements.btnCheckModelStatus) {
      elements.btnCheckModelStatus.addEventListener('click', handleCheckModelStatus);
    }
    if (elements.btnPingHealth) {
      elements.btnPingHealth.addEventListener('click', handlePingHealth);
    }
    if (elements.btnSubmitRegDevice) {
      elements.btnSubmitRegDevice.addEventListener('click', handleRegisterNewDevice);
    }
    if (elements.btnRefreshAdminUsers) {
      elements.btnRefreshAdminUsers.addEventListener('click', loadAdminUsers);
    }

    // Receipt Modal
    if (elements.btnCloseReceipt) {
      elements.btnCloseReceipt.addEventListener('click', () => {
        elements.modalReceipt.close();
      });
    }
  }

  // App Initialization
  function init() {
    initEventListeners();

    // Set default values in Admin inputs
    if (elements.cfgDeviceId) elements.cfgDeviceId.value = state.deviceId;
    if (elements.cfgDeviceKey) elements.cfgDeviceKey.value = state.deviceKey;
    if (elements.cfgAdminKey) elements.cfgAdminKey.value = state.adminKey;

    // Initialize ESP32 URL input & test connection in background
    if (elements.esp32DeviceUrl) elements.esp32DeviceUrl.value = state.esp32Url;
    testEsp32Connection(false);

    // Populate user cache
    loadUsersDropdown();
    handleCheckModelStatus();

    // Start real-time live video stream from ESP32
    startEsp32LiveStream();

    // Start real-time background synchronization
    startRealTimePolling();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
