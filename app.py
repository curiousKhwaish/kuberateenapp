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

def today_utc():
    return datetime.now(timezone.utc).date()

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

def available_shields(anon_id, today):
    shields = supabase.table("kubera_shields").select("*").eq("anon_id", anon_id).execute().data
    cutoff = (today - timedelta(days=30)).isoformat()
    return [s for s in shields if s["used_date"] is None and s["earned_date"] >= cutoff]

def compute_debt(amount):
    if amount <= 700:
        return 100
    extra = amount - 700
    increments = extra // 200
    return 100 + 50 * increments

def crossed_milestones(old_balance, new_balance):
    hits = []
    if old_balance < 100 <= new_balance:
        hits.append(100)
    start = ((old_balance // 500) + 1) * 500
    t = start
    while t <= new_balance:
        hits.append(t)
        t += 500
    return hits

def award_milestones(anon_id, old_balance, new_balance):
    messages = []
    for t in crossed_milestones(old_balance, new_balance):
        supabase.table("kubera_badges").insert({"anon_id": anon_id, "badge_type": f"milestone_{t}"}).execute()
        messages.append(f"New milestone badge: ₹{t} saved!")
    return messages

@app.route("/")
def home():
    if "anon_id" not in session:
        new_id = str(uuid.uuid4())
        session["anon_id"] = new_id
        supabase.table("kubera_sessions").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_wallets").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_streaks").insert({"anon_id": new_id}).execute()

    if "view_mode" not in session:
        session["view_mode"] = "teen"

    anon_id = session["anon_id"]

    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", anon_id).single().execute()
    balance = wallet.data["balance"]

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

    return f"""
    Hello, KuberaTeenApp! Your anonymous ID is {session['anon_id']}<br>
    Current view: <b>{session['view_mode']}</b><br>
    Wallet balance: ₹{balance}<br>
    <a href="/pay">Pay</a><br>
    <a href="/log-cash-expense">Log a cash spend</a><br>
    <a href="/history">Where did my money go?</a><br>
    <hr>
    {streak_block}
    <a href="/checkin">Check in today</a><br>
    <a href="/badges">My Badges</a><br>
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

@app.route("/pay/<payee>", methods=["GET", "POST"])
def pay_payee(payee):
    if request.method == "POST":
        amount = int(request.form["amount"])
        category = request.form["category"]

        wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", session["anon_id"]).single().execute()
        balance = wallet.data["balance"]

        if amount > balance:
            return f"<p>You only have ₹{balance} left — you can't pay ₹{amount}.</p><a href='/pay/{payee}'>Go back</a>"

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
            messages.append(f"New badge: Day {new_streak} streak!")
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
