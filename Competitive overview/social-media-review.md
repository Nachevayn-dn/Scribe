# Social Media Presence — Competitor Review

_Last updated: 2026-09-04_

## Method & a hard caveat

LinkedIn, X/Twitter, Instagram, and TikTok are all login-walled or otherwise
unreachable by direct fetch from this session (same network egress
restriction noted in `competitive-landscape.md` — confirmed again here by a
blocked `WebFetch` attempt). Every number below is pulled from **search-engine
snippets that surface follower/employee counts indexed from these pages**,
not a live visit to the profile. That means:

- Counts can be stale (search indexes cache pages, sometimes for weeks).
- A couple of companies (Nabla, Heidi Health) have **name collisions** with
  unrelated brands — flagged inline where it matters.
- Treat every figure here as **directionally right, not exact** — good
  enough to compare scale between competitors, not good enough to quote
  externally without a live re-check.

---

## Follower snapshot

| Company | LinkedIn | X / Twitter | Instagram | TikTok / YouTube | Handle(s) |
|---|---|---|---|---|---|
| Abridge | 14,236 | 4,623 (@AbridgeHQ) | present (@abridgehq), count not surfaced | YouTube channel active — CEO product demos, conference talks; no sub count found | [LinkedIn](https://www.linkedin.com/company/abridgehq) · [X](https://x.com/AbridgeHQ) |
| Nuance / Microsoft Dragon Copilot | 154,134 (parent **Nuance Communications** page — not scribe-specific) | none dedicated to the scribe product | none dedicated | none dedicated | [LinkedIn](https://www.linkedin.com/company/nuance-communications) |
| Suki AI | 38,310 | 1,753 (@SukiHQ) | 489 (@lifeatsuki.ai — reads as an employer-branding/careers account, not product marketing) | none found | [LinkedIn](https://www.linkedin.com/company/sukihq) · [X](https://x.com/sukihq) |
| Nabla | 37,743 | 3,233 (@nabla_ai) | ⚠️ 33K on @nablahealth — **likely a different company** (a same-named women's-health consumer app); do not cite without verifying it's the ambient-scribe Nabla | none found | [LinkedIn](https://www.linkedin.com/company/nablahq) · [X](https://x.com/nabla_ai) |
| Ambience Healthcare | 39,297 | present (@AmbienceAI), count not surfaced | not found | not found | [LinkedIn](https://www.linkedin.com/company/ambiencehealthcare) · [X](https://x.com/AmbienceAI) |
| Freed | **1,396** | not found | not found | referenced in user-generated clinician TikToks, no official brand account found | [LinkedIn](https://www.linkedin.com/company/freed-ai) |
| Heidi Health | 3,001 on the "Heidi Health" page / 32,659 on a separate "Heidi" AU page — likely the same company mid-rebrand from "Heidi Health" → "Heidi"; treat 32,659 as current | not found | 222 (@heidi.health) | active creator-program content (see below); no official brand TikTok found | [LinkedIn](https://www.linkedin.com/company/heidihealth) |
| DeepScribe | not surfaced | present (@DeepScribeAI), count not surfaced | **151, 0 posts** (@deepscribeai — effectively dormant) | none found | [X](https://twitter.com/deepscribeai) · [Instagram](https://www.instagram.com/deepscribeai/) |
| IKS Health | **128,230** | two accounts (@IKSHealth, @joinikshealth — the latter a recruiting handle, 40 followers) | not found | not found | [LinkedIn](https://www.linkedin.com/company/ikshealth) |
| Commure | 10,543 | present, recently migrated handle @commurehealth → @CommureOS, count not surfaced | not found | not found | [LinkedIn](https://www.linkedin.com/company/commure) |
| Sunoh.ai | present, follower count not surfaced (page is login-walled in the search index) | present (@Sunoh_ai), count not surfaced | not found | not found | [X](https://twitter.com/Sunoh_ai) |

---

## What this actually tells us

**Follower count does not track funding or customer scale — and that gap is
the real signal.** Freed has 26,000+ paying clinicians and $20M+ ARR on a
1,396-follower LinkedIn page; Abridge, at $5.3B valuation, sits at ~14K.
Neither company is under-marketing — they're both winning through channels
this snapshot doesn't capture:

- **Freed's growth reads as SEO/content-led, not social-led.** Its site
  carries an unusually large library of comparison and cost-guide content
  ("10 Best AI Medical Scribes," "Cost of AI Medical Scribes," scribe vs.
  scribe pages) clearly built to rank for exactly the searches a shopping
  independent clinician runs. Its actual growth engine looks like organic
  search + peer word-of-mouth inside clinician communities, not LinkedIn.
- **Heidi Health runs a formal clinician-creator program** (2,000+
  follower minimum, targets people already posting clinical/workflow
  content) — a distinct, deliberate influencer-seeding strategy none of
  the other nine companies appear to run. Worth watching directly:
  `heidihealth.com/en-us/creator-program`.
- **Enterprise Tier-1 players (Abridge, Ambience, Nuance) under-index on
  social by design.** Their buyer is a health-system CIO/CMIO reached via
  KLAS reports, conference talks, and direct sales, not a LinkedIn feed —
  their follower counts (14K–39K) are modest relative to valuation because
  social isn't the sales channel.
- **IKS Health's 128K LinkedIn followers is a workforce artifact, not a
  demand-gen signal.** IKS is a large human-in-the-loop scribing/BPO
  operation with a big global employee base; that page count almost
  certainly reflects staff and recruiting reach, not customer engagement.
  Don't read it as "10x the market presence" of the AI-native players.
- **DeepScribe's near-empty Instagram (151 followers, 0 posts) and no
  surfaced LinkedIn count** suggest social isn't a channel they've invested
  in at all — consistent with a company that competes on accuracy
  benchmarks and specialty depth rather than brand reach.
- **Nuance/Dragon Copilot has no scribe-specific brand identity on social**
  — it's a feature line inside Microsoft's healthcare business, riding the
  parent Nuance Communications page (154K followers, but that page predates
  DAX/Dragon Copilot by years and isn't scribe-specific). This is a real
  gap: a buyer researching "AI medical scribe" on social finds Abridge,
  Ambience, Suki, Nabla, and Heidi content — not Microsoft's.

**For MedicDesk.ai:** the practice-level competitors worth watching on
social are Freed and Heidi Health, and Heidi's creator program specifically
is a GTM pattern worth a closer look — recruiting clinicians who already
have an audience to produce first-person "I switched to X" content is
cheap, credible, and hard for enterprise-focused competitors to copy.

---

## Data gaps / next steps

- Every "count not surfaced" cell needs a live check — a Wappalyzer-style
  extension isn't enough here, this needs someone to actually open the X/
  Instagram/TikTok profile (or a social-listening tool: Brandwatch, Sprout
  Social, Rival IQ) since this session cannot reach those domains directly.
- Verify the Nabla Instagram figure before using it anywhere — high
  confidence it's a different, unrelated "Nabla" brand.
- Confirm whether "Heidi Health" and "Heidi" are the same LinkedIn entity
  mid-rebrand (likely) or two separate pages that both need tracking.
- No posting-frequency, engagement-rate, or content-format data is included
  here — this snapshot is follower counts and one qualitative strategy
  observation per company, not a full audit. A deeper pass (posting
  cadence, video vs. static split, employee-advocacy activity) would need
  the same live tool access called out above.
