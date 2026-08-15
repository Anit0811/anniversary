# Build Prompt: "Love Quiz" — 25th Anniversary Party App

Copy everything below into Antigravity as the project brief.

---

## What this app is

A live, phone-based party game for ~70 guests at a 25th wedding anniversary.
Couples pair up on the spot (no pre-registration), each answer a set of
multiple-choice questions about themselves, then guess what their partner
answered. The match percentage between guess and reality is their "Love
Score." Results show live on a shared screen/leaderboard.

## Tech stack (keep it light — this is a single-event app, not a product)

- **Backend:** Python, FastAPI
- **DB:** SQLite (file-based, no external DB service needed)
- **Frontend:** Server-rendered HTML templates (Jinja2) + vanilla JS `fetch`
  calls for interactivity. No React/build step — keep it a single deployable
  service.
- **Realtime-ish updates:** simple polling every 3–5 seconds for the
  leaderboard screen. No websockets needed at this scale.
- **Deployment target:** Render free web service (single instance). Must run
  comfortably with ~70 concurrent users on a free-tier instance.
- **Sessions:** no user accounts/auth. Identify guests via a short random
  code stored in a cookie/localStorage + returned in the URL, not a login
  system.

## Core flow

### 1. Landing / pairing
- Guest opens the app (via QR code shown on a screen at the venue).
- One partner taps **"Start as a couple"**:
  - Enters both partners' names.
  - App generates a short, human-readable **4-digit room code** and shows it
    big on screen.
- The other partner taps **"Join with code"**, enters the same 4-digit code,
  and is now linked to the same couple session.
- Store couple session in DB: `couple_id`, `partner_a_name`,
  `partner_b_name`, `room_code`, `created_at`, `status`.

