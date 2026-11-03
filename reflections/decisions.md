# Decisions log

A running log of major decisions (architecture, scope, product) made during a single long working session — per `docs/PEDAGOGY.md`, recorded once that session's conversation has run long (roughly 250k tokens or more), so a long session's real decisions don't get lost. Not a blow-by-blow of every change; just the decisions and why, dated under that session's heading.

All of the planning-phase decisions (repo structure, architecture, the final 4-feature scope, the deployment URL call) are already recorded in `BUILD_PLAN.md`, in their proper permanent home — this file picks up from Day 1 of actual building onward, for decisions made *during* a session rather than settled going in.

## 2026-11-02 — Day 1 session

- **Feature 1 and Feature 2 design redesign** (wallet-as-pay-flow, mocked
  payment-method picker, rule-based payee→category lookup instead of real
  ML, cutting pattern-based auto-categorization, separating the main
  pocket-money wallet from the streak/cushion wallet) was worked out
  during this session but written directly into `BUILD_PLAN.md` — that's
  permanent spec, not logged again here. See that file's Feature 1/2
  sections for the full reasoning.
- **Anonymous ID implemented via Flask's built-in `session` object**
  (signed cookie backed by `app.secret_key`), not a hand-rolled signed
  cookie. Flask's `session` already gives tamper-resistance for free —
  no reason to build that mechanism manually when the framework provides
  it. `app.secret_key` is currently a hardcoded placeholder string in
  `app.py` — fine for local building, needs to become a real random
  secret before deployment (open item, not forgotten).
- **Built the anonymous session cookie before the `kubera_*` Supabase
  tables**, reversing the order listed in `BUILD_PLAN.md`'s Day 1 row
  (which lists scaffold → tables → cookie → toggle). Reasoning: the
  table schema will need a column referencing the anonymous session ID,
  so designing that schema makes more sense once the cookie concept is
  already built and understood, not before it. Schedule and scope are
  unaffected — same four pieces, different order within the day.
- **Reusing Setuh's existing Supabase project credentials** rather than
  creating a new Supabase account/project — matches the architecture
  decision already in `BUILD_PLAN.md` (same project, `kubera_`-prefixed
  tables). Credentials get copied into this repo's own `.env` file
  (already `.gitignore`d), not shared in chat or hardcoded in `app.py`.

### Day 1 — complete (closed out 2026-11-03)

All four Day 1 pieces built and verified working:
1. **`.env` with Supabase credentials** — reused Setuh's `Setuh` project
   (not `setuh-test`, which is paused). Decided to store the service role
   key under the generic name `SUPABASE_KEY` (not
   `SUPABASE_SERVICE_ROLE_KEY`) so `app.py` never needs to change if the
   key type changes later — judgment call made and held firm on by
   Khwaish (reasoning: this app's Flask backend is the only thing reading
   `.env`, never a browser, so the service-role key's full access is
   acceptable here).
2. **`kubera_sessions` table** — created via Supabase SQL editor:
   `anon_id text primary key`, `created_at timestamptz default now()`.
   `anon_id` as primary key (no separate auto-increment id) — Khwaish's
   call, reasoning it's already guaranteed unique.
3. **Libraries installed** — `supabase` and `python-dotenv`,
   `requirements.txt` refreshed via `pip freeze`.
4. **Teen/Parent toggle** — `view_mode` stored in the same `flask.session`
   cookie as `anon_id` (not the database — Khwaish's reasoning: it's
   browser-specific, not something to look up later). Defaults to
   `"teen"`, remembered across visits, changed via `/switch-view/<mode>`
   with a allow-list check (`teen`/`parent` only).

Two real bugs hit and fixed during this session, both good diagnostic
practice: (1) `app.py` referencing `SUPABASE_KEY` while `.env` had it
named `SUPABASE_SERVICE_ROLE_KEY` — `KeyError` at startup, fixed by
renaming the `.env` line to match; (2) the very first "does the insert
work" test showed 0 rows in Supabase despite no error — root cause was a
leftover Day-1-testing session cookie already containing `anon_id`, so
the `if "anon_id" not in session` insert branch never ran. Fixed by
testing in an incognito window instead (same mechanism as Day 1's Q3
about incognito judges, which made the diagnosis click quickly).

### Day 2 — starts here (2026-11-03 session, same day as Day 1 close-out)

Per `BUILD_PLAN.md`'s schedule, Day 2 (4 Nov) is the expense tracker —
Feature 1, answering "where did all my money go?" Design for this feature
is already fully locked in `BUILD_PLAN.md`'s Feature 1 section (wallet
balance, Pay button, mocked payment-picker, payee→category lookup table,
raw ₹ amounts). Next session should start by designing the
`kubera_wallets` / `kubera_expenses` tables (not yet designed) before any
Flask routes get built.

