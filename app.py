import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, session, redirect, request
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-random-secret-later"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def with_retries(fn, attempts=3, delay=0.25):
    # Supabase/Vercel occasionally hiccups on a single network round trip
    # (cold start, transient DNS/connection blip) — on a request that
    # makes several sequential calls (seeding a new account does ~7),
    # one bad roll used to 500 the whole page. Retrying the one call that
    # failed is cheap and absorbs almost all of that flakiness instead of
    # crashing the user-facing request over it.
    last_exc = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise last_exc

@app.before_request
def ensure_anon_session():
    # Runs before every route, not just home() — a visitor landing directly
    # on any other page (a bookmarked/shared link, or just not "/") used to
    # crash with KeyError: 'anon_id', since only home() ever created one.
    if request.endpoint == "static":
        return
    # Without this, Flask writes the session cookie with no Max-Age, so
    # browsers treat it as a tab/browser-session-only cookie — gone the
    # next time the browser (or a backgrounded mobile tab) restarts,
    # silently handing out a brand-new anon_id and a fresh demo reseed.
    # That's the "my transactions and milestones disappeared" bug: the
    # old anon_id's rows were never deleted, they just became unreachable
    # once the cookie pointing to them was gone.
    session.permanent = True
    anon_id = session.get("anon_id")
    if anon_id is None:
        anon_id = str(uuid.uuid4())
        session["anon_id"] = anon_id
        session["verified"] = False

    # The browser's cookie can outlive the account it points to (e.g.
    # after a database cleanup like 2026-11-09's), or seed_demo_account()
    # below can fail partway through (a transient Supabase hiccup leaves
    # e.g. the wallet row inserted but coins/streak missing) — either way,
    # self-heal by backfilling instead of crashing with a Postgres
    # "0 rows" error the first time home() does a .single() lookup on a
    # table that's missing its row. Checking only kubera_sessions used to
    # miss the partial-seed case: the session row already existed, so it
    # never re-ran, and every later request 500'd forever for that
    # anon_id. Now it checks the three crash-critical tables too.
    #
    # "verified" caches a clean bill of health *in the signed cookie
    # itself* so this 4-query check only ever runs once per anon_id, not
    # on every single request to every route — running it unconditionally
    # on every request was adding real latency (and real failure surface)
    # to pages that didn't need it at all, which is its own way to turn
    # an occasional network hiccup into a user-visible 500.
    if not session.get("verified"):
        has_session = with_retries(lambda: supabase.table("kubera_sessions").select("anon_id").eq("anon_id", anon_id).execute().data)
        has_wallet = with_retries(lambda: supabase.table("kubera_wallets").select("anon_id").eq("anon_id", anon_id).execute().data)
        has_coins = with_retries(lambda: supabase.table("kubera_coins").select("anon_id").eq("anon_id", anon_id).execute().data)
        has_streak = with_retries(lambda: supabase.table("kubera_streaks").select("anon_id").eq("anon_id", anon_id).execute().data)
        if not has_session:
            with_retries(lambda: supabase.table("kubera_sessions").insert({"anon_id": anon_id}).execute())
        if not (has_wallet and has_coins and has_streak):
            seed_demo_account(anon_id)
        session["verified"] = True
    if "view_mode" not in session:
        session["view_mode"] = "teen"

def table_has_row(table_name, anon_id):
    return bool(with_retries(lambda: supabase.table(table_name).select("anon_id").eq("anon_id", anon_id).limit(1).execute().data))

def seed_demo_account(new_id):
        # Demo seed, locked 2026-11-09 (v2, replacing the simpler Day-13
        # version from earlier the same day) — a fresh judge lands mid-
        # streak with real history already behind them, matched exactly
        # to Khwaish's own reference incognito account so the permanent
        # seed is the literal scenario she reviewed and approved, not a
        # re-description of it. Narrative: a clean, no-missed-days streak
        # that started 13 days ago. Day 7 (today-7) earned the weekly
        # badge + a Shield; Day 10 (today-4) crossed the ₹100 cushion
        # milestone. Yesterday, the parent verified the big 10th-boards
        # milestone (150,000 coins) and the teen claimed a second one
        # (sports tournament, still awaiting verification) — so a judge
        # opening the parent view immediately sees one real "ready to
        # verify" action waiting, not an empty list. last_checkin is
        # yesterday, so the minimum ₹10 check-in today is still the live,
        # on-stage moment — streak 13→14, a brand-new weekly badge, a
        # second Shield, and 1,000 more Kubera Coins.
        today = today_utc()
        day1 = today - timedelta(days=13)
        day7_date = (day1 + timedelta(days=6)).isoformat()
        day10_date = (day1 + timedelta(days=9)).isoformat()
        yesterday = (today - timedelta(days=1)).isoformat()
        yesterday_dt = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).isoformat()

        saved_so_far = 130  # 13 days x ₹10/day

        # Real spend history so a judge sees "where did my money go" already
        # populated, not a blank slate — same 4 transactions reviewed live.
        seed_expenses = [
            {"anon_id": new_id, "amount": 30, "payee": "Bombay Stationery", "category": "shopping"},
            {"anon_id": new_id, "amount": 60, "payee": "Ola Cabs", "category": "transport"},
            {"anon_id": new_id, "amount": 40, "payee": None, "category": "snacks"},  # cash expense — doesn't touch wallet
            {"anon_id": new_id, "amount": 1010, "payee": "Sriram Vadewala", "category": "snacks"},
        ]
        wallet_pay_deductions = sum(e["amount"] for e in seed_expenses if e["payee"] is not None)
        starting_wallet = (3000 - saved_so_far) - wallet_pay_deductions  # = 1,770

        # 1,000 (weekly_7) + 2,000 (milestone_100) + 150,000 (verified
        # 10th-boards macro milestone) — already earned before the judge
        # does anything.
        starting_coins = 1000 + 2000 + 150000

        # Each insert below is guarded by an existence check — this
        # function now also runs as a *repair* for a partially-seeded
        # anon_id (see ensure_anon_session), where some of these tables
        # already succeeded on an earlier, interrupted run. Blindly
        # re-inserting would either duplicate rows (breaking every
        # .single() call that assumes exactly one) or, for tables with a
        # unique constraint, 500 on the conflict — either way worse than
        # the bug this is fixing.
        if not table_has_row("kubera_wallets", new_id):
            with_retries(lambda: supabase.table("kubera_wallets").insert({"anon_id": new_id, "balance": starting_wallet}).execute())
        if not table_has_row("kubera_streaks", new_id):
            with_retries(lambda: supabase.table("kubera_streaks").insert({
                "anon_id": new_id,
                "streak_count": 13,
                "cushion_balance": saved_so_far,
                "debt_remaining": 0,
                "last_checkin": yesterday,
            }).execute())
        if not table_has_row("kubera_coins", new_id):
            with_retries(lambda: supabase.table("kubera_coins").insert({"anon_id": new_id, "current_coins": starting_coins}).execute())
        if not table_has_row("kubera_badges", new_id):
            with_retries(lambda: supabase.table("kubera_badges").insert([
                {"anon_id": new_id, "badge_type": "weekly_7", "earned_date": day7_date, "seen_by_teen": True},
                {"anon_id": new_id, "badge_type": "milestone_100", "earned_date": day10_date, "seen_by_teen": True},
                # Trophy badge for the already-verified 10th-boards milestone —
                # keeps "My Badges" consistent with the Kubera Story's own
                # "verify a milestone, get a trophy badge" promise.
                {"anon_id": new_id, "badge_type": "trophy_150000", "earned_date": yesterday, "seen_by_teen": True},
            ]).execute())
        if not table_has_row("kubera_shields", new_id):
            with_retries(lambda: supabase.table("kubera_shields").insert({"anon_id": new_id, "earned_date": day7_date}).execute())
        if not table_has_row("kubera_expenses", new_id):
            with_retries(lambda: supabase.table("kubera_expenses").insert(seed_expenses).execute())
        # NOTE: every dict in this bulk insert carries the exact same keys
        # on purpose — PostgREST's bulk insert derives the batch's columns
        # from the first row, so any row missing a key gets NULL written
        # explicitly instead of falling back to the column's DB default
        # (bit us once already: the two "pending" rows 500'd on a missing
        # not-null "status" until this was made uniform).
        if table_has_row("kubera_milestones", new_id):
            return
        with_retries(lambda: supabase.table("kubera_milestones").insert([
            {
                "anon_id": new_id,
                "title": "Score 90%+ in 10th board exams",
                "coin_reward": 150000,
                "status": "verified",
                "note": "Scored 92.4% --- marksheet",
                "verified_at": yesterday_dt,
                "seen_by_parent": True,
                "seen_by_teen": True,
            },
            {
                "anon_id": new_id,
                "title": "Win a sports tournament or school competition",
                "coin_reward": 25000,
                "status": "claimed",
                "note": "certificate and gold medalll",
                "verified_at": None,
                "seen_by_parent": True,
                "seen_by_teen": False,
            },
            {
                "anon_id": new_id,
                "title": "Score 90%+ in half-yearly / pre-board exams",
                "coin_reward": 25000,
                "status": "pending",
                "note": None,
                "verified_at": None,
                "seen_by_parent": False,
                "seen_by_teen": False,
            },
            {
                "anon_id": new_id,
                "title": "Consistent chores or extra reading goals this month",
                "coin_reward": 28000,
                "status": "pending",
                "note": None,
                "verified_at": None,
                "seen_by_parent": False,
                "seen_by_teen": False,
            },
        ]).execute())

PAYEE_CATEGORY = {
    "Bombay Stationery": "shopping",
    "Sriram Vadewala": "snacks",
    "Ola Cabs": "transport",
}
PAYEES = ["Bombay Stationery", "Sriram Vadewala", "Ola Cabs", "Campus Café", "Timely Treasures"]
CATEGORIES = ["snacks", "movies", "transport", "bills", "gifts", "shopping", "grocery"]

CATEGORY_ICONS = {
    "snacks": "🫔",
    "movies": "🎟️",
    "transport": "🛺",
    "bills": "🧾",
    "gifts": "🎁",
    "shopping": "🛍️",
    "grocery": "🛒",
}

def guess_category(name):
    # Same "rule-based lookup, not real ML" categorization BUILD_PLAN.md
    # already locked in for the preset payees — extended to handle a
    # typed phone number or UPI ID too (e.g. "sriramvadewala@okaxis" or
    # "sriram.vadewala-personal") by comparing letters-only, so a free-
    # text entry still gets a real category guess whenever the name is
    # recognizable, with the same manual-dropdown fallback as before.
    normalized = re.sub(r"[^a-z]", "", name.lower())
    if not normalized:
        return None
    for payee, category in PAYEE_CATEGORY.items():
        payee_normalized = re.sub(r"[^a-z]", "", payee.lower())
        if payee_normalized and payee_normalized in normalized:
            return category
    return None

def payee_avatar_html(payee, size=56):
    category = guess_category(payee)
    icon = CATEGORY_ICONS.get(category, "💳")
    if category:
        highlight, dark, glow = CATEGORY_GLOSS[category]
        base = CATEGORY_COLORS[category]
    else:
        highlight, dark, glow, base = "#E5E7EB", "#4B5563", "100, 116, 139", "#94A3B8"
    icon_size = round(size * 0.46)
    return f"""
    <div class="payee-avatar" style="width:{size}px;height:{size}px;
        background:radial-gradient(circle at 32% 26%, {highlight}, {base} 55%, {dark} 100%);
        box-shadow:0 6px 16px rgba({glow}, 0.5), inset 0 -6px 10px rgba(0,0,0,0.25), inset 0 5px 8px rgba(255,255,255,0.5);">
        <span class="sheen"></span>
        <span class="payee-avatar-icon" style="font-size:{icon_size}px">{icon}</span>
    </div>
    """

def glossy_icon_html(emoji, accent="blue", size=76):
    icon_size = round(size * 0.46)
    return f"""
    <div class="payee-avatar glossy-{accent}" style="width:{size}px;height:{size}px;margin:0 auto 14px;">
        <span class="sheen"></span>
        <span class="payee-avatar-icon" style="font-size:{icon_size}px">{emoji}</span>
    </div>
    """

