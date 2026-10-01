# TON/GRAM cross-chain arbitrage scanner

## What changed

The 12h candle thesis is retired. Candle direction says nothing about the price
of the other asset, transaction size, or whether the cycle can be repeated.
`/arb` checks the configured native trade sizes. Subscribers receive only full
cycle estimates above `ARB_MIN_NET_PCT`. No signing, keys or trading is implemented.
`BLOCKED` is the expected default until real providers are configured.

## Cycle and accounting

1. Native TON/GRAM -> **exactly** Ethereum
   `0x582d872a1b094fc48f5de31d3b73f2d9be47def1`.
2. Sell received ERC20 through Uniswap v3 QuoterV2 via WETH to Ethereum USDT.
   First hop is 1%; second hop tries 0.05%, 0.3%, 1%, selecting best output.
   Every route uses the same block. Chain ID, token decimals and block age are
   checked. `eth_call` is read-only. Output already includes pool fees and price
   impact; **do not deduct those again**. No USD spot-price multiplication.
3. Transfer Ethereum USDT to the custodial wallet balance.
4. Buy native and withdraw to a TON address, ready for the next bridge transfer.

Provider outputs must be net of all fees charged from that leg's asset. External
costs paid from separate balances (ETH gas, approval, claim, swap, USDT transfer,
TON wallet funding) are denominated in USDT and assigned to exactly one provider
leg. The DEX adapter sets external cost to zero: the settlement provider MUST
budget the wallet-specific Ethereum approval/swap/transfer costs, and the bridge
provider MUST budget the claim. An all-zero external-cost budget is rejected.

Let S = starting native, U = USDT entering buy leg, N = native delivered to the
external TON wallet, C = sum of separately paid external costs in USDT.

```
net_native = (N - C * N / U) * (1 - ARB_SAFETY_BPS / 10000)
net_pct = (net_native / S - 1) * 100
```

The native deduction is an **economic cost equivalent** at the buy quote's average
rate. It is not the actual token balance delivered. ETH/TON gas balances must be
funded separately. The safety reserve is a configurable haircut, not a proven
bound on losses. A multi-minute bridge cannot lock future DEX/native prices.
`PROFIT` (>= configured threshold), `STRONG` (>=8%), `EXTREME` (>=15%) are estimates,
never guaranteed or atomic execution. `NO_PROFIT` suppresses notifications.

## Configuration

Copy `.env.example` into the environment used by systemd. This project reads
process environment variables; it does not automatically load .env files.

- `ARB_ETH_RPC_URL`: Ethereum mainnet JSON-RPC with eth_call access.
- `ARB_BRIDGE_QUOTE_URL`: trusted read-only native -> wrapped bridge adapter.
- `ARB_SETTLEMENT_QUOTE_URL`: trusted ETH-USDT -> custodial-USDT adapter.
- `ARB_NATIVE_QUOTE_URL`: trusted custodial-USDT -> external native adapter.
- `ARB_TRADE_SIZES`: native input sizes, default 100,500,1000.
- `ARB_MIN_NET_PCT`: positive minimum profit, default 3%.
- `ARB_SAFETY_BPS`: reserve haircut, default 100 basis points.
- `ARB_MAX_QUOTE_AGE_SECONDS`: quote/block freshness, default 60.
- `ARB_POLL_SECONDS`: scheduler cadence, default 60.

Use private, controlled HTTPS services. These are **adapter contracts**, not
existing public Wallet APIs. No undocumented Wallet API or simulated bridge is
silently substituted. The repository does not ship bridge/Wallet adapters because
live support and account-specific access have not been established. Providers
must report unavailable until their route is verified; setting executable=true
on a spreadsheet estimate defeats this protection.

## Read-only provider protocol

HTTP GET with `amount_in` decimal string, `asset_in`, `asset_out`. Response:

```json
{
  "executable": true,
  "asset_in": "ton:native",
  "asset_out": "ethereum:0x582d872a1b094fc48f5de31d3b73f2d9be47def1",
  "amount_in": "1000",
  "amount_out": "995",
  "external_cost_usdt": "5.00",
  "timestamp": 1790888400,
  "expires_at": 1790888460,
  "source": "verified bridge adapter",
  "evidence": "live route/fee/limit check identifier"
}
```

Values above are illustrative, not a current quote or bridge fee. Timestamps
are Unix seconds UTC. Missing/nonfinite/negative numbers, booleans as amounts,
zero output, wrong asset, wrong input size, expired/future/stale quotes, missing
source/evidence and unavailable routes all block signals. Quotes are rechecked
for expiry and age after the last leg arrives.

Exact next-leg identities:

| Leg | asset_in | asset_out |
| --- | --- | --- |
| Bridge | `ton:native` | `ethereum:0x582d872a1b094fc48f5de31d3b73f2d9be47def1` |
| Settlement | `ethereum:0xdac17f958d2ee523a2206206994597c13d831ec7` | `wallet:USDT` |
| Buy + withdrawal | `wallet:USDT` | `ton:native` |

Bridge adapter must verify outbound direction, exact mint contract, amount
limits, net minted quantity, claim fees, oracle availability and current route
status. A historical completed transfer or a working homepage alone does not
prove current outbound availability. Settlement/buy adapters must verify the
actual account's deposits, KYC/limits, exchange quote, withdrawal availability,
fees and external destination. `evidence` is audit metadata; the scanner trusts
the configured adapter and does not independently verify an on-chain receipt.

## Operations and validation

`/arb` is restricted to the configured administrator to avoid public RPC abuse.
`/arb_help` explains statuses. Scheduler scans every minute by default; alert
cooldown reuses persisted token_alerts (6h), independently for each input size.
It records successful delivery only; level changes do not reset the cooldown.
Errors are reported as BLOCKED without publishing credentials or endpoint URLs.
Existing PoW/token discovery remains unchanged. The compatibility candle entry
point now calls the cycle scanner and cannot emit old candle recommendations.

```
python -m unittest discover -s tests -v
python -m compileall -q bot.py config.py handlers services
```

Tests cover accounting, losses, wrong-chain RPC, ABI path construction, best
route selection, mismatched quantities, stale/expired quotes, invalid inputs,
missing providers and missing external cost budgets. RPC is mocked: there is
no live bridge test, Wallet account test or end-to-end trade verification.

Before production, connect and validate all three providers, supply RPC, run
`/arb`, compare each output with live interfaces and gas budgets, then complete
a small manually authorized round trip. Only after observed complete settlement
should route automation be considered. Changing code does not restart the
already-running server; this PR must be deployed through the existing operator.

## Primary references checked 2026-10-02

- https://docs.ton.org/onboarding/bridges — legacy bridges are not recommended
  and can be deprecated at any moment.
- https://developers.uniswap.org/docs/sdks/v3/guides/swapping/quoting —
  amount-specific QuoterV2 simulations, including multihop quotes.
- https://help.wallet.tg/article/716-supported-tokens-in-wallet — supported
  assets; token support alone is not an executable buy/withdrawal quote.