**Resolved — wallet seeding (2026-11-03, next session):** Khwaish's call:
the real-product rule stays ₹0 at creation, requiring a genuine "parent
tops up" action — true to how pocket money actually works, and the
honest design even though it's not what gets built for the demo. But
since every visitor to the live judge link effectively *is* a demo
visitor (no separate real user base behind it), the practical build
decision is to **pre-seed ₹3,000 the moment a new `anon_id` is created**
— same move already made for Feature 2's pre-seeded streak. Held firm
when asked "what would change your mind?" ("No, I would not change my
mind.").

### Day 2 — complete (2026-11-03, same session as Day 1 close-out)

Feature 1 (expense tracker) built fully, one day ahead of schedule.
`kubera_wallets` and `kubera_expenses` tables, the Pay button + mocked
payment picker, payee→category lookup (with honest manual fallback,
"Other" dropped in favor of a believable second unmatched shop name,
"Timely Treasures" — Khwaish's call), the pay-and-deduct logic, a
`/history` page (category totals + full transaction list, totals shown
above the list on purpose — a deliberate "10-second test" ordering
call), manual cash-expense logging (does not touch wallet balance — see
`BUILD_PLAN.md` Feature 1 section), and a tiered concrete-item monthly
summary (also in `BUILD_PLAN.md`). Full reasoning for each lives in
`BUILD_PLAN.md`'s Feature 1 section, kept current in the same session.

**Mid-session product question, resolved:** Khwaish asked whether the
payee→category matching should actually use real AI (an external
API call) instead of the hardcoded lookup dictionary, since a wrong
guess could just be corrected by the user. Talked through the real
tradeoff — an external call adds live demo-reliability risk (network
failure in front of judges) for marginal benefit over the free,
zero-latency dictionary lookup. She chose to keep the rule-based
lookup, deliberately keeping the "(auto-suggested)" label as intentional
signaling of AI-ish ambition to judges without the actual risk — a real,
considered call, not a shortcut. Surfaced in that discussion: there is
currently **no way to edit a logged expense's category after the
fact** — a genuine gap, not yet built, worth revisiting if there's time
before submission.

**Two real bugs hit and fixed this session** (both good diagnostic
practice, detailed in `reflections/understanding.md`'s 2026-11-03
entry): (1) the `amount > 0` check constraint on `kubera_expenses`
silently never applied because the table had already been created by an
earlier, pre-constraint version of the same `create table` statement —
Postgres's "relation already exists" error was initially misread as
harmless when it actually meant the newer blueprint never took effect;
fixed by dropping and recreating the table, then re-verified with a real
insert test. (2) `ModuleNotFoundError: No module named 'supabase'` when
running `python app.py` from a `(base)` conda prompt instead of the
project's `venv` — the library was never missing, just installed into a
different Python environment than the one actually running.

### Day 3 + Day 4 — complete (2026-11-03, same session)

Cushion/streak wallet core, badges, Shields, and the full Refill Mode
debt system all built and verified working, two days ahead of schedule.
Full technical spec lives in `BUILD_PLAN.md`'s Feature 2 section
(kept current in the same session, as required). Key decisions, in
order:

- **Streak resets to 0 on a missed day (unless Shield-protected);
  `cushion_balance` never resets** — Khwaish's call, protecting real
  money/trust while still using the streak as the habit motivator.
- **Full Shield + dual-card gamification system** built as originally
  designed by Khwaish (2-shield cap, 30-day rolling expiry per shield,
  5-day cooldown between uses, weekly cards every 7 streak days,
  milestone cards at ₹100 then every ₹500) — a deliberate, eyes-open
  scope expansion over the original lighter Day 4 plan, made explicitly
  while still ahead of schedule (Rule 13 triage reasoning, not silent
  creep). Milestone card art later simplified to one shared style
  (not per-tier-unique) to control scope further.
- **Refill Mode**, a full state-machine delay-calculator (not just a
  popup message): spending from the cushion sets a Debt Counter (flat
  ₹100 for ₹0–700 withdrawals, scaling above that), freezes the streak
  and `cushion_balance`, and routes daily deposits 100% into the debt
  until cleared — at which point any overpayment becomes real savings
  immediately, and normal streak/cushion growth resumes the *next* day.
  Designed by Khwaish in very precise, example-driven detail across
  several rounds — each example caught and corrected an assumption
  the assistant had made (notably: cushion does NOT grow in parallel
  with debt repayment, deposits are variable-amount in both normal and
  Refill Mode, not flat ₹10).
- **Deposits became variable-amount** (min ₹10, no cap) for both normal
  check-ins and Refill Mode repayments, per Khwaish's original spec —
  required changing the single-click check-in button into a small form,
  and changing milestone-badge detection from exact-equality to
  "crossed the threshold," since a variable deposit can jump past a
  round number without landing on it exactly.

**Real debugging time, worth recording honestly:** a significant chunk
of this session (~30+ messages) went into Khwaish repeatedly reporting
"the cushion isn't updating" when the app was actually working
correctly the whole time — she kept re-triggering the intentional
"one check-in per day" rule without reading the exact confirmation
message or checking the real stored data, which made intermittent
"it works / it doesn't" reports hard to diagnose from chat alone. Only
resolved once she read the raw `kubera_streaks` row directly via Table
Editor. Genuinely useful as a live case of `docs/PEDAGOGY.md` Rule 9
(diagnose before escalating) — logged in `reflections/understanding.md`
as this task's Q3 — but also a real time cost worth naming plainly, not
glossing over, given the 8-day clock.
