/* LoveQuay citizen card numbers.
 *
 * Format  LQ-XXXX-XXXX  — seven random characters and one check character.
 *
 * The alphabet is Crockford base32 with Z removed, leaving 31 symbols: no I,
 * L, O, U or Z, so nothing in a printed number can be mistaken for something
 * else. Input is normalised the Crockford way (I and L read as 1, O reads as 0,
 * U reads as V), so a card read aloud over the phone still lands on the right
 * number.
 *
 * 31 is the point. The check character is a weighted sum modulo 31, and because
 * 31 is prime and the weights are 1..7, it catches EVERY single-character error
 * and EVERY transposition of two adjacent characters. An earlier version used
 * all 32 symbols and modulo 32; because 32 is a power of two, even weights
 * collided and it missed about one single-character typo in twenty.
 *
 * 31^7 is about 27 billion numbers, so guessing a real one is not a practical
 * attack. The check character is there for honest fingers, not hostile ones.
 *
 * tools/build_idcard.py carries the same logic. If you change it here, change
 * it there, and run the cross-check in that file.
 */
(function (root) {
  'use strict';

  var ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXY';   // 31 symbols: no I L O U Z
  var BODY = 7;                       // random characters, before the check

  /* Fold the ambiguous characters onto the ones they look like. */
  function normalise(raw) {
    if (raw == null) return '';
    var s = String(raw).toUpperCase().replace(/[^0-9A-Z]/g, '');
    if (s.indexOf('LQ') === 0) s = s.slice(2);
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === 'I' || c === 'L') c = '1';
      else if (c === 'O') c = '0';
      else if (c === 'U') c = 'V';
      if (ALPHABET.indexOf(c) >= 0) out += c;
    }
    return out;
  }

  /* Weighted sum modulo 31. Weights are 1..7 and 31 is prime, which is what
   * makes the detection total rather than merely good. */
  function checkChar(body) {
    var sum = 0;
    for (var i = 0; i < body.length; i++) {
      sum += ALPHABET.indexOf(body[i]) * (i + 1);
    }
    return ALPHABET[sum % 31];
  }

  function format(digits) {
    return 'LQ-' + digits.slice(0, 4) + '-' + digits.slice(4, 8);
  }

  /* Returns {ok, id, reason}. `ok` only means the number is well formed —
   * whether a card was ever issued is a question for the server. */
  function parse(raw) {
    var d = normalise(raw);
    if (!d) return { ok: false, reason: 'empty' };
    if (d.length !== BODY + 1) return { ok: false, reason: 'length', got: d.length };
    if (checkChar(d.slice(0, BODY)) !== d[BODY]) return { ok: false, reason: 'checksum' };
    return { ok: true, id: format(d) };
  }

  /* A card number can be carried in a QR as the bare number or as a URL that
   * ends in one. Accept either, so a card scanned by a plain camera app still
   * lands somewhere useful. */
  function fromScan(text) {
    if (!text) return { ok: false, reason: 'empty' };
    var s = String(text).trim();
    var m = s.match(/[?&]id=([^&#]+)/i);
    if (m) return parse(decodeURIComponent(m[1]));
    m = s.match(/LQ[-\s]?[0-9A-Z]{4}[-\s]?[0-9A-Z]{4}/i);
    if (m) return parse(m[0]);
    return parse(s);
  }

  var api = { ALPHABET: ALPHABET, normalise: normalise, checkChar: checkChar,
              format: format, parse: parse, fromScan: fromScan };

  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LQID = api;
}(typeof globalThis !== 'undefined' ? globalThis : this));
