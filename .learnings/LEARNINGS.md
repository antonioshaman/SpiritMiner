# SpiritMiner Learnings

## Session 2026-04-25

### Build
- WhatToMine API v1 returns coins as dict (not list) under "coins" key — parser handles both formats
- WhatToMine API fetched 135 PoW coins on first scan
- Rate limiting critical: WhatToMine ~0.5 req/s, CoinGecko ~0.3 req/s, GitHub unauthenticated 60/hour
- Initial rescore of 135 coins takes several minutes due to external API rate limits — bot is responsive during this time
- MiningPoolStats has no API, HTML scraping needed; page structure varies by coin
- Empty GitHub repo clone works fine, git init is redundant after clone

### Deploy
- Hetzner VPS uses PEP 668 (externally managed Python) — must use venv
- Git remote was HTTPS but gh auth uses SSH protocol — need to `git remote set-url` to SSH
- systemd service with Environment= for bot token works cleanly
