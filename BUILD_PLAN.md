# KuberaTeenApp — Build Plan

**Its own dedicated repo, not part of Setuh.** Built for the Dezerv Kids
Hackathon — a teen financial-literacy web app. Different product,
different audience, different rules (it legally *can't* touch real money
or real personal data, which is a different category of problem than
anything Setuh solves). Started as a sibling folder inside the Setuh repo
during planning, then moved out to its own git repo on 2026-11-03 so the
whole commit history is unambiguously post-28-Oct, with nothing to explain
to a judge about an older, unrelated history sitting next to it. Own Flask
app, own templates/static, own Vercel deployment. The only thing it still
shares with Setuh is the Supabase project (new, clearly prefixed tables —
see Architecture below).

If anything here ever needs to change, update this file in the same
session as the decision — this is the one place future sessions (starting
with tomorrow's) should be able to read cold and have full context.

---

## The competition — Dezerv Kids Hackathon (hackathon.dezerv.in)

**Hard constraints:**
- Build must start on/after 28 Oct 2026 — genuinely fresh code, no reusing
  pre-existing projects.
- **Submission locks 10 Nov 2026, 11:59 PM IST.** Don't change the
  submitted link after that.
- The live link must keep working until 14 Nov 2026 (top 3 present live
  that day, from home, with a parent present).
- **No real money** anywhere in the app — made-up amounts only.
- **No real personal info** — no real names, phone numbers, addresses,
  schools, or photos.
- **No ads, no payment** — the app is free to use.
- **Opens from a link, no download, no sign-in** — a judge must be able to
  open it and use it immediately, no login wall.
- Must be the team's own idea/design/decisions — tutorials, templates, and
  no-code/AI tools are explicitly allowed as long as the thinking is
  theirs.
- Ages 8–18, teams of up to 3 in the same age group, judged against that
  age group (Juniors vs. Seniors separately). One entry per
  person/team. Judges' decision is final.
- **Admin step, separate from the build:** a parent must register on
  hackathon.dezerv.in (gives consent, stays in the loop). Parent gets
  emailed if the team places top 10 (email sent 12 Nov); top 3 also get a
  short tech-check call 13 Nov. *(Status as of this doc: unconfirmed
  whether this registration has been done yet — check first thing.)*

**The app must answer all 3 of these in one app, for both Juniors and
Seniors:**
1. **"Where did all my money go?"** — help them see what they spent and
   what's left. Concretely (e.g. ₹500 shown as 25 samosas), not as a bare
   number.
2. **"How do I save for that cycle?"** — set a goal, watch themselves get
   closer. E.g. "this ice cream pushes your cycle back 3 days."
3. **"Can I buy this, Mum?"** — help them decide about money together with
   their parent. E.g. a "can I buy this?" request a parent can approve.

Plus an optional **"out-of-the-box" bonus**: any fresh idea that helps
kids with money — a game, a savings challenge, something nobody's built.

**Scoring, out of 100:**
| Criterion | Points | Judged on |
|---|---|---|
| Answers the questions | 40 | Does it really help a kid see, save, and decide together? |
| Easy to use | 25 | Can a new kid figure it out in 10 seconds? |
| Creative | 20 | Have the judges seen this idea before? |
| Money smarts | 15 | Does it build a real money habit (saving, spending wisely)? |

Top 10 win. Judges look at whatever is live at the 10 Nov deadline.

---

## Research — already done, not a thing to redo

**Primary sources live in `research/`** — the competition rules PDF
(`Dezerv Kids Competition.pdf`) and the actual research report
(`Dezerv Hackathon Project Proposal & Research Report.pdf`) this section
summarizes. The summary below is what sessions should work from day to
day; go back to the PDFs themselves if a detail here ever seems
incomplete or you need something this summary left out.

Three insights came out of real interviews with teens (names anonymized
in this doc's quotes — same names appear in the original research, not
real identities for the purposes of this project):

**Insight 1 — Passive spending, zero financial literacy.** Teens don't
track spend or budget unless prompted. Fixed-allowance teens (₹2,000–5,000/
month) often run out in 10–15 days, mostly on food, tuck shop, and local
auto commute — all unmonitored routine spend, not one big purchase.

**Insight 2 — Social "treat" crises, no emergency reserve.** An impromptu
birthday treat or outing catches teens with their allowance already spent.
They end up asking parents for extra money or awkwardly negotiating a bill
split, because there's no dedicated buffer for exactly this situation.

**Insight 3 — Two-tiered goal motivation.** Teens treat small self-funded
goals (shoes, stationery) completely differently from big aspirational
ones (MacBook, bike, CLAT/IIM Indore admission). For the big ones, tying
the reward to a mutually agreed academic/personal milestone with a parent
measurably doubles motivation — a shared checklist a parent can verify
against keeps it honest and keeps them going.

**ICP:** 15–20 year olds, financially dependent on parents. Either a fixed
monthly allowance (₹2,000–5,000) or on-demand money as needs arise. Mostly
digital wallets/UPI linked to a parent's account (FamPay, GPay, Amazon
Pay), plus cash for small local spends. High-frequency spend categories:
food/tuck shop, auto/travel, shopping, hobbies. Comfortable with automated
approval thresholds (e.g. parent approval only needed above ₹500–1,000) —
the friction they resent is asking permission for *small* everyday stuff,
not oversight in general.

