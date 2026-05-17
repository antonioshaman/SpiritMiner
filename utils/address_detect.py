from __future__ import annotations

import re

EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
TON_USER_FRIENDLY_RE = re.compile(r"^[EUkU0][QQqQ][A-Za-z0-9_-]{46}$")
TON_RAW_RE = re.compile(r"^-?[01]:[0-9a-fA-F]{64}$")
SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

EVM_CANDIDATE_CHAINS = ["ethereum", "bsc", "base", "arbitrum", "polygon", "optimism", "avalanche"]


def detect_address(text: str) -> tuple[str | None, str]:
    """Returns (family, normalized_address). family ∈ {evm, solana, ton, None}."""
    s = text.strip()
    if EVM_RE.match(s):
        return "evm", s.lower()
    if TON_RAW_RE.match(s) or TON_USER_FRIENDLY_RE.match(s):
        return "ton", s
    if SOLANA_RE.match(s):
        return "solana", s
    return None, s
