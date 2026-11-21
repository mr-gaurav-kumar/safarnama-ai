"""What the Help chat knows about each page of the app.

The chat widget tells the server which page the person is on. Each page
here has:
  title     -- shown in the chat header ("Help with Profile")
  intro     -- the first line when the chat opens on that page
  starters  -- tappable questions for that page
  faqs      -- (keywords, answer): matched against the question
  clarify   -- asked back when a question on this page is too vague

Answers name the real buttons and sections as they appear on screen, so
update them here when a page changes. Keywords are matched as whole words,
in English and the Hinglish people actually type.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Page:
    title: str
    intro: str
    starters: list[str]
    faqs: list[tuple[tuple[str, ...], str]]
    clarify: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


_BOOKING_FAQS: list[tuple[tuple[str, ...], str]] = [
    (("book here", "book directly", "payment", "pay", "paise", "kharid", "buy here", "ticket book"),
     "Booking and payment happen on the partner site (MakeMyTrip, Skyscanner, redBus and the rest). "
     "Pick a site and it opens in a new tab with your search filled in."),
    (("not filled", "fill nahi", "empty", "details missing", "copy details", "homepage", "fill my details",
      "doesn't fill", "does not fill", "not fill"),
     "Some sites (marked “Copy details”) don't accept a ready-made search link, so they open on their "
     "search page. Tap the chips under “Your search” to copy each detail across."),
    (("from my trip", "fill from", "trip se", "my trip", "auto fill", "autofill"),
     "Use “Fill from a trip” at the top and pick a trip: places, dates and travellers fill in. "
     "Switch Onward / Return for the journey home."),
    (("save ticket", "after booking", "where to save", "ticket save", "pnr save", "add ticket"),
     "After you book, open your Profile → “My tickets” → Add ticket, and enter the PNR. Link it to "
     "your trip and it shows on the trip page too."),
    (("airport", "nearest airport", "no airport", "kaunsa airport"),
     "For places without their own airport we pick the nearest one — Manali uses Bhuntar (KUU), "
     "Gangtok uses Bagdogra (IXB). You can change it in “From” / “To”."),
    (("compare", "cheapest", "sasta", "price", "comparison"),
     "Open the same search on two or three sites and compare there — prices change by the minute, "
     "so we don't copy them into the app."),
]

PAGES: dict[str, Page] = {
    "profile": Page(
        title="Profile",
        intro="You're on your Profile. Ask me about your details, documents, tickets, photo or password.",
        starters=["How do I add my Aadhaar or PAN?", "Is my document safe here?",
                  "How do I change my profile photo?", "How do I save a ticket I booked elsewhere?"],
        faqs=[
            (("aadhaar", "aadhar", "adhar", "pan", "passport", "licence", "license", "dl", "voter", "document",
              "documents", "id proof", "upload"),
             "Scroll to “My documents”, pick the slot (Aadhaar, PAN, Driving licence, Passport — or “Add another” "
             "for Voter ID and others) and press Add. Choose a photo or PDF and we read the number for you; check it "
             "and press Save. A locked e-Aadhaar PDF asks for its password: the first 4 letters of your name in "
             "capitals and your birth year, like RAJA1990."),
            (("safe", "secure", "security", "privacy", "private", "encrypt", "encrypted", "who can see", "admin see",
              "leak", "surakshit"),
             "Your documents and tickets are encrypted on our server and only you can open them — there is no admin "
             "access to them. Numbers stay masked until you press Show, and the number is read from your photo on "
             "your own device."),
            (("photo", "picture", "dp", "avatar", "pic", "profile pic", "image"),
             "Click your picture (or “Add photo”) at the top of your profile. JPG, PNG or WebP up to 5 MB. We crop it "
             "square and remove the location data phones hide in photos. “Remove” takes it off."),
            (("ticket", "tickets", "pnr", "booking", "irctc", "boarding"),
             "In “My tickets” press Add ticket, choose Train, Flight, Bus or Hotel, and enter the PNR and details — "
             "attach the e-ticket if you like. Link it to a trip and it shows on that trip's page too. Train tickets "
             "have a “PNR status” button."),
            (("password", "forgot", "change password", "reset"),
             "Use “Change password” at the bottom of this page. Signed up with Google and never set one? Use "
             "“Forgot password?” on the login page to create one."),
            (("home town", "hometown", "name", "phone", "mobile", "number change", "details", "dob", "birth",
              "interests", "gender"),
             "Edit them under “Personal details” and press Save. Your home town is where “Where to go” and the "
             "train / bus searches start from."),
            (("email", "verify", "verified", "change email"),
             "Your email can't be changed here. If it says “Email not verified”, use “Resend email” on your "
             "dashboard and check spam."),
            (("expiry", "expire", "expires", "valid till", "validity", "renew"),
             "Add the “Valid till” date to a passport or driving licence and we show how many days are left — it "
             "turns amber in the last 6 months."),
            (("show number", "full number", "masked", "xxxx", "hidden"),
             "Press Show on the document to see the full number for 30 seconds; it hides itself again."),
        ],
        clarify="Is this about your personal details, documents (Aadhaar, PAN…), tickets, profile photo or password?",
    ),
    "trip": Page(
        title="This trip",
        intro="You're looking at a trip plan. Ask me about the plan, changing it, booking travel, friends or the PDF.",
        starters=["How do I download this plan as a PDF?", "Can I change the dates or budget?",
                  "How do I invite friends to this trip?", "Why was this plan suggested?"],
        faqs=[
            (("pdf", "download", "print", "email me", "mail", "export"),
             "Use “Download PDF” next to the trip actions, or “Email me this” to get the PDF in your inbox — "
             "that one needs a confirmed email."),
            (("change", "edit", "dates", "date", "budget", "badalna", "modify"),
             "Changing the dates or budget of a planned trip isn't supported yet. Plan a new trip with the new "
             "details from your dashboard, then delete this one."),
            (("invite", "friends", "friend", "group", "together", "share", "dost"),
             "Under “Travelling together” use “Invite by email”. They join from the email, add their own trip "
             "styles, and you can “Replan for the group”. The “Trip room” is your shared chat."),
            (("why", "suggested", "reason", "memory", "past trips", "kyun"),
             "“Why this plan” shows which of your past trips shaped it, and “How we thought about it” shows the "
             "season, crowds and budget check we did first."),
            (("weather", "season", "mausam", "cold", "rain", "monsoon"),
             "The badge on the ticket and “How we thought about it” show what that month is usually like there, "
             "from our season model. For live weather, ask the Assistant."),
            (("packing", "pack", "luggage", "bag", "saaman", "samaan"),
             "Press “Packing list” at the top: get suggestions for this trip's weather, then tick items as you "
             "pack to leave and again to come home."),
            (("flight", "hotel", "train", "bus", "book", "travel"),
             "Use Flights, Hotels, Trains or Buses at the top — they open the booking sites with this trip's "
             "places and dates filled in."),
            (("ticket", "pnr", "tickets"),
             "“Tickets for this trip” lists tickets you linked to it. Add one there, or from your Profile."),
            (("stuck", "processing", "loading", "failed", "not ready", "taking long"),
             "If a plan stays on “planning” for more than a few minutes, delete it from your dashboard and plan "
             "it again. If it fails twice, tell me and I'll pass it to the team."),
            (("delete", "remove", "cancel"),
             "Delete a trip with “Delete” next to it on your dashboard. It also leaves your travel memory."),
            (("rate", "feedback", "review", "stars"),
             "After the trip, rate it on this page. Your ratings steer future plans and “Where to go”."),
        ],
        clarify="Is it about the plan itself, changing the trip, booking travel, inviting people, or the PDF?",
    ),
    "packing": Page(
        title="Packing list",
        intro="You're on the packing list. Ask about suggestions, adding items, or the going / coming-home ticks.",
        starters=["What does “Packing to come home” do?", "How are the suggestions chosen?",
                  "Can I remove an item the admin added?", "How do I add my own item?"],
        faqs=[
            (("come home", "coming home", "return", "lautte", "wapas", "going", "two lists", "tick twice"),
             "Tick items in “Packing to leave” as they go in the bag. Before you check out, switch to “Packing to "
             "come home” and tick them again — anything unticked is what you might leave behind."),
            (("suggest", "suggestion", "suggestions", "ai", "how chosen", "weather", "based"),
             "“Suggest what to pack” looks at the days, the season the trip falls in (cold, hot, monsoon), whether "
             "it's hills or a beach, and your trip style — jackets and boots for the hills in winter, half-sleeves "
             "and sunscreen for the heat. Untick what you don't need before adding."),
            (("admin", "lock", "locked", "can't remove", "cannot delete", "remove admin"),
             "Items marked “Added by admin” can be ticked but not changed or removed — only the admin can take "
             "them off."),
            (("add", "own item", "my item", "new item", "vest"),
             "Type it in “Add an item”, pick a category and quantity, and press Add."),
            (("quantity", "how many", "kitne", "count"),
             "Use − and + next to an item. Suggested quantities follow the number of days."),
            (("untick", "reset", "clear"),
             "“Untick all” clears the ticks for the list you're on (leaving or coming home)."),
            (("group", "friends", "members"),
             "Everyone on a group trip has their own packing list."),
        ],
        clarify="Is it about suggestions, adding or removing items, quantities, or the going / coming-home ticks?",
    ),
    "assistant": Page(
        title="Assistant",
        intro="This is the travel assistant page. Ask me how it works, or ask the assistant itself where to go.",
        starters=["What can I ask the assistant?", "How is the rough budget worked out?",
                  "Is the weather live?", "Why didn't it find my place?"],
        faqs=[
            (("what can", "what to ask", "how to use", "example", "kya puchu"),
             "Tell it your budget, days, people, month, where you start and the mood — like “₹20,000 mein 3 din, "
             "Delhi se pahad, 2 log”. Ask about a place too: “How is Manali in January?”."),
            (("budget", "estimate", "rough", "cost", "kharcha", "worked out", "calculate"),
             "Getting there is priced by distance and the likely mode (bus, train or flight), return for everyone. "
             "Stay, food and local travel come from the place's typical daily cost. Friday and Saturday nights add "
             "about 25% to the stay."),
            (("weather", "live", "forecast", "mausam", "season"),
             "Every place shows what that month is usually like. For trips this month you also get the live "
             "7-day forecast."),
            (("not found", "didn't find", "place", "spelling", "unknown", "list mein"),
             "It knows about 70 popular places and forgives spelling slips (“nanital” works). For a place it "
             "doesn't know, try the nearest well-known town."),
            (("weekend", "weekday", "weekdays"),
             "Say “weekend” and it plans Saturday–Sunday; “weekdays” starts on a Monday — usually cheaper."),
            (("plan this trip", "plan it", "next step"),
             "“Plan this trip” on a card opens the trip form with that place, days, people and budget filled in."),
        ],
        clarify="Is it about what to ask, how the budget is worked out, the weather, or a place it didn't find?",
    ),
    "recommend": Page(
        title="Where to go",
        intro="You're on Where to go. Ask me about From and To, the match score, or why places are missing.",
        starters=["Why is “From” needed?", "What does “To” do?", "What does the match % mean?",
                  "Why are some places missing?"],
        faqs=[
            (("from", "starting", "start", "kahan se"),
             "“From” is where your trip starts. Every place is priced from there — the fare there and back plus "
             "days on the ground — so nearby places keep more of your budget."),
            (("to", "state", "destination", "specific place"),
             "“To” is optional. A place (Manali) shows it first plus places within about 250 km; a state (Kerala) "
             "shows only that state; empty shows all of India."),
            (("match", "percent", "%", "score"),
             "Match mixes how well the place suits your styles, how comfortably the budget covers it, and how good "
             "the season is that month."),
            (("missing", "not showing", "why not", "left out", "over budget", "closed"),
             "Places that cost too much for the budget are left out, and national-park core zones closed that "
             "month too. The numbers at the top say how many."),
            (("rated", "learn", "memory", "ratings"),
             "With “Learn from my rated trips” on, places like the trips you rated highly move up, and ones like "
             "trips you disliked move down."),
            (("long journey", "far", "door"),
             "For trips of 3 days or less, places more than ~700 km away by road move down — too much of the trip "
             "would be travel."),
        ],
        clarify="Is it about From and To, the match score, the budget, or places that don't show up?",
    ),
    "book": Page(
        title="Book travel",
        intro="You're on Book travel. Ask me how booking works here, or how to save the ticket afterwards.",
        starters=["Can I book directly here?", "Why doesn't one site fill my details?",
                  "How do I fill this from my trip?", "Where do I save the ticket after booking?"],
        faqs=_BOOKING_FAQS + [
            (("pnr status", "train status", "waitlist", "wl", "confirm"),
             "Save the train ticket in Profile → “My tickets” and use “PNR status” on it."),
        ],
        clarify="Is it about booking on the partner sites, filling the search, or saving the ticket afterwards?",
    ),
    "dashboard": Page(
        title="My trips",
        intro="You're on your trips. Ask me about planning, a plan's status, deleting a trip or emails.",
        starters=["How do I plan a new trip?", "Where is my trip plan?", "How do I delete a trip?",
                  "Why haven't I got the email?"],
        faqs=[
            (("plan a new trip", "new trip", "plan", "create trip", "start a trip"),
             "Use “Plan a new trip” at the top of your trips: pick the place, dates, budget and styles. The plan is "
             "ready in about a minute."),
            (("where is", "my plan", "status", "ready", "processing", "kahan hai"),
             "Your trips are listed here, newest first — open one to see its day-by-day plan. A trip still "
             "“planning” finishes in about a minute."),
            (("delete", "remove", "cancel"),
             "Use “Delete” on the trip's card. Deleting also removes it from your travel memory, so it won't shape "
             "future plans."),
            (("email", "mail", "verify", "verification", "haven't got", "not received"),
             "If your email isn't confirmed, use “Resend email” here and check spam. Plan-ready emails and reminders "
             "only go to a confirmed address."),
            (("invite", "invitation", "join", "pending"),
             "Invitations from friends appear under “Invitations” — accept to join their trip."),
            (("rate", "finished", "feedback"),
             "When a trip is over, the dashboard reminds you to rate it. Ratings make future plans better."),
        ],
        clarify="Is it about planning a trip, a plan's status, deleting a trip, or emails?",
    ),
    "new_trip": Page(
        title="Plan a trip",
        intro="You're planning a trip. Ask me about any field on this form.",
        starters=["What does “Use my past trip preferences” do?", "How long does planning take?",
                  "Can I plan for a group?", "What are trip styles?"],
        faqs=[
            (("past trip", "preferences", "memory", "use my past"),
             "With it on, we look at your most similar past trips and what you rated them, and lean the new plan "
             "towards what you enjoyed."),
            (("how long", "time", "minute", "wait"),
             "Usually about a minute. You can watch each step on the trip page while it plans."),
            (("group", "friends", "together"),
             "Plan it, then invite friends from the trip page. Their styles are added and you can replan for the group."),
            (("style", "styles", "adventure", "relax", "culture", "food", "nature"),
             "Styles tell the planner what to lean towards — pick one or more. They also shape suggestions in "
             "Where to go."),
            (("budget", "how much", "kitna"),
             "Use the whole trip's budget for everyone, travel included. Not sure? Ask the Assistant what a place "
             "would cost."),
        ],
        clarify="Which part of the form — the place, dates, budget, styles, or using your past trips?",
    ),
    "packages": Page(
        title="Packages",
        intro="You're browsing packages. Ask me how booking, cancelling or payment works.",
        starters=["How do I book a package?", "Can I cancel a package booking?", "Who runs these packages?",
                  "Is payment taken here?"],
        faqs=[
            (("book", "opt", "join", "how to book"),
             "Open a package and use “Opt into this package”: pick a start date and travellers. It's a request "
             "until the agency (or our team) confirms it."),
            (("cancel", "cancellation", "refund"),
             "Your requests are under “My bookings” on the Packages page — cancel from there."),
            (("who", "agency", "business", "runs", "operator", "verified"),
             "Packages come from our team or from travel businesses we've approved. Their page shows who they are."),
            (("payment", "pay", "paise", "price", "total"),
             "No payment is taken in the app. The agency contacts you to confirm and arranges payment."),
        ],
        clarify="Is it about booking a package, cancelling, payment, or who runs it?",
    ),
    "trip_room": Page(
        title="Trip room",
        intro="This is the trip room for your group. Ask me about the room, members or leaving the trip.",
        starters=["Who can see this room?", "How do I add someone?", "How do I leave this trip?"],
        faqs=[
            (("who can see", "private", "members"), "Only the people on this trip can see the room."),
            (("add", "invite"), "Invite people from the trip page under “Travelling together”."),
            (("leave", "exit", "quit"), "Leave from the trip page under “Travelling together”."),
        ],
        clarify="Is it about the chat, the members, or leaving the trip?",
    ),
    "insights": Page(
        title="Insights",
        intro="You're on Insights. Ask me where the numbers come from or how to use them.",
        starters=["Where does this data come from?", "How do I pick a quieter month?"],
        faqs=[
            (("source", "data", "where", "official"),
             "The figures are official Ministry of Tourism statistics — each chart names its source."),
            (("quiet", "busy", "crowd", "month"),
             "Months with fewer arrivals are usually quieter and cheaper. Pair that with the season badge when you plan."),
        ],
        clarify="Is it about where the data comes from, or how to use it for planning?",
    ),
}

# --- pages people see before they log in (answered by POST /chat/public) ---

_FREE = ("It's free to make an account and plan trips. Booking travel or a package happens with the partner "
         "site or the agency.")

PAGES.update({
    "login": Page(
        title="Logging in",
        intro="Trouble logging in? Ask me, or pick a question below.",
        starters=["I forgot my password", "It says “Incorrect email or password”", "Can I log in with Google?",
                  "My account is blocked"],
        faqs=[
            (("forgot", "forget", "bhool", "bhul", "reset", "new password", "forgot password", "password yaad"),
             "Use “Forgot password?” under the password box. We email you a reset link that works for 30 minutes — "
             "check spam if it doesn't arrive."),
            (("incorrect", "wrong", "galat", "not working", "can't log in", "cannot log in", "login nahi",
              "invalid", "error"),
             "Check the email for typos — it must be exactly the one you signed up with — and that Caps Lock is off. "
             "Still stuck? Use “Forgot password?” to set a new one."),
            (("google", "gmail", "sso"),
             "When Google sign-in is switched on, use “Continue with Google” above the form. Until then, log in with "
             "your email and password."),
            (("blocked", "suspended", "disabled", "band"),
             "A blocked account can't log in. If you think that's a mistake, write to our support team from the email "
             "you signed up with."),
            (("business", "agency", "merchant", "partner"),
             "Business accounts log in here too — you'll land on your Partner dashboard."),
            (("no account", "sign up", "signup", "create account", "register", "new here"),
             "New here? Use “Create an account” at the top right — it's free."),
            (("stay logged in", "logged out", "session", "remember me"),
             "You stay logged in on this browser for 14 days. “Log out” ends that session."),
        ],
        clarify="Is it about a forgotten password, an error when logging in, Google sign-in, or a blocked account?",
    ),
    "signup": Page(
        title="Signing up",
        intro="Creating an account? I can explain any step.",
        starters=["Is it free?", "Why do you need my home town and birth date?", "I didn't get the verification email",
                  "What are the password rules?"],
        faqs=[
            (("free", "cost", "paid", "charge", "paisa", "paise", "price"), _FREE),
            (("home town", "hometown", "birth", "dob", "personal", "phone", "gender", "interests", "why do you need"),
             "Your home town is where trips and travel searches start from; birth date and interests help tailor "
             "plans. Phone and gender are optional, and you can change any of it later in your Profile."),
            (("verify", "verification", "confirm", "didn't get", "not received", "mail nahi", "email nahi", "link"),
             "We email a confirmation link right after you sign up — it works for 24 hours. Check spam; “Resend "
             "email” on your dashboard sends a fresh one."),
            (("password rules", "password", "strong", "characters"),
             "At least 8 characters, with both letters and numbers."),
            (("already", "existing", "exists", "registered"),
             "That email already has an account — use “Log in”, or “Forgot password?” if you don't remember it."),
            (("business", "agency", "hotel", "operator", "tour"),
             "Run a travel business? Use “For business” at the top to create a partner account. We review it before "
             "your packages go live."),
            (("privacy", "safe", "data", "secure"),
             "Your details stay with us. Documents and tickets you save later are encrypted and only you can open them."),
            (("google", "gmail"),
             "When Google sign-in is switched on, “Continue with Google” creates your account in one step."),
        ],
        clarify="Is it about what we ask for, the password, the verification email, or a business account?",
    ),
    "forgot_password": Page(
        title="Resetting your password",
        intro="Resetting your password? Ask me if something isn't working.",
        starters=["The reset email didn't arrive", "The link says it has expired", "Can I reset without my email?"],
        faqs=[
            (("didn't arrive", "not received", "nahi aaya", "no email", "spam", "not getting", "didn't get"),
             "Check spam and give it a minute. The email only goes to an address that has an account, so use the one "
             "you signed up with."),
            (("expired", "invalid", "not working", "used"),
             "Reset links work for 30 minutes and only once. Ask for a new one on this page."),
            (("without", "no access", "phone", "lost email", "can't access"),
             "Resets go by email only. If you can't reach that inbox, contact our support team."),
        ],
        clarify="Is the email not arriving, or is the link not working?",
    ),
    "business_signup": Page(
        title="Business sign-up",
        intro="Signing up your travel business? Ask me about approval or what you can do here.",
        starters=["How long does approval take?", "Do I need a GSTIN?", "What can I do once approved?",
                  "Is there a fee?"],
        faqs=[
            (("approval", "approve", "approved", "how long", "review", "pending"),
             "Our team reviews each new business. You can log in and set up straight away; your packages go live once "
             "you're approved."),
            (("gst", "gstin", "tax"),
             "GSTIN is optional. If you add it, it must be the 15-character GST number."),
            (("once approved", "after", "what can", "publish", "packages", "bookings"),
             "Publish packages with photos, get booking requests from travellers, and confirm or decline them on your "
             "Partner dashboard. You also get a public page to share."),
            (("fee", "commission", "charge", "cost", "free"), "There's no fee to sign up."),
        ],
        clarify="Is it about approval, the details we ask for, or what you can do afterwards?",
    ),
    "home": Page(
        title="Safarnama",
        intro="Hi! New here? Ask me what the app does or how to start.",
        starters=["What does this app do?", "Is it free?", "Do I need an account?",
                  "Can I see packages without signing up?"],
        faqs=[
            (("what does", "app do", "kya hai", "about", "what is", "features"),
             "It plans day-by-day trips around India, learns from the trips you rate, suggests where to go for your "
             "budget, and keeps your tickets, packing list and ID documents in one place."),
            (("free", "cost", "paid", "price", "paise"), _FREE),
            (("account", "need", "sign up", "login", "register"),
             "You need a free account to plan trips. Packages and Insights are open to everyone."),
            (("packages", "package", "tour"),
             "Yes — “Packages” in the menu is open to everyone. You need an account to opt into one."),
        ],
        clarify="Do you want to know what the app does, what it costs, or how to get started?",
    ),
})

PUBLIC_PAGES = frozenset({"login", "signup", "forgot_password", "business_signup", "home", "packages", "insights"})


def public_reply(page: str | None, message: str) -> str:
    """For people who aren't logged in: answers from the help notes only --
    no account data, no model, nothing stored."""
    from app.chat.classify import classify

    p = page_for(page)
    intent, _ = classify(message)
    if intent == "greeting":
        return f"Hi! {p.intro}"
    if intent == "thanks":
        return "Happy to help!"
    found, _ = answer(page, message)
    return found or p.clarify


GENERAL = Page(
    title="Help",
    intro="Hi! Ask me about your trips, planning, tickets, documents or anything in the app.",
    starters=["Where is my trip plan?", "How do I plan a new trip?", "How do I save a ticket?",
              "Is my data safe?"],
    faqs=[],
    clarify="Could you tell me a bit more — is it about a trip, your profile, booking, or packing?",
)


def page_for(key: str | None) -> Page:
    return PAGES.get(key or "", GENERAL)


def _hits(text: str, words: tuple[str, ...]) -> int:
    return sum(1 for w in words if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text))


def answer(key: str | None, message: str) -> tuple[str | None, str | None]:
    """(answer, None) from THIS page's help notes only. Each page keeps to its
    own issues: a question about another part of the app gets this page's
    follow-up question instead of an answer from somewhere else. (The second
    value is kept for callers; it is always None now.)"""
    text = " ".join(message.lower().split())
    here = PAGES.get(key or "") or (GENERAL if key is None else None)
    best: tuple[int, str | None] = (0, None)
    for words, ans in (here.faqs if here else []):
        n = _hits(text, words)
        if n > best[0]:
            best = (n, ans)
    return best[1], None


def describe(key: str | None) -> str:
    """The page's help notes, for the language model."""
    p = page_for(key)
    notes = "\n".join(f"- {a}" for _, a in p.faqs) or "- (general help)"
    return (f"The user is on the “{p.title}” page.\nHelp notes for this page:\n{notes}\n"
            f"Only help with this page. If the question is about something else or is vague, don't answer it -- "
            f"ask: {p.clarify}")
