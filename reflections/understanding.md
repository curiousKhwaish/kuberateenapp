# Understanding log

Comprehension Q&A, recorded after each completed task per `docs/PEDAGOGY.md` Rule 5. Entries are only added after she actually answers live — never backfilled or guessed.

## 2026-11-02
### Task: Day 1 — Flask scaffold + anonymous session cookie

**Q1:** The app gives every visitor an anonymous ID the moment they open the link, instead of asking them to sign in. In your own words — why does that matter for this specific app, not just in general?
**A1:** "The anonymous ID is important because to recognize if it is the same user or not. Because the user needs to be shown his own details and not others. It does the work of the symlink." Then, after a nudge back to the two competition rules: "It is against the rules [to collect real personal info]. Secondly, it will be easier for the judge without any sign-on... we also said not to share any personal details, like email ID. And it will make the flow complicated. Here instead, we will use cookies. That will help us in a similar way."

**Q2:** We could have built real parent/teen accounts with email and password instead. What's one thing we'd gain from that, and why did we decide it wasn't worth it here?
**A2:** "We have to make a demo app, we don't have to actually make this app, because it does not involve real money, and I cannot onboard actual customers on it. If I were to admit actual customers, then I would definitely involve the login and sign in procedure through emails, phone numbers, or passwords — that will help us more. But through the cookies, the [identity] remains anonymous, according to the rules of the competition. And for this specific project, it isn't worth it, because judges are not gonna judge us on the login basis. They are gonna judge upon the whole web app."

**Q3:** If the anonymous session cookie gets cleared — say, a judge opens the link in a private/incognito window — what happens to that visitor's data? Is that a problem for this specific use case, or not really?
**A3:** Needed scaffolding on the general mechanics of incognito mode (didn't know it offhand), but once given that piece, reasoned correctly: "They start from nothing, so they'd get a new ID." And on the judgment call: "Not really, since there's no real money or data to lose."

**Teacher note:** Q1 and Q2 needed a nudge each to connect the mechanism back to the two specific competition rules (no real personal info, no sign-in wall) rather than stopping at the general "recognizes the same user" purpose — once nudged, she reasoned the rest out correctly both times. Q3 needed more scaffolding since the gap was missing background knowledge (how incognito mode works technically, not a reasoning gap) — once given that fact, she correctly derived both the technical consequence and the real-world judgment call unassisted. Strong grasp of the WHY and good instinct for the "does this actually matter here" judgment; worth a quick refresher on browser/cookie mechanics if it comes up again.

## 2026-11-03
### Task: Day 1 close-out — Teen/Parent toggle (session-based view_mode)

**Q1:** The `view_mode` toggle lives in the `session` cookie, not in a database table like `kubera_sessions`. In your own words — why does it make sense to keep it there instead of saving it to the database?
**A1:** "Putting it in a database will sound very unnecessary because the toggle's work is to show the things on this browser, right? It's to switch sides, and it is only meant for this browser. We don't have to always go on the database and check for the content, because it is a fixed thing that it is doing. Plus it is related to the browser only." Correct on the first try — no nudge needed.

**Q2:** In `switch_view`, we check `if mode in ("teen", "parent"):` before saving it. What would happen if we skipped that check and just saved whatever came in the URL?
**A2:** Initially conflated this value-validation check with cross-user data protection ("anyone could access anybody else's data... spend the money from the wallet"). Corrected: this specific check only keeps `view_mode` from becoming a junk value — the actual guard against impersonating another visitor is the *signed* `anon_id` cookie (tamper-resistant via `app.secret_key`), which this check has nothing to do with. She confirmed she understood the distinction once it was drawn out explicitly.

**Q3:** If the browser's cookies get cleared entirely, what happens to the toggle's "remembered" behavior, and is that a problem for this app?
**A3:** Needed two passes — first answer didn't address the cleared-cookie case directly, got frustrated when asked to connect it back to Day 1's incognito question. On the second, simpler framing, correctly landed on it herself: "the old customer also now acts as a new one because they get a new cookie" — exactly right, `anon_id` and `view_mode` reset together since they share one cookie.

**Teacher note:** Q1 was immediate and correct, strongest answer of the three. Q2 revealed a real conceptual gap worth watching for again — she's inclined to attribute *any* validation/security-shaped code to broad "data protection," rather than distinguishing what each specific check actually guards (value correctness vs. identity authenticity); worth re-surfacing when the parent-approval threshold logic gets built (Day 5), since that's a case where the distinction will matter for real. Q3 needed re-framing to land — when she says "I don't understand," simplifying and tying back to a concrete prior example works better than re-explaining the same abstraction a different way.