---

## Architecture decisions

**Location:** its own repo (`~/KhwaishProjects/kuberateenapp`), own Flask
app (own `app.py`/package, own `requirements.txt`, own templates/static)
— not blueprints inside Setuh's `app/` package. This app can't share
Setuh's auth (real email/password via Supabase Auth would collect info the
competition rules forbid) anyway. Own Vercel project, own deployment — see
Deployment & URLs below for exactly where it's hosted.

**Database:** same Supabase project as Setuh (saves a setup step under
deadline pressure), but entirely new tables, clearly prefixed `kubera_`,
so it's logically separate from `tenants`/`bookings`/etc. *(If this starts
to feel like the wrong call once we're building — e.g. it makes Setuh's
own schema harder to reason about — revisit and split to a dedicated
Supabase project; it's a cheap change early, more annoying later.)*

**No real sign-in, no real accounts:** when the link opens, the app
silently gives the browser a random anonymous ID via a signed cookie (same
trick `app/tenant.py` already uses for tenant preview links) — no email,
no password, no real name, ever. A **"Teen view / Parent view" toggle**
switches between the two sides of the app **in the same browser session**.
This isn't a shortcut — it's actually the better match for the rules: the
FAQ says the top 3 present live "from home, with a parent present," i.e.
parent and teen looking at one screen together, not separate logins on
separate devices. No pairing codes, no accounts, nothing to "sign in" to
— the link just opens and works.

---

## Deployment & URLs

**Decided 2026-11-03.** Two separate pages exist for two separate
purposes — don't conflate them:

1. **The judges' link (the actual product).** KuberaTeenApp deploys to its
   own Vercel project and ships to judges on its **free `.vercel.app`
   URL** (e.g. `kuberateenapp.vercel.app`) — not a `setuh.co` subdomain.
   Reasons:
   - **Shared-infra risk.** `*.setuh.co` is a wildcard that already routes
     every subdomain through Setuh's own `app/tenant.py` tenant lookup,
     into Setuh's own Flask app. Pointing one specific subdomain at a
     completely different app (this one) means custom DNS overrides on
     Setuh's live production domain — real risk of breaking Setuh's actual
     tenant routing, not worth taking with days on the clock.
   - **Keeps the "independent business" framing consistent.** This project
     already moved to its own repo specifically so its history reads as
     unambiguously its own. Hosting the submitted product on Setuh's
     commercial domain would undo that — independent repo, dependent
     domain sends a mixed signal about whose project this actually is.
   - A `.vercel.app` URL fully satisfies the rules as written: "opens from
     a link in a browser, no download, no sign-in." Nothing about a custom
     domain is required.
   - A real custom domain (e.g. `kuberateen.app`) is a fine later
     upgrade if there's time and appetite for it — optional polish, never
     something to let block the 10 Nov submission.

2. **`kuberaapp.setuh.co` (the explainer page, built later, no deadline
   pressure).** After the competition, KuberaTeenApp also gets a normal
   Setuh tenant page — same `/newclient`-style process as any other
   business (research → design system → build) — that tells the story
   ("what we built for this competition, what the app is about") with one
   primary button: **"Go have a look at the app"**, linking out to
   wherever the real product is deployed (the `.vercel.app` URL above, or
   its eventual custom domain). This page is presentation-only, not the
   product — same split Setuh already draws for every tenant between the
   presentation layer and the actual thing being presented.

