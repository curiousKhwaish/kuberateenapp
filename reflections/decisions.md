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

### Day 5 — complete (2026-11-03, same session), plus a mid-session spec review

**"Kubera Coin & Goal System" dev spec reviewed, partially applied, mostly deferred.** Khwaish brought a full written spec for a virtual Kubera Coin currency, a Main Goal pot, and parent-verified macro milestones (board-exam-style rewards). This is real scope for Feature 4 (Day 6), not built yet — decided to stick to the planned order (Feature 3 next) rather than jump ahead, even though the team is ahead of schedule. Full pointer and reasoning in `BUILD_PLAN.md`'s Feature 4 section — **re-read that spec with Khwaish before starting Day 6, it was never saved as its own file, only reviewed in-chat.** Two numeric corrections the spec surfaced for already-built Feature 2 were pulled forward and applied immediately, since Feature 2's math was already live:
- Debt threshold: ₹700 → **₹300** (`compute_debt()`).
- Milestone list: flat "₹100 then every ₹500" → **₹100, ₹500, ₹750, ₹1,000, then every ₹500 after** (`MILESTONE_THRESHOLDS` + `all_milestones_upto()`) — Khwaish's own design, front-loading early wins before settling into a steady rhythm.

**Demo seed state locked and wired as a real default, not just a one-off patch.** Ideal starting point for the judge link: wallet ₹3,000, streak Day 6, cushion ₹90 — deliberately chosen so a judge's single minimum ₹10 check-in crosses both the ₹100 milestone and the Day-7 weekly card at once. Initially only patched onto one test `anon_id`'s row; caught that this wouldn't apply to a judge opening the link fresh on their own device, so traced it to the Supabase table's column **defaults** (`kubera_wallets.balance`, `kubera_streaks.*`) and updated the actual default for `cushion_balance` (₹60 → ₹90) so every new visitor gets this state automatically, not just the one browser session tested in. Full reasoning in `BUILD_PLAN.md`'s Feature 2 "Demo problem and its fix" note.

**Feature 3 (parent-approval request) built in full, four days ahead of schedule.** Design decisions and what was built are recorded in `BUILD_PLAN.md`'s Feature 3 section (kept current same session). Notable judgment calls made by Khwaish during the build, each via the Rule 13 "ask, don't decide for her" pattern:
- Threshold (₹1,000) made **parent-editable** rather than hardcoded, despite the extra build cost, since that's closer to the real product.
- **Approve re-checks the wallet balance at decision time**, not at request time — guards against the teen spending the money elsewhere while a request sits pending.
- **Resending an identical request after a decline is deliberately left unblocked** — weighed pressure-the-parent risk against trapping a legitimate "we talked, go ahead" re-ask, chose to trust the teen rather than engineer friction in.
- Parent view **scoped down to balance + requests + badges only** — the first time `view_mode` actually changes what gets fetched/shown, not just a cosmetic label (true since Day 1).
- Teen-side resolution message built as a **timed, auto-dismissing toast (JS, first in this app)** rather than a static message — Khwaish's specific UX request, confirmed worth the one-time cost of introducing JavaScript to an otherwise JS-free codebase.
- **Open backlog item, deliberately not built today:** a reminder nudge for a parent sitting on a pending request too long. Discussed as a genuine judgment call (not overkill), but not yet scoped — revisit after Feature 4 if there's time.

**Two real process incidents worth naming plainly:**
1. **Accidental Rule 6 violation, caught and corrected same turn.** Mid-build, the assistant edited `app.py` directly via a tool instead of showing Khwaish the code to type/paste herself — immediately flagged, reverted precisely (not a blanket `git checkout`, since that would have also discarded her own legitimate in-progress edits), and corrected course for the rest of the session. Worth remembering: this project's "never do it for her" rule applies to direct file edits, not just shell commands.
2. **A full-file paste silently corrupted `app.py`** — nearly every long line got truncated mid-word, with the overflow text lost entirely (confirmed via raw `cat -A`, not a display artifact). Root cause: Khwaish had been manually drag-selecting code blocks to copy them instead of using the block's copy-icon button, and text that scrolled off-screen during the drag never made it into the selection. Fixed by having her use the copy button instead; now standing practice to tell her to use it whenever a long code block is involved. Also established as a new standing preference this session: **give the whole file from `import` every time, even for one-line changes** — she asked for this explicitly, multiple times, after several rounds of smaller "just these two lines" instructions caused confusion about where exactly to paste.

