
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

@app.route("/")
def home():
    if "anon_id" not in session:
        new_id = str(uuid.uuid4())
        session["anon_id"] = new_id
        supabase.table("kubera_sessions").insert({"anon_id": new_id}).execute()
        supabase.table("kubera_wallets").insert({"anon_id": new_id}).execute()

    if "view_mode" not in session:
        session["view_mode"] = "teen"

    wallet = supabase.table("kubera_wallets").select("balance").eq("anon_id", session["anon_id"]).single().execute()
    balance = wallet.data["balance"]

    return f"""
    Hello, KuberaTeenApp! Your anonymous ID is {session['anon_id']}<br>
    Current view: <b>{session['view_mode']}</b><br>
    Wallet balance: ₹{balance}<br>
    <a href="/pay">Pay</a><br>
    <a href="/log-cash-expense">Log a cash spend</a><br>
    <a href="/history">Where did my money go?</a><br>
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

@app.route("/switch-view/<mode>")
def switch_view(mode):
    if mode in ("teen", "parent"):
        session["view_mode"] = mode
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
