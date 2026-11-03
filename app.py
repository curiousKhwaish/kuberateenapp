import os
import uuid
from flask import Flask, session, redirect
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-random-secret-later"

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

@app.route("/")
def home():
    if "anon_id" not in session:
        new_id = str(uuid.uuid4())
        session["anon_id"] = new_id
        supabase.table("kubera_sessions").insert({"anon_id": new_id}).execute()

    if "view_mode" not in session:
        session["view_mode"] = "teen"

    return f"""
    Hello, KuberaTeenApp! Your anonymous ID is {session['anon_id']}<br>
    Current view: <b>{session['view_mode']}</b><br>
    <a href="/switch-view/teen">Switch to Teen view</a> |
    <a href="/switch-view/parent">Switch to Parent view</a>
    """

@app.route("/switch-view/<mode>")
def switch_view(mode):
    if mode in ("teen", "parent"):
        session["view_mode"] = mode
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