**One moment worth recording honestly for future sessions, not just the code decisions.** During Feature 3's Q3 (judgment call: should a parent get reminded about a stale pending request?), Khwaish's first two answers had the clear structure and phrasing of outside-sourced text (bolded headers, phrases like "lightweight notification mechanic," a fully-formed "48-hour cooldown on a Nudge button" detail with no visible reasoning trail) — a sharp break from how she'd argued every other point all session (including code-mixed Hindi-English, run-on reasoning, explicit "I don't know"s). Named directly, twice, rather than silently recorded — per `docs/PEDAGOGY.md` Rule 5, this log and `understanding.md` only mean anything if they reflect what she actually thinks. Third attempt was shorter and first-person, accepted as her landing position, but flagged in `understanding.md` as genuinely uncertain rather than confirmed. Not treated as an accusation or a disciplinary moment — treated as protecting the one thing this whole project is actually for.

**Visual design deliberately deferred to Days 7-8, confirmed not an oversight.** Khwaish's call: finish and functionally verify all four features first (plain unstyled HTML is enough to confirm logic works), then one focused design pass at the end — rather than styling incrementally per feature. Real risk flagged honestly: if Day 7's real-kid testing surfaces functional bugs, that eats into the same 1.5 days meant for a full visual pass across 5+ pages. Recorded in `BUILD_PLAN.md`'s schedule section too.

**Two specs saved as files this session, previously only in chat scrollback:**
- `research/kubera-coin-spec.md` — the full Kubera Coin & Goal System dev spec (Main Goal pot, parent macro milestones, weekly/milestone card coin payouts). **Not yet reviewed/locked for Feature 4** — session ended before the planned walkthrough happened. Next session should start Feature 4 by going through this spec together, the same way Feature 2 and Feature 3's designs got worked out in detail before building.
- `research/design-spec.md` — the full UI/UX visual design spec ("Kubera, Holographic Light Mode": glassmorphism, color palette, atomic component breakdown, exact on-screen copy). Not applied to any page yet, by design — this is the Day 7-8 reference doc. Note: it visually assumes Feature 4 already exists (references a Kubera Coins card, a macro goal progress bar, a coin history link), so it can't actually be applied until Feature 4 is built.

**Session ended here, 2026-11-03.** Picking up next session: review `research/kubera-coin-spec.md` with Khwaish to lock Feature 4's final design (same process as Features 2/3), then build it. Days 1-5 of the schedule are done, four days ahead.

## 2026-11-04 — Day 6 session (Feature 4 — Kubera Coins, Main Goal, parent macro milestones)

Session opened with a housekeeping note: the Day 5 work (Feature 3, plus the two research spec files) was sitting uncommitted in git from the prior session — flagged to Khwaish, not committed without her asking.

**`research/kubera-coin-spec.md` reviewed line-by-line before any code, same process as Features 2/3.** Full final design written into `BUILD_PLAN.md`'s Feature 4 section (kept current in the same session, as required). Key decisions, in order:

- **Main Goal Target: 3,00,000 Kubera Coins**, Khwaish's own number, not the spec's original 5,00,000. Her reasoning, reached only after two earlier attempts at this same question were flagged and rejected as likely outside-sourced (see below): 5,00,000 would make daily-habit coins (1,000/2,000 per card) feel insignificant, forcing reliance on parent milestones alone; her real landing logic was simpler and more practical than the rejected polished answers — the real product should let a *parent* set this number (mirroring the approval-threshold pattern), and 3,00,000 is just a good round demo number. This real insight only surfaced once the polished, over-precise answers were pushed back on.
- **10th board exam milestone locked at 1,50,000 coins; 12th boards dropped from scope entirely** (her explicit call — "for now no 12th std boards in this goal, pls remove it completely"). The "other" bucket holds flexible, parent-created custom milestones, demo-seeded with 3 examples (half-yearly 25,000 / sports 25,000 / chores 28,000 coins).
- **Weekly card (1,000 coins) and milestone card (2,000 coins) payouts hooked directly into Feature 2's existing trigger logic** via one new `award_coins()` helper — no new triggers invented, coins just ride along on badges that already fire.

