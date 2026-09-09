# Competitive overview

Research and notes on competing AI medical scribe / healthcare AI platforms, for reference while building MedicDesk.ai. Compiled September 2026 from public vendor sites, review/comparison sites, and analyst write-ups; prices marked "est." are third-party estimates, not vendor-confirmed.

## Ambient documentation / AI medical scribes

| Player | Category | Public positioning | Published price |
|---|---|---|---|
| **Dragon Copilot** (Microsoft/Nuance, formerly DAX Copilot) | Enterprise scribe + dictation | Ambient capture merged with Dragon Medical One dictation under one Microsoft brand (March 2025); built for large health systems, deep EHR ties. | ~$369–$830+/provider/mo (est., not vendor-confirmed) |
| **Abridge** | Enterprise ambient scribe | "Doctors focus on patients while creating better notes, faster." Best in KLAS (Ambient Speech) 2025 and 2026; major health-system deployments (e.g. Kaiser Permanente); patient-facing visit summaries. | Custom / enterprise only |
| **Ambience Healthcare** | Enterprise ambient scribe | Leads with coding accuracy and revenue-cycle lift (~$5/visit net revenue lift claimed); 38+ specialty templates; ships into Epic and athenaOne. | Custom / enterprise only |
| **Suki** | Voice-first clinical assistant | Goes beyond passive listening — spoken commands for chart retrieval, order staging, coding. | ~$299–$399/provider/mo |
| **Nabla** | Ambient scribe, EHR-native | "Brings back the joy of clinical practice" — calm, clinician-first tone; structured notes sync into the EHR. | Free – ~$119/mo |
| **DeepScribe** | Ambient scribe | Enterprise-leaning documentation platform. | ~$400–$750/mo (est.) |
| **Freed** | Self-serve scribe | Cheap, fast self-signup aimed at independent clinicians and small practices. | $39–$119/mo |
| **Heidi Health** | Self-serve scribe | Consumer-friendly, free tier plus paid plans, billed annually. | ~$150/user/mo (annual) |

## Inbound / outbound voice agents

| Player | Category | Public positioning | Published price |
|---|---|---|---|
| **Hippocratic AI** | Clinical-adjacent voice agents | Library of 1,000+ agents with hard guardrails against diagnosing/prescribing; post-discharge follow-up, chronic-care check-ins, screening outreach. | ~$9/agent-hour |
| **Assort Health** | Front-office voice agents | Scheduling, intake, triage, referrals, follow-up across 20+ specialties (ortho, derm, ophtho, OB-GYN, FQHC, peds, primary care, ENT, cardiology, urology); claims 150M+ patient interactions. | Custom — demo only |
| **Infinitus** | Payer-facing enterprise voice AI | "Safety-first" platform automating authorization calls to patients, payers, and providers at Fortune 50 payer scale (Carelon, UnitedHealthcare, Humana, CVS, Cigna, Aetna). | Annual platform + usage fees, custom |

## The gap MedicDesk.ai fills

No competitor currently sells **one branded, transparently-priced desk** that covers both sides of the practice — the note *and* the phone — and scales cleanly from a single clinic to a multi-site chain:

- The enterprise scribes (Dragon Copilot, Abridge, Ambience) are built for health-system procurement cycles, not a clinic that wants to start this month.
- The self-serve scribes (Freed, Heidi) are cheap and fast but stop at documentation — no voice-agent story, no chain-scale offering.
- The voice-agent players (Hippocratic, Assort, Infinitus) don't touch the note, and mostly quote enterprise-only, demo-gated pricing.

MedicDesk.ai's position: **ambient scribe + inbound agent + outbound agent, one vendor, transparent published pricing at the clinic tier, negotiated pricing at the chain tier.** See `brand/BRAND.md` for the full brand strategy and pricing framework built on this research.
