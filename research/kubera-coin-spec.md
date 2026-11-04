# Kubera Coin & Goal System — Developer Specification

Pasted into chat by Khwaish, 2026-11-03, during the Day 5 (Feature 3) build
session. Saved here verbatim so it isn't only living in conversation
scrollback before Feature 4 (Day 6) build. See `BUILD_PLAN.md`'s Feature 4
section for the review status: two numeric corrections this spec surfaced
for already-built Feature 2 (debt threshold, milestone list) were applied
immediately on 2026-11-03; the Kubera Coin / Main Goal / parent macro
milestone system described below is still pending design review before
Day 6's build starts.

---

## 1. Core Concept and Definition

**Kubera Coins vs. Real Money Savings:**

- **Real Money Savings (The Cushion / Savings Pot):** This is actual fiat
  currency (measured in ₹) representing the user's real savings and
  emergency cushion. Minimum daily deposit is ₹10 (no upper limit).
- **Virtual Kubera Coins:** This is a virtual, in-app gamification reward
  currency (not real money). Its sole purpose is to fill up a progress bar
  toward the user's Main Final Goal (set jointly with parents).
- **Tracking:** Real money savings (₹) and virtual Kubera Coins are
  tracked on two separate parallel tracks, but both feed into the user's
  overall app experience.

## 2. Setting Up the Main Goal and Parent-Set Milestones

**The Main Goal Pot:**

- The user and their parents agree on a Max Coin Target for the final goal
  (e.g., 5,00,000 Kubera Coins).
- This sets the total capacity of the main goal progress bar
  (current_coins / max_coins).

**Parent-Set Macro Milestones (Life/Academic Achievements):**

- Parents can manually assign high-value coin rewards for major real-world
  achievements stored in the app.
- Example Rules:
  - Scoring 90%+ in 10th Board Exams = Awards 1,00,000 Kubera Coins.
  - Scoring 90%+ in 12th Board Exams = Awards 2,00,000 Kubera Coins.
- These are unlocked/triggered manually by parent verification inside the
  app.

## 3. Micro-Earning Mechanisms

Users earn Kubera Coins automatically through their daily habits and
savings milestones inside the app:

**A. Weekly Habit Cards:**
- Trigger: Successfully completing a full 7-day savings streak.
- Reward: Unlocks a Weekly Habit Card AND grants 1,000 Kubera Coins added
  to the Main Goal pot.

**B. Savings Milestone Cards:**
- Trigger: Cumulative savings crossing every multiple of ₹500 (e.g., ₹500,
  ₹1,000, ₹1,500, ₹2,000, and continuing endlessly until the goal amount
  is reached).
- Reward: Unlocks a Savings Milestone Card AND grants 2,000 Kubera Coins
  added to the Main Goal pot.

## 4. The Complete Coin Accumulation Formula

The Main Goal pot's total coin balance (current_coins) is calculated as
the sum of all inputs:

```
current_coins = Σ(Weekly Habit Rewards) + Σ(Savings Milestone Rewards) + Σ(Parent-Approved Life Milestones)
```

When current_coins equals or exceeds max_coins, the Main Goal progress bar
hits 100%, signaling that the goal is unlocked and ready to be claimed
with their parents.

## 5. Emergency Cushion Withdrawal & Refill Mode Rules

When a user withdraws money from their savings pot, apply the following
automated state logic:

**Step 1: The Withdrawal Flow & Friction**
- Teen enters a withdrawal amount.
- App shows a Goal Delay Popup: "Withdrawing ₹X pushes your goal back Y
  days" (calculated as debt ÷ ₹10).
- Teen explicitly confirms before the withdrawal happens.

**Step 2: Cushion Balance & Streak Pause**
- Upon confirmation, cushion_balance drops immediately by the withdrawn
  amount (the money is spent).
- The user's streak is paused (does not reset to 0, just stops counting
  up).

**Step 3: The Progressive Debt Formula**
- For expenses between ₹10 to ₹300: The required refill debt is a flat
  ₹100.
- For expenses beyond ₹300: The base debt is ₹100, plus an additional ₹50
  for every ₹200 increment past ₹300.

**Step 4: Refill Mode Behavior (debt > 0)**
- The app enters "Refill Mode" (marked as "In Debt to Yourself").
- The user can check in daily and deposit money with no upper limit
  (minimum ₹10).
- Each deposit goes 100% toward shrinking the Debt Counter.
- cushion_balance does not move at all while paying off debt — it stays
  frozen at the post-withdrawal amount.
- The streak remains frozen and cannot increment.
- Constraint: Users cannot initiate a second withdrawal while
  debt_remaining > 0.

**Step 5: Exiting Refill Mode**
- The check-in that brings the debt to exactly ₹0 clears the debt.
- The next day's check-in is the first one that resumes normal behavior:
  streak increments by +1, cushion balance increases by the deposit
  amount, continuing normally from the frozen streak number.
- Badges & Shields: Milestone and weekly badge checks only run during
  normal check-ins (never during debt-repayment check-ins). Shields and
  streak reset rules (resetting to 0 only if a normal check-in is missed
  without a shield) function independently.

---

## Review status (updated during the Day 5 session)

- **Section 5's debt threshold (₹300) and badge-trigger wording** were
  reviewed against what Feature 2 had already built (₹700 threshold,
  "₹100 then every ₹500" milestone list) — the ₹300 threshold from this
  spec was adopted (`compute_debt()` in `app.py`), but the milestone list
  diverged further from both this spec and the original build: Khwaish's
  final call was ₹100, ₹500, ₹750, ₹1,000, then every ₹500 after that —
  not a flat "every ₹500" as written in Section 3B above. See
  `BUILD_PLAN.md`'s Feature 2 section for the final, authoritative
  numbers — this file is the original spec as given, not the as-built
  design.
- **Sections 1-4 (Kubera Coins, Main Goal pot, parent macro milestones)**
  are not yet built or reviewed in detail — this is the open design work
  for Day 6 (Feature 4).