---

## Final feature list — 4 features, each mapped to a required question

Originally scoped as 5 separate features from the research doc's "Top 5
App Features" list. Collapsed to 4 during planning (2026-11-02) once it
became clear two of them were really one mechanic wearing two names — see
reasoning below. This is tighter, more original, and buys back some of the
8-day schedule.

### 1. Expense tracker — answers Q1 ("Where did all my money go?")

**Design locked 2026-11-02, after a long judgment-call discussion (worth
reading if this section ever needs revisiting) — superseding the original
"25 samosas" framing below.**

- **A main pocket-money wallet balance**, separate from Feature 2's
  streak/cushion pot — this is the "what's left" number. Parent tops it up
  from their view; entirely simulated (just a number in the database), no
  real bank or money, same as everywhere else in this app.
- **Primary flow (what a judge sees/does):** wallet is pre-seeded as if the
  parent already transferred money in. Teen taps a Kubera-branded **Pay**
  button, enters the amount, and sees a **mocked GPay/FamPay/Amazon-Pay-
  style picker screen** (required for the demo, not a cut-if-short
  flourish — her call) with a short list of **preset payees with realistic
  shop names** (e.g. "Bombay Stationery," "Sriram Vadewala," "Ola Cabs").
  Picking a payee **auto-suggests the category** via a lookup table (payee
  → category) — this is the "AI categorization," deliberately rule-based
  lookup rather than real ML, since real pattern-detection ML was
  considered and explicitly cut for scope (see below). If no payee matches
  or the teen picks "other," they select a category manually from a
  dropdown (snacks, movies, transport, bills, gifts, shopping, grocery) or
  type a custom one. In the demo, be upfront that only some sample
  transactions (e.g. 2 of 5) auto-match by payee; the rest are manual —
  that's honest, not a bug.
- **Secondary flow (fallback, lower priority, build only if time allows):**
  a cash spend that never went through the wallet gets logged after the
  fact — manually, or caught by a nightly nudge ("did you spend anything
  today? how much, what for?"). Manual logging is NOT the primary demo
  path; paying from the wallet already *is* the log, in one tap.
  **Built 2026-11-03:** a manually-logged cash expense is written to
  `kubera_expenses` with `payee = null` (displayed as "(cash)" wherever
  shown) but deliberately does **not** subtract from `kubera_wallets.
  balance` — Khwaish's call: the wallet balance tracks digital/app money
  only, cash is a separate real-world pool the app was never holding, so
  logging a cash spend is pure record-keeping for the "where did it go"
  picture, not a balance-affecting transaction.
- **Amount shown as raw ₹ at the moment of logging** — not a per-entry
  "25 samosas" conversion (killed because not everyone eats samosas and
  samosa prices vary, so the conversion is a tax on the reader, not a
  help). An **optional monthly summary** may still use a concrete-unit
  comparison ("this month = 2 movie tickets") since that's one
  calculation a month, not one per entry — monthly rather than weekly,
  matching the ICP's actual pocket-money cycle (₹2,000–5,000/**month**).
  **Built 2026-11-03:** the monthly summary picks from a small **tiered**
  list of reference items instead of one fixed item, so the comparison
  always reads naturally at whatever scale the monthly total actually is
  — waffle (₹150), movie ticket (₹350), pair of wireless headphones
  (₹2,000), foldable magnetic charger (₹3,500), pair of PUMA sneakers
  (₹6,000, sized to the ₹2,000–5,000 pocket-money ICP range, not an
  unrealistic big-ticket item like a phone). Picks the most expensive
  tier the total still clears, then **rounds to a whole number** —
  Khwaish's explicit call, no decimals ("11.1 movie tickets" reads as a
  bug, not a feature).
