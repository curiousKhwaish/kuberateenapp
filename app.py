import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, session, redirect, request
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-random-secret-later"

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

PAYEE_CATEGORY = {
    "Bombay Stationery": "shopping",
    "Sriram Vadewala": "snacks",
    "Ola Cabs": "transport",
}
PAYEES = ["Bombay Stationery", "Sriram Vadewala", "Ola Cabs", "Campus Café", "Timely Treasures"]
CATEGORIES = ["snacks", "movies", "transport", "bills", "gifts", "shopping", "grocery"]

DEMO_MILESTONES = [
    ("Score 90%+ in 10th board exams", 150000),
    ("Score 90%+ in half-yearly / pre-board exams", 25000),
    ("Win a sports tournament or school competition", 25000),
    ("Consistent chores or extra reading goals this month", 28000),
]

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

@app.route("/")
def home():
    if "anon_id" not in session:
        new_id = str(uuid.uuid4())
        session["anon_id"] = new_id
        supabase.table("kubera_sessions").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_wallets").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_streaks").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_coins").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_milestones").insert([
            {"anon_id": new_id, "title": title, "coin_reward": reward}
            for title, reward in DEMO_MILESTONES
        ]).execute()

    if "view_mode" not in session:
        session["view_mode"] = "teen"

    anon_id = session["anon_id"]

    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
    balance = wallet.data["balance"]

    coins = supabase.table("kubera_coins").select("*").eq("anon_id", anon_id).single().execute().data
    coins_line = f"Kubera Coins: {coins['current_coins']} / {coins['max_coins']} toward the Main Goal<br>"

    milestone_rows = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).execute().data

    if session["view_mode"] == "parent":
        badge_rows = supabase.table("kubera_badges").select("*").eq("anon_id", anon_id).order("earned_date").execute().data
        badges_html = "".join(f"<li>{b['badge_type']} — earned {b['earned_date']}</li>" for b in badge_rows) or "<li>No badges earned yet.</li>"

        newly_claimed = [m for m in milestone_rows if m["status"] == "claimed" and not m["seen_by_parent"]]
        milestone_toast_block = ""
        if newly_claimed:
            lines = [f"📋 Your child sent in \"{m['title']}\" for you to verify!" for m in newly_claimed]
            for m in newly_claimed:
                supabase.table("kubera_milestones").update({"seen_by_parent": True}).eq("id", m["id"]).execute()
            milestone_toast_block = toast_html("milestone-claimed-toast", lines)

        view_block = f"""
        Wallet balance left with your teen: ₹{balance}<br>
        <a href="/parent/requests">Pending approval requests</a><br>
        {coins_line}
        <a href="/parent/milestones">Manage milestones</a><br>
        {milestone_toast_block}
        <h3>Badges earned</h3>
        <ul>{badges_html}</ul>
        """
    else:
        all_reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).execute().data

        pending_reqs = [r for r in all_reqs if r["status"] == "pending"]
        pending_lines = [f"⏳ Waiting for parent: \"Can I spend ₹{r['amount']} at {r['payee'] or 'cash'}?\"" for r in pending_reqs]
        pending_block = ("<p>" + "<br>".join(pending_lines) + "</p>") if pending_lines else ""

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
        shields_count = len(available_shields(anon_id, today_utc()))

        if streak["debt_remaining"] > 0:
            streak_block = f"""
            <p>⚠️ Refill Mode — ₹{streak['debt_remaining']} debt left.<br>
            Streak frozen at Day {streak['streak_count']}, savings frozen at ₹{streak['cushion_balance']}.</p>
            """
        else:
            streak_block = f"""
            Streak: Day {streak['streak_count']}<br>
            Cushion saved: ₹{streak['cushion_balance']}<br>
            Shields available: {shields_count}<br>
            <a href="/cushion/spend">Emergency spend from cushion</a><br>
            """

        view_block = f"""
        Wallet balance: ₹{balance}<br>
        {pending_block}
        {toast_block}
        {milestone_toast_block}
        <a href="/pay">Pay</a><br>
        <a href="/log-cash-expense">Log a cash spend</a><br>
        <a href="/history">Where did my money go?</a><br>
        <hr>
        {streak_block}
        <a href="/checkin">Check in today</a><br>
        <a href="/badges">My Badges</a><br>
        <hr>
        {coins_line}
        <a href="/milestones">My Milestones</a><br>
        """

    return f"""
    Hello, KuberaTeenApp! Your anonymous ID is {session['anon_id']}<br>
    Current view: <b>{session['view_mode']}</b><br>
    <hr>
    {view_block}
    <hr>
    <a href="/switch-view/teen">Switch to Teen view</a> |
    <a href="/switch-view/parent">Switch to Parent view</a>
    """