### 2. Round 1 — Answer about yourself
- Once both partners have joined, **each partner independently** gets the
  same question set on their own phone (they should NOT be shown as "waiting
  together" — just silently poll until both are done).
- Do **not** tell them in the UI that there's a guessing round coming later
  — this is the anti-cheating trick (see Design Notes below). Just label
  this screen simply, e.g. "Love Quiz — Round 1".
- Questions are multiple choice (4 options, labeled A–D). One question shown
  at a time, no back button, no editing after submit (locks per question).
- Store each answer: `couple_id`, `partner` (a/b), `question_id`,
  `selected_option`, `answered_at`.
- Once submitted, show a simple "Waiting for your partner to finish..."
  holding screen (no indication of what's coming next).

### 3. Round 2 — Guess your partner's answer
- Unlocks only once **both** partners in a couple have completed Round 1.
- Same question set (or a configurable subset — see Config section), but
  now the prompt is reframed: "What do you think your partner answered?"
- Same one-question-at-a-time, lock-on-submit UX.
- Store: `couple_id`, `partner` (a/b, i.e. who is guessing),
  `question_id`, `guessed_option`, `answered_at`.

### 4. Scoring
- For each question: guess is correct if `guessed_option == partner's
  actual Round 1 answer`.
- Love Score for the couple = `(number of matching answers across both
  partners' guesses) / (total possible matches) * 100`.
  - Total possible matches = `2 × number of scored questions` (each partner
    guesses independently, both guesses count).
- Bonus/free-text questions (if any are included) are excluded from
  scoring — shown as a fun readout only, not counted toward the percentage.
- Store computed score on the couple record once both have finished Round 2:
  `love_score`, `completed_at`.

### 5. Results & leaderboard
- Each couple sees their own score immediately after finishing Round 2, with
  a simple per-question breakdown (✅ matched / ❌ didn't match — don't need
  to show what the "wrong" guess was unless you want the reveal moment to
  happen live on stage instead).
- A separate **`/leaderboard`** route, meant to be displayed on a projector/
  TV at the venue: shows all completed couples sorted by Love Score
  descending, auto-refreshing every 3–5 seconds via polling.
- Admin/host route (simple, no auth needed for a one-day event, but keep it
  at an unguessable path like `/host-xyz123`) to:
  - See how many couples have joined / are mid-quiz / have finished.
  - Manually advance or reset a couple if something breaks.

## Data model (SQLite)

```
questions
  id INTEGER PRIMARY KEY
  genre TEXT
  text TEXT
  option_a TEXT
  option_b TEXT
  option_c TEXT
  option_d TEXT
  is_bonus BOOLEAN DEFAULT 0   -- bonus/free-text, excluded from scoring
  active BOOLEAN DEFAULT 1     -- lets host toggle which questions are live

couples
  id INTEGER PRIMARY KEY
  room_code TEXT UNIQUE
  partner_a_name TEXT
  partner_b_name TEXT
  status TEXT   -- 'pairing' | 'round1' | 'round2' | 'done'
  love_score REAL
  created_at TIMESTAMP
  completed_at TIMESTAMP

answers
  id INTEGER PRIMARY KEY
  couple_id INTEGER
  partner TEXT           -- 'a' or 'b'
  question_id INTEGER
  round INTEGER           -- 1 or 2
  selected_option TEXT    -- 'a'/'b'/'c'/'d', or free text for bonus questions
  answered_at TIMESTAMP
```

## Config the host can control without redeploying

- Which questions are `active` (so the question list from our shortlist can
  be toggled without code changes — ideally a simple `/host-xyz123`
  screen with checkboxes, or at minimum a seed script that's easy to edit).
- Number of scored questions to use per couple (e.g. 12–15 out of the full
  bank).

## Design notes to build in (from earlier planning — important, don't skip)

- **Anti-cheating:** Round 1 must never be labeled as "answer about
  yourself before your partner guesses" — keep it neutral so couples don't
  coordinate answers while sitting together. The guessing round should feel
  like a reveal/twist, not something they saw coming.
- **No editing after submit** — once an option is tapped and confirmed, it's
  locked. This also naturally discourages phone-passing/coordination.
- **One question at a time** — never show the full question list at once,
  so there's nothing to glance over a shoulder and scan.
- Randomizing option order per user is a nice-to-have, not essential — skip
  if it adds complexity, since the "no early reveal of Round 2" trick plus
  an MC announcing "no talking during this round" covers most of the risk.

## Non-functional requirements

- Must handle ~70 concurrent users on a free Render instance without
  breaking — this is a light load, avoid over-engineering (no Redis, no
  background workers needed).
- Mobile-first responsive UI — every guest is on their own phone. Big
  tappable buttons, minimal typing (only needed for names + room code).
- Should gracefully handle a guest closing the tab and reopening — persist
  their identity via a token in localStorage/cookie tied to their
  `couple_id` + `partner` so they resume where they left off instead of
  losing progress.
- Keep the whole thing to a single deployable service (one `render.yaml` /
  one web process) — no separate frontend deployment.

## Deliverables expected from this build

1. FastAPI app with routes for: pairing, round 1, round 2, results,
   leaderboard, host panel.
2. SQLite schema + seed script for questions (I'll provide the final
   question list separately once finalized).
3. Simple, warm, celebratory visual style (this is a 25th anniversary party
   — feel free to use a soft romantic color palette, not a generic quiz-app
   look).
4. Instructions for deploying to Render free tier.
5. A basic `/host-xyz123` panel to monitor progress live during the event.

---

## UPDATE — Final questions, randomization rule, UX polish, admin delete

### 1. Final question bank (seed this — 22 questions, all active, no bonus/free-text ones)

Seed the `questions` table with the following 22 rows. Each has 4 options
(A–D), all self-only format (no "who's more likely" comparisons). No genre/
age tagging needed — drop those columns if already built, they're not
needed anymore.

1. Lazy Sunday — "Your idea of a perfect lazy Sunday is..." → Sleeping in till noon / Long breakfast + phone in bed / Movie marathon / "Relaxing" but somehow still doing chores
2. Eat one thing forever — "If you had to eat just ONE dish for the rest of your life, it'd be..." → Something spicy & desi / Something sweet / A comfort classic like dal-chawal/khichdi / You could never choose just one
3. Worst habit — "Your biggest guilty habit is..." → Losing your phone/keys constantly / Snoring or talking in your sleep / Leaving lights/fans on everywhere / Being chronically late
4. Lottery — "You just won the lottery — first thing you're buying is..." → A house/property / A car / A big trip / Something for the family
5. Packing/trip role — "When packing for a trip, you're the one who..." → Packs days in advance with a list / Throws it all in last minute / Over-packs "just in case" / Makes everyone else pack while you supervise
6. Movie genre — "The kind of movie that always makes you stop and watch, no matter how many times you've seen it, is..." → A romantic drama / A comedy / An action-thriller / An old family classic
7. Song genre — "The kind of song that makes you turn the volume up is..." → An old-school classic / A soft romantic melody / An upbeat dance number / A soulful/devotional tune
8. Romantic evening — "Your idea of the perfect romantic evening is..." → A quiet dinner at home / A fancy night out / A long walk and talk / Just watching something together
9. Dream trip — "Your dream trip right now is..." → A mountain getaway / A beach holiday / A pilgrimage / Somewhere abroad you've never been
10. Holiday evening energy — "On a holiday, by evening you're usually..." → Ready to crash early / Still up for going out / Looking for good food nearby / Wanting one more thing ticked off the list
11. Colours — "The shades you're naturally drawn to are..." → Soft pastels / Deep, bold colours / Classic black & white/neutrals / Bright, vibrant colours
12. Free evening — "If you suddenly got a totally free evening tonight, you'd..." → Call up a friend / Curl up with a book/music, alone / Cook something just for the joy of it / Go for a drive/walk with no destination
13. Stress response — "When you're stressed, your go-to move is..." → Eating something / Talking to someone about it / Sleeping it off / Cleaning or organizing something
14. Instant skill — "If you could instantly master one skill, it'd be..." → Cooking / Dancing / A musical instrument / Public speaking
15. Perfect gift — "Your idea of the perfect gift to receive is..." → Something handmade or personal / Something practical you actually need / Something surprising and spontaneous / An experience, not a thing
16. Grocery run — "Left alone at a grocery store, you always end up buying..." → Snacks you didn't plan for / Way more than the list / Exactly what's on the list, nothing else / Something for someone else, not yourself
17. Ideal weather — "Your favourite kind of weather is..." → Monsoon rain / Crisp winter cold / Warm sunny days / Cool breezy evenings
18. Sleep style — "When it comes to sleep, you're..." → Asleep the moment your head hits the pillow / Someone who needs total silence and dark / A light sleeper, up at every sound / Someone who reads/scrolls till you doze off
19. Party role — "At a big family function, you're usually the one..." → On the dance floor first / Chatting in a corner with a few people / Helping host/organize things / Sneaking off early
20. Comfort activity — "When you need to unwind after a long day, you reach for..." → Food / Music or a show / A phone call to someone / Silence and some time alone
21. Spending style — "When it comes to spending money, you're more of a..." → A planner — budgets everything / A spontaneous spender / A saver, thinks twice always / Spends freely on others, careful for yourself
22. Morning ritual — "The very first thing you do after waking up is..." → Check your phone / Make tea/coffee / Step outside or open a window / Lie there a few minutes before moving

### 2. Randomization rule (important — read carefully)

- When a couple starts Round 1, randomly select a subset of N questions
  (configurable, default N=12) from the 22-question bank, and randomly
  shuffle their order.
- This random selection + order must be **generated once per couple** and
  **stored against the `couple_id`** (e.g. a `couple_question_order` table
  or a JSON array of question IDs on the `couples` row) — do NOT
  re-randomize per partner or per round.
- Both partners within the same couple must see the exact same questions,
  in the exact same order, in both Round 1 and Round 2. Only the
  **couple-to-couple** selection/order varies — every couple in the room
  can get a different random set and order, but partner A and partner B
  within one couple are always in sync.
- This means: generate and persist the question list at couple-creation
  time (or at Round 1 start), then both Round 1 and Round 2 for that couple
  read from that stored list — never re-roll randomness mid-couple.

### 3. UX polish

- Replace any raw/inline forms (name entry, room code entry, join flow)
  with **modal/popup dialogs** rather than full page navigations — e.g.
  tapping "Start as a couple" opens a clean centered modal to enter names,
  tapping "Join with code" opens a modal with a code input. Keep transitions
  smooth, not jarring page reloads where avoidable.
- General UX bar: this should look like a **professional, polished
  product**, not a hackathon quiz app. Clean spacing, consistent button
  styles, clear typography hierarchy, subtle transitions/animations on
  screen changes, proper loading/disabled states on buttons during
  submission (avoid double-submits).
- **Remove all emojis** from the UI — no emoji icons, no emoji in button
  labels or headings. Use clean text or simple line-icon SVGs instead if an
  icon is needed. Keep the tone warm but not cutesy/gimmicky.
- Form inputs should have proper validation feedback (e.g. invalid/expired
  room code shows a clear inline error in the modal, not a blank failure).

### 4. Admin: delete couple entries

- On the `/host-xyz123` panel, add a **Delete** action next to each couple
  in the couples list/table.
- Clicking delete should ask for a confirmation (simple confirm dialog is
  fine) before removing.
- Deleting a couple should cascade-delete their associated `answers` rows
  too, so no orphaned data is left behind.
- This is needed for testing/cleanup before the real event — so make sure
  it's easy to spot and use, doesn't require touching the database
  directly.

---

**Status:** Question bank is final (22 questions, listed above) — seed
these directly, no further changes expected before the event.