def cat_icon(category):
    icon = CATEGORY_ICONS.get(category, "💸")
    return f'<span class="cat-icon animate-in">{icon}</span>'

# Fixed category -> hue assignment (never cycled — a category keeps its color
# identity whether it's one of 2 slices or all 7). Validated for colorblind
# separation on both the linear order AND the pie-specific wraparound pair
# (last slice touching first), which a bar/stack chart never has to check.
CATEGORY_COLORS = {
    "snacks": "#2a78d6",
    "movies": "#eb6834",
    "transport": "#1baf7a",
    "bills": "#eda100",
    "gifts": "#e87ba4",
    "shopping": "#008300",
    "grocery": "#4a3aa7",
}

# Glossy variants (highlight, dark edge, glow rgb) for each category's base
# hue in CATEGORY_COLORS — same "bright highlight -> saturated mid -> deep
# edge" recipe as the app-wide .glossy-* atoms, just one per spending category.
CATEGORY_GLOSS = {
    "snacks":    ("#BFE0FC", "#123F73", "42, 120, 214"),
    "movies":    ("#FFD1B8", "#8A3A15", "235, 104, 52"),
    "transport": ("#B8F5E0", "#0C6B48", "27, 175, 122"),
    "bills":     ("#FFE4A8", "#8A5D00", "237, 161, 0"),
    "gifts":     ("#FFD9E8", "#8A3D59", "232, 123, 164"),
    "shopping":  ("#B8F0B8", "#004D00", "0, 131, 0"),
    "grocery":   ("#D6CCF2", "#2A1F63", "74, 58, 167"),
}

def _pack_bubbles(items):
    """Greedy spiral packing: place the biggest circle at the center, then
    walk each smaller one outward along a spiral until it clears every
    circle already placed. Good enough for the handful of categories this
    app ever has (<=7), not meant as a general-purpose packer."""
    placed = []
    for i, (key, r) in enumerate(items):
        if i == 0:
            placed.append((key, 0.0, 0.0, r))
            continue
        angle, radius = 0.0, r
        while True:
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            if all(math.hypot(x - px, y - py) >= (r + pr + 3) for _, px, py, pr in placed):
                break
            angle += 0.28
            radius += 0.9
        placed.append((key, x, y, r))
    return placed

def category_bubbles_html(totals):
    if not totals:
        return '<p style="text-align:center;color:var(--text-muted)">No spending logged yet.</p>'

    total = sum(totals.values())
    ordered = sorted((c for c in CATEGORIES if c in totals), key=lambda c: totals[c], reverse=True)
    max_amt = max(totals[c] for c in ordered)

    def radius_for(amt):
        return max(24.0, min(58.0, 58.0 * math.sqrt(amt / max_amt)))

    placed = _pack_bubbles([(c, radius_for(totals[c])) for c in ordered])

    min_x = min(x - r for _, x, y, r in placed)
    max_x = max(x + r for _, x, y, r in placed)
    min_y = min(y - r for _, x, y, r in placed)
    max_y = max(y + r for _, x, y, r in placed)
    cluster_cx, cluster_cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    field_w = max(260.0, max_x - min_x + 24)
    field_h = max(170.0, max_y - min_y + 24)

    bubbles = []
    legend_rows = []
    for i, (cat, x, y, r) in enumerate(placed):
        amt = totals[cat]
        pct = amt / total * 100
        base = CATEGORY_COLORS.get(cat, "#898781")
        highlight, dark, glow = CATEGORY_GLOSS.get(cat, ("#FFFFFF", "#333333", "100, 100, 100"))
        icon = CATEGORY_ICONS.get(cat, "💸")
        left = field_w / 2 + (x - cluster_cx) - r
        top = field_h / 2 + (y - cluster_cy) - r
        size_cls = " small" if r < 32 else ""

        bubbles.append(f"""
        <div class="bubble{size_cls} animate-in" style="width:{r*2:.0f}px;height:{r*2:.0f}px;left:{left:.0f}px;top:{top:.0f}px;
            background:radial-gradient(circle at 32% 26%, {highlight}, {base} 55%, {dark} 100%);
            box-shadow:0 6px 16px rgba({glow}, 0.5), inset 0 -8px 14px rgba(0,0,0,0.25), inset 0 6px 10px rgba(255,255,255,0.5);">
            <span class="sheen" style="animation-delay:{(i % 5) * 0.6}s"></span>
            <span class="spark" style="top:20%;left:65%;animation-delay:{(i % 4) * 0.4}s">✦</span>
            <span class="bicon">{icon}</span>
            <span class="bname">{cat.title()}</span>
            <span class="bamt">₹{amt}</span>
        </div>
        """)
        legend_rows.append(f"""
        <div class="pie-legend-row">
            <span class="pie-swatch" style="background:{base}"></span>
            <span class="pie-legend-icon">{icon}</span>
            <span class="pie-legend-label">{cat.title()}</span>
            <span class="pie-legend-value">₹{amt} · {pct:.0f}%</span>
        </div>
        """)

    field = f'<div class="bubble-field" style="height:{field_h:.0f}px">{"".join(bubbles)}</div>'
    return f"""
    <div class="pie-wrap">
        <p class="bubble-total">Total Spent · ₹{total:,}</p>
        {field}
        <div class="pie-legend">{''.join(legend_rows)}</div>
    </div>
    """

def txn_row_html(e):
    icon = CATEGORY_ICONS.get(e["category"], "💸")
    payee = e["payee"] or "Cash expense"
    date = e["created_at"][:10]
    return f"""
    <li class="txn-row">
        <span class="txn-avatar animate-in">{icon}</span>
        <div class="txn-body">
            <p class="txn-name">{payee}</p>
            <p class="txn-meta">{e['category'].title()} · {date}</p>
        </div>
        <span class="txn-amount">-₹{e['amount']}</span>
        <a class="btn-small btn-small-edit" href="/expenses/{e['id']}/edit">Edit</a>
    </li>
    """

def badge_display(badge_type):
    if badge_type.startswith("weekly_"):
        n = badge_type.split("_", 1)[1]
        return "🔥", f"{n} Days Streak"
    if badge_type.startswith("milestone_"):
        amt = badge_type.split("_", 1)[1]
        return "💰", f"₹{amt} Saved"
    if badge_type.startswith("trophy_"):
        return "🏆", "Milestone Verified"
    return "🏅", badge_type.replace("_", " ").title()

def badge_treasure_grid_html(badge_rows):
    if not badge_rows:
        return "<p style='text-align:center;color:rgba(255,255,255,0.75)'>No badges earned yet.</p>"
    cards = []
    for b in badge_rows:
        icon, _ = badge_display(b["badge_type"])
        celebration_title = badge_celebration_title(b["badge_type"])
        coins = badge_coin_reward(b["badge_type"])
        cards.append(f"""
        <div class="badge-card treasure-card">
            <div class="treasure-rays"></div>
            <span class="treasure-corner tc-tl">🌀</span>
            <span class="treasure-corner tc-tr">🌀</span>
            <span class="treasure-corner tc-bl">🌀</span>
            <span class="treasure-corner tc-br">🌀</span>
            <div class="treasure-content">
                <div class="achv-icon">{icon}</div>
                <h2 class="achv-title">{celebration_title}</h2>
                <p class="achv-sub">+{coins:,}</p>
                <p class="achv-extra">{b['earned_date']}</p>
            </div>
        </div>
        """)
    return f'<div class="badge-grid">{"".join(cards)}</div>'

def short_badge_label(badge_type):
    if badge_type.startswith("weekly_"):
        return f"Day {badge_type.split('_', 1)[1]}"
    if badge_type.startswith("milestone_"):
        return f"₹{badge_type.split('_', 1)[1]}"
    if badge_type.startswith("trophy_"):
        return "Trophy"
    return badge_type.replace("_", " ").title()

def badge_coin_reward(badge_type):
    if badge_type.startswith("weekly_"):
        return 1000
    if badge_type.startswith("milestone_"):
        return 2000
    if badge_type.startswith("trophy_"):
        return int(badge_type.split("_", 1)[1])
    return 0

def badge_celebration_title(badge_type):
    if badge_type.startswith("weekly_"):
        return f"{badge_type.split('_', 1)[1]} DAYS STREAK!"
    if badge_type.startswith("milestone_"):
        return f"₹{badge_type.split('_', 1)[1]} SAVED!"
    return badge_display(badge_type)[1].upper() + "!"

KUBERA_STORY_SLIDES = [
    ("👋", "Welcome to Kubera", "Kubera is a money app built for teens. It helps you see what you actually spend, build a saving habit that becomes your own safety net, and work toward big goals together with your parent.", "blue"),
    ("🎮", "Why Saving Money is Like Keeping Another Life in Reserve", "<strong class=\"story-highlight\">The XP Shield:</strong> Having cash ready shields you from unexpected glitches — like a cracked phone screen or broken headphones — without blowing your entire allowance.<br><br><strong class=\"story-highlight\">Leveling Up:</strong> Systematic saving turns \"I wish I had that\" into buying your dream laptop, sneakers, or concert tickets on your own terms.<br><br><strong class=\"story-highlight\">Zero Stress:</strong> A personal cushion lets you hangout with friends, grab food, or buy what you want with total peace of mind and full independence.", "blue"),
    ("🔥", "Starting Your Streak", "Every day, check in and save at least ₹10. Keep checking in daily and your streak grows — Day 1, Day 2, Day 3... Miss a day and it usually resets to zero, so showing up daily is the whole point.", "blue"),
    ("🏅", "Streak Rewards", "Every 7 days of your streak — Day 7, Day 14, Day 21, and onward — you earn a badge plus 1,000 Kubera Coins. <strong class=\"story-highlight\">Keep the streak going and the badges keep coming.</strong>", "gold"),
    ("🛡️", "Shields — Your Safety Net", "Missing a day usually resets your streak to zero. A Shield protects you instead — it absorbs one missed day so your streak survives. You earn Shields automatically as you hit streak milestones.", "gold"),
    ("⚡", "Shield Rules", "You can hold up to 2 Shields at once. Each one expires 30 days after you earn it. And you need a 5-day gap between using one Shield and the next — no using two back-to-back.", "gold"),
    ("🏆", "Milestone Badges", "Complete a milestone your parent sets — like acing an exam or hitting a goal — submit your proof, and once they verify it you earn real Kubera Coins plus a trophy badge for My Badges, right alongside your streak and savings cards. <strong class=\"story-highlight\">Share it and show your friends what you've earned.</strong>", "gold"),
]

def story_row_html(kubera_seen_today, badge_rows):
    kubera_ring = "seen" if kubera_seen_today else "unseen"
    avatars = [f"""
    <div class="story-avatar" data-story-type="kubera" data-story-ref="">
        <div class="story-ring {kubera_ring}"><div class="story-pfp story-pfp-kubera">👑</div></div>
        <p class="story-label">Kubera</p>
    </div>
    """]
    for b in badge_rows:
        icon, _ = badge_display(b["badge_type"])
        ring = "seen" if b["seen_by_teen"] else "unseen"
        avatars.append(f"""
        <div class="story-avatar" data-story-type="badge" data-story-ref="{b['id']}">
            <div class="story-ring {ring}"><div class="story-pfp">{icon}</div></div>
            <p class="story-label">{short_badge_label(b['badge_type'])}</p>
        </div>
        """)
    return f'<div class="story-row">{"".join(avatars)}</div>'

