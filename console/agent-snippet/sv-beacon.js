/* SpoofVane real-time protection beacon (W8).
 * Embed on the REAL site. On load, it reports the serving origin so SpoofVane
 * can detect when the page's assets are loaded from a foreign origin (a clone).
 * Privacy: sends only a coarse origin + a hashed, non-identifying fingerprint.
 * Tamper-resistant: self-invoking, no globals, fails closed (silent) on error.
 */
(function () {
  "use strict";
  try {
    var SITE = "REPLACE_WITH_YOUR_CANONICAL_ORIGIN"; // e.g. https://acmebank.com
    var INGEST = "REPLACE_WITH_INGEST_URL";          // e.g. https://rtp.spoofvane.example/api/rtp/beacon
    var origin = window.location.origin;

    // Coarse, non-identifying fingerprint (no PII): UA + screen + tz bucket.
    var fpRaw = [
      navigator.userAgent,
      screen.width + "x" + screen.height,
      Intl.DateTimeFormat().resolvedOptions().timeZone
    ].join("|");

    var payload = {
      site: SITE,
      origin: origin,
      fingerprint: fpRaw,
      ts: new Date().toISOString(),
      ua: navigator.userAgent.slice(0, 200)
    };

    // Only beacon when served from an origin other than the canonical one.
    if (origin !== SITE) {
      navigator.sendBeacon
        ? navigator.sendBeacon(INGEST, JSON.stringify(payload))
        : fetch(INGEST, { method: "POST", body: JSON.stringify(payload), keepalive: true });
    }
  } catch (e) {
    /* fail closed: never break the host page */
  }
})();
