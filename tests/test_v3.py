import csv
import gzip
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ["PS_DATA_DIR"] = tempfile.mkdtemp(prefix="pentasignal_v3_test_")
os.environ["DRY_RUN"] = "1"

from pentasignal import settings, scenarios, store
from pentasignal.engine import Engine
from pentasignal.ohlcv_store import append_candles, load
from pentasignal.utils import tehran_now

TEHRAN = ZoneInfo("Asia/Tehran")


class TestPentaSignalV3(unittest.TestCase):
    def test_version_and_strategy_unchanged_shape(self):
        self.assertEqual(settings.VERSION, "3.1.3")
        self.assertEqual(scenarios.ACTIVE_SCENARIOS, ["F1", "F2", "F3", "F4", "F5"])
        self.assertEqual(len(scenarios.UNION_SYMBOLS), 21)
        self.assertEqual(settings.FEE_RT, 0.002)
        self.assertEqual(settings.CSV_KEEP_DAYS, 90)

    def test_signal_csv_contains_entry_timestamp(self):
        self.assertIn("entry_candle_ts", store.SIGNAL_HEADERS)
        store.init()
        row = {
            "signal_id": "TEST-1", "issued_at_tehran": "2026-09-09 07:30:00",
            "candle_close_tehran": "2026-09-09 07:30:00", "symbol": "BTC-USDT",
            "direction": "LONG", "scenario_id": "F1", "entry_price": "100",
            "stop_loss": "90", "take_profit": "", "exit_mode": "BK",
            "exit_param": "arm=1.0", "sl_atr_mult": "4", "cm_candles": "288",
            "atr": "2", "entry_candle_ts": "1788921000", "position_size_usd": "10",
            "status": "OPEN", "be_armed": "0", "be_price": "",
        }
        store.append_signal(row)
        got = store.get_signal("TEST-1")
        self.assertEqual(got["entry_candle_ts"], "1788921000")

    def test_ohlcv_dedup_and_rolling_store(self):
        ts = int(datetime(2026, 9, 8, 12, 0, tzinfo=TEHRAN).timestamp())
        candles = [{"t": ts + i * 60, "o": 100+i, "h": 101+i, "l": 99+i, "c": 100.5+i, "v": 10} for i in range(3)]
        self.assertEqual(append_candles("BTC-USDT", candles, closed_before_ts=ts+300), 3)
        self.assertEqual(append_candles("BTC-USDT", candles, closed_before_ts=ts+300), 0)
        got = load("BTC-USDT", start_ts=ts, end_ts=ts+300)
        self.assertEqual(len(got), 3)

    def test_one_minute_settlement(self):
        # Open LONG at 100; 1m candle later hits BE threshold and then BE stop.
        entry_ts = int(datetime(2026, 9, 9, 10, 0, tzinfo=TEHRAN).timestamp())
        row = {
            "signal_id": "F1-BTC-USDT-20260909-1000", "issued_at_tehran": "2026-09-09 10:00:00",
            "candle_close_tehran": "2026-09-09 10:00:00", "symbol": "BTC-USDT",
            "direction": "LONG", "scenario_id": "F1", "entry_price": "100",
            "stop_loss": "92", "take_profit": "", "exit_mode": "BK", "exit_param": "arm=1.0",
            "sl_atr_mult": "4", "cm_candles": "288", "atr": "2", "entry_candle_ts": str(entry_ts),
            "position_size_usd": "10", "status": "OPEN", "be_armed": "0", "be_price": "",
        }
        store.append_signal(row)
        cs = [
            {"t": entry_ts, "o": 100, "h": 101, "l": 99.5, "c": 100.5, "v": 1},
            {"t": entry_ts+60, "o": 100.5, "h": 108.5, "l": 100.4, "c": 108, "v": 1},
            {"t": entry_ts+120, "o": 108, "h": 108.2, "l": 100.2, "c": 101, "v": 1},
        ]
        ctx = scenarios.MarketContext({"BTC-USDT": []}, candles1m={"BTC-USDT": cs})
        eng = Engine(sender=None)
        logs = eng.settle_all(datetime.fromtimestamp(entry_ts+180, TEHRAN), ctx)
        self.assertTrue(any(x.kind == "BE_ARMED" for x in logs))
        self.assertTrue(any(x.kind == "SETTLE" for x in logs))
        self.assertEqual(store.get_signal(row["signal_id"])["status"], "BE_HIT")

    def test_nightly_is_explicit(self):
        ctx = scenarios.MarketContext({})
        eng = Engine(sender=None)
        logs = eng.on_candle_close(datetime(2026, 9, 9, 10, 0, tzinfo=TEHRAN), ctx, allow_new=False)
        self.assertFalse(any(x.kind == "REPORT" for x in logs))
        logs2 = eng.nightly(datetime(2026, 9, 9, 2, 0, tzinfo=TEHRAN))
        self.assertIsNotNone(logs2)
        self.assertEqual(logs2.kind, "REPORT")

    def test_operational_time_windows(self):
        from run_bot import current_mode
        self.assertEqual(current_mode(datetime(2026, 9, 9, 7, 0, tzinfo=TEHRAN)), "signal")
        self.assertEqual(current_mode(datetime(2026, 9, 9, 19, 30, tzinfo=TEHRAN)), "signal")
        self.assertEqual(current_mode(datetime(2026, 9, 9, 20, 0, tzinfo=TEHRAN)), "settle")
        self.assertEqual(current_mode(datetime(2026, 9, 10, 0, 30, tzinfo=TEHRAN)), "settle")
        self.assertEqual(current_mode(datetime(2026, 9, 10, 1, 0, tzinfo=TEHRAN)), "settle")
        self.assertEqual(current_mode(datetime(2026, 9, 10, 1, 1, tzinfo=TEHRAN)), "idle")
        self.assertEqual(current_mode(datetime(2026, 9, 10, 2, 0, tzinfo=TEHRAN)), "nightly")

    def test_workflow_schedule_strings(self):
        root = Path(__file__).parents[1]
        signal = (root/".github/workflows/signal-bot.yml").read_text()
        settle = (root/".github/workflows/settle-bot.yml").read_text()
        nightly = (root/".github/workflows/nightly-report.yml").read_text()
        self.assertIn('cron: "0,30 3-16 * * *"', signal)
        self.assertIn('cron: "0,30 16-21 * * *"', settle)
        self.assertIn('cron: "30 22 * * *"', nightly)
        self.assertIn("--signal", signal)
        self.assertIn("--settle", settle)
        self.assertIn("--nightly", nightly)


if __name__ == "__main__":
    unittest.main(verbosity=2)
