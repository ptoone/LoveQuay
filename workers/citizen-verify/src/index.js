/**
 * LoveQuay citizen card verification.
 *
 *   GET /v1/verify?id=LQ-XXXX-XXXX
 *
 * Thexyz runs WHMCS and WHMCS knows whether a subscription is still active, so
 * WHMCS is the source of truth. This Worker exists only because a static page
 * cannot hold the API credential, and because the card number must not reveal
 * the mailbox behind it.
 *
 * What it deliberately does not do:
 *   - never returns the holder's name, email address or client id;
 *   - never confirms a mailbox directly, so it cannot be used to harvest
 *     @lovequay.com addresses;
 *   - never reports "unknown" when WHMCS is unreachable. A door check has to be
 *     able to tell "this card is not real" apart from "I cannot reach the
 *     server right now", so an outage returns 503 and says so.
 */

const CARD_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXY';   // 31 symbols: no I L O U Z
const CARD_BODY = 7;

const ALLOWED_ORIGINS = new Set([
  'https://lovequay.com',
  'https://www.lovequay.com',
]);

/** Mirror of assets/js/lqid.js. Never trust the browser's own check. */
function normaliseCard(raw) {
  if (raw == null) return '';
  let s = String(raw).toUpperCase().replace(/[^0-9A-Z]/g, '');
  if (s.startsWith('LQ')) s = s.slice(2);
  let out = '';
  for (const ch of s) {
    let c = ch;
    if (c === 'I' || c === 'L') c = '1';
    else if (c === 'O') c = '0';
    else if (c === 'U') c = 'V';
    if (CARD_ALPHABET.includes(c)) out += c;
  }
  return out;
}

function cardCheckChar(body) {
  let sum = 0;
  for (let i = 0; i < body.length; i++) {
    sum += CARD_ALPHABET.indexOf(body[i]) * (i + 1);
  }
  return CARD_ALPHABET[sum % 31];
}

function parseCard(raw) {
  const d = normaliseCard(raw);
  if (d.length !== CARD_BODY + 1) return null;
  if (cardCheckChar(d.slice(0, CARD_BODY)) !== d[CARD_BODY]) return null;
  return d;
}

function prettyCard(digits) {
  return `LQ-${digits.slice(0, 4)}-${digits.slice(4, 8)}`;
}

function corsHeaders(origin) {
  const h = {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    Vary: 'Origin',
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    h['Access-Control-Allow-Origin'] = origin;
    h['Access-Control-Allow-Methods'] = 'GET, OPTIONS';
    h['Access-Control-Max-Age'] = '86400';
  }
  return h;
}

function json(body, status, origin, extra) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), ...(extra || {}) },
  });
}

/**
 * Ask WHMCS about one service. Returns {status, nextDue} or throws.
 *
 * WHMCS does not document the full set of status values — the API reference
 * only ever shows "Active" and "Terminated" — so anything that is not exactly
 * "Active" is treated as not valid. That is the safe direction to be wrong in.
 */
async function lookupService(env, serviceId) {
  const form = new URLSearchParams({
    identifier: env.WHMCS_IDENTIFIER,
    secret: env.WHMCS_SECRET,
    action: 'GetClientsProducts',
    serviceid: String(serviceId),
    responsetype: 'json',
  });

  const res = await fetch(env.WHMCS_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
    signal: AbortSignal.timeout(8000),
  });

  if (!res.ok) throw new Error(`whmcs http ${res.status}`);

  // The payload is one service record. Small and bounded, so reading it whole
  // is fine; anything unbounded would be streamed instead.
  const data = await res.json();
  if (data.result !== 'success') throw new Error(`whmcs result ${data.result}`);

  const product = data.products && data.products.product && data.products.product[0];
  if (!product) return null;

  return { status: String(product.status || ''), nextDue: product.nextduedate || null };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin');

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== 'GET') {
      return json({ error: 'method_not_allowed' }, 405, origin);
    }
    if (url.pathname !== '/v1/verify') {
      return json({ error: 'not_found' }, 404, origin);
    }

    // Rate limit on the caller, not the card, so one bad actor cannot lock a
    // real holder out of being checked.
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const { success } = await env.VERIFY_LIMIT.limit({ key: ip });
    if (!success) {
      return json({ error: 'rate_limited' }, 429, origin, { 'Retry-After': '60' });
    }

    const digits = parseCard(url.searchParams.get('id'));
    if (!digits) {
      // Malformed never reaches WHMCS, so a typo costs nothing upstream.
      return json({ status: 'malformed' }, 400, origin);
    }
    const id = prettyCard(digits);

    // Short edge cache. A card's status changes at most once a billing cycle,
    // so a minute of staleness is a fair trade for not hammering WHMCS.
    const cacheKey = new Request(`${url.origin}/v1/verify?id=${digits}`, { method: 'GET' });
    const cache = caches.default;
    const hit = await cache.match(cacheKey);
    if (hit) {
      const body = await hit.json();
      return json(body, 200, origin, { 'X-Cache': 'hit' });
    }

    let record;
    try {
      record = await env.CARDS.get(`card:${digits}`, { type: 'json', cacheTtl: 300 });
    } catch (err) {
      console.error(JSON.stringify({ event: 'kv_error', id, message: String(err) }));
      return json({ status: 'unavailable' }, 503, origin);
    }

    if (!record || !record.serviceid) {
      console.log(JSON.stringify({ event: 'verify', id, result: 'unknown' }));
      const body = { id, status: 'unknown' };
      ctx.waitUntil(cache.put(cacheKey, new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' },
      })));
      return json(body, 200, origin);
    }

    let service;
    try {
      service = await lookupService(env, record.serviceid);
    } catch (err) {
      // Upstream trouble must not look like a forged card.
      console.error(JSON.stringify({ event: 'whmcs_error', id, message: String(err) }));
      return json({ status: 'unavailable' }, 503, origin);
    }

    const active = service && service.status === 'Active';
    const body = {
      id,
      status: active ? 'active' : 'inactive',
      ...(active && service.nextDue ? { renews: service.nextDue } : {}),
    };

    console.log(JSON.stringify({
      event: 'verify', id, result: body.status,
      whmcs: service ? service.status : 'no_service',
    }));

    ctx.waitUntil(cache.put(cacheKey, new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' },
    })));

    return json(body, 200, origin);
  },
};