- **Category privacy by design:** categories stay broad on purpose (e.g.
  "gifts," not who it's for) — parents get real transparency on spending
  *patterns*, not surveillance on specifics. This keeps teens willing to
  log honestly instead of avoiding the app.
- **Explicitly cut for scope:** true pattern-based auto-categorization
  (inferring e.g. "this is a commute/travel spend" from recurring amount +
  time-of-day + period, across different payees) was considered and
  deliberately dropped — real build cost for Day 1 of 8 with zero code
  written yet, versus the lookup-table version above which gets most of
  the "wow, this feels smart" effect for a fraction of the cost. Only
  revisit as a stretch goal if Days 1–5 go smoothly.

### 2. Short-term goal = Cushion/Streak Wallet — answers Q2 (short-term tier)
**Clarified 2026-11-02: this cushion/streak pot is a separate balance from
Feature 1's main pocket-money wallet** — the daily ₹10 streak-save builds
*this* pot specifically; everyday tuck-shop/auto/shopping spends come out
of the main wallet and don't touch it. Keeping them separate was a
deliberate call — mixing them would mean an ordinary samosa purchase eats
into the emergency cushion too, defeating the point of having one.

**This is the merged feature** — originally planned as two separate things
(a "Goal Delay Calculator" and a "Peer-Pressure Emergency Cushion vault").
They're one mechanic: the cushion *is* the short-term goal's savings pot,
not a separate fund.

- Teen does a daily check-in, saves a small fixed amount (e.g. ₹10) →
  builds a **streak** → the streak balance *is* the Cushion Wallet.
- When a social/emergency spend comes up (Insight 2), they spend from the
  Cushion Wallet instead of asking a parent or raiding other savings.
- Spending from the wallet **inserts refill days** before streak-saving
  resumes toward the next short-term goal — that's what the delay
  calculator is showing ("this pushes your goal back N days"). It's a
  real recalculation off the same pot, not just flavor text.
- **Gamification — expanded design, locked 2026-11-03 (Day 3 session):**
  a collector-card layer on top of the streak, giving teens something to
  chase and show off. Originally scoped as simple day-count badges (day
  7, 15, 21...); Khwaish designed a considerably fuller system this
  session, built the same day it was designed, consciously accepting the
  schedule cost (see Day-by-day schedule note below).
  - **Streak vs. money are tracked separately, and behave differently on
    a miss.** `cushion_balance` (real ₹ saved) **never resets** — missing
    a day doesn't cost the teen any money already saved, protecting real
    progress and trust in the app. `streak_count` **does reset to 0** on
    a missed day, *unless* a Shield protects it (below) — the streak is
    the motivator, the money is the thing that actually matters.
  - **Cushion balance accumulates indefinitely, month to month** — no
    monthly reset. ₹10/day saved and not spent on an emergency just
    keeps compounding; this was already true of the basic design, no
    extra code needed for it.
  - **Dual-track cards:**
    - *Weekly cards* — ongoing, for streak consistency (every 7 days of
      streak: day 7, 14, 21, ...).
    - *Milestone cards* — for cumulative cushion savings hitting ₹100,
      then every multiple of ₹500 after that (₹500, ₹1,000, ₹1,500,
      ₹2,000, ...). **Simplified 2026-11-03:** all milestone cards share
      one visual style (distinct from the weekly cards' style), no
      per-tier special-casing — keeps the card art scope flat regardless
      of how high savings climb.
  - **Shield system (habit insurance), with guardrails:**
    - Earned automatically on completing a 7-day streak (i.e. every time
      a weekly card unlocks) — **only if** the teen is currently holding
      fewer than the inventory cap.
    - **Inventory cap: 2 shields held at once**, max — a new one isn't
      granted past the cap.
    - **Expiry: 30 days, rolling, from the exact date each shield was
      earned** — tracked per-shield, not just as a count, since two held
      shields can have different earn dates and therefore different
      expiry dates.
    - **Usage rule: a shield can only be used once every 5+ days of
      normal saving** — i.e. no two shields used back-to-back; there
      must be a real gap of at least 5 days between any two shield uses.
    - When a streak would otherwise reset (a missed day, no check-in),
      an eligible shield is consumed automatically instead: the streak
      is preserved, that day's ₹10 just doesn't get added, and the
      5-day usage cooldown starts from that point.
  - **Compliance note for when we actually build the cards:** card art
    shows a nickname/avatar only, never a real name or photo — keeps
    sharing compliant with the "no real personal info" rule.
  - **Refill Mode (the delay calculator, built as a real mechanic, not
    just a popup) — locked 2026-11-03, built and verified same session:**
    - Deposits are **variable amounts** (min ₹10, no upper limit) in
      *both* normal check-ins and Refill Mode repayments — not a flat
      ₹10. This changed the check-in button into a small form.
    - Milestone badges trigger on **crossing** a threshold, not exact
      equality — required once deposits became variable, since a jump
      could skip straight over a threshold. **Revised 2026-11-03** (after
      reviewing a "Kubera Coin & Goal System" dev spec that also proposed
      a new, separate virtual-currency layer — that part deferred to
      Feature 4 on Day 6, but these two number changes were pulled
      forward and applied the same session since they correct Feature 2
      itself): the threshold list is no longer an even ₹500 spacing from
      the start. It's now **₹100, ₹500, ₹750, ₹1,000, then every ₹500
      after that** (₹1,500, ₹2,000, ₹2,500, ...) — front-loaded early
      wins for a new saver, settling into a steady rhythm once the pot
      is bigger. Implemented as `MILESTONE_THRESHOLDS = [100, 500, 750,
      1000]` plus a ₹500 step after 1000, in `all_milestones_upto()` /
      `crossed_milestones()` in `app.py`.
    - **Spending from the cushion:** shows a "Withdrawing ₹X pushes your
      goal back Y days" confirmation screen before acting. On confirm,
      `cushion_balance` drops immediately by the withdrawn amount (the
      money is really gone), and a **Debt Counter** is set: flat ₹100
      for any withdrawal ₹0–₹300, then **+₹50 per additional ₹200**
      above ₹300 (`compute_debt()` in `app.py`). **Revised 2026-11-03**
      from the original ₹700 threshold — same dev-spec review as above;
      this number was corrected in place rather than deferred, since
      Feature 2's debt math is already live. Days shown in the popup =
      debt ÷ ₹10.
    - **While debt > 0 (Refill Mode):** the streak freezes (doesn't
      reset to 0 — spending isn't the same as missing a day). Each
      check-in's deposit goes **100% toward the debt**, and
      `cushion_balance` stays **frozen** at the post-withdrawal amount —
      it does not grow in parallel with debt repayment.
    - **Overpaying the debt:** if a deposit exceeds the remaining debt,
      the debt clears to exactly ₹0 and the leftover goes straight into
      `cushion_balance` as real savings in that same action (and can
      trigger a milestone badge) — no money is lost.
    - **Resuming:** the check-in that clears the debt to ₹0 is still
      just a debt-clearing action — streak doesn't move that same day.
      The *next* day's check-in is the first one that resumes normal
      streak-building and cushion growth, continuing from the frozen
      streak number (not restarting it).
    - **Can't stack withdrawals:** a second emergency spend is blocked
      with a message while `debt_remaining > 0` — pay off the current
      one first.
    - **One check-in (of any kind — normal, debt repayment, or the
      check-in that clears debt) per calendar day**, enforced by a
      single `last_checkin` date field — this is intentional and uniform
      across all three cases, not a special case per mode.
- **Demo problem and its fix:** a judge won't wait real days to see a
  streak build. The live demo link opens with a **pre-seeded streak
  already in progress** so the full loop — check-in, badges, cushion
  spend, delay calc — is visible within the "10-second test."
  **Ideal starting point, locked 2026-11-03:** wallet balance ₹3,000,
  streak Day 6, cushion ₹90. Deliberate numbers, not arbitrary — a judge
  doing the **minimum ₹10 check-in** pushes cushion from ₹90 to exactly
  ₹100 *and* streak from Day 6 to Day 7, so **one single check-in fires
  both a milestone card (₹100 crossing) and a weekly card (Day 7) at
  once** — the richest possible first impression from the smallest
  possible judge action. **Kubera Coins are deliberately not part of
  this seed** — reviewed 2026-11-03 (see Feature 4 note above), decided
  to demo the weekly/milestone cards as already built and explain
  coins/Main Goal as coming in a later build session, rather than pull
  Feature 4 forward ahead of Feature 3.

### 3. Parent-approval request — answers Q3 ("Can I buy this, Mum?")
Purchase above a parent-set threshold (per the ICP, ~₹500–1,000) triggers
a real-time approval request the parent can approve/decline from their
view. Below the threshold, it just logs — no friction for everyday small
spends, which is exactly the friction teens said they resent (ICP, "zero
approval friction" point).

**Built 2026-11-03, four days ahead of schedule:**
- **Threshold is parent-editable** (a deliberate call over hardcoding —
  `kubera_wallets.approval_threshold`, defaults to ₹1,000), not baked into
  the code. `/pay/<payee>` checks the amount against it before touching
  the wallet or logging anything — ordering matters here specifically so
  a decline is real (money never moved) rather than theater, which is the
  actual reason the parent's role stays meaningful.
- Over-threshold spends write a row to `kubera_approval_requests`
  (`status`: `pending`/`approved`/`declined`) instead of completing
  immediately. Parent view (`/parent/requests`) lists pending ones as the
  teen's own quoted question ("Can I spend ₹X at Y?") next to the current
  wallet balance, plus Approved/Declined history below.
- **Approve** re-checks the wallet balance at decision time (not the
  balance from when the request was made) before logging the expense and
  deducting — guards against the teen having spent the money elsewhere
  while the request sat pending.
- **Decline** only flips the status; no money moves. Resending the exact
  same request after a decline is **deliberately unblocked** — Khwaish's
  call after weighing both sides (spam-pressure risk vs. trapping a
  legitimate "we talked, go ahead" re-ask): trust a 15–20 year old to be
  mindful about when to re-ask, don't engineer friction into it.
- **Parent view scoped down** to only wallet balance, pending/approved/
  declined requests, and badges earned — `view_mode` now actually changes
  what the home page fetches and shows, not just a cosmetic label like it
  was through Day 1–4.
- **Teen-side status, two different mechanisms doing two different jobs:**
  a persistent ⏳ banner for still-pending requests (re-reads `status`
  fresh every page load, no memory needed — it's always just telling the
  truth about right now), and a one-time ✅/❌ toast for newly-resolved
  ones (a `seen_by_teen` boolean flips `true` the instant it's shown, so
  it never reappears — this is a one-time *event*, not a live state, so it
  needs its own memory). The toast also auto-hides after ~4 seconds via a
  small inline `<script>` — the first JavaScript anywhere in this app.
- **Open backlog item, not built:** a reminder nudge for a parent sitting
  on a pending request too long (mirroring Feature 4's planned milestone
  reminders). Discussed and judged worth having, not overkill — not yet
  scoped or built; revisit if there's time after Feature 4.

### 4. Long-term goal = Milestone Contract — the aspirational tier + bonus
Big-ticket goals (MacBook, bike, CLAT/IIM Indore admission) are **not**
funded by the daily streak — per Insight 3, teens don't realistically
self-fund these from pocket money. Instead: teen + parent set a milestone
together (an academic or behavioral target), progress is shown with
nudge-style reminders ("you're falling behind on X — don't lose this
goal"), and the parent verifies when the milestone is actually hit. No
delay-calculator math here — this is accountability, not a cash pot. This
is also the feature most likely to read as the "out-of-the-box" bonus to
judges, since a parent-verified achievement contract isn't something a
plain expense tracker would have.

**Pending spec, reviewed 2026-11-03, deferred to Day 6 build:** Khwaish
brought a "Kubera Coin & Goal System" dev spec this session — a virtual
coin currency (separate from real ₹) that fills a Main Goal progress bar,
fed by (a) Feature 2's weekly-streak and savings-milestone cards each
paying out a fixed coin amount, and (b) parent-verified macro milestones
(e.g. board-exam results) paying out a large one-time coin amount. This is
real scope for Feature 4, not yet built — decided to stick to the planned
Day 5/Day 6 order (Feature 3 next) rather than jump ahead, since we're
ahead of schedule but Feature 3 is still next in line. Two numeric
corrections this spec surfaced for already-built Feature 2 (debt
threshold, milestone list) were pulled forward and applied immediately —
see Feature 2 section above. Re-read the full spec with Khwaish before
starting Day 6 — it wasn't saved verbatim anywhere else.

**Built 2026-11-04 (Day 6), design locked and reviewed line-by-line with
Khwaish before any code was written — same process as Features 2/3:**

- **Two fully separate tracks, confirmed:** real ₹ cushion savings
  (`kubera_streaks`) and virtual Kubera Coins (`kubera_coins`) never mix.
  Deliberately tested with a concrete scenario — a cushion withdrawal must
  never move the Main Goal progress bar, since an emergency withdrawal is
  a normal, intentional use of the cushion (established back on Day 3-4),
  not something that should also punish an unrelated goal.
- **Main Goal Target: 3,00,000 Kubera Coins**, hardcoded for this build.
  Khwaish's own insight during design: in a "real" version this should be
  parent-editable (same pattern as the approval threshold), but for the
  judge-facing demo a fixed, good-sounding number is simpler and there's
  no second real user to disagree with it. Parent-editable goal target is
  an explicit open item below, not built.
- **10th board exam milestone: 1,50,000 coins** (fixed macro milestone).
  **12th boards: explicitly out of scope**, dropped per Khwaish's call —
  not deferred quietly, a real decision not to build it this round.
- **"Other" bucket — flexible, parent-created custom milestones**, no
  fixed total enforced. Demo-seeded with 3 examples on every new
  `anon_id` (half-yearly/pre-board 90%+: 25,000 coins; sports/competition
  win: 25,000 coins; consistent chores/reading goals: 28,000 coins) plus
  the 10th-boards one — same "real mechanism, pre-seeded for the demo"
  pattern as the wallet balance and streak day. A parent can add further
  custom milestones live via a small form.
- **Weekly streak card: 1,000 coins. Savings milestone card: 2,000
  coins.** Both values matched the original spec, no change — hooked
  directly into the *existing* Feature 2 trigger logic (`checkin()`'s
  weekly-badge block, `award_milestones()`) via one new `award_coins()`
  helper, rather than new trigger logic.
- **Milestone claim→verify flow, a real judgment call Khwaish raised
  unprompted mid-build:** the original design let a parent "Verify" a
  milestone with zero input from the teen — she caught that this made
  "verify" meaningless, since a parent could click it with no evidence
  anything happened. Resolved into a three-state flow: `pending`
  (parent-set, not yet claimed) → `claimed` (teen submits a mandatory
  short text note, e.g. "scored 92% in pre-boards") → `verified` (parent
  reviews the note and confirms; coins awarded on this transition). **No
  reject/"send back" option built this round** — a parent can only
  Verify a claim, not decline it; flagged as a real, deliberate scope
  cut, not an oversight, open item below.
- **Evidence type: text note only — photo, screenshot, and voice note
  were explicitly considered and dropped.** Real reason, not just a
  time-saver: a report-card screenshot or photo would very likely show
  the teen's real name and school, directly conflicting with the
  competition's hard "no real photos, no real personal info" rule — a
  disqualification-shaped risk, not a style question. Voice notes were
  separately cut for being a genuinely new category of engineering
  (audio capture/storage/playback) not justified by the time left.
  Khwaish pushed hard for all four evidence types before landing here —
  see `reflections/understanding.md`'s 2026-11-04 entry for the full
  back-and-forth, including a judgment-call answer that had to be
  challenged twice before she gave her real reasoning (text is enough
  specifically *because* stronger verification is ruled out by the
  competition's rules, not because she didn't want it in principle).
- **Toast notifications on both sides**, same mechanism as Feature 3's
  Day 5 approval toast (`seen_by_teen`-style one-time flag + 4-second JS
  `setTimeout`, now generalized into a small `toast_html()` helper since
  it was about to be copy-pasted a third time): parent gets a one-time
  toast when a teen claims a milestone (`kubera_milestones.
  seen_by_parent`), teen gets a one-time toast when a parent verifies one
  (`kubera_milestones.seen_by_teen`). Both flags live on the database
  row, not the session cookie — deliberately, since the "already shown"
  fact has to survive a cleared/reset browser session, same reasoning as
  why `anon_id` itself has to be a cookie backed by a database row rather
  than purely client-side state.
- **New tables:** `kubera_coins` (`anon_id`, `current_coins`, `max_coins`
  default 300000) and `kubera_milestones` (`id`, `anon_id`, `title`,
  `coin_reward`, `status`, `note`, `created_at`, `verified_at`,
  `seen_by_parent`, `seen_by_teen`) — kept separate from `kubera_streaks`
  despite both being "one row per teen," since the deciding factor was
  that each table maps to one distinct feature/concept (the real-money
  habit mechanic vs. the virtual reward layer), not list-vs-single-value
  like the Day 2 `kubera_wallets`/`kubera_expenses` split.

**Open items, not built this round, flagged honestly rather than
silently dropped:**
- Main Goal target (3,00,000) is hardcoded, not parent-editable, unlike
  the approval threshold.
- No "send back"/reject path for a parent who doesn't buy a teen's claim
  — verify-only for now.
- Photo/screenshot/voice-note evidence — ruled out for this competition
  specifically (real-photo risk, build cost), not a universal "never."

---

## Day-by-day schedule

Today (2026-11-02) is planning only — no code yet. Building starts
tomorrow. 8 build days to the 10 Nov deadline, with a real-kid-testing
checkpoint before the final polish day.

| Day | Date | Focus |
|---|---|---|
| 1 | 3 Nov | Flask app scaffold, `kubera_*` Supabase tables, anonymous-session cookie, Teen/Parent toggle shell |
| 2 | 4 Nov | ~~Feature 1 — expense tracker (Q1)~~ **Done 2026-11-03, one day ahead of schedule.** |
| 3 | 5 Nov | ~~Feature 2a — cushion/streak wallet core~~ **Done 2026-11-03, two days ahead of schedule.** |
| 4 | 6 Nov | ~~Feature 2b — badge/card gamification + delay calculator~~ **Done 2026-11-03, same session — built bigger than originally scoped (Shields, Refill Mode state machine); see Feature 2 section above.** |
| 5 | 7 Nov | ~~Feature 3 — parent-approval request flow (Q3)~~ **Done 2026-11-03, four days ahead of schedule.** |
| 6 | 8 Nov | ~~Feature 4 — long-term milestone contract + parent verification + reminders~~ **Done 2026-11-04, four days ahead of schedule.** |
| 7 | 9 Nov | **Checkpoint.** Test with a real kid. Fix what surfaces. Polish for the "10-second test" (25 pts) |
| 8 | 10 Nov | Final polish, deploy, submit **before** 11:59 PM IST — don't wait for deadline night |

**Built-in cut line:** if Features 1–3 aren't solid by Day 5, Feature 4
gets cut rather than submitting four half-working things — a broken
feature scores worse on both "answers the questions" and "easy to use"
than a missing one. This is a call to make honestly in the moment if it
comes up, not a decision made in advance here.

**Visual design, confirmed intentional 2026-11-03:** every page built so
far (Days 1-5) is deliberately bare, unstyled HTML — no colors, no layout,
no branding. This is not an oversight. Khwaish's explicit call: finish and
verify all four features functionally first (plain text is enough to
confirm the logic actually works), then do one focused visual design pass
on Days 7-8 as already scheduled, rather than styling incrementally as
each feature is built. Real risk worth flagging honestly if Day 7's
real-kid testing surfaces functional bugs: that eats into the same 1.5
days meant for a full visual pass across 5+ pages — if that happens, it's
a live Rule 13 triage call in the moment, not something to silently
absorb.

**Schedule note, 2026-11-03:** Feature 2's gamification (above) grew
considerably past its original Day 4 scope — full Shield system with
expiry/cooldown tracking, dual card tracks — a deliberate, eyes-open
call by Khwaish, made while still a day ahead of schedule (Feature 1
finished on Day 2's slot, a day early). Built the same session it was
designed. If this ends up pushing Days 4-5 later than planned, the
built-in cut line above is still the backstop — flag it honestly in the
moment rather than quietly absorbing the slip.

---

## How these sessions run

**Decided 2026-11-02:** `docs/PEDAGOGY.md`'s full teaching ceremony
applies to this project too, same as Setuh — explain why before how,
Khwaish types every command herself, 3 comprehension questions after each
feature, logged to `reflections/understanding.md`, daily reflection to
`reflections/daily.md`. This was a deliberate choice against the clock,
made with the schedule above already accounting for the slower pace — not
something to silently abandon if Day 5 feels tight. If the deadline
pressure genuinely requires revisiting this, that's a conversation to have
explicitly, not a quiet shortcut.

`SETUH_BUILD_SPEC.md`'s A1–A9/Phase 1–9 progress checklist (Rule 10) does
**not** apply here — that's Setuh's own curriculum, unrelated to this
project. This file is KuberaTeenApp's equivalent reference point instead.

---

## Open items

- [ ] Confirm parent registration on hackathon.dezerv.in is done (separate
      from the build, but time-sensitive in its own right).
- [ ] Decide who the "real kid" for Day 7's testing checkpoint will be.