def story_overlay_html(badge_rows):
    kubera_slides = "".join(f"""
        <div class="story-slide">
            <div class="story-orb glossy-{accent}">
                <span class="sheen"></span>
                <span class="spark" style="top:14%;left:70%;animation-delay:0s">✦</span>
                <span class="spark" style="top:66%;left:16%;animation-delay:0.6s">✦</span>
                <span class="spark" style="top:30%;left:22%;animation-delay:1.1s">✦</span>
                <span class="story-orb-icon">{icon}</span>
            </div>
            <h2 class="story-slide-title">{title}</h2>
            <p class="story-slide-body">{body}</p>
        </div>
        """ for icon, title, body, accent in KUBERA_STORY_SLIDES)

    badge_set_blocks = []
    for b in badge_rows:
        icon, _ = badge_display(b["badge_type"])
        celebration_title = badge_celebration_title(b["badge_type"])
        coins = badge_coin_reward(b["badge_type"])
        badge_set_blocks.append(f"""
        <div class="story-slide-set" data-story-type="badge" data-story-ref="{b['id']}">
            <div class="story-slide">
                <div class="story-badge-card treasure-card">
                    <div class="treasure-rays"></div>
                    <span class="treasure-corner tc-tl">🌀</span>
                    <span class="treasure-corner tc-tr">🌀</span>
                    <span class="treasure-corner tc-bl">🌀</span>
                    <span class="treasure-corner tc-br">🌀</span>
                    <div class="treasure-content">
                        <div class="achv-icon">{icon}</div>
                        <h2 class="achv-title">{celebration_title}</h2>
                        <p class="achv-sub">+{coins:,} Kubera Coins</p>
                        <p class="achv-extra">Earned {b['earned_date']}</p>
                    </div>
                </div>
                <div class="story-share-row">
                    <div class="share-button">📤 Share</div>
                </div>
            </div>
        </div>
        """)
    badge_sets = "".join(badge_set_blocks)

    return f"""
    <div id="story-overlay" class="story-overlay">
        <div class="story-chrome">
            <div class="story-segments" id="story-segments"></div>
            <div class="story-header">
                <span class="story-header-icon" id="story-header-icon"></span>
                <span class="story-header-title" id="story-header-title"></span>
                <button type="button" class="story-close" id="story-close">✕</button>
            </div>
        </div>
        <div id="story-slides">
            <div class="story-slide-set" data-story-type="kubera" data-story-ref="">
                {kubera_slides}
            </div>
            {badge_sets}
        </div>
        <div class="story-tap-zone story-tap-left" id="story-tap-left"></div>
        <div class="story-tap-zone story-tap-right" id="story-tap-right"></div>
        <p class="story-hold-hint" id="story-hold-hint">Hold to pause, release to resume</p>
    </div>
    <script>
    (function() {{
        var avatars = document.querySelectorAll('.story-avatar');
        var overlay = document.getElementById('story-overlay');
        var segmentsEl = document.getElementById('story-segments');
        var headerIcon = document.getElementById('story-header-icon');
        var headerTitle = document.getElementById('story-header-title');
        var closeBtn = document.getElementById('story-close');
        var tapLeft = document.getElementById('story-tap-left');
        var tapRight = document.getElementById('story-tap-right');
        var holdHint = document.getElementById('story-hold-hint');
        var holdHintDismissed = false;

        var currentType = null;
        var currentRef = '';
        var currentSlide = 0;
        var autoTimer = null;
        var SLIDE_MS = 5000;
        var HOLD_THRESHOLD_MS = 250;
        var isPaused = false;
        var slideStartedAt = 0;
        var remainingMs = SLIDE_MS;

        function activeSet() {{
            return document.querySelector('.story-slide-set[data-story-type="' + currentType + '"][data-story-ref="' + currentRef + '"]');
        }}

        function clearAutoTimer() {{
            if (autoTimer) {{ clearTimeout(autoTimer); autoTimer = null; }}
        }}

        function currentFill() {{
            var segs = segmentsEl.querySelectorAll('.story-segment');
            var seg = segs[currentSlide];
            return seg ? seg.querySelector('.story-segment-fill') : null;
        }}

        function openStory(type, ref, iconText, labelText) {{
            currentType = type;
            currentRef = ref;
            var slides = activeSet().querySelectorAll('.story-slide');
            segmentsEl.innerHTML = '';
            for (var i = 0; i < slides.length; i++) {{
                var seg = document.createElement('div');
                seg.className = 'story-segment';
                var fill = document.createElement('div');
                fill.className = 'story-segment-fill';
                seg.appendChild(fill);
                segmentsEl.appendChild(seg);
            }}
            headerIcon.textContent = iconText;
            headerTitle.textContent = labelText;
            showSlide(0);
            overlay.classList.add('open');
            markSeen(type, ref);
        }}

        function showSlide(idx) {{
            // Clear .active globally, not just on this story's slides — a
            // previously-opened story's slide staying .active is what made
            // two different stories render stacked on top of each other.
            document.querySelectorAll('.story-slide.active').forEach(function(s) {{
                s.classList.remove('active');
            }});
            var slides = activeSet().querySelectorAll('.story-slide');
            currentSlide = idx;
            slides[idx].classList.add('active');

            var segs = segmentsEl.querySelectorAll('.story-segment');
            segs.forEach(function(seg, i) {{
                var fill = seg.querySelector('.story-segment-fill');
                fill.style.animation = 'none';
                void fill.offsetWidth; // restart the fill animation from 0 on re-trigger
                if (i < idx) {{
                    seg.classList.add('filled');
                    fill.style.width = '100%';
                }} else if (i === idx) {{
                    seg.classList.remove('filled');
                    fill.style.width = '0%';
                    fill.style.animation = 'story-progress ' + SLIDE_MS + 'ms linear forwards';
                    fill.style.animationPlayState = 'running';
                }} else {{
                    seg.classList.remove('filled');
                    fill.style.width = '0%';
                }}
            }});

            isPaused = false;
            remainingMs = SLIDE_MS;
            slideStartedAt = Date.now();
            clearAutoTimer();
            autoTimer = setTimeout(nextSlide, remainingMs);
        }}

        function pauseStory() {{
            if (isPaused) return;
            isPaused = true;
            clearAutoTimer();
            var elapsed = Date.now() - slideStartedAt;
            remainingMs = Math.max(0, remainingMs - elapsed);
            var fill = currentFill();
            if (fill) {{ fill.style.animationPlayState = 'paused'; }}
        }}

        function resumeStory() {{
            if (!isPaused) return;
            isPaused = false;
            slideStartedAt = Date.now();
            autoTimer = setTimeout(nextSlide, remainingMs);
            var fill = currentFill();
            if (fill) {{ fill.style.animationPlayState = 'running'; }}
        }}

        function nextSlide() {{
            var count = activeSet().querySelectorAll('.story-slide').length;
            if (currentSlide + 1 < count) {{ showSlide(currentSlide + 1); }}
            else {{ closeStory(); }}
        }}

        function prevSlide() {{
            if (currentSlide > 0) {{ showSlide(currentSlide - 1); }}
        }}

        function closeStory() {{
            clearAutoTimer();
            isPaused = false;
            overlay.classList.remove('open');
            currentType = null;
            currentRef = '';
        }}

        function markSeen(type, ref) {{
            var url = type === 'kubera' ? '/stories/kubera/seen' : '/stories/badge/' + ref + '/seen';
            fetch(url, {{ method: 'POST' }}).then(function() {{
                var sel = '.story-avatar[data-story-type="' + type + '"][data-story-ref="' + ref + '"]';
                var avatar = document.querySelector(sel);
                if (avatar) {{
                    var ring = avatar.querySelector('.story-ring');
                    if (ring) {{ ring.classList.remove('unseen'); ring.classList.add('seen'); }}
                }}
            }});
        }}

        avatars.forEach(function(a) {{
            a.addEventListener('click', function() {{
                var type = a.dataset.storyType;
                var ref = a.dataset.storyRef;
                var iconText = a.querySelector('.story-pfp').textContent;
                var labelText = a.querySelector('.story-label').textContent;
                openStory(type, ref, iconText, labelText);
            }});
        }});
        closeBtn.addEventListener('click', closeStory);

        // Press-and-hold anywhere on the slide pauses the timer and the
        // progress fill exactly where it is; releasing resumes from there.
        // A quick press-release (under HOLD_THRESHOLD_MS) counts as a tap
        // instead, and navigates — so the same zone does both jobs, same as
        // a real Instagram story.
        function wireTapZone(zone, navigateFn) {{
            var downAt = 0;
            zone.addEventListener('pointerdown', function(e) {{
                downAt = Date.now();
                if (zone.setPointerCapture) {{
                    try {{ zone.setPointerCapture(e.pointerId); }} catch (err) {{}}
                }}
                pauseStory();
            }});
            zone.addEventListener('pointerup', function() {{
                var heldFor = Date.now() - downAt;
                if (heldFor < HOLD_THRESHOLD_MS) {{
                    navigateFn();
                }} else {{
                    resumeStory();
                    if (!holdHintDismissed) {{
                        holdHintDismissed = true;
                        holdHint.style.display = 'none';
                    }}
                }}
            }});
            zone.addEventListener('pointercancel', resumeStory);
        }}
        wireTapZone(tapLeft, prevSlide);
        wireTapZone(tapRight, nextSlide);

        document.addEventListener('keydown', function(e) {{
            if (!overlay.classList.contains('open')) return;
            if (e.key === 'Escape') closeStory();
            if (e.key === 'ArrowRight') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }});
    }})();
    </script>
    """

def today_utc():
    return datetime.now(timezone.utc).date()

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

def available_shields(anon_id, today):
    shields = supabase.table("kubera_shields").select("*").eq("anon_id", anon_id).execute().data
    cutoff = (today - timedelta(days=30)).isoformat()
    return [s for s in shields if s["used_date"] is None and s["earned_date"] >= cutoff]

def compute_debt(amount):
    if amount <= 300:
        return 100
    extra = amount - 300
    increments = extra // 200
    return 100 + 50 * increments

MILESTONE_THRESHOLDS = [100, 500, 750, 1000]

def all_milestones_upto(balance):
    hits = [t for t in MILESTONE_THRESHOLDS if t <= balance]
    t = 1500
    while t <= balance:
        hits.append(t)
        t += 500
    return hits

def crossed_milestones(old_balance, new_balance):
    return [t for t in all_milestones_upto(new_balance) if t > old_balance]

def award_coins(anon_id, amount):
    coins = supabase.table("kubera_coins").select("current_coins").eq("anon_id", anon_id).single().execute().data
    supabase.table("kubera_coins").update({"current_coins": coins["current_coins"] + amount}).eq("anon_id", anon_id).execute()

def award_milestones(anon_id, old_balance, new_balance):
    messages = []
    for t in crossed_milestones(old_balance, new_balance):
        supabase.table("kubera_badges").insert({"anon_id": anon_id, "badge_type": f"milestone_{t}"}).execute()
        award_coins(anon_id, 2000)
        messages.append(f"New milestone badge: ₹{t} saved! +2,000 Kubera Coins.")
    return messages

def generate_insights(balance, streak, expenses, milestone_rows):
    lines = []

    if streak["debt_remaining"] > 0:
        lines.append(f"⚠️ In Refill Mode — streak frozen while paying back ₹{streak['debt_remaining']} from an emergency cushion withdrawal.")

    today = today_utc()
    month_start_iso = datetime(today.year, today.month, 1, tzinfo=timezone.utc).isoformat()
    spent_this_month = sum(e["amount"] for e in expenses if e["created_at"] >= month_start_iso)
    total_this_cycle = spent_this_month + balance
    if 15 <= today.day <= 20 and total_this_cycle > 0 and spent_this_month / total_this_cycle >= 0.75:
        lines.append("💸 He's spending a lot of money — wallet is nearly empty. He needs to put a brake on his desires.")

    streak_count = streak["streak_count"]
    if streak_count >= 21:
        lines.append(f"🔥 On fire! Day {streak_count} streak — he's an incredibly consistent saver.")
    elif streak_count >= 14:
        lines.append(f"🔥 Day {streak_count} streak — he's really good at saving, a great habit forming!")
    elif streak_count >= 7:
        lines.append(f"🔥 Day {streak_count} streak — off to a great start on saving!")

    verified_count = len([m for m in milestone_rows if m["status"] == "verified"])
    if verified_count > 0:
        lines.append(f"🏆 Verified {verified_count} milestone{'s' if verified_count != 1 else ''} so far — real progress on the big goals.")

    if not lines:
        lines.append("Nothing unusual to report — steady as usual.")

    return lines[:3]