**A real, unprompted product catch from Khwaish, mid-build:** after the first version of the milestone system was built (parent-only "Verify" button, no teen input), she stopped and asked why a parent could verify a milestone with zero evidence the teen actually did it — correctly identifying that this made "verify" meaningless. This became the three-state `pending` → `claimed` → `verified` flow (teen submits a mandatory text note to move something from pending to claimed; parent reviews the note before verifying). This is the same "ask one judgment-call question per task" pattern working as intended, except she originated the question herself rather than being prompted for it.

**Evidence-type fight, resolved in favor of text-only — a real compliance catch, not just scope triage:** Khwaish initially wanted four mandatory evidence types (text, photo, screenshot, voice note) for a teen's milestone claim. Pushed back on directly: a real report-card photo/screenshot would almost certainly show the teen's actual name and school, a direct conflict with the competition's hard "no real photos, no real personal info" rule — framed correctly to her as a disqualification risk, not a style preference. Voice notes were separately cut as a genuinely new, unbuilt-before category of engineering (audio capture/storage/playback) not justified this close to the deadline. She pushed back hard twice before agreeing to text-only; final, genuine agreement: "Okay bro now this is what I think... There should only be an option to add a short text. Now I agree with you."

**Toast notifications added to both sides of the claim→verify flow**, directly requested by Khwaish once the core mechanism worked, reusing Feature 3's exact Day 5 pattern (one-time DB-backed "seen" flag + 4-second JS `setTimeout`) rather than inventing a new mechanism — the repeated toast code was pulled into one `toast_html()` helper in the same pass, since it was about to be duplicated a third time.

**A real paste-corruption bug recurred, same root cause as Day 5:** a full-file paste silently turned `and not` into `andnot` on one line, breaking Python's syntax (`"[" was not closed`), caught via a Pylance squiggle in VS Code rather than a runtime crash. Diagnosed the same way as Day 5's version of this bug — asked how the code was copied (drag-select vs. the block's copy-icon button) rather than just handing over the fix, and flagged that a drag-select paste could have corrupted more than the one visible spot, not just the one Python happened to reach first.

**Authenticity concerns recurred multiple times this session, more often than any prior session — worth naming plainly, same as the Day 5 precedent set for exactly this reason.** At least four separate answers across this session had the same tell (bulleted, precisely-summing numeric breakdowns or confident lists of alternatives, landing on a short deflating line like "but honestly I don't wanna do that") on judgment questions: the Main Goal target reasoning (twice — rejected both times, third attempt accepted), the 10th-board-exam reward number, the "other" bucket's example milestones, and Q3 of the end-of-task comprehension check (mandatory text note vs. stronger verification). The clearest tell of the session: in that last one, she re-suggested photo upload as a serious verification option, directly contradicting a decision she herself had made and confirmed only minutes earlier in the same conversation — strong evidence the polished answer wasn't live reasoning, not just a style mismatch. Each time, named directly and asked for the short/rough/in-her-own-words version instead, per the standing practice — never accepted silently. Her real, accepted answers were consistently shorter, more practical, and often revealed a better insight than the rejected polished version (e.g. "parents will set this in the real app, 3 lakh just sounds cool for the demo" vs. the rejected precise 50-70% breakdown). **Worth flagging as a pattern for future sessions, not a one-off:** this recurred specifically on numeric/judgment design questions asked *during* active building, more than on the end-of-task comprehension questions seen in earlier sessions — suggests the mid-build "what number should this be" style of question may be more prone to this than a reflective post-task question.

**Feature 4 built and fully verified working, four days ahead of schedule** — coin-earning hooks, Main Goal display on both views, parent milestone creation, the full claim→verify state machine, both toast notifications. All numbers checked by hand against expectations during testing (3,000 coins from one weekly + one milestone badge; 28,000 after verifying the 25,000-coin half-yearly milestone), not just eyeballed — consistent with `docs/PEDAGOGY.md` Rule 14's expectation for math that could affect judging.

**Open items carried forward, not built this round:** Main Goal target (3,00,000) is hardcoded, not parent-editable, unlike the approval threshold; no "send back"/reject path for a parent who doesn't buy a teen's claim, verify-only for now; photo/screenshot/voice-note evidence ruled out for this competition specifically, not a universal design stance.

**Still uncommitted as of this session:** Day 5's work (Feature 3) and this session's Feature 4 work are both sitting in the working tree, not yet committed to git. Khwaish hasn't asked for a commit yet — flagged, not actioned.
