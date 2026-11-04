# UI/UX & Design Specification: Kubera (Holographic Light Mode)

Pasted into chat by Khwaish, 2026-11-03. Saved here verbatim so it isn't
only living in conversation scrollback. Per `BUILD_PLAN.md`'s "Visual
design, confirmed intentional" note, this spec is **not yet applied** —
every page built through Day 5 is deliberately bare, unstyled HTML.
Khwaish's explicit call: finish and verify all four features functionally
first, then do one focused visual design pass using this spec on Days 7-8
as scheduled, rather than styling incrementally per feature.

---

## 1. Overall Aesthetic & Theme Direction

- **Base Theme:** A clean, crisp, premium light-mode background with soft
  holographic gradients (subtle blends of periwinkle blue, soft pink,
  electric purple, and warm orange).
- **Card Style:** Frosted glass effect (glassmorphism) with soft white
  translucent containers, subtle borders, and gentle drop shadows to
  create a clean, floating, modern mobile game feel without looking
  visually heavy.
- **Typography:** Clean, highly legible sans-serif font with bold numeric
  weights for financial and coin counters.

## 2. Color Palette & Psychology

- **Background** (`#F8FAFC` / Holographic Light): Clean white/silver base
  infused with soft iridescent highlights to keep the app feeling light,
  airy, and modern.
- **Primary / Vault Real Money** (`#10B981` Emerald Green): Used for the
  real cash savings cushion, indicating growth, real-world security, and
  actual fiat currency (₹).
- **Gamification / Kubera Coins** (`#8B5CF6` Royal Purple / Violet): Used
  for virtual coin totals, progress rings, and macro goal pots to
  separate in-game points from real money.
- **Action Buttons & Accents** (`#3B82F6` to `#8B5CF6` Holographic
  Gradient): Smooth blue-to-purple gradients used for primary interactive
  buttons (like "Check-In").
- **Streak & Shields** (`#3B82F6` Electric Blue & Warm Amber Accent):
  Used for daily streaks (flame icon) and shield inventories.

## 3. Atomic Design System Breakdown

### A. Atoms (Individual Building Blocks)

**Icons:**
- 🔒 Vault/Safe Icon: Represents security and locked savings.
- 🪙 Coin Icon: Represents virtual Kubera Coins.
- 🔥 Flame Icon: Represents the active daily savings streak.
- 🛡️ Shield Icon: Represents streak protection items.
- ✅ Checkmark Icon: Confirms completed daily check-ins.

**Badges & Pills:** Small capsule containers holding status details like
"2/2 Available" or "Expiry: 12 days".

**Interactive Buttons:** Rounded pill-shaped buttons with smooth
gradients and bold white text.

### B. Molecules (Small Functional Components)

**Real Savings Card (Cushion):**
- Displays a green-tinted container.
- Content: Title (`CUSHION (Real Money)`), numerical balance (`₹12,450`),
  and an action text (`Withdraw`).

**Kubera Coins Card (Virtual Wealth):**
- Displays a purple-tinted container.
- Content: Title (`KUBERA COINS (Points)`), virtual coin count
  (`142,000`), and link (`My Coin History`).

**Daily Habits / Streak Component:**
- Displays the current streak count (`28 Days`) next to a flame icon,
  alongside shield inventory status.

### C. Organisms (Complex Sections)

**The Main Macro Goal Organism (Top Header):**
- Title: `KUBERA (Goal Finance)` with a profile/settings bell icon.
- Goal Container: A frosted dark/holographic card displaying the
  parent-approved goal (`LAPTOP & BIKE`).
- Progress Tracker: A radial or linear progress bar showing completion
  (`325,000 / 500,000 Kubera Coins` — 50% to 75% progress).

**The Dual-Balance Vault Section:**
- Side-by-side or stacked modular cards separating Real Money (Rupees)
  from Virtual Currency (Kubera Coins) so users never confuse real cash
  with game points.

**The Daily Check-In Action Organism (Bottom CTA):**
- A prominent, wide holographic gradient button
  (`CHECK IN (₹10+) & SAVE`) that triggers the daily deposit flow.

## 4. Summary of Key Labels & Copywriting on Screen

- Header: `KUBERA — Goal Finance`
- Macro Goal Title: `MY MACRO GOAL: LAPTOP & BIKE`
- Progress Metric: `325,000 / 500,000 Kubera Coins`
- Real Savings Track: `CUSHION (Real Money) — ₹12,450 — Withdraw`
- Virtual Track: `KUBERA COINS (Points) — 142,000 — My Coin History`
- Streak Status: `Streak — 28 Days`
- Shield Inventory: `Shields — 2/2 Available (Expiry: 12 days)`
- Primary Action: `CHECK IN (₹10+) & SAVE`

---

## Notes for when this actually gets built (Days 7-8)

- This spec visually assumes the Kubera Coin & Goal System (see
  `research/kubera-coin-spec.md`) is already built — it references a
  macro goal progress bar, a Kubera Coins card, and a coin history link,
  none of which exist yet as of Day 5. Feature 4 needs to be functionally
  built first; this file describes how to *style* it afterward.
- The dual-balance vault section's real-money/virtual-currency separation
  matches an existing, already-built product decision (`BUILD_PLAN.md`
  Feature 2: real ₹ cushion and virtual coins are already two separate
  parallel tracks in the data model) — the visual design just needs to
  make that separation legible, not invent it.
