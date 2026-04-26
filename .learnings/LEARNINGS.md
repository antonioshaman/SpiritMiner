# SpiritMiner Learnings

## Session 2026-04-25

### Build
- WhatToMine API v1 returns coins as dict (not list) under "coins" key — parser handles both formats
- WhatToMine API fetched 135 PoW coins on first scan
- Rate limiting critical: WhatToMine ~0.5 req/s, CoinGecko ~0.3 req/s, GitHub unauthenticated 60/hour
- Initial rescore of 135 coins takes ~12 minutes due to external API rate limits
- MiningPoolStats has no API, HTML scraping needed; page structure varies by coin
- Empty GitHub repo clone works fine, git init is redundant after clone

### Critical Bug: Rescore blocks polling
- **Problem**: `await rescore_all()` ran before `dp.start_polling()`, blocking bot for ~12 min
- **Fix**: `asyncio.create_task()` for background rescore
- **Lesson**: Any long-running init task must be non-blocking

### Critical Bug: /start not handled from FSM states
- **Problem**: FSM state handlers `@router.message(SomeState.waiting_for_input)` intercepted ALL messages including /start
- **Fix**: Add `~Command("start"), ~Command("help")` exclusion to FSM handlers
- **Lesson**: In aiogram 3, FSM state handlers catch all messages in that state. Commands must be explicitly excluded.

### Scoring
- All 135 coins got first_seen=now() on first scan — established coins wrongly scored as "new"
- Fixed by using CoinGecko genesis_date for real coin age
- Age score: +20 for <7 days, +10 for <30 days, 0 for older

### Deploy
- Hetzner VPS uses PEP 668 (externally managed Python) — must use venv
- Git remote was HTTPS but gh auth uses SSH protocol — need to `git remote set-url` to SSH
- systemd service with Environment= for bot token works cleanly
- Admin notification on restart: version + stats — essential for visibility

## Session 2026-04-25 (continued)

### v1.5.0 Features
- Spirit Points: gamification with 5 levels (Новичок→Легенда), points for actions
- Partnership links: static partner data with algorithm-based relevance matching
- MiningPoolStats: enhanced scraping returns pool names, hashrate, workers (not just count)
- Spirit Index: aggregate market indicator from 4 components (quality/sentiment/activity/discovery)

### Council Review Findings (v1.5.1)
- **get_user_actions had no WHERE user_id** — parameter accepted but never bound to SQL. Data leak bug.
- **API key hardcoded as os.getenv default** — never put real keys as fallback values, use empty string
- **HTML injection in Telegram messages** — all external strings (coin names, user queries, usernames) must be html.escape()'d before HTML parse_mode
- **Fire-and-forget asyncio.create_task** — always store task ref + add done_callback for error logging
- **APScheduler overlap** — always set max_instances=1, coalesce=True for long-running interval jobs
- **Pool scraping in rescore loop** — adding 135 HTTP calls with 3.3s rate limit bloats job to 7.5+ min. Separate into own less-frequent job
- **FSM state leak** — cb_main_menu (back button) must clear FSMContext, otherwise stale state catches next message
- **Migration error swallowing** — bare except pass hides real failures. Log warnings, only suppress expected "already exists"
- **Main menu scroll** — 12 single-button rows is too tall on mobile. Group into rows of 2

### Architecture Decisions
- Pool enrichment separated into own 6-hour scheduled job (was blocking hourly rescore)
- Rescore log level changed from debug to warning for per-coin failures (were invisible in production)
- Leaderboard uses "Miner #N" fallback instead of raw user_id exposure
