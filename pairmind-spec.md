# PairMind — Production Readiness & Demo Completion Spec

**Goal:** Ship a fully working, publicly demoable version of PairMind by **end of July 2026**, so the LinkedIn post shows a real live demo, not a landing page.

**Target post date:** ~July 30–31
**Working window:** ~3 weeks (July 9 → July 30)
**Constraint:** Solo dev, alongside DSA prep + job search — budget ~6–8 hrs/week on this.

---

## Phase 0 — Critical Fix (Day 1–2, do this first)

Nothing else matters if the demo is broken for visitors.

- [ ] **0.1 — Fix mixed-content HTTPS bug**
  - Put Nginx in front of the FastAPI backend on the EC2 instance.
  - Get a free TLS cert via Certbot (Let's Encrypt) — needs a domain/subdomain pointed at `43.205.210.113` (e.g. `api.pairminds.dev` or subdomain of `pavanb.in`).
  - Update `VITE_API_URL` in the Lovable project to the new `https://` endpoint.
  - **Acceptance:** `/auth/verify-token` succeeds from `https://pairminds.lovable.app` in a real browser (not curl).
  - Est: 2–3 hrs (mostly DNS propagation wait)

- [ ] **0.2 — Basic rate limiting on `/auth/verify-token`**
  - Add IP-based throttling (slowapi or nginx `limit_req`) — tokens shouldn't be brute-forceable.
  - **Acceptance:** 6th rapid request from same IP within 1 min gets 429.
  - Est: 1 hr

---

## Phase 1 — Core Demo Feature (Week 1)

This is the actual product. Right now `/demo` shows a placeholder after token verification — this phase replaces it with the real thing.

- [ ] **1.1 — Document upload panel**
  - Two upload zones: Buyer corpus, Seller corpus (PDF/TXT).
  - Files POST to a new `/demo/session/{id}/upload` endpoint, stored per-session (not persisted long-term — demo sessions should be ephemeral/TTL'd).
  - **Acceptance:** uploading a PDF returns a session-scoped doc ID; visible in UI as a chip/tag.

- [ ] **1.2 — Negotiation trigger**
  - "Start Negotiation" button once both corpora have ≥1 doc.
  - Calls backend to kick off the LangGraph run for that session.
  - **Acceptance:** clicking start transitions UI to a live "session.open" state matching the existing landing-page aesthetic.

- [ ] **1.3 — SSE streaming into the chat/ledger view**
  - Reuse the visual language from the landing page's `Ledger` component (turn cards, price tape, citation stamps) but drive it from real backend events instead of the hardcoded `TURNS` array.
  - Backend: confirm FastAPI SSE endpoint emits `{n, side, type, unit/terms, rationale, citations}` per turn.
  - Frontend: `EventSource` or fetch-stream reader, append turns as they arrive, reuse `TurnCard`/`TurnRow` components.
  - **Acceptance:** a real negotiation between uploaded docs streams turn-by-turn into the UI, ending in AGREEMENT/WALK_AWAY/DEADLOCK/TIMEOUT.

- [ ] **1.4 — Session expiry handling**
  - Wire the existing `onExpired()` hook (already stubbed) to any 401 from the backend during a live session — resets to gate view.
  - **Acceptance:** manually expiring a token server-side kicks the UI back to token entry with the "session expired" notice (already built).

- [ ] **1.5 — Session persistence across refresh**
  - Store `session_token` in `sessionStorage` (fine for this app — it's not a Claude artifact) so a page refresh doesn't force re-entry.
  - **Acceptance:** refresh mid-demo keeps you logged into the session (until natural expiry).

---

## Phase 2 — Backend Hardening (Week 1–2, can overlap with Phase 1)

- [ ] **2.1 — Ephemeral session cleanup**
  - TTL/cron to delete uploaded demo docs + OpenSearch indices after session expiry (privacy + disk hygiene — you already hit a disk-fill issue once).
  - Est: 2 hrs

- [ ] **2.2 — Cap concurrent demo sessions**
  - t3.small has limited headroom. Cap to N concurrent live negotiations; queue or politely reject beyond that with a clear message.
  - Est: 1–2 hrs

- [ ] **2.3 — Basic request logging/monitoring**
  - Log demo requests, session starts, outcomes (agreement/walk-away/timeout) to a file or lightweight table — gives you real numbers for the LinkedIn post ("N live negotiations run during testing").
  - Est: 1–2 hrs

---

## Phase 3 — Supporting Features (Week 2)

- [ ] **3.1 — Replace `mailto:` demo request form with a real backend**
  - POST to a small endpoint that stores the request (DB row or even a log file) and optionally emails you via a transactional service.
  - Reason: `mailto:` silently fails for anyone without a configured desktop mail client.
  - **Acceptance:** submitting the form works with no mail client installed.
  - Est: 2 hrs

- [ ] **3.2 — Manual token issuance flow**
  - Since demo access is invite-only, you need *some* way to generate/send tokens when a request comes in — even a simple CLI script or admin endpoint is enough for launch.
  - Est: 1–2 hrs

- [ ] **3.3 — GitHub link on landing page**
  - Footer says "clone the repo" but there's no link. Add a repo badge/link near the footer or nav.
  - Est: 15 min

---

## Phase 4 — Polish, Analytics, SEO (Week 3)

- [ ] **4.1 — Lightweight analytics**
  - Plausible (or similar privacy-friendly option) on the landing page + demo funnel (visits → demo requests → sessions started → completed).
  - Gives you real numbers to quote in the LinkedIn post.
  - Est: 1 hr

- [ ] **4.2 — OG image for link previews**
  - Screenshot-based `og:image` so the link looks good when shared on LinkedIn/Twitter.
  - Est: 1 hr

- [ ] **4.3 — System status indicator**
  - Small "backend live" badge on the landing page pinging a health endpoint — nice engineering-credibility signal, cheap to build.
  - Est: 1–2 hrs

- [ ] **4.4 — Final QA pass**
  - Full run-through: token request → email/manual issue → gate → upload → live negotiation → outcome, on both desktop and mobile.
  - Est: 1–2 hrs

---

## Phase 5 — LinkedIn Post Prep (Final 2–3 days)

- [ ] **5.1 — Capture a demo recording**
  - Screen-record a full negotiation end-to-end (agreement path) — this becomes the post's visual, not just screenshots.
- [ ] **5.2 — Pull real numbers**
  - From analytics/logging (Phase 2.3, 4.1): sessions run, avg turns to agreement, uptime, etc.
- [ ] **5.3 — Draft the post**
  - Lead with the problem (two-agent negotiation, citation-grounded, isolated corpora) → show the demo clip → close with stack + link.
  - I can draft this with you once the numbers are in.

---

## Suggested Weekly Pacing

| Week | Focus |
|---|---|
| Week 1 (Jul 9–15) | Phase 0 (fix HTTPS) + start Phase 1 (upload + trigger) |
| Week 2 (Jul 16–22) | Finish Phase 1 (SSE streaming) + Phase 2 + Phase 3 |
| Week 3 (Jul 23–29) | Phase 4 (polish/analytics) + QA |
| Jul 30–31 | Record demo, draft + post on LinkedIn |

---

## Notes

- Phase 0 and 1.3 are the load-bearing items — everything else is enhancement. If time runs short, cut Phase 3/4 items before cutting the real SSE demo.
- Reuse existing visual components (`TurnCard`, `Ledger`, stamp/seal styling) for the real demo view — don't redesign, just re-wire data source. Keeps effort down.