@app.route("/pay")
def pay():
    links = "".join(f'<li><a href="/pay/{p}">{p}</a></li>' for p in PAYEES)
    return f"""
    <h2>Pay with Kubera</h2>
    <p>Choose where you're paying:</p>
    <ul>{links}</ul>
    """

@app.route("/parent/requests")
def parent_requests():
    anon_id = session["anon_id"]
    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
    balance = wallet.data["balance"]

    all_reqs = supabase.table("kubera_approval_requests").select("*").eq("anon_id", anon_id).order("created_at", desc=True).execute().data

    pending = [r for r in all_reqs if r["status"] == "pending"]
    approved = [r for r in all_reqs if r["status"] == "approved"]
    declined = [r for r in all_reqs if r["status"] == "declined"]

    pending_items = "".join(f"""
        <li>"Can I spend ₹{r['amount']} at {r['payee'] or 'cash'} for {r['category']}?"
            <form method="POST" action="/parent/requests/{r['id']}/approve" style="display:inline">
                <button type="submit">Approve</button>
            </form>
            <form method="POST" action="/parent/requests/{r['id']}/decline" style="display:inline">
                <button type="submit">Decline</button>
            </form>
        </li>
        """ for r in pending)

    approved_items = "".join(f"<li>₹{r['amount']} at {r['payee'] or 'cash'} — {r['category']}</li>" for r in approved)
    declined_items = "".join(f"<li>₹{r['amount']} at {r['payee'] or 'cash'} — {r['category']}</li>" for r in declined)

    return f"""
    <h2>Pending approval requests</h2>
    <p>Wallet balance: ₹{balance} left.</p>
    <ul>{pending_items or "<li>Nothing pending right now.</li>"}</ul>
    <h3>Approved</h3>
    <ul>{approved_items or "<li>None yet.</li>"}</ul>
    <h3>Declined</h3>
    <ul>{declined_items or "<li>None yet.</li>"}</ul>
    <a href="/">Back home</a>
    """

@app.route("/parent/requests/<int:req_id>/<action>", methods=["POST"])
def parent_request_action(req_id, action):
    anon_id = session["anon_id"]
    req = supabase.table("kubera_approval_requests").select("*").eq("id", req_id).eq("anon_id", anon_id).single().execute().data

    if req["status"] != "pending":
        return "<p>This request was already handled.</p><a href='/parent/requests'>Back</a>"

    if action == "decline":
        supabase.table("kubera_approval_requests").update({"status": "declined"}).eq("id", req_id).execute()
        return "<p>Request declined.</p><a href='/parent/requests'>Back</a>"

    if action == "approve":
        wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
        balance = wallet.data["balance"]

        if req["amount"] > balance:
            return f"<p>Can't approve — teen only has ₹{balance} left, request was for ₹{req['amount']}.</p><a href='/parent/requests'>Back</a>"

        supabase.table("kubera_expenses").insert({
            "anon_id": anon_id,
            "amount": req["amount"],
            "payee": req["payee"],
            "category": req["category"],
        }).execute()

        supabase.table("kubera_wallets").update({"balance": balance - req["amount"]}).eq("anon_id", anon_id).execute()
        supabase.table("kubera_approval_requests").update({"status": "approved"}).eq("id", req_id).execute()

        return "<p>Approved — expense logged, wallet updated.</p><a href='/parent/requests'>Back</a>"

    return "<p>Unknown action.</p><a href='/parent/requests'>Back</a>"

