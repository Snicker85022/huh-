/**
 * Display Persistence Hierarchy — standalone module
 * Source: Kitchen Display TV Disposition & Layout v1.0
 * Notion page 371e152fc199812d80fbf10d9a231d4e
 *
 * When a voice query arrives at any TV, the current display status
 * determines whether the response is visual or audio-only:
 *   RED/AMBER → audio-only, do NOT override the on-screen display
 *   GREEN     → show visual response for 10s, then revert
 */

'use strict';

// Revert timer handle — module-level so callers can inspect/cancel
let _revertTimer = null;

/**
 * Handle an incoming voice query according to the persistence hierarchy.
 *
 * @param {string} currentStatus  - 'RED' | 'AMBER' | 'GREEN'
 * @param {string} queryResponse  - content to speak and/or display
 * @param {object} [opts]
 * @param {function} [opts.speak]          - TTS callback: speak(text). Default: no-op.
 * @param {function} [opts.showVisual]     - Render visual response: showVisual(text). Default: no-op.
 * @param {function} [opts.revertVisual]   - Restore previous display state. Default: no-op.
 * @param {number}   [opts.revertDelayMs]  - Override revert delay (default 10000ms).
 * @returns {{ mode: 'audio-only'|'visual', reverted: boolean }}
 */
function handleVoiceQuery(currentStatus, queryResponse, opts = {}) {
  const status = (currentStatus || '').toUpperCase().trim();
  const speak = opts.speak || (() => {});
  const showVisual = opts.showVisual || (() => {});
  const revertVisual = opts.revertVisual || (() => {});
  const revertDelayMs = opts.revertDelayMs != null ? opts.revertDelayMs : 10000;

  if (!['RED', 'AMBER', 'GREEN'].includes(status)) {
    throw new Error(`Invalid display status: "${currentStatus}". Expected RED, AMBER, or GREEN.`);
  }

  // Cancel any pending revert from a previous GREEN query
  if (_revertTimer) {
    clearTimeout(_revertTimer);
    _revertTimer = null;
  }

  // RED or AMBER: critical/warning display active — audio only, preserve screen
  // (Design doc: "Is current display status RED or AMBER? → YES → Respond AUDIO ONLY, do not override display")
  if (status === 'RED' || status === 'AMBER') {
    speak(queryResponse);
    return { mode: 'audio-only', reverted: false };
  }

  // GREEN: safe to show visual — render, then auto-revert after delay
  // (Design doc: "NO → Show visual response for 10 seconds then revert")
  speak(queryResponse);
  showVisual(queryResponse);

  _revertTimer = setTimeout(() => {
    revertVisual();
    _revertTimer = null;
  }, revertDelayMs);

  return { mode: 'visual', reverted: false };
}

/**
 * Cancel any pending visual revert (e.g., if user manually navigates away).
 */
function cancelPendingRevert() {
  if (_revertTimer) {
    clearTimeout(_revertTimer);
    _revertTimer = null;
    return true;
  }
  return false;
}

// ─── Exports ───
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { handleVoiceQuery, cancelPendingRevert };
}

// ─── Self-test (run via: node display-persistence.js) ───
if (typeof require !== 'undefined' && require.main === module) {
  const log = [];
  const mockOpts = (label) => ({
    speak: (text) => log.push(`[${label}] SPEAK: "${text}"`),
    showVisual: (text) => log.push(`[${label}] SHOW_VISUAL: "${text}"`),
    revertVisual: () => log.push(`[${label}] REVERT_VISUAL`),
    revertDelayMs: 50, // fast for testing
  });

  console.log('=== Display Persistence Hierarchy — Self Test ===\n');

  // Test 1: RED status — audio only
  const r1 = handleVoiceQuery('RED', 'Order 42 is ready', mockOpts('RED'));
  console.log('TEST RED:   mode=' + r1.mode);
  console.assert(r1.mode === 'audio-only', 'RED should be audio-only');

  // Test 2: AMBER status — audio only
  const r2 = handleVoiceQuery('AMBER', 'Allergen alert on table 5', mockOpts('AMBER'));
  console.log('TEST AMBER: mode=' + r2.mode);
  console.assert(r2.mode === 'audio-only', 'AMBER should be audio-only');

  // Test 3: GREEN status — visual with revert
  const r3 = handleVoiceQuery('GREEN', 'Next prep task: dice onions', mockOpts('GREEN'));
  console.log('TEST GREEN: mode=' + r3.mode);
  console.assert(r3.mode === 'visual', 'GREEN should be visual');

  // Wait for revert timer
  setTimeout(() => {
    console.log('\nAction log:');
    log.forEach((l) => console.log('  ' + l));

    // Verify RED/AMBER only spoke, GREEN spoke + showed + reverted
    const redSpoke = log.some((l) => l.includes('[RED] SPEAK'));
    const redVisual = log.some((l) => l.includes('[RED] SHOW_VISUAL'));
    const amberSpoke = log.some((l) => l.includes('[AMBER] SPEAK'));
    const amberVisual = log.some((l) => l.includes('[AMBER] SHOW_VISUAL'));
    const greenSpoke = log.some((l) => l.includes('[GREEN] SPEAK'));
    const greenVisual = log.some((l) => l.includes('[GREEN] SHOW_VISUAL'));
    const greenReverted = log.some((l) => l.includes('[GREEN] REVERT_VISUAL'));

    console.log('\nAssertions:');
    console.log('  RED spoke:          ' + redSpoke + (redSpoke ? ' ✓' : ' ✗ FAIL'));
    console.log('  RED no visual:      ' + !redVisual + (!redVisual ? ' ✓' : ' ✗ FAIL'));
    console.log('  AMBER spoke:        ' + amberSpoke + (amberSpoke ? ' ✓' : ' ✗ FAIL'));
    console.log('  AMBER no visual:    ' + !amberVisual + (!amberVisual ? ' ✓' : ' ✗ FAIL'));
    console.log('  GREEN spoke:        ' + greenSpoke + (greenSpoke ? ' ✓' : ' ✗ FAIL'));
    console.log('  GREEN visual shown: ' + greenVisual + (greenVisual ? ' ✓' : ' ✗ FAIL'));
    console.log('  GREEN reverted:     ' + greenReverted + (greenReverted ? ' ✓' : ' ✗ FAIL'));

    const allPass = redSpoke && !redVisual && amberSpoke && !amberVisual && greenSpoke && greenVisual && greenReverted;
    console.log('\n' + (allPass ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'));
    process.exit(allPass ? 0 : 1);
  }, 200);

  // Test 4: Invalid status — should throw
  try {
    handleVoiceQuery('PURPLE', 'bad input', mockOpts('INVALID'));
    console.log('TEST INVALID: FAIL — should have thrown');
  } catch (e) {
    console.log('TEST INVALID: correctly threw — ' + e.message);
  }
}
