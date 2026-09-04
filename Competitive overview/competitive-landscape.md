# Competitive Landscape — AI Medical/Dental Scribes

_Last updated: 2026-09-04_

## Scope & method

This review covers the ambient AI clinical documentation ("AI scribe") market
MedicDesk.ai competes in. It's built entirely from public sources — funding
announcements, press coverage, vendor pricing/blog pages, KLAS research
mentions, and G2/Capterra ratings picked up in search results. Links are
inlined so every number below can be re-checked.

**What's not in here: direct visitor/traffic data.** SimilarWeb (the usual
source for monthly visits, traffic sources, and country breakdowns) is
blocked by this environment's network egress policy, and no SimilarWeb /
Semrush / Ahrefs / Crunchbase Pro connector is available in this Claude
account. See [Data gaps](#data-gaps--getting-real-traffic-numbers) for how to
close this the next time someone runs this review with tool access.

---

## Companies reviewed

| Company | Site | Funding raised | Valuation | Scale | Pricing (per clinician) | Segment focus |
|---|---|---|---|---|---|---|
| **Abridge** | abridge.com | ~$812M total; $300M Series E (Jun 2025) + $316M extension (Apr 2026) | $5.3B | $100M ARR (May 2025); 90+ health systems incl. Kaiser Permanente (24,600 physicians), Mayo Clinic (2,000+), Johns Hopkins, Duke, UPMC | ~$2,500/yr enterprise license (~$250–500+/mo reported) | Large enterprise health systems |
| **Nuance DAX / Microsoft Dragon Copilot** | nuance.com | Acquired by Microsoft for ~$19.7B (2022) | N/A (Microsoft BU) | 550+ health systems; 3M+ ambient conversations/month across 600 orgs | Enterprise licensing, bundled w/ Microsoft healthcare stack | Large hospital systems, Epic/Meditech shops |
| **Suki AI** | suki.ai | $165M total; $70M Series D (Oct 2024) | $500M (Oct 2024) | ~$14.9M revenue; 400+ health systems | ~$300–400/mo reported | Health systems + individual physicians |
| **Nabla** | nabla.com | $120M total; $70M Series C (Jun 2025) | reported ~$5.3B (2026, per one tracker — treat as unverified, see note) | 85,000 clinicians, 130+ orgs (Univ. of Iowa, Denver Health, CVS Health); revenue 5x in H1 2025 | ~$119/mo reported | Individual clinicians, multilingual/telehealth |
| **Ambience Healthcare** | ambiencehealthcare.com | ~$370M total; $243M Series C (Jul 2025) | $1.0–1.25B | $30M ARR (May 2025); Cleveland Clinic (exclusive, 300+ clinicians/20 specialties), UCSF, Memorial Hermann | Enterprise, not published | Large enterprise health systems; broadest product (scribe + coding + workflow automation) |
| **Freed** | getfreed.ai | $37.2M total; $30M Series A (Sequoia) | Not disclosed | 26,000+ clinicians, 1,000+ orgs; >$20M ARR (Apr 2025) | $39–119/mo (unlimited at $99/mo) | **Independent/small practice clinicians (PLG, self-serve)** |
| **Heidi Health** | heidihealth.com | ~$100M total; $65M Series B (Oct 2025, Point72) | $465M | 2M+ clinicians, 116 countries, 2M+ consults/week; 20M+ lifetime interactions | Free tier; paid ~$110–150/mo | **Individual clinicians globally, freemium/PLG, international-first** |
| **DeepScribe** | deepscribe.ai | ~$59M total | Not disclosed | $14.6M revenue (2025), 133 employees; reported 3rd-party accuracy score 98.8 (highest disclosed) | Not disclosed | Specialty-depth ambient scribe |

Sources: [TechCrunch](https://techcrunch.com/2025/06/24/in-just-4-months-ai-medical-scribe-abridge-doubles-valuation-to-5-3b/), [Fierce Healthcare (Abridge)](https://www.fiercehealthcare.com/ai-and-machine-learning/ambient-ai-startup-abridge-scores-300m-series-e-backed-a16z-and-khosla), [ValueAddVC](https://valueaddvc.com/blog/abridge-valuation-2026-5-3b-100m-arr-and-how-the-ai-scribe-beat-nuance-and-ambience), [Healthcare Dive (Nuance/Epic)](https://www.healthcaredive.com/news/nuance-dax-copilot-epic-available-artificial-intelligence-clinical-documentation/705026/), [Microsoft News (Dragon Copilot)](https://news.microsoft.com/source/2025/03/03/microsoft-dragon-copilot-provides-the-healthcare-industrys-first-unified-voice-ai-assistant-that-enables-clinicians-to-streamline-clinical-documentation-surface-information-and-automate-task/), [Fierce Healthcare (Suki)](https://www.fiercehealthcare.com/ai-and-machine-learning/suki-banks-70m-build-out-ai-assistants-doctors-it-inks-more-health-system), [StatNews (Nabla)](https://www.statnews.com/2025/06/17/nabla-raises-70-million-ambient-market-heats-up/), [Nabla blog](https://www.nabla.com/blog/70m-series-c), [Becker's (Ambience)](https://www.beckershospitalreview.com/healthcare-information-technology/ai/ambience-healthcare-reaches-1-25b-valuation/), [Fierce Healthcare (Ambience)](https://www.fiercehealthcare.com/health-tech/ambience-banks-243m-series-c-investors-continue-bet-big-ambient-ai), [VentureBeat (Freed)](https://venturebeat.com/ai/freed-says-20000-clinicians-are-using-its-medical-ai-transcription-scribe-but-competition-is-rising-fast), [Fierce Healthcare (Freed)](https://www.fiercehealthcare.com/health-tech/fierce-healthcare-fundraising-tracker-freed-picks-30m-ai-clinician-assistant), [Heidi Health blog](https://www.heidihealth.com/en-us/blog/heidi-series-b), [MobiHealthNews (Heidi)](https://www.mobihealthnews.com/news/heidi-health-raises-65m-expand-global-reach-its-ai-medical-scribe-platform), [Getlatka (DeepScribe)](https://getlatka.com/companies/deepscribe.ai), [Commure comparison (accuracy scores)](https://www.commure.com/blog-scribe/ai-medical-scribe-alternatives).

> ⚠️ The Nabla $5.3B 2026 valuation figure came from a single aggregator and
> conflicts with its Series C round size — flag as **unverified** until
> corroborated by a primary source (press release or Series D announcement).

---

## Tiered competitive map

**Tier 1 — Enterprise incumbents.** Abridge, Nuance DAX/Dragon Copilot
(Microsoft), Ambience Healthcare. Sell multi-year contracts into large
health systems, deep Epic/EHR integration, KLAS-validated, 7–9 figure ARR.
Not direct day-to-day competitors for an independent-practice buyer, but
they set the credibility/accuracy bar the whole category gets judged
against, and their sales motion increasingly reaches down into
health-system-affiliated small practices.

**Tier 2 — Scaled multi-segment challengers.** Suki, Nabla, DeepScribe.
Sell to both health systems and individual clinicians; multilingual (Nabla)
or specialty-depth (DeepScribe) as the wedge.

**Tier 3 — Practice-level / PLG (closest overlap with MedicDesk.ai).**
Freed, Heidi Health. Self-serve signup, transparent per-seat pricing,
built for solo/small-practice clinicians rather than IT-procurement health
systems — the same buyer MedicDesk.ai is built for. **These two are the
most important to watch closely.**

**Tier 4 — Adjacent / infrastructure (watch list, added by this review).**
See [new competitors](#recommended-additions-to-the-tracked-list) below.

---

## Proposed ranking criteria

A weighted scorecard to rank competitors on an ongoing basis. Weights are a
starting proposal — adjust once the team agrees what matters most for
MedicDesk.ai's positioning.

| # | Criterion | Weight | What it measures | How to source it |
|---|---|---|---|---|
| 1 | **ICP overlap** | 20% | How directly they compete for MedicDesk.ai's actual buyer (independent/small practice, dental included) vs. enterprise health systems | Their own marketing/pricing page, sales motion (self-serve vs. "book a demo") |
| 2 | **Market traction** | 15% | Customers, clinicians, ARR, growth rate | Press releases, funding announcements, Sacra/Latka estimates |
| 3 | **Product breadth** | 15% | Scribe-only vs. full platform (coding, billing, follow-up, EHR write-back, agentic actions) | Product/feature pages |
| 4 | **Funding & runway** | 10% | Total raised, valuation, recency of last round | Crunchbase/PitchBook/press |
| 5 | **Customer sentiment** | 10% | G2/Capterra rating and review volume, KLAS score | G2, Capterra, KLAS Research |
| 6 | **Pricing accessibility** | 10% | Transparent public pricing, price point relative to ours, free tier availability | Vendor pricing page |
| 7 | **EHR/integration depth** | 10% | Number & depth of EHR integrations (Epic, athena, DrChrono, dental PMS) | Integration/partner pages |
| 8 | **Digital demand gen** | 5% | Organic search visibility, monthly site visits, growth trend | SimilarWeb/Semrush (see gap below) |
| 9 | **International/multilingual reach** | 5% | Language support, country coverage | Vendor site |

**Composite score** = Σ(criterion score 1–10 × weight). Recompute quarterly
as the tracked-list document is refreshed.

I did **not** fabricate numeric 1–10 scores against this scorecard in this
pass — several criteria (G2 rating, EHR integration count) don't have
reliable public data for every company yet, and a false-precision number is
worse than none. The [data table above](#companies-reviewed) has what's
verifiable today; use it to fill in the scorecard as data is confirmed.

---

## Recommended additions to the tracked list

Found while researching the above — proposing these join the tracked list:

- **DeepScribe** (deepscribe.ai) — already profiled above; specialty-depth
  positioning and the highest disclosed third-party accuracy score (98.8)
  in one comparison. $59M raised, $14.6M revenue (2025).
- **IKS Health** — won Best in KLAS 2026 for Virtual Scribing Services
  (2nd year running), but on a **human-in-the-loop** model rather than
  pure AI. Worth tracking as the benchmark for the "AI + human review"
  alternative some practices still prefer over pure-AI output.
- **Commure Scribe** — bundled inside Commure's broader health-system
  operations platform (not sold standalone); reported 93.3 accuracy score.
  Relevant because it shows incumbents packaging scribing as a feature of
  a bigger suite rather than a standalone product — a platform-bundling
  threat pattern worth watching.
- **Sunoh.ai** — ambient scribe integrated directly into practice-management/EHR
  platforms (came up repeatedly in 2026 "best AI scribe" roundups
  alongside Freed/Heidi); positioning looks closer to MedicDesk.ai's
  practice-level segment than the enterprise names. Needs its own funding/
  traction research pass — not enough verified data to profile fully here.
- **Big-tech infrastructure entrants (watch category, not yet a named
  competitor)** — Amazon HealthScribe (AWS API primitive for ambient
  clinical notes) lets any smaller vendor bootstrap a scribe without
  building the AI themselves. Worth a standing watch item: if a wave of
  thin wrappers on top of AWS/Google infra shows up targeting small
  practices, that changes the competitive dynamics fast.

These are added to `tracked-competitors.md` with a "needs research" status
where the data isn't solid yet.

---

## Data gaps & getting real traffic numbers

Visitor/traffic tracking (monthly visits, traffic sources, country split,
engagement) could **not** be pulled in this session:

- `similarweb.com` is blocked by this environment's network egress policy.
- No SimilarWeb, Semrush, Ahrefs, or Crunchbase Pro connector is currently
  enabled on this Claude account (checked via the connector list).

**To close this gap:** either (a) connect one of those tools/connectors and
re-run this review, or (b) pull the numbers manually from a SimilarWeb or
Semrush free-tier lookup for each domain in the table above and paste them
into `tracked-competitors.md`. Free-tier SimilarWeb typically gives monthly
visits, top traffic source (search/direct/social/referral), and top 5
countries — enough to fill criterion #8 above.
