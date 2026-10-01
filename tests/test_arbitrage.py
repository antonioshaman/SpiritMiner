import unittest
from unittest.mock import patch, AsyncMock
from decimal import Decimal as D
from services.arbitrage import Leg, validate_leg, evaluate, scan_amount, dex_sell, WRAPPED, USDT


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.legs = (Leg(D(1000), D(995), D(5), 'bridge', 1000, 'receipt'),
                     Leg(D(995), D('1731.3'), D(0), 'dex', 1000, 'block'),
                     Leg(D('1731.3'), D('1727.3'), D(2), 'settlement', 1000, 'fees'),
                     Leg(D('1727.3'), D('1136.381578947368421052631579'), D(1), 'buy', 1000, 'quote'))

    def test_profit_costs_and_reserve(self):
        with patch('config.ARB_SAFETY_BPS', '100'), patch('config.ARB_MIN_NET_PCT', '3'):
            r = evaluate(D(1000), self.legs, 1001)
        self.assertEqual(r.status, 'STRONG')
        self.assertAlmostEqual(float(r.final), (1727.3 - 8) / 1.52 * .99)

    def test_no_profit(self):
        legs = self.legs[:-1] + (Leg(D('1727.3'), D(990), D(1), 'buy', 1000, 'quote'),)
        self.assertEqual(evaluate(D(1000), legs, 1001).status, 'NO_PROFIT')

    def test_stale(self):
        with self.assertRaises(ValueError):
            evaluate(D(1000), self.legs, 2000)

    def test_expired_mid_cycle(self):
        legs = (Leg(D(1000), D(995), D(5), 'bridge', 1000, 'receipt', 1001),) + self.legs[1:]
        with self.assertRaises(ValueError):
            evaluate(D(1000), legs, 1002)

    def test_disconnected_amount(self):
        with self.assertRaises(ValueError):
            evaluate(D(999), self.legs, 1001)

    def test_zero_costs_rejected(self):
        legs = tuple(Leg(x.amount_in, x.amount_out, D(0), x.source, x.timestamp, x.evidence) for x in self.legs)
        with self.assertRaises(ValueError):
            evaluate(D(1000), legs, 1001)

    def test_provider_validation(self):
        valid = dict(executable=True, asset_in='ton:native', asset_out='ethereum:' + WRAPPED,
                     amount_in='1000', amount_out='995', external_cost_usdt='5',
                     timestamp=1000, expires_at=1050, source='bridge', evidence='live route')
        for field, bad in [('amount_in', '500'), ('asset_out', 'ethereum:other'),
                           ('executable', False), ('timestamp', 1), ('timestamp', 1100),
                           ('expires_at', 999), ('source', ''), ('evidence', ''),
                           ('amount_out', 'NaN'), ('amount_out', True), ('external_cost_usdt', '-1')]:
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                validate_leg({**valid, field: bad}, D(1000), 'ton:native', 'ethereum:' + WRAPPED, 1001)
        with self.assertRaises(ValueError):
            validate_leg([], D(1000), 'ton:native', 'ethereum:' + WRAPPED, 1001)
        self.assertEqual(validate_leg(valid, D(1000), 'ton:native', 'ethereum:' + WRAPPED, 1001).amount_out, D(995))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_bridge_blocks(self):
        with patch('config.ARB_BRIDGE_QUOTE_URL', ''):
            r = await scan_amount(None, D(1000))
        self.assertEqual(r.status, 'BLOCKED')
        self.assertIsNone(r.net_pct)

    async def test_rpc_path_and_best_quote(self):
        seen = []
        async def mock_rpc(session, method, params):
            if method == 'eth_chainId': return '0x1'
            if method == 'eth_blockNumber': return '0x100'
            if method == 'eth_getBlockByNumber': return {'timestamp': hex(1000)}
            payload = params[0]['data']
            if payload == '0x313ce567': return hex(9)
            seen.append(payload)
            self.assertEqual(params[1], '0x100')
            return '0x' + format(len(seen) * 1000000, '064x')
        with patch('services.arbitrage.rpc', mock_rpc), patch('services.arbitrage.time.time', return_value=1000):
            r = await dex_sell(None, D(995))
        self.assertEqual(r.amount_out, D(3))
        self.assertEqual(len(seen), 3)
        self.assertEqual(int(seen[0][10:74], 16), 64)
        self.assertEqual(int(seen[0][74:138], 16), 995000000000)
        self.assertEqual(int(seen[0][138:202], 16), 66)
        self.assertTrue(seen[0][202:].startswith(WRAPPED[2:] + '002710'))
        self.assertIn(USDT[2:], seen[0])

    async def test_wrong_rpc_chain_rejected(self):
        with patch('services.arbitrage.rpc', AsyncMock(return_value='0x38')):
            with self.assertRaises(ValueError):
                await dex_sell(None, D(100))
