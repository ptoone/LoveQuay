/* Citizen card verification form.
 *
 * The number is checked for shape here, in the browser, so an obvious typo
 * never reaches the server. Whether a card was actually issued, and whether the
 * subscription behind it is still paid, is only ever answered by the API.
 *
 * Four outcomes, and the fourth is the one that matters:
 *   active     the card exists and the subscription is paid
 *   inactive   the card exists, the subscription is not currently active
 *   unknown    no card with that number
 *   unsure     we could not ask. NOT the same as unknown, and never shown as if
 *              it were — somebody checking a card at the water needs to be able
 *              to tell "this is fake" from "my phone has no signal".
 */
(function () {
  'use strict';

  var API = 'https://api.lovequay.com/v1/verify';

  var form = document.getElementById('lqVerifyForm');
  if (!form || !window.LQID) return;

  var input = document.getElementById('lqCardId');
  var hint = document.getElementById('lqCardHint');
  var btn = document.getElementById('lqCheckBtn');
  var result = document.getElementById('lqResult');
  var head = document.getElementById('lqResultHead');
  var body = document.getElementById('lqResultBody');
  var idOut = document.getElementById('lqResultId');
  var scanBtn = document.getElementById('lqScanBtn');
  var scanWrap = document.getElementById('lqScanWrap');
  var video = document.getElementById('lqScanVideo');
  var scanStop = document.getElementById('lqScanStop');

  var HINT = hint.innerHTML;
  var stream = null;
  var scanning = false;

  var STATES = {
    active: ['active', '✓ Valid', 'This card exists and the subscription behind it is paid and active.'],
    inactive: ['inactive', '● Not active', 'This card number was issued, but the subscription behind it is not active right now. It may have lapsed or been cancelled.'],
    unknown: ['unknown', '✕ No such card', 'No card has ever been issued with this number.'],
    unsure: ['unsure', '— Could not check', 'The verification service could not be reached. This does not mean the card is fake — it means we could not ask. Try again in a moment.'],
    malformed: ['unknown', '✕ Not a card number', 'That is not a well-formed LoveQuay card number. Check for a mistyped character.']
  };

  function show(kind, extra, cardId) {
    var s = STATES[kind] || STATES.unsure;
    result.className = 'verify-result mt-4 is-shown verify-result--' + s[0];
    head.textContent = s[1];
    body.textContent = extra ? s[2] + ' ' + extra : s[2];
    idOut.textContent = cardId || '';
  }

  function hide() {
    result.className = 'verify-result mt-4';
  }

  function setBusy(on) {
    btn.disabled = on;
    btn.textContent = on ? 'Checking…' : 'Check this card';
  }

  /* Tidy the number as it is typed, without fighting the caret at the end. */
  input.addEventListener('input', function () {
    var atEnd = input.selectionStart === input.value.length;
    var d = window.LQID.normalise(input.value).slice(0, 8);
    var pretty = d.length > 4 ? 'LQ-' + d.slice(0, 4) + '-' + d.slice(4) : (d ? 'LQ-' + d : '');
    if (pretty !== input.value) {
      input.value = pretty;
      if (atEnd) input.setSelectionRange(pretty.length, pretty.length);
    }
    input.classList.remove('is-bad');
    hint.classList.remove('is-bad');
    hint.innerHTML = HINT;
    hide();
  });

  async function check(raw) {
    var parsed = window.LQID.parse(raw);
    if (!parsed.ok) {
      input.classList.add('is-bad');
      hint.classList.add('is-bad');
      hint.textContent = parsed.reason === 'checksum'
        ? 'That number fails its own check character — one of them is wrong.'
        : 'A card number is LQ followed by eight characters.';
      show('malformed');
      return;
    }

    setBusy(true);
    try {
      var res = await fetch(API + '?id=' + encodeURIComponent(parsed.id), {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(10000)
      });

      if (res.status === 429) {
        show('unsure', 'Too many checks from this connection — wait a minute.', parsed.id);
        return;
      }
      if (!res.ok && res.status !== 400) {
        show('unsure', null, parsed.id);
        return;
      }

      var data = await res.json();
      if (data.status === 'active') {
        show('active', data.renews ? 'Renews ' + data.renews + '.' : null, data.id || parsed.id);
      } else if (data.status === 'inactive') {
        show('inactive', null, data.id || parsed.id);
      } else if (data.status === 'unknown') {
        show('unknown', null, parsed.id);
      } else {
        show('unsure', null, parsed.id);
      }
    } catch (err) {
      // Offline, DNS failure, timeout, CORS, the API not deployed yet — all of
      // these mean "we could not ask", never "the card is fake".
      show('unsure', null, parsed.id);
    } finally {
      setBusy(false);
    }
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    void check(input.value);
  });

  /* ---------------------------------------------------------------- scan -- */

  function canScan() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
           ('BarcodeDetector' in window || window.jsQR);
  }

  function loadJsQR() {
    if (window.jsQR) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function startScan() {
    try {
      if (!('BarcodeDetector' in window)) await loadJsQR();
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
    } catch (err) {
      show('unsure', 'The camera could not be opened — type the number instead.');
      return;
    }

    video.srcObject = stream;
    scanWrap.classList.add('is-shown');
    await video.play();
    scanning = true;

    var detector = ('BarcodeDetector' in window)
      ? new BarcodeDetector({ formats: ['qr_code'] })
      : null;
    var canvas = document.createElement('canvas');
    var cx = canvas.getContext('2d', { willReadFrequently: true });

    while (scanning) {
      var text = null;
      try {
        if (detector) {
          var found = await detector.detect(video);
          if (found.length) text = found[0].rawValue;
        } else if (video.videoWidth) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          cx.drawImage(video, 0, 0);
          var img = cx.getImageData(0, 0, canvas.width, canvas.height);
          var code = window.jsQR(img.data, img.width, img.height);
          if (code) text = code.data;
        }
      } catch (err) { /* a dropped frame is not worth stopping for */ }

      if (text) {
        var parsed = window.LQID.fromScan(text);
        if (parsed.ok) {
          stopScan();
          input.value = parsed.id;
          void check(parsed.id);
          return;
        }
      }
      await new Promise(function (r) { setTimeout(r, 180); });
    }
  }

  function stopScan() {
    scanning = false;
    scanWrap.classList.remove('is-shown');
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    video.srcObject = null;
  }

  if (canScan() || (navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
    scanBtn.hidden = false;
    scanBtn.addEventListener('click', function () { void startScan(); });
    scanStop.addEventListener('click', stopScan);
    window.addEventListener('pagehide', stopScan);
  }
}());