def toast_html(element_id, lines):
    return f"""
    <div id="{element_id}" style="background:#222;color:#fff;padding:10px;border-radius:6px;display:inline-block;">
        {"<br>".join(lines)}
    </div>
    <script>
        setTimeout(function() {{
            var el = document.getElementById('{element_id}');
            if (el) el.style.display = 'none';
        }}, 4000);
    </script>
    """

def reengage_banner_html():
    return """
    <div id="reengage-banner" class="reengage-banner">
        <div class="reengage-progress"><div class="reengage-progress-fill"></div></div>
        <a href="/expenses/today" class="reengage-content">
            <span class="reengage-icon">👀</span>
            <span class="reengage-text">Where did today's money go? Tap to tell us!</span>
        </a>
        <button type="button" class="reengage-close" id="reengage-close" aria-label="Dismiss">✕</button>
    </div>
    <script>
    (function() {
        var banner = document.getElementById('reengage-banner');
        var closeBtn = document.getElementById('reengage-close');
        var dismissed = false;
        function dismiss() {
            if (dismissed) return;
            dismissed = true;
            banner.classList.add('closing');
            setTimeout(function() { banner.remove(); }, 350);
        }
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            dismiss();
        });
        setTimeout(dismiss, 5000);
    })();
    </script>
    """

def get_notifications(anon_id, view_mode):
    items = []
    if view_mode == "parent":
        reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).eq("status", "pending").execute().data
        items += [f'⏳ "{r["payee"] or "cash"}" — ₹{r["amount"]} needs your approval' for r in reqs]
        claimed = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).eq("status", "claimed").execute().data
        items += [f'📋 "{m["title"]}" is ready for you to verify' for m in claimed]
    else:
        reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).eq("seen_by_teen", False).neq("status", "pending").execute().data
        for r in reqs:
            label = r["payee"] or "cash"
            items.append(f"✅ Approved: ₹{r['amount']} at {label}" if r["status"] == "approved" else f"❌ Declined: ₹{r['amount']} at {label}")
        verified = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).eq("seen_by_teen", False).eq("status", "verified").execute().data
        items += [f'🎉 "{m["title"]}" verified! +{m["coin_reward"]} coins' for m in verified]
    return items

def page(body, active_tab=None, hide_topbar=False):
    # active_tab is vestigial now that the app is one scrolling page instead
    # of three tabs — left on every call site rather than touched, since
    # removing it everywhere would be a lot of churn for zero behavior change.
    anon_id = session.get("anon_id")
    view_mode = session.get("view_mode", "teen")
    notif_items = get_notifications(anon_id, view_mode) if anon_id else []
    bell_dot = '<span class="bell-dot"></span>' if notif_items else ""
    notif_list = "".join(f"<li>{n}</li>" for n in notif_items) or "<li>No new notifications.</li>"

    action_footer = ""
    if view_mode == "teen":
        action_footer = """
<div class="action-footer">
    <a class="action-footer-btn action-footer-save" href="/checkin">💰 Save</a>
    <a class="action-footer-btn action-footer-pay" href="/pay">💳 Pay</a>
</div>
"""

    # The topbar's buttons (menu-btn, bell-btn) are wired up unconditionally
    # by the script in `tail` below, so on a page that hides the topbar
    # (hide_topbar=True) it's kept in the DOM and just visually hidden via
    # CSS, rather than omitted outright — omitting it would make that wiring
    # script crash on a null element and silently break other unrelated JS
    # (the scroll-in animations) further down the same script block.
    topbar_style = ' style="display:none"' if hide_topbar else ""
    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kubera</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="topbar"{topbar_style}>
    <button id="menu-btn" class="menu-btn">☰</button>
    <div class="topbar-title-group">
        <span class="topbar-title" style="color:inherit;flex:none">KUBERA</span>
        <span class="topbar-sub">Teen Finance</span>
    </div>
    <button id="bell-btn" class="bell-btn">🔔{bell_dot}</button>
</div>
<div id="nav-overlay" class="nav-overlay"></div>
<nav id="nav-drawer" class="nav-drawer">
    <a href="/switch-view/teen">Switch to Teen view</a>
    <a href="/switch-view/parent">Switch to Parent view</a>
</nav>
<div id="bell-overlay" class="nav-overlay"></div>
<div id="bell-panel" class="bell-panel">
    <p class="card-title">Notifications</p>
    <ul>{notif_list}</ul>
</div>
<div id="achv-stage" class="achv-stage">
    <div id="achv-fountain" class="achv-fountain"></div>
    <div id="achv-modal" class="achv-modal treasure-card">
        <div class="treasure-rays"></div>
        <span class="treasure-corner tc-tl">🌀</span>
        <span class="treasure-corner tc-tr">🌀</span>
        <span class="treasure-corner tc-bl">🌀</span>
        <span class="treasure-corner tc-br">🌀</span>
        <div class="treasure-content">
            <div class="achv-icon" id="achv-icon">🏆</div>
            <h2 class="achv-title" id="achv-title">Achievement!</h2>
            <p class="achv-sub" id="achv-sub">+0 Kubera Coins</p>
            <p class="achv-extra" id="achv-extra"></p>
            <button class="achv-close btn-hero" id="achv-close">Nice!</button>
        </div>
    </div>
</div>
<script>
window.showAchievements = function(cards) {{
    var stage = document.getElementById('achv-stage');
    var fountain = document.getElementById('achv-fountain');
    var iconEl = document.getElementById('achv-icon');
    var titleEl = document.getElementById('achv-title');
    var subEl = document.getElementById('achv-sub');
    var extraEl = document.getElementById('achv-extra');
    var closeBtn = document.getElementById('achv-close');
    var queue = cards.slice();

    function spawnCoins() {{
        var spawner = setInterval(function() {{
            var coin = document.createElement('span');
            coin.className = 'coin-particle';
            coin.textContent = '🪙';
            coin.style.setProperty('--dx', ((Math.random() * 2 - 1) * 130) + 'px');
            coin.style.setProperty('--rise', (-(130 + Math.random() * 90)) + 'px');
            coin.style.setProperty('--rot', ((Math.random() * 2 - 1) * 360) + 'deg');
            coin.style.setProperty('--dur', (1.3 + Math.random() * 0.9) + 's');
            fountain.appendChild(coin);
            setTimeout(function() {{ coin.remove(); }}, 2500);
        }}, 90);
        setTimeout(function() {{ clearInterval(spawner); }}, 3000);
    }}

    function countUp(target) {{
        var start = null;
        var duration = 2600;
        function step(ts) {{
            if (!start) {{ start = ts; }}
            var p = Math.min((ts - start) / duration, 1);
            subEl.textContent = '+' + Math.round(target * p).toLocaleString() + ' Kubera Coins';
            if (p < 1) {{ requestAnimationFrame(step); }}
        }}
        requestAnimationFrame(step);
    }}

    function showNext() {{
        if (queue.length === 0) {{
            stage.classList.remove('open');
            fountain.innerHTML = '';
            return;
        }}
        var card = queue.shift();
        iconEl.textContent = card.icon;
        titleEl.textContent = card.title;
        extraEl.textContent = card.extra || '';
        stage.classList.add('open');
        fountain.innerHTML = '';
        spawnCoins();
        countUp(card.amount);
    }}

    closeBtn.onclick = showNext;
    showNext();
}};
</script>
<div class="container">
"""
    tail = """
