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

**Paused 2026-11-03 mid-task, resume point:** about to design the
`kubera_wallets` table. Open judgment call posed to Khwaish, answer
pending (she wants to think on it overnight): should the wallet's starting
balance be seeded **automatically** the moment a new `anon_id`/
`kubera_sessions` row is created (same moment, so every new visitor
instantly has demo money), or should it start at ₹0 and require a
separate "parent tops up" action before the teen can spend anything? Ask
her for her answer first thing next session before writing the table SQL
— do not pick for her.