@app.route("/parent/milestones", methods=["GET", "POST"])
def parent_milestones():
    anon_id = session["anon_id"]

    if request.method == "POST":
        title = request.form["title"]
        coin_reward = int(request.form["coin_reward"])
        supabase.table("kubera_milestones").insert({
            "anon_id": anon_id,
            "title": title,
            "coin_reward": coin_reward,
        }).execute()
        return redirect("/parent/milestones")

    rows = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).order("created_at").execute().data
    pending = [m for m in rows if m["status"] == "pending"]
    claimed = [m for m in rows if m["status"] == "claimed"]
    verified = [m for m in rows if m["status"] == "verified"]

    pending_items = "".join(f"<li>{m['title']} — {m['coin_reward']} coins (not claimed by your teen yet)</li>" for m in pending)

    claimed_items = "".join(f"""
        <li>{m['title']} — {m['coin_reward']} coins<br>
            Your teen says: "{m['note']}"
            <form method="POST" action="/parent/milestones/{m['id']}/verify" style="display:inline">
                <button type="submit">Verify</button>
            </form>
        </li>
        """ for m in claimed)

    verified_items = "".join(f"<li>{m['title']} — {m['coin_reward']} coins (verified {m['verified_at']})</li>" for m in verified)

    return f"""
    <h2>Milestones</h2>
    <h3>Waiting on your teen</h3>
    <ul>{pending_items or "<li>None.</li>"}</ul>
    <h3>Ready to verify</h3>
    <ul>{claimed_items or "<li>None.</li>"}</ul>
    <h3>Verified</h3>
    <ul>{verified_items or "<li>None yet.</li>"}</ul>
    <h3>Add a new milestone</h3>
    <form method="POST">
        <label>Title: <input type="text" name="title" required></label><br>
        <label>Coin reward: <input type="number" name="coin_reward" min="1" required></label><br>
        <button type="submit">Add milestone</button>
    </form>
    <a href="/">Back home</a>
    """