</div>
<script>
(function() {
  function wire(btn, panel, overlay) {
    btn.addEventListener('click', function() {
      panel.classList.add('open');
      overlay.classList.add('open');
    });
  }
  var menuBtn = document.getElementById('menu-btn');
  var drawer = document.getElementById('nav-drawer');
  var navOverlay = document.getElementById('nav-overlay');
  var bellBtn = document.getElementById('bell-btn');
  var bellPanel = document.getElementById('bell-panel');
  var bellOverlay = document.getElementById('bell-overlay');

  function closeAll() {
    drawer.classList.remove('open');
    navOverlay.classList.remove('open');
    bellPanel.classList.remove('open');
    bellOverlay.classList.remove('open');
  }

  wire(menuBtn, drawer, navOverlay);
  wire(bellBtn, bellPanel, bellOverlay);
  navOverlay.addEventListener('click', closeAll);
  bellOverlay.addEventListener('click', closeAll);
  var links = drawer.querySelectorAll('a');
  for (var i = 0; i < links.length; i++) { links[i].addEventListener('click', closeAll); }

  var animated = document.querySelectorAll('.animate-in');
  if ('IntersectionObserver' in window) {
    var scrollObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
        }
      });
    }, { threshold: 0.4 });
    animated.forEach(function(el) { scrollObs.observe(el); });
  } else {
    animated.forEach(function(el) { el.classList.add('in-view'); });
  }
})();
</script>
</body>
</html>"""
    return head + body + action_footer + tail

@app.route("/")
def home():
    anon_id = session["anon_id"]

    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
    balance = wallet.data["balance"]

    coins = supabase.table("kubera_coins").select("*").eq("anon_id", anon_id).single().execute().data
    goal_pct = min(100, round(coins["current_coins"] / coins["max_coins"] * 100)) if coins["max_coins"] else 0
    edit_link = '<a class="edit-link" href="/goal/edit">Edit</a>'
    main_goal_card = f"""
    <div class="hero-card hero-goal">
        <div class="goal-orb"></div>
        <div class="goal-body">
            <p class="goal-label">My Macro Goal</p>
            <div class="goal-name-row">
                <h2 class="goal-name-text">{coins['goal_name']}</h2>
                {edit_link}
            </div>
            <div class="goal-progress-wrap">
                <div class="goal-ticks"><span>50%</span><span>75%</span><span>100%</span></div>
                <div class="goal-track"><div class="goal-fill" style="width:{goal_pct}%"></div></div>
            </div>
            <p class="goal-coins-text">{coins['current_coins']:,} / {coins['max_coins']:,} Kubera Coins</p>
        </div>
    </div>
    """

    milestone_rows = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).order("created_at").execute().data

    if session["view_mode"] == "parent":
        badge_rows = supabase.table("kubera_badges").select("*").eq("anon_id", anon_id).order("earned_date").execute().data
        badges_html = badge_treasure_grid_html(badge_rows)

        newly_claimed = [m for m in milestone_rows if m["status"] == "claimed" and not m["seen_by_parent"]]
        milestone_toast_block = ""
        if newly_claimed:
            lines = [f"📋 Your child sent in \"{m['title']}\" for you to verify!" for m in newly_claimed]
            for m in newly_claimed:
                supabase.table("kubera_milestones").update({"seen_by_parent": True}).eq("id", m["id"]).execute()
            milestone_toast_block = toast_html("milestone-claimed-toast", lines)

        all_reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).order("created_at", desc=True).execute().data
        pending_reqs = [r for r in all_reqs if r["status"] == "pending"]
        approved_reqs = [r for r in all_reqs if r["status"] == "approved"]
        declined_reqs = [r for r in all_reqs if r["status"] == "declined"]

        pending_ms = [m for m in milestone_rows if m["status"] == "pending"]
        claimed_ms = [m for m in milestone_rows if m["status"] == "claimed"]
        verified_ms = [m for m in milestone_rows if m["status"] == "verified"]

        # ---- Placards: Approval Needed / Milestone Ready / Insight, in that
        # priority order — Insight always last if either action card is present,
        # Insight-only if neither is ----
        streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data
        all_expenses = supabase.table("kubera_expenses").select("*").eq("anon_id", anon_id).execute().data
        insight_lines = generate_insights(balance, streak, all_expenses, milestone_rows)
        insight_card = f"""
        <div class="card card-red placard">
            <span class="placard-holo-bar"><span class="placard-holo-sheen"></span></span>
            <p class="card-title">🧭 Insight</p>
            {"".join(f'<p class="placard-line">{line}</p>' for line in insight_lines)}
        </div>
        """

        payment_card = ""
        if pending_reqs:
            if len(pending_reqs) == 1:
                r = pending_reqs[0]
                req_summary = f"₹{r['amount']} at {r['payee'] or 'cash'} is waiting for your approval."
            else:
                oldest = pending_reqs[-1]
                req_summary = f"{len(pending_reqs)} requests waiting — oldest: ₹{oldest['amount']} at {oldest['payee'] or 'cash'}."
            payment_card = f"""
            <div class="card card-blue placard">
                <span class="placard-holo-bar"><span class="placard-holo-sheen"></span></span>
                <p class="card-title">💳 Approval Needed</p>
                <p class="placard-line">{req_summary}</p>
                <a class="placard-link" href="#requests-section">Review requests →</a>
            </div>
            """

        milestone_card = ""
        if claimed_ms:
            if len(claimed_ms) == 1:
                m = claimed_ms[0]
                ms_summary = f"\"{m['title']}\" is ready for you to verify."
            else:
                oldest = claimed_ms[0]
                ms_summary = f"{len(claimed_ms)} milestones ready to verify — oldest: \"{oldest['title']}\"."
            milestone_card = f"""
            <div class="card card-gold placard">
                <span class="placard-holo-bar"><span class="placard-holo-sheen"></span></span>
                <p class="card-title">📋 Milestone Ready</p>
                <p class="placard-line">{ms_summary}</p>
                <a class="placard-link" href="#milestones-section">Review milestones →</a>
            </div>
            """

        placard_row = f'<div class="placard-row">{payment_card}{milestone_card}{insight_card}</div>'

        overview_section = f"""
        <div id="overview-section">
        {placard_row}
        <p class="section-heading">👋 Overview</p>
        {main_goal_card}
        <div class="card card-wallet-bg">
            <p class="card-title">Wallet left with your teen</p>
            <p class="card-value">₹{balance}</p>
            <div style="text-align:right;margin-top:10px">
                <a class="btn-small btn-small-refill" href="/parent/wallet/refill">🔄 Refill Wallet</a>
            </div>
        </div>
        {milestone_toast_block}
        <div class="card card-badges-bg">
            <p class="card-title">Badges earned</p>
            {badges_html}
        </div>
        </div>
        """

        # ---- Requests section (used to be its own page, now scrolled to) ----
        pending_req_items = "".join(f"""
        <div class="item-card item-card-blue">
            <span class="item-card-icon animate-in">⏳</span>
            <div class="item-card-body">
                <p class="item-card-title">₹{r['amount']} at {r['payee'] or 'cash'}</p>
                <p class="item-card-meta">{r['category']}</p>
            </div>
            <div class="item-card-action">
                <form method="POST" action="/parent/requests/{r['id']}/approve" style="display:inline">
                    <button type="submit" class="btn-small btn-small-approve">Approve</button>
                </form>
                <form method="POST" action="/parent/requests/{r['id']}/decline" style="display:inline">
                    <button type="submit" class="btn-small btn-small-decline">Decline</button>
                </form>
            </div>
        </div>
        """ for r in pending_reqs) or '<p style="text-align:center;color:var(--text-muted)">Nothing pending right now.</p>'

        approved_req_items = "".join(f"""
        <div class="item-card item-card-green">
            <span class="item-card-icon animate-in">✅</span>
            <div class="item-card-body">
                <p class="item-card-title">₹{r['amount']} at {r['payee'] or 'cash'}</p>
                <p class="item-card-meta">{r['category']}</p>
            </div>
        </div>
        """ for r in approved_reqs) or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'

        declined_req_items = "".join(f"""
        <div class="item-card item-card-red">
            <span class="item-card-icon animate-in">❌</span>
            <div class="item-card-body">
                <p class="item-card-title">₹{r['amount']} at {r['payee'] or 'cash'}</p>
                <p class="item-card-meta">{r['category']}</p>
            </div>
        </div>
        """ for r in declined_reqs) or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'

        requests_section = f"""
        <div id="requests-section">
        <p class="section-heading">📝 Requests</p>
        <p style="text-align:center;color:var(--text-muted);margin-top:-8px">Wallet balance: ₹{balance} left.</p>
        {pending_req_items}
        <div class="card">
            <p class="card-title">Approved</p>
            {approved_req_items}
        </div>
        <div class="card">
            <p class="card-title">Declined</p>
            {declined_req_items}
        </div>
        </div>
        """

        # ---- Milestones section (used to be its own page, now scrolled to) ----
        pending_ms_items = "".join(f"""
        <div class="item-card">
            <span class="item-card-icon animate-in">🎯</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta item-card-reward">+{m['coin_reward']} coins — not claimed yet</p>
            </div>
        </div>
        """ for m in pending_ms) or '<p style="text-align:center;color:var(--text-muted)">None.</p>'

        claimed_ms_items = "".join(f"""
        <div class="item-card item-card-gold item-card-actions-below">
            <span class="item-card-icon animate-in">📋</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta item-card-reward">+{m['coin_reward']} coins</p>
                <p class="item-card-meta">Your teen says: "{m['note']}"</p>
            </div>
            <div class="item-card-action">
                <form method="POST" action="/parent/milestones/{m['id']}/verify" style="display:inline">
                    <button type="submit" class="btn-small btn-small-approve">Verify</button>
                </form>
                <form method="POST" action="/parent/milestones/{m['id']}/reject" style="display:inline">
                    <button type="submit" class="btn-small btn-small-decline">Reject</button>
                </form>
            </div>
        </div>
        """ for m in claimed_ms) or '<p style="text-align:center;color:var(--text-muted)">None.</p>'

        verified_ms_items = "".join(f"""
        <div class="item-card item-card-gold">
            <span class="item-card-icon animate-in">🏆</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta item-card-reward">+{m['coin_reward']} coins — verified {m['verified_at'][:10]}</p>
            </div>
        </div>
        """ for m in verified_ms) or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'

        milestones_section = f"""
        <div id="milestones-section">
        <p class="section-heading">🎯 Milestones</p>
        <div class="card">
            <p class="card-title">Waiting on your teen</p>
            {pending_ms_items}
        </div>
        <div class="card">
            <p class="card-title">Ready to verify</p>
            {claimed_ms_items}
        </div>
        <div class="card card-gold">
            <p class="card-title">Verified</p>
            {verified_ms_items}
        </div>
        <div class="card">
            <p class="card-title">Add a new milestone</p>
            <form method="POST" action="/parent/milestones">
                <label>Title: <input type="text" name="title" required></label><br>
                <label>Coin reward: <input type="number" name="coin_reward" min="1" required></label><br>
                <button type="submit" class="btn-primary">Add milestone</button>
            </form>
        </div>
        </div>
        """

        view_block = overview_section + requests_section + milestones_section
    else:
        badge_rows = supabase.table("kubera_badges").select("*").eq("anon_id", anon_id).order("earned_date").execute().data
        teen_session = supabase.table("kubera_sessions").select("kubera_intro_seen_date, last_reviewed_at").eq("anon_id", anon_id).single().execute().data
        kubera_seen_today = teen_session["kubera_intro_seen_date"] == today_utc().isoformat()
        story_block = story_row_html(kubera_seen_today, badge_rows) + story_overlay_html(badge_rows)

        # Re-engagement nudge: a hard-to-miss banner (not a quiet toast) that
        # fires on EVERY app-open as long as there's a real payment the teen
        # hasn't reviewed yet — not a visit counter. Visiting /expenses/today
        # (which only the banner links to) marks everything up to now as
        # reviewed; a brand-new payment makes it unreviewed again. A fresh
        # account with no expenses yet never shows it, so it never competes
        # with the first-time Kubera intro story.
        latest_expense = supabase.table("kubera_expenses").select("created_at").eq("anon_id", anon_id).order("created_at", desc=True).limit(1).execute().data
        last_reviewed_at = teen_session["last_reviewed_at"]
        if latest_expense and (last_reviewed_at is None or latest_expense[0]["created_at"] > last_reviewed_at):
            story_block += reengage_banner_html()

        all_reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).execute().data

        pending_reqs = [r for r in all_reqs if r["status"] == "pending"]
        pending_block = "".join(f"""
        <div class="item-card item-card-blue">
            <span class="item-card-icon animate-in">⏳</span>
            <div class="item-card-body">
                <p class="item-card-title">₹{r['amount']} at {r['payee'] or 'cash'}</p>
                <p class="item-card-meta">Waiting for your parent to approve</p>
            </div>
        </div>
        """ for r in pending_reqs)

        newly_resolved = [r for r in all_reqs if r["status"] != "pending" and not r["seen_by_teen"]]
        toast_block = ""
        if newly_resolved:
            toast_lines = []
            for r in newly_resolved:
                label = r["payee"] or "cash"
                if r["status"] == "approved":
                    toast_lines.append(f"✅ Your parent approved ₹{r['amount']} at {label}!")
                else:
                    toast_lines.append(f"❌ Your parent declined ₹{r['amount']} at {label}.")
                supabase.table("kubera_approval_requests").update({"seen_by_teen": True}).eq("id", r["id"]).execute()
            toast_block = toast_html("approval-toast", toast_lines)

        newly_verified = [m for m in milestone_rows if m["status"] == "verified" and not m["seen_by_teen"]]
        milestone_toast_block = ""
        if newly_verified:
            lines = [f"🎉 Your parent verified \"{m['title']}\"! +{m['coin_reward']} Kubera Coins." for m in newly_verified]
            for m in newly_verified:
                supabase.table("kubera_milestones").update({"seen_by_teen": True}).eq("id", m["id"]).execute()
            milestone_toast_block = toast_html("milestone-verified-toast", lines)

        streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data
        avail_shields = available_shields(anon_id, today_utc())
        shields_count = len(avail_shields)

        if shields_count > 0:
            soonest_days = min((parse_date(s["earned_date"]) + timedelta(days=30) - today_utc()).days for s in avail_shields)

        if streak["debt_remaining"] > 0:
            debt_card = f"""
            <div class="hero-card hero-debt">
                <p class="hero-title">⚠️ Refill Mode</p>
                <p style="margin:0">₹{streak['debt_remaining']} debt left. Streak frozen at Day {streak['streak_count']}, savings frozen at ₹{streak['cushion_balance']}.</p>
            </div>
            """
        else:
            debt_card = ""

        cushion_wallet_row = f"""
        <div class="hero-row">
            <div class="hero-card hero-indigo">
                <p class="hero-title">Wallet</p>
                <p class="hero-sub">(Spendable)</p>
                <p class="hero-value">₹{balance}</p>
                <a class="hero-link" href="#track-section">View activity</a>
            </div>
            <div class="hero-card hero-green">
                <p class="hero-title">Savings</p>
                <p class="hero-sub">(Real Money)</p>
                <p class="hero-value">₹{streak['cushion_balance']}</p>
                <a class="hero-link" href="/cushion/spend">💸 Withdraw</a>
            </div>
        </div>
        """

        habits_card = f"""
        <p class="section-heading" style="margin-bottom:6px">Daily Habits</p>
        <div class="habits-row">
            <div class="habit-stat">
                <span class="habit-big-icon flame-icon animate-in">🔥</span>
                <div class="habit-text">
                    <p class="habit-stat-label">🔥 Streak</p>
                    <p class="habit-stat-value">{streak['streak_count']} Days</p>
                </div>
            </div>
            <div class="habit-divider"></div>
            <div class="habit-stat">
                <span class="habit-big-icon shield-icon animate-in">
                    <svg viewBox="0 0 24 24">
                        <defs>
                            <radialGradient id="shield-glossy-gold" cx="32%" cy="26%" r="75%">
                                <stop offset="0%" stop-color="#FEF3C7"></stop>
                                <stop offset="55%" stop-color="#EAB308"></stop>
                                <stop offset="100%" stop-color="#92400E"></stop>
                            </radialGradient>
                        </defs>
                        <path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3z" fill="url(#shield-glossy-gold)"></path>
                    </svg>
                </span>
                <div class="habit-text">
                    <p class="habit-stat-label">🛡️ Shields</p>
                    <p class="habit-stat-value">{shields_count}/2 Available</p>
                    <p class="habit-stat-sub">{("Expiry: " + str(soonest_days) + " days") if shields_count > 0 else "None earned yet"}</p>
                </div>
            </div>
        </div>
        """

        goal_section = f"""
        <div id="goal-section">
        {story_block}
        <p class="section-heading">🎯 Goal Pot</p>
        {pending_block}
        {toast_block}
        {milestone_toast_block}
        {debt_card}
        {cushion_wallet_row}
        {main_goal_card}
        {habits_card}
        <div class="checkin-heading">
            <h3>Daily Check-In</h3>
            <span class="checkin-badge">✓</span>
        </div>
        <a class="btn-hero" href="/checkin">Daily Savings</a>
        </div>
        """

        # ---- Track & Pay section (used to be its own page, now scrolled to) ----
        expenses = supabase.table("kubera_expenses").select("*").eq("anon_id", anon_id).order("created_at", desc=True).execute().data
        totals = {}
        for e in expenses:
            totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
        bubbles_html = category_bubbles_html(totals)

        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        monthly_total = sum(e["amount"] for e in expenses if e["created_at"] >= cutoff)

        monthly_html = ""
        if monthly_total > 0:
            compare_items = [
                (150, "waffle", "waffles"),
                (350, "movie ticket", "movie tickets"),
                (2000, "pair of wireless headphones", "pairs of wireless headphones"),
                (3500, "foldable magnetic charger", "foldable magnetic chargers"),
                (6000, "pair of PUMA sneakers", "pairs of PUMA sneakers"),
            ]
            price, singular, plural = compare_items[0]
            for item_price, item_singular, item_plural in compare_items:
                if monthly_total >= item_price:
                    price, singular, plural = item_price, item_singular, item_plural
            count = round(monthly_total / price)
            label = singular if count == 1 else plural
            monthly_html = f'<p style="text-align:center;color:var(--text-muted);font-size:13px;margin:-6px 0 0">This month: ₹{monthly_total} — about {count} {label}.</p>'

        transactions_html = "".join(txn_row_html(e) for e in expenses[:3])
        view_all_link = '<p style="text-align:center;margin:12px 0 0"><a href="/transactions">View all transactions</a></p>' if len(expenses) > 3 else ""

        track_section = f"""
        <div id="track-section">
        <p class="section-heading">💳 Track &amp; Pay</p>
        <a class="btn-primary" href="/pay">Pay via Kubera</a>
        <p></p>
        <a class="btn-primary" style="background:var(--green)" href="/log-cash-expense">Log Cash Expense</a>
        <div class="card" style="margin-top:16px">
            <p class="card-title">Where did my money go?</p>
            {bubbles_html}
            {monthly_html}
        </div>
        <div class="card">
            <p class="card-title">Recent transactions</p>
            <ul class="txn-list">{transactions_html or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'}</ul>
            {view_all_link}
        </div>
        </div>
        """

        # ---- Rewards section (used to be its own page, now scrolled to) ----
        reward_badges_html = badge_treasure_grid_html(badge_rows)

        reward_rows = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).order("created_at").execute().data
        pending_m = [m for m in reward_rows if m["status"] == "pending"]
        claimed_m = [m for m in reward_rows if m["status"] == "claimed"]
        verified_m = [m for m in reward_rows if m["status"] == "verified"]

        pending_m_items = "".join(f"""
        <div class="item-card item-card-gold">
            <span class="item-card-icon animate-in">🎯</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta item-card-reward">+{m['coin_reward']} coins</p>
            </div>
            <label class="item-card-action">
                <input type="checkbox" class="claim-checkbox" data-id="{m['id']}" data-title="{m['title'].replace('"', '&quot;')}" data-reward="{m['coin_reward']}">
            </label>
        </div>
        """ for m in pending_m) or '<p style="text-align:center;color:var(--text-muted)">None right now.</p>'

        claimed_m_items = "".join(f"""
        <div class="item-card item-card-blue">
            <span class="item-card-icon animate-in">⏳</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta">Your note: "{m['note']}"</p>
            </div>
        </div>
        """ for m in claimed_m) or '<p style="text-align:center;color:var(--text-muted)">None.</p>'

        verified_m_items = "".join(f"""
        <div class="item-card item-card-gold">
            <span class="item-card-icon animate-in">🏆</span>
            <div class="item-card-body">
                <p class="item-card-title">{m['title']}</p>
                <p class="item-card-meta item-card-reward">+{m['coin_reward']} coins — verified</p>
            </div>
        </div>
        """ for m in verified_m) or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'

        rewards_section = f"""
        <div id="rewards-section">
        <p class="section-heading">🏆 Rewards and Achievements</p>
        <div class="card card-badges-bg">
            <p class="card-title">My Badges</p>
            {reward_badges_html}
        </div>
        <div class="card">
            <p class="card-title">Milestones to be Covered</p>
            {pending_m_items}
        </div>
        <div class="card">
            <p class="card-title">Waiting on Your Parent</p>
            {claimed_m_items}
        </div>
        <div class="card card-gold">
            <p class="card-title">Verified Milestones</p>
            {verified_m_items}
        </div>
        </div>

        <div id="claim-overlay" class="nav-overlay"></div>
        <div id="claim-modal" class="modal">
            <h3 id="claim-modal-title">Milestone</h3>
            <p id="claim-modal-reward" class="pill"></p>
            <form id="claim-modal-form" method="POST" action="">
                <label>Add a brief note for your parent (e.g. "Scored 92% in pre-boards"):<br>
                    <input type="text" name="note" id="claim-modal-note" required>
                </label>
                <p></p>
                <button type="submit" class="btn-primary">Submit for Verification</button>
            </form>
            <p><a href="#" id="claim-modal-cancel">Cancel</a></p>
        </div>
        <script>
        (function() {{
            var checkboxes = document.querySelectorAll('.claim-checkbox');
            var overlay = document.getElementById('claim-overlay');
            var modal = document.getElementById('claim-modal');
            var form = document.getElementById('claim-modal-form');
            var titleEl = document.getElementById('claim-modal-title');
            var rewardEl = document.getElementById('claim-modal-reward');
            var cancelLink = document.getElementById('claim-modal-cancel');

            function openModal(id, title, reward) {{
                titleEl.textContent = title;
                rewardEl.textContent = reward + ' Kubera Coins';
                form.action = '/milestones/' + id + '/claim';
                overlay.classList.add('open');
                modal.classList.add('open');
            }}
            function closeModal() {{
                overlay.classList.remove('open');
                modal.classList.remove('open');
                checkboxes.forEach(function(cb) {{ cb.checked = false; }});
            }}

            checkboxes.forEach(function(cb) {{
                cb.addEventListener('change', function() {{
                    if (cb.checked) {{
                        openModal(cb.dataset.id, cb.dataset.title, cb.dataset.reward);
                    }}
                }});
            }});
            overlay.addEventListener('click', closeModal);
            cancelLink.addEventListener('click', function(e) {{
                e.preventDefault();
                closeModal();
            }});
        }})();
        </script>
        """

        view_block = goal_section + track_section + rewards_section

    body = f"""
    <p class="pill">{session['view_mode'].title()} view</p>
    {view_block}
    """
    return page(body, active_tab="goal")

@app.route("/transactions")
def transactions():
    anon_id = session["anon_id"]
    expenses = supabase.table("kubera_expenses").select("*").eq("anon_id", anon_id).order("created_at", desc=True).execute().data
    transactions_html = "".join(txn_row_html(e) for e in expenses)

    return page(f"""
    <div class="page-header-row">
        <a class="btn-primary" href="/#track-section">← Back</a>
        <input type="text" id="txn-search" class="page-header-search" placeholder="Search by payee, category, or amount" autocomplete="off">
    </div>
    <div class="card">
        <ul class="txn-list" id="txn-list">{transactions_html or '<p style="text-align:center;color:var(--text-muted)">None yet.</p>'}</ul>
        <p id="txn-no-results" style="text-align:center;color:var(--text-muted);display:none">No matching transactions.</p>
    </div>
    <script>
    (function() {{
        var input = document.getElementById('txn-search');
        var rows = document.querySelectorAll('#txn-list .txn-row');
        var noResults = document.getElementById('txn-no-results');
        input.addEventListener('input', function() {{
            var q = input.value.trim().toLowerCase();
            var visibleCount = 0;
            rows.forEach(function(row) {{
                var match = row.textContent.toLowerCase().indexOf(q) !== -1;
                row.style.display = match ? '' : 'none';
                if (match) visibleCount++;
            }});
            noResults.style.display = (q && visibleCount === 0) ? '' : 'none';
        }});
    }})();
    </script>
    """, active_tab="track", hide_topbar=True)

@app.route("/expenses/today")
def expenses_today():
    anon_id = session["anon_id"]
    supabase.table("kubera_sessions").update({"last_reviewed_at": datetime.now(timezone.utc).isoformat()}).eq("anon_id", anon_id).execute()

    today_start = datetime(today_utc().year, today_utc().month, today_utc().day, tzinfo=timezone.utc).isoformat()
    expenses = supabase.table("kubera_expenses").select("*").eq("anon_id", anon_id).gte("created_at", today_start).order("created_at", desc=True).execute().data
    rows_html = "".join(txn_row_html(e) for e in expenses)

    return page(f"""
    <h2>Today's expenses</h2>
    <p style="color:var(--text-muted);margin-top:-8px">Anything look miscategorized? Tap Edit to fix it.</p>
    <div class="card">
        <ul class="txn-list">{rows_html or '<p style="text-align:center;color:var(--text-muted)">Nothing logged yet today.</p>'}</ul>
    </div>
    <p><a class="btn-primary" href="/#track-section">Back</a></p>
    """, active_tab="track")

@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
def edit_expense(expense_id):
    anon_id = session["anon_id"]
    try:
        expense = supabase.table("kubera_expenses").select("*").eq("id", expense_id).eq("anon_id", anon_id).single().execute().data
    except Exception:
        return page("<p>That expense doesn't exist.</p><a class='btn-primary' href='/expenses/today'>Back</a>", active_tab="track")

    if request.method == "POST":
        category = request.form["category"]
        supabase.table("kubera_expenses").update({"category": category}).eq("id", expense_id).execute()
        return redirect("/expenses/today")

    options = "".join(
        f'<option value="{c}"{" selected" if c == expense["category"] else ""}>{c.title()}</option>'
        for c in CATEGORIES
    )
    payee = expense["payee"] or "Cash expense"
    return page(f"""
    <h2>Edit category</h2>
    <div class="card">
        <p class="card-title">{payee}</p>
        <p class="card-value">₹{expense['amount']}</p>
    </div>
    <form method="POST">
        <label>Category<select name="category">{options}</select></label>
        <button type="submit" class="btn-primary">Save</button>
    </form>
    <p><a class="btn-primary" href="/expenses/today">Cancel</a></p>
    """, active_tab="track")

@app.route("/goal/edit", methods=["GET", "POST"])
def edit_goal():
    anon_id = session["anon_id"]

    if request.method == "POST":
        name = request.form["goal_name"].strip()
        if name:
            supabase.table("kubera_coins").update({"goal_name": name}).eq("anon_id", anon_id).execute()
        return redirect("/")

    coins = supabase.table("kubera_coins").select("goal_name").eq("anon_id", anon_id).single().execute().data
    return page(f"""
    <h2>What are you saving for?</h2>
    <form method="POST">
        <label>Goal name: <input type="text" name="goal_name" value="{coins['goal_name']}" required></label><br>
        <button type="submit" class="btn-primary">Save</button>
    </form>
    <p><a href="/">Cancel</a></p>
    """, active_tab="goal")

@app.route("/pay")
def pay():
    rows = "".join(f"""
    <a href="/pay/{p}" class="payee-row">
        {payee_avatar_html(p, 56)}
        <div class="payee-row-body">
            <p class="payee-row-name">{p}</p>
            <p class="payee-row-tag">{(PAYEE_CATEGORY.get(p) or "pick category after").title()}</p>
        </div>
        <span class="payee-row-chevron">›</span>
    </a>
    """ for p in PAYEES)
    # Three ways to pay (FamPay/GPay-style), all purely mocked UI feeding
    # the exact same /pay/<payee> confirm-and-pay flow below — no real
    # payment gateway, so no new backend risk and no "is this app actually
    # processing payments" question for a judge. The category guess on the
    # confirm screen (guess_category()) works off whatever name/ID gets
    # typed here too, same as the existing preset payees.
    return page(f"""
    <h2>Pay with Kubera</h2>
    <div class="pay-tabs">
        <button type="button" class="pay-tab active" data-tab="qr">📷 Scan QR</button>
        <button type="button" class="pay-tab" data-tab="number">📱 Number</button>
        <button type="button" class="pay-tab" data-tab="upi">🆔 UPI ID</button>
    </div>

    <div class="pay-tab-panel active" id="pay-tab-qr">
        <div class="qr-scan-frame">
            <span class="qr-corner qr-corner-tl"></span>
            <span class="qr-corner qr-corner-tr"></span>
            <span class="qr-corner qr-corner-bl"></span>
            <span class="qr-corner qr-corner-br"></span>
            <div class="qr-scan-pattern"></div>
            <div class="qr-scan-line"></div>
        </div>
        <p class="qr-scan-hint">Point your camera at a QR code to pay</p>
        <p class="section-heading" style="margin-top:20px">Or pick a contact</p>
        <div class="payee-list">{rows}</div>
    </div>

    <div class="pay-tab-panel" id="pay-tab-number">
        <div class="pay-confirm-card" style="margin-top:0">
            {glossy_icon_html("📱", "blue")}
            <h2 class="pay-confirm-name">Pay to Mobile Number</h2>
            <form class="pay-confirm-form" onsubmit="event.preventDefault(); var v = document.getElementById('pay-number-input').value.trim(); if (v) window.location.href = '/pay/' + encodeURIComponent(v);">
                <label class="pay-amount-label">Mobile Number
                    <input type="tel" id="pay-number-input" class="page-header-search pay-text-input" placeholder="98765 43210" required autofocus>
                </label>
                <button type="submit" class="btn-primary">Continue</button>
            </form>
        </div>
    </div>

    <div class="pay-tab-panel" id="pay-tab-upi">
        <div class="pay-confirm-card" style="margin-top:0">
            {glossy_icon_html("🆔", "blue")}
            <h2 class="pay-confirm-name">Pay via UPI ID</h2>
            <form class="pay-confirm-form" onsubmit="event.preventDefault(); var v = document.getElementById('pay-upi-input').value.trim(); if (v) window.location.href = '/pay/' + encodeURIComponent(v);">
                <label class="pay-amount-label">UPI ID
                    <input type="text" id="pay-upi-input" class="page-header-search pay-text-input" placeholder="name@bank" required autofocus>
                </label>
                <button type="submit" class="btn-primary">Continue</button>
            </form>
        </div>
    </div>

    <script>
    (function() {{
        var tabs = document.querySelectorAll('.pay-tab');
        var panels = {{
            qr: document.getElementById('pay-tab-qr'),
            number: document.getElementById('pay-tab-number'),
            upi: document.getElementById('pay-tab-upi')
        }};
        tabs.forEach(function(tab) {{
            tab.addEventListener('click', function() {{
                tabs.forEach(function(t) {{ t.classList.remove('active'); }});
                tab.classList.add('active');
                Object.keys(panels).forEach(function(k) {{ panels[k].classList.remove('active'); }});
                panels[tab.dataset.tab].classList.add('active');
            }});
        }});
    }})();
    </script>
    """, active_tab="track")

@app.route("/parent/requests/<int:req_id>/<action>", methods=["POST"])
def parent_request_action(req_id, action):
    anon_id = session["anon_id"]
    req = supabase.table("kubera_approval_requests").select("*").eq("id", req_id).eq("anon_id", anon_id).single().execute().data

    if req["status"] != "pending":
        return page("<p>This request was already handled.</p><a class='btn-primary' href='/#requests-section'>Back</a>")

    if action == "decline":
        supabase.table("kubera_approval_requests").update({"status": "declined"}).eq("id", req_id).execute()
        return page("<p>Request declined.</p><a class='btn-primary' href='/#requests-section'>Back</a>")

    if action == "approve":
        wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
        balance = wallet.data["balance"]

        if req["amount"] > balance:
            return page(f"<p>Can't approve — teen only has ₹{balance} left, request was for ₹{req['amount']}.</p><a class='btn-primary' href='/#requests-section'>Back</a>")

        supabase.table("kubera_expenses").insert({
            "anon_id": anon_id,
            "amount": req["amount"],
            "payee": req["payee"],
            "category": req["category"],
        }).execute()

        supabase.table("kubera_wallets").update({"balance": balance - req["amount"]}).eq("anon_id", anon_id).execute()
        supabase.table("kubera_approval_requests").update({"status": "approved"}).eq("id", req_id).execute()

        return page("<p>Approved — expense logged, wallet updated.</p><a class='btn-primary' href='/#requests-section'>Back</a>")

    return page("<p>Unknown action.</p><a class='btn-primary' href='/#requests-section'>Back</a>")

@app.route("/parent/wallet/refill", methods=["GET", "POST"])
def refill_wallet():
    anon_id = session["anon_id"]
    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute().data

    if request.method == "POST":
        amount = int(request.form["amount"])
        if amount > 0:
            supabase.table("kubera_wallets").update({"balance": wallet["balance"] + amount}).eq("anon_id", anon_id).execute()
        return redirect("/#overview-section")

    return page(f"""
    <div class="pay-confirm-card">
        {glossy_icon_html("🔄", "blue")}
        <h2 class="pay-confirm-name">Refill Wallet</h2>
        <p style="color:var(--text-muted);margin:-8px 0 16px;text-align:center">Current balance: ₹{wallet['balance']}. Add money for your teen to spend.</p>
        <form method="POST" class="pay-confirm-form">
            <label class="pay-amount-label">Amount
                <div class="pay-amount-field">
                    <span class="pay-amount-currency">₹</span>
                    <input type="number" name="amount" min="1" required autofocus>
                </div>
            </label>
            <button type="submit" class="btn-primary">Add to Wallet</button>
        </form>
    </div>
    """)

@app.route("/parent/milestones", methods=["POST"])
def parent_milestones():
    anon_id = session["anon_id"]
    title = request.form["title"]
    coin_reward = int(request.form["coin_reward"])
    supabase.table("kubera_milestones").insert({
        "anon_id": anon_id,
        "title": title,
        "coin_reward": coin_reward,
    }).execute()
    return redirect("/#milestones-section")

@app.route("/parent/milestones/<milestone_id>/verify", methods=["POST"])
def verify_milestone(milestone_id):
    anon_id = session["anon_id"]
    try:
        m = supabase.table("kubera_milestones").select("*").eq("id", milestone_id).eq("anon_id", anon_id).single().execute().data
    except Exception:
        return page("<p>That milestone doesn't exist.</p><a class='btn-primary' href='/#milestones-section'>Back</a>")

    if m["status"] != "claimed":
        return page("<p>This milestone hasn't been claimed by your teen yet.</p><a class='btn-primary' href='/#milestones-section'>Back</a>")

    supabase.table("kubera_milestones").update({
        "status": "verified",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", milestone_id).execute()

    award_coins(anon_id, m["coin_reward"])
    supabase.table("kubera_badges").insert({"anon_id": anon_id, "badge_type": f"trophy_{m['coin_reward']}"}).execute()

    achv_cards = [{"icon": "🏆", "title": m["title"], "amount": m["coin_reward"], "extra": ""}]
    achv_script = f"<script>showAchievements({json.dumps(achv_cards)});</script>"
    return page(f"<p>Verified! +{m['coin_reward']} Kubera Coins.</p><a class='btn-primary' href='/#milestones-section'>Back</a>{achv_script}")

@app.route("/parent/milestones/<milestone_id>/reject", methods=["POST"])
def reject_milestone(milestone_id):
    anon_id = session["anon_id"]
    try:
        m = supabase.table("kubera_milestones").select("*").eq("id", milestone_id).eq("anon_id", anon_id).single().execute().data
    except Exception:
        return page("<p>That milestone doesn't exist.</p><a class='btn-primary' href='/#milestones-section'>Back</a>")

    if m["status"] != "claimed":
        return page("<p>This milestone hasn't been claimed by your teen yet.</p><a class='btn-primary' href='/#milestones-section'>Back</a>")

    supabase.table("kubera_milestones").update({"status": "pending"}).eq("id", milestone_id).execute()

    return redirect("/#milestones-section")

@app.route("/milestones")
def milestones():
    # Legacy standalone page — no longer linked from anywhere in the normal
    # flow since Milestones got folded into the one-page scroll (teen:
    # #rewards-section, parent: #milestones-section). Rather than hand-polish
    # a second, parallel bare template that would just drift out of sync
    # with the real one, redirect straight to the already-built, already-
    # verified section so a stray direct link lands somewhere polished.
    anchor = "#milestones-section" if session["view_mode"] == "parent" else "#rewards-section"
    return redirect("/" + anchor)

@app.route("/milestones/<milestone_id>/claim", methods=["GET", "POST"])
def claim_milestone(milestone_id):
    anon_id = session["anon_id"]
    try:
        m = supabase.table("kubera_milestones").select("*").eq("id", milestone_id).eq("anon_id", anon_id).single().execute().data
    except Exception:
        return page("<p>That milestone doesn't exist.</p><a class='btn-primary' href='/#rewards-section'>Back</a>", active_tab="rewards")

    if m["status"] != "pending":
        return page("<p>This milestone isn't waiting to be claimed.</p><a class='btn-primary' href='/#rewards-section'>Back</a>", active_tab="rewards")

    if request.method == "GET":
        return page(f"""
        <h2>{m['title']}</h2>
        <form method="POST">
            <label>Tell your parent what you did: <input type="text" name="note" required></label><br>
            <button type="submit" class="btn-primary">Submit</button>
        </form>
        """, active_tab="rewards")

    note = request.form["note"]
    supabase.table("kubera_milestones").update({
        "status": "claimed",
        "note": note,
    }).eq("id", milestone_id).execute()

    return page("<p>Sent to your parent!</p><a class='btn-primary' href='/#rewards-section'>Back</a>", active_tab="rewards")

@app.route("/pay/<payee>", methods=["GET", "POST"])
def pay_payee(payee):
    if request.method == "POST":
        amount = int(request.form["amount"])
        category = request.form["category"]

        wallet = supabase.table("kubera_wallets").select("balance, approval_threshold").eq("anon_id", session["anon_id"]).single().execute()
        balance = wallet.data["balance"]
        threshold = wallet.data["approval_threshold"]

        if amount > balance:
            return page(f"<p>You only have ₹{balance} left — you can't pay ₹{amount}.</p><a class='btn-primary' href='/pay/{payee}'>Go back</a>", active_tab="track")

        if amount > threshold:
            supabase.table("kubera_approval_requests").insert({
                "anon_id": session["anon_id"],
                "payee": payee,
                "category": category,
                "amount": amount,
            }).execute()
            return page(f"<p>₹{amount} to {payee} is over your ₹{threshold} limit — sent to your parent for approval.</p><a class='btn-primary' href='/'>Back home</a>", active_tab="track")

        supabase.table("kubera_expenses").insert({
            "anon_id": session["anon_id"],
            "amount": amount,
            "payee": payee,
            "category": category,
        }).execute()

        supabase.table("kubera_wallets").update({"balance": balance - amount}).eq("anon_id", session["anon_id"]).execute()

        return redirect("/")

    suggested = guess_category(payee)
    if suggested:
        icon = CATEGORY_ICONS.get(suggested, "💸")
        highlight, dark, glow = CATEGORY_GLOSS[suggested]
        base = CATEGORY_COLORS[suggested]
        category_field = f"""
        <input type="hidden" name="category" value="{suggested}">
        <div class="pay-category-pill" style="background:{highlight};color:{dark}">
            {icon} {suggested.title()} <span class="pay-category-pill-tag">auto-detected</span>
        </div>
        """
    else:
        options = "".join(f'<option value="{c}">{c.title()}</option>' for c in CATEGORIES)
        category_field = f'<label>Category<select name="category">{options}</select></label>'

    return page(f"""
    <div class="pay-confirm-card">
        {payee_avatar_html(payee, 76)}
        <h2 class="pay-confirm-name">{payee}</h2>
        <form method="POST" class="pay-confirm-form">
            <label class="pay-amount-label">Amount
                <div class="pay-amount-field">
                    <span class="pay-amount-currency">₹</span>
                    <input type="number" name="amount" min="1" required autofocus>
                </div>
            </label>
            {category_field}
            <button type="submit" class="btn-primary">Pay {payee}</button>
        </form>
    </div>
    """, active_tab="track")

@app.route("/log-cash-expense", methods=["GET", "POST"])
def log_cash_expense():
    if request.method == "POST":
        amount = int(request.form["amount"])
        category = request.form["category"]

        supabase.table("kubera_expenses").insert({
            "anon_id": session["anon_id"],
            "amount": amount,
            "payee": None,
            "category": category,
        }).execute()

        return redirect("/")

    options = "".join(f'<option value="{c}">{c.title()}</option>' for c in CATEGORIES)
    return page(f"""
    <div class="pay-confirm-card">
        {glossy_icon_html("🧾", "green")}
        <h2 class="pay-confirm-name">Log a Cash Spend</h2>
        <p style="color:var(--text-muted);margin:-8px 0 16px;text-align:center">Spent cash that didn't go through the Pay button? Log it here — this won't touch your wallet balance.</p>
        <form method="POST" class="pay-confirm-form">
            <label class="pay-amount-label">Amount
                <div class="pay-amount-field">
                    <span class="pay-amount-currency">₹</span>
                    <input type="number" name="amount" min="1" required autofocus>
                </div>
            </label>
            <label>Category<select name="category">{options}</select></label>
            <button type="submit" class="btn-primary">Log It</button>
        </form>
    </div>
    """, active_tab="track")

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    anon_id = session["anon_id"]
    today = today_utc()
    streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data

    if request.method == "GET":
        if streak["debt_remaining"] > 0:
            heading = "Refill Mode"
            prompt = f"You're in Refill Mode, owing ₹{streak['debt_remaining']}. Deposit to pay it down (min ₹10)."
            icon, accent = "🛡️", "red"
        else:
            heading = "Daily Check-In"
            prompt = f"Day {streak['streak_count']} streak. Keep it going — minimum ₹10 today."
            icon, accent = "🔥", "blue"
        return page(f"""
        <div class="pay-confirm-card">
            {glossy_icon_html(icon, accent)}
            <h2 class="pay-confirm-name">{heading}</h2>
            <p style="color:var(--text-muted);margin:-8px 0 16px;text-align:center">{prompt}</p>
            <form method="POST" class="pay-confirm-form">
                <label class="pay-amount-label">Amount
                    <div class="pay-amount-field">
                        <span class="pay-amount-currency">₹</span>
                        <input type="number" name="amount" min="10" value="10" required autofocus>
                    </div>
                </label>
                <button type="submit" class="btn-primary">Save</button>
            </form>
        </div>
        """, active_tab="goal")

    last_checkin = parse_date(streak["last_checkin"])
    if last_checkin == today:
        return page("<p>You already checked in today — come back tomorrow!</p><a class='btn-primary' href='/'>Back home</a>", active_tab="goal")

    amount = int(request.form["amount"])
    if amount < 10:
        return page("<p>Minimum deposit is ₹10.</p><a class='btn-primary' href='/checkin'>Go back</a>", active_tab="goal")

    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
    wallet_balance = wallet.data["balance"]
    if amount > wallet_balance:
        return page(f"<p>You only have ₹{wallet_balance} in your wallet — you can't save more than that today.</p><a class='btn-primary' href='/checkin'>Go back</a>", active_tab="goal")

    messages = []
    achievements = []
    debt = streak["debt_remaining"]

    if debt > 0:
        if amount >= debt:
            leftover = amount - debt
            new_debt = 0
            old_cushion = streak["cushion_balance"]
            new_cushion = old_cushion + leftover
            new_streak = streak["streak_count"]
            if leftover > 0:
                messages.append(f"Debt cleared! ₹{leftover} added to your savings. Refill Mode ended — streak resumes tomorrow.")
                messages += award_milestones(anon_id, old_cushion, new_cushion)
                for t in crossed_milestones(old_cushion, new_cushion):
                    achievements.append({"icon": "💰", "title": f"₹{t} SAVED!", "amount": 2000, "extra": ""})
            else:
                messages.append("Debt cleared! Refill Mode ended — streak resumes tomorrow.")
        else:
            new_debt = debt - amount
            new_cushion = streak["cushion_balance"]
            new_streak = streak["streak_count"]
            messages.append(f"₹{amount} went toward your debt. ₹{new_debt} left to repay.")

        supabase.table("kubera_streaks").update({
            "streak_count": new_streak,
            "cushion_balance": new_cushion,
            "debt_remaining": new_debt,
            "last_checkin": today.isoformat(),
        }).eq("anon_id", anon_id).execute()

    else:
        gap = (today - last_checkin).days if last_checkin else 1
        new_streak = streak["streak_count"]

        if gap == 1:
            new_streak += 1
        else:
            shields = supabase.table("kubera_shields").select("*").eq("anon_id", anon_id).execute().data
            avail = available_shields(anon_id, today)
            used_dates = [s["used_date"] for s in shields if s["used_date"]]
            last_used = max(used_dates) if used_dates else None
            cooldown_ok = last_used is None or (today - parse_date(last_used)).days >= 5

            if avail and cooldown_ok:
                supabase.table("kubera_shields").update({"used_date": today.isoformat()}).eq("id", avail[0]["id"]).execute()
                new_streak += 1
                messages.append("A Shield protected your streak!")
            else:
                new_streak = 1

        old_cushion = streak["cushion_balance"]
        new_cushion = old_cushion + amount

        supabase.table("kubera_streaks").update({
            "streak_count": new_streak,
            "cushion_balance": new_cushion,
            "debt_remaining": 0,
            "last_checkin": today.isoformat(),
        }).eq("anon_id", anon_id).execute()

        if new_streak % 7 == 0:
            supabase.table("kubera_badges").insert({"anon_id": anon_id, "badge_type": f"weekly_{new_streak}"}).execute()
            award_coins(anon_id, 1000)
            messages.append(f"New badge: Day {new_streak} streak! +1,000 Kubera Coins.")
            shield_extra = ""
            if len(available_shields(anon_id, today)) < 2:
                supabase.table("kubera_shields").insert({"anon_id": anon_id}).execute()
                messages.append("You earned a Shield!")
                shield_extra = "+1 Shield"
            achievements.append({"icon": "🔥", "title": f"{new_streak} DAYS STREAK!", "amount": 1000, "extra": shield_extra})

        messages += award_milestones(anon_id, old_cushion, new_cushion)
        for t in crossed_milestones(old_cushion, new_cushion):
            achievements.append({"icon": "💰", "title": f"₹{t} SAVED!", "amount": 2000, "extra": ""})

        if not messages:
            messages.append(f"Checked in! +₹{amount} saved.")

    # Whatever amount was deposited today — whether it grew the cushion or
    # paid down Refill Mode debt — is money the teen chose not to spend, so
    # it comes out of the Wallet either way, same as a real savings transfer.
    supabase.table("kubera_wallets").update({"balance": wallet_balance - amount}).eq("anon_id", anon_id).execute()

    achv_script = f"<script>showAchievements({json.dumps(achievements)});</script>" if achievements else ""
    return page(f"<p>{'<br>'.join(messages)}</p><a class='btn-primary' href='/'>Back home</a>{achv_script}", active_tab="goal")

@app.route("/cushion/spend", methods=["GET", "POST"])
def cushion_spend():
    anon_id = session["anon_id"]
    streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data

    if streak["debt_remaining"] > 0:
        return page(f"<p>You're still paying off a previous emergency spend (₹{streak['debt_remaining']} left) — clear that first.</p><a class='btn-primary' href='/'>Back home</a>", active_tab="goal")

    if request.method == "GET":
        return page(f"""
        <div class="pay-confirm-card">
            {glossy_icon_html("💸", "green")}
            <h2 class="pay-confirm-name">Emergency Spend</h2>
            <p style="color:var(--text-muted);margin:-8px 0 16px;text-align:center">Withdraw from your Cushion for something urgent. We'll show you the impact before anything moves.</p>
            <form method="POST" class="pay-confirm-form">
                <label class="pay-amount-label">Amount
                    <div class="pay-amount-field">
                        <span class="pay-amount-currency">₹</span>
                        <input type="number" name="amount" min="1" required autofocus>
                    </div>
                </label>
                <button type="submit" class="btn-primary">See Impact</button>
            </form>
        </div>
        """, active_tab="goal")

    amount = int(request.form["amount"])

    if request.form.get("confirmed") != "yes":
        if amount < 1 or amount > streak["cushion_balance"]:
            return page(f"<p>You only have ₹{streak['cushion_balance']} saved — you can't withdraw ₹{amount}.</p><a class='btn-primary' href='/cushion/spend'>Go back</a>", active_tab="goal")

        debt = compute_debt(amount)
        days = debt // 10
        return page(f"""
        <div class="pay-confirm-card">
            {glossy_icon_html("⚠️", "red")}
            <h2 class="pay-confirm-name">Are You Sure?</h2>
            <p style="color:var(--text-muted);margin:-8px 0 16px;text-align:center">Withdrawing ₹{amount} pushes your goal back {days} days.</p>
            <form method="POST" class="pay-confirm-form">
                <input type="hidden" name="amount" value="{amount}">
                <input type="hidden" name="confirmed" value="yes">
                <button type="submit" class="btn-primary">Confirm Withdrawal</button>
            </form>
            <p style="margin-top:12px"><a href="/cushion/spend" style="color:var(--text-muted);font-size:14px">Cancel</a></p>
        </div>
        """, active_tab="goal")

    if amount < 1 or amount > streak["cushion_balance"]:
        return page(f"<p>You only have ₹{streak['cushion_balance']} saved — you can't withdraw ₹{amount}.</p><a class='btn-primary' href='/'>Back home</a>", active_tab="goal")

    debt = compute_debt(amount)
    new_cushion = streak["cushion_balance"] - amount

    supabase.table("kubera_streaks").update({
        "cushion_balance": new_cushion,
        "debt_remaining": debt,
    }).eq("anon_id", anon_id).execute()

    return page(f"<p>₹{amount} withdrawn. You're now in Refill Mode — ₹{debt} debt, streak paused.</p><a class='btn-primary' href='/'>Back home</a>", active_tab="goal")

@app.route("/badges")
def badges():
    # Legacy standalone page, same reasoning as the /milestones redirect
    # above — redirect to the already-polished badge grid instead of
    # maintaining a second, bare copy of it.
    anchor = "#overview-section" if session["view_mode"] == "parent" else "#rewards-section"
    return redirect("/" + anchor)

@app.route("/stories/kubera/seen", methods=["POST"])
def mark_kubera_story_seen():
    anon_id = session["anon_id"]
    supabase.table("kubera_sessions").update({"kubera_intro_seen_date": today_utc().isoformat()}).eq("anon_id", anon_id).execute()
    return ("", 204)

@app.route("/stories/badge/<badge_id>/seen", methods=["POST"])
def mark_badge_story_seen(badge_id):
    anon_id = session["anon_id"]
    supabase.table("kubera_badges").update({"seen_by_teen": True}).eq("id", badge_id).eq("anon_id", anon_id).execute()
    return ("", 204)

@app.route("/switch-view/<mode>")
def switch_view(mode):
    if mode in ("teen", "parent"):
        session["view_mode"] = mode
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
