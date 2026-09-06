# PairMind — Production Readiness & Demo Completion Spec

**Goal:** Ship a fully working, publicly demoable version of PairMind by **end of July 2026**, so the LinkedIn post shows a real live demo, not a landing page.

**Target post date:** ~July 30–31
**Working window:** ~3 weeks (July 9 → July 30)
**Constraint:** Solo dev, alongside DSA prep + job search — budget ~6–8 hrs/week on this.

> **Status as of 2026-09-07 (code freeze for the LinkedIn post): superseded by what actually shipped.**
> The architecture diverged from this plan early — instead of a separate Lovable-hosted landing project calling a `VITE_API_URL` backend, `landing/` got squash-imported into this monorepo and now shares the same domain/Nginx as the app (see README §1.9 and the Access Tokens section). Checkboxes below are marked against what's actually live, not the original mechanism. **README.md is the source of truth for current architecture** — treat this file as historical planning context only.

---

## Phase 0 — Critical Fix (Day 1–2, do this first)

Nothing else matters if the demo is broken for visitors.

- [x] **0.1 — Fix mixed-content HTTPS bug** — done, different mechanism
  - Nginx + Certbot on the single EC2, domain `pairmind.pavanb.in` (GoDaddy DNS), auto-renewing cert. No separate Lovable project/`VITE_API_URL` — landing and app share one origin, so there's no cross-origin `/api` call to secure in the first place.

- [ ] **0.2 — Basic rate limiting on `/auth/verify-token`** — **not done**
  - IP-based throttling was never added. What exists instead: per-token expiry (7 days) and usage caps (3 negotiations), which bounds cost per issued token but doesn't stop someone from hammering `/auth/verify-token` with guessed tokens. Worth adding (`slowapi` or Nginx `limit_req`) if the demo gets meaningfully more traffic than expected.

---

## Phase 1 — Core Demo Feature (Week 1)

This is the actual product. Right now `/demo` shows a placeholder after token verification — this phase replaces it with the real thing.

- [x] **1.1 — Document upload panel** — done pre-existing, plus more
  - `frontend/`'s `UploadPanel.jsx` already had this from the original build (`/upload` with `tag` + `session_id`, not the `/demo/session/{id}/upload` shape envisioned here). Also added since: a "Use Sample Documents Instead" button (`/upload-sample`) so visitors can skip uploading entirely.

- [x] **1.2 — Negotiation trigger** — done pre-existing (`/negotiate`, now token-gated and quota-consuming)

- [x] **1.3 — SSE streaming into the chat/ledger view** — done, different UI
  - Not built into the landing page's `Ledger` component — instead `landing/` stays gate-only and hands off to the pre-existing `frontend/` negotiation UI at `/app` (`ChatBubble`/`NegotiateView`/SSE hook), which already had real streaming from the original build.

- [x] **1.4 — Session expiry handling** — done, different mechanism
  - No pre-existing `onExpired()` hook — built fresh as an axios response interceptor: any 401 clears the stored token and redirects to `/?expired=1`, which reopens the landing gate with a notice.

- [x] **1.5 — Session persistence across refresh** — done for the access token (`sessionStorage`, survives refresh on `/`); an in-progress negotiation on `/app` does **not** currently reconnect/resume after a refresh — that part of this item is still open.

---

## Phase 2 — Backend Hardening (Week 1–2, can overlap with Phase 1)

- [ ] **2.1 — Ephemeral session cleanup** — **partially done**
  - `/reset` deletes a session's own OpenSearch chunks on demand (manual, per-session), and this is scoped correctly (verified it can't touch other sessions' data). What's still missing: no automatic TTL/cron — a visitor who uploads and never negotiates or resets leaves their chunks in the index indefinitely. Not urgent at current expected volume, but a real gap for long-term disk hygiene.

- [ ] **2.2 — Cap concurrent demo sessions** — **not done**
  - Token usage caps (3 negotiations per token) bound total cost per token over time, but nothing stops N different valid tokens from all negotiating at once and overloading the t3.small. Worth adding if the post gets real traction.

- [ ] **2.3 — Basic request logging/monitoring** — **not done**
  - No structured outcome logging beyond default uvicorn access logs and `manage_demo_requests.py`/`issue_token.py list` (which show requests/tokens, not negotiation outcomes). Pulling "N negotiations run, X% agreement rate" for the LinkedIn post (Phase 5.2) will need this first.

---

## Phase 3 — Supporting Features (Week 2)

- [x] **3.1 — Replace `mailto:` demo request form with a real backend** — done
  - `POST /demo-request` saves to SQLite (`demo_requests_store.py`); no transactional email, you review via `manage_demo_requests.py list`.

- [x] **3.2 — Manual token issuance flow** — done
  - CLI script (`issue_token.py issue --note "..."`), not an admin endpoint — matches the "simple script is enough" framing here.

- [x] **3.3 — GitHub link on landing page** — done (fixed during this doc pass — footer now actually links to the repo)

---

## Phase 4 — Polish, Analytics, SEO (Week 3)

- [ ] **4.1 — Lightweight analytics** — not done
- [ ] **4.2 — OG image for link previews** — not done
- [ ] **4.3 — System status indicator** — not done
- [x] **4.4 — Final QA pass** — done, ongoing throughout
  - Not one discrete pass — each feature (token gating, sample docs, session isolation, citation fix) was verified end-to-end against the real EC2 deployment as it was built, including a real browser click-through of the gate → upload/sample → negotiate → citation flow. Desktop only; mobile hasn't been checked.

---

## Phase 5 — LinkedIn Post Prep (Final 2–3 days)

This is the phase to pick up next — everything above this line is either done or a known, accepted gap.

- [ ] **5.1 — Capture a demo recording**
  - Screen-record a full negotiation end-to-end (agreement path) — this becomes the post's visual, not just screenshots.
- [ ] **5.2 — Pull real numbers**
  - Phase 2.3/4.1 logging was never built, so there's nothing to pull yet — either skip the numbers claim for this post, or build minimal outcome logging first.
- [ ] **5.3 — Draft the post**
  - Lead with the problem (two-agent negotiation, citation-grounded, isolated corpora) → show the demo clip → close with stack + link.

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