@app.route("/parent/milestones/<milestone_id>/verify", methods=["POST"])
def verify_milestone(milestone_id):
    anon_id = session["anon_id"]
    m = supabase.table("kubera_milestones").select("*").eq("id", milestone_id).eq("anon_id", anon_id).single().execute().data

    if m["status"] != "claimed":
        return "<p>This milestone hasn't been claimed by your teen yet.</p><a href='/parent/milestones'>Back</a>"

    supabase.table("kubera_milestones").update({
        "status": "verified",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", milestone_id).execute()

    award_coins(anon_id, m["coin_reward"])

    return f"<p>Verified! +{m['coin_reward']} Kubera Coins.</p><a href='/parent/milestones'>Back</a>"

@app.route("/milestones")
def milestones():
    anon_id = session["anon_id"]
    rows = supabase.table("kubera_milestones").select("*").eq("anon_id", anon_id).order("created_at").execute().data

    pending = [m for m in rows if m["status"] == "pending"]
    claimed = [m for m in rows if m["status"] == "claimed"]
    verified = [m for m in rows if m["status"] == "verified"]

    pending_items = "".join(f"""
        <li>{m['title']} — {m['coin_reward']} coins
            <a href="/milestones/{m['id']}/claim">I did this</a>
        </li>
        """ for m in pending)

    claimed_items = "".join(f"<li>{m['title']} — waiting on your parent to verify. Your note: \"{m['note']}\"</li>" for m in claimed)
    verified_items = "".join(f"<li>{m['title']} — {m['coin_reward']} coins (verified!)</li>" for m in verified)

    return f"""
    <h2>My Milestones</h2>
    <h3>Not done yet</h3>
    <ul>{pending_items or "<li>None right now.</li>"}</ul>
    <h3>Waiting for parent to verify</h3>
    <ul>{claimed_items or "<li>None.</li>"}</ul>
    <h3>Verified</h3>
    <ul>{verified_items or "<li>None yet.</li>"}</ul>
    <a href="/">Back home</a>
    """

@app.route("/milestones/<milestone_id>/claim", methods=["GET", "POST"])
def claim_milestone(milestone_id):
    anon_id = session["anon_id"]
    m = supabase.table("kubera_milestones").select("*").eq("id", milestone_id).eq("anon_id", anon_id).single().execute().data

    if m["status"] != "pending":
        return "<p>This milestone isn't waiting to be claimed.</p><a href='/milestones'>Back</a>"

    if request.method == "GET":
        return f"""
        <h2>{m['title']}</h2>
        <form method="POST">
            <label>Tell your parent what you did: <input type="text" name="note" required></label><br>
            <button type="submit">Submit</button>
        </form>
        """

    note = request.form["note"]
    supabase.table("kubera_milestones").update({
        "status": "claimed",
        "note": note,
    }).eq("id", milestone_id).execute()

    return "<p>Sent to your parent!</p><a href='/milestones'>Back</a>"

@app.route("/pay/<payee>", methods=["GET", "POST"])
def pay_payee(payee):
    if request.method == "POST":
        amount = int(request.form["amount"])
        category = request.form["category"]

        wallet = supabase.table("kubera_wallets").select("balance, approval_threshold").eq("anon_id", session["anon_id"]).single().execute()
        balance = wallet.data["balance"]
        threshold = wallet.data["approval_threshold"]

        if amount > balance:
            return f"<p>You only have ₹{balance} left — you can't pay ₹{amount}.</p><a href='/pay/{payee}'>Go back</a>"

        if amount > threshold:
            supabase.table("kubera_approval_requests").insert({
                "anon_id": session["anon_id"],
                "payee": payee,
                "category": category,
                "amount": amount,
            }).execute()
            return f"<p>₹{amount} to {payee} is over your ₹{threshold} limit — sent to your parent for approval.</p><a href='/'>Back home</a>"

        supabase.table("kubera_expenses").insert({
            "anon_id": session["anon_id"],
            "amount": amount,
            "payee": payee,
            "category": category,
        }).execute()

        supabase.table("kubera_wallets").update({"balance": balance - amount}).eq("anon_id", session["anon_id"]).execute()

        return redirect("/")

    suggested = PAYEE_CATEGORY.get(payee)
    if suggested:
        category_field = f'<input type="hidden" name="category" value="{suggested}"><p>Category: {suggested} (auto-suggested)</p>'
    else:
        options = "".join(f'<option value="{c}">{c}</option>' for c in CATEGORIES)
        category_field = f'<label>Category: <select name="category">{options}</select></label>'

    return f"""
    <h2>Pay {payee}</h2>
    <form method="POST">
        <label>Amount: ₹<input type="number" name="amount" min="1" required></label><br>
        {category_field}<br>
        <button type="submit">Pay</button>
    </form>
    """

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

    options = "".join(f'<option value="{c}">{c}</option>' for c in CATEGORIES)
    return f"""
    <h2>Log a cash spend</h2>
    <p>Spent cash that didn't go through the Pay button? Log it here — this won't touch your wallet balance.</p>
    <form method="POST">
        <label>Amount: ₹<input type="number" name="amount" min="1" required></label><br>
        <label>Category: <select name="category">{options}</select></label><br>
        <button type="submit">Log it</button>
    </form>
    """

@app.route("/history")
def history():
    expenses = supabase.table("kubera_expenses").select("*").eq("anon_id", session["anon_id"]).order("created_at", desc=True).execute()
    rows = expenses.data

    totals = {}
    for e in rows:
        totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]

    totals_html = "".join(f"<li>{cat}: ₹{amt}</li>" for cat, amt in totals.items())

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    monthly_total = sum(e["amount"] for e in rows if e["created_at"] >= cutoff)

    monthly_html = ""
    if monthly_total > 0:
        items = [
            (150, "waffle", "waffles"),
            (350, "movie ticket", "movie tickets"),
            (2000, "pair of wireless headphones", "pairs of wireless headphones"),
            (3500, "foldable magnetic charger", "foldable magnetic chargers"),
            (6000, "pair of PUMA sneakers", "pairs of PUMA sneakers"),
        ]
        price, singular, plural = items[0]
        for item_price, item_singular, item_plural in items:
            if monthly_total >= item_price:
                price, singular, plural = item_price, item_singular, item_plural

        count = round(monthly_total / price)
        label = singular if count == 1 else plural
        monthly_html = f"<p>This month you spent ₹{monthly_total} — about {count} {label}.</p>"

    transactions_html = "".join(
        f"<tr><td>{e['created_at']}</td><td>{e['payee'] or '(cash)'}</td><td>{e['category']}</td><td>₹{e['amount']}</td></tr>"
        for e in rows
    )

    return f"""
    <h2>Where did my money go?</h2>
    <h3>By category</h3>
    <ul>{totals_html}</ul>
    {monthly_html}
    <h3>Every transaction</h3>
    <table border="1" cellpadding="5">
    <tr><th>When</th><th>Payee</th><th>Category</th><th>Amount</th></tr>
    {transactions_html}
    </table>
    <br><a href="/">Back home</a>
    """

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    anon_id = session["anon_id"]
    today = today_utc()
    streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data

    if request.method == "GET":
        if streak["debt_remaining"] > 0:
            prompt = f"You're in Refill Mode, owing ₹{streak['debt_remaining']}. Deposit to pay it down (min ₹10):"
        else:
            prompt = f"Day {streak['streak_count']} streak. Enter today's deposit (min ₹10):"
        return f"""
        <h2>Check in</h2>
        <p>{prompt}</p>
        <form method="POST">
            <label>Amount: ₹<input type="number" name="amount" min="10" value="10" required></label><br>
            <button type="submit">Check in</button>
        </form>
        """

    last_checkin = parse_date(streak["last_checkin"])
    if last_checkin == today:
        return "<p>You already checked in today — come back tomorrow!</p><a href='/'>Back home</a>"

    amount = int(request.form["amount"])
    if amount < 10:
        return "<p>Minimum deposit is ₹10.</p><a href='/checkin'>Go back</a>"

    messages = []
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
            if len(available_shields(anon_id, today)) < 2:
                supabase.table("kubera_shields").insert({"anon_id": anon_id}).execute()
                messages.append("You earned a Shield!")

        messages += award_milestones(anon_id, old_cushion, new_cushion)

        if not messages:
            messages.append(f"Checked in! +₹{amount} saved.")

    return f"<p>{'<br>'.join(messages)}</p><a href='/'>Back home</a>"

@app.route("/cushion/spend", methods=["GET", "POST"])
def cushion_spend():
    anon_id = session["anon_id"]
    streak = supabase.table("kubera_streaks").select("*").eq("anon_id", anon_id).single().execute().data

    if streak["debt_remaining"] > 0:
        return f"<p>You're still paying off a previous emergency spend (₹{streak['debt_remaining']} left) — clear that first.</p><a href='/'>Back home</a>"

    if request.method == "GET":
        return """
        <h2>Emergency spend from cushion</h2>
        <form method="POST">
            <label>Amount: ₹<input type="number" name="amount" min="1" required></label><br>
            <button type="submit">See impact</button>
        </form>
        """

    amount = int(request.form["amount"])

    if request.form.get("confirmed") != "yes":
        if amount < 1 or amount > streak["cushion_balance"]:
            return f"<p>You only have ₹{streak['cushion_balance']} saved — you can't withdraw ₹{amount}.</p><a href='/cushion/spend'>Go back</a>"

        debt = compute_debt(amount)
        days = debt // 10
        return f"""
        <h2>Are you sure?</h2>
        <p>Withdrawing ₹{amount} pushes your goal back {days} days.</p>
        <form method="POST">
            <input type="hidden" name="amount" value="{amount}">
            <input type="hidden" name="confirmed" value="yes">
            <button type="submit">Confirm withdrawal</button>
        </form>
        <a href="/cushion/spend">Cancel</a>
        """

    if amount < 1 or amount > streak["cushion_balance"]:
        return f"<p>You only have ₹{streak['cushion_balance']} saved — you can't withdraw ₹{amount}.</p><a href='/'>Back home</a>"

    debt = compute_debt(amount)
    new_cushion = streak["cushion_balance"] - amount

    supabase.table("kubera_streaks").update({
        "cushion_balance": new_cushion,
        "debt_remaining": debt,
    }).eq("anon_id", anon_id).execute()

    return f"<p>₹{amount} withdrawn. You're now in Refill Mode — ₹{debt} debt, streak paused.</p><a href='/'>Back home</a>"

@app.route("/badges")
def badges():
    rows = supabase.table("kubera_badges").select("*").eq("anon_id", session["anon_id"]).order("earned_date").execute().data
    items = "".join(f"<li>{b['badge_type']} — earned {b['earned_date']}</li>" for b in rows)
    return f"""
    <h2>My Badges</h2>
    <ul>{items}</ul>
    <a href="/">Back home</a>
    """

@app.route("/switch-view/<mode>")
def switch_view(mode):
    if mode in ("teen", "parent"):
        session["view_mode"] = mode
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

