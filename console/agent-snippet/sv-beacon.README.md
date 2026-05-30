# SpoofVane Beacon (`sv-beacon.js`) — Install Guide (W8)

The beacon is a tamper-resistant JS snippet you embed on your **real** site. When
a phishing kit clones your page and serves your assets from its own origin, the
beacon fires from that foreign origin — SpoofVane detects the clone in real time,
counts per-victim visits, and can serve markered decoy credentials.

## Install

1. Copy `sv-beacon.js` to your site's static assets.
2. Replace the two placeholders:
   - `REPLACE_WITH_YOUR_CANONICAL_ORIGIN` → your real origin, e.g. `https://acmebank.com`
   - `REPLACE_WITH_INGEST_URL` → your SpoofVane ingest endpoint, e.g. `https://rtp.spoofvane.example/api/rtp/beacon`
3. Include it on every page you want protected:
   ```html
   <script src="/assets/sv-beacon.js" defer></script>
   ```

## Privacy

The beacon sends only: the serving origin, a coarse hashed fingerprint (UA +
screen + timezone bucket — no PII), and a timestamp. It fires **only** when the
page is served from an origin other than your canonical one, so legitimate
same-origin traffic generates no beacons. It fails closed: any error is swallowed
so it can never break your page.

## How detection works

- Same-origin load → no beacon (benign).
- Foreign-origin load → beacon → `clone_detector` opens an alert; `victim_tracker`
  aggregates victims per spoof cluster into an incident with an attack magnitude.
- Decoy credentials (optional, RBAC-gated) render harvested creds useless and
  identify the attacker if reused.
