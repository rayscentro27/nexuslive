-- paper_trade_journal — paper trading research only
-- NO LIVE TRADING. NO REAL MONEY. Educational research and simulation.
-- Applied: 2026-05-19 | Approved: c2f8da59-4019-4657-b981-c0d05f7b9fcf

CREATE TABLE IF NOT EXISTS paper_trade_journal (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  strategy_id         TEXT NOT NULL,
  strategy_version    TEXT NOT NULL DEFAULT '1.0',
  market              TEXT NOT NULL,
  asset_class         TEXT NOT NULL
    CHECK (asset_class IN ('forex','crypto','options','equities')),
  session             TEXT,
  timeframe           TEXT NOT NULL,
  direction           TEXT NOT NULL
    CHECK (direction IN ('long','short','neutral')),

  -- Entry
  entry_date          DATE NOT NULL,
  entry_time          TIME,
  entry_price         DECIMAL(18,8) NOT NULL,
  entry_reason        TEXT,

  -- Risk parameters
  stop_loss           DECIMAL(18,8) NOT NULL,
  take_profit_1       DECIMAL(18,8),
  take_profit_2       DECIMAL(18,8),
  risk_pct            DECIMAL(5,4) DEFAULT 0.01,
  position_size       DECIMAL(18,4),
  risk_usd            DECIMAL(12,2),

  -- Exit
  exit_date           DATE,
  exit_time           TIME,
  exit_price          DECIMAL(18,8),
  exit_reason         TEXT,

  -- Results
  result_r            DECIMAL(8,4),
  result_pct          DECIMAL(8,4),
  paper_pnl_usd       DECIMAL(12,2),
  outcome             TEXT
    CHECK (outcome IN ('win','loss','breakeven','open','missed','skipped')),

  -- Market context
  atr_at_entry        DECIMAL(12,6),
  vix_at_entry        DECIMAL(8,4),
  market_condition    TEXT,
  news_nearby         BOOLEAN DEFAULT FALSE,
  setup_quality       INTEGER CHECK (setup_quality BETWEEN 1 AND 5),
  followed_rules      BOOLEAN DEFAULT TRUE,

  notes               TEXT,
  screenshot_ref      TEXT,

  -- Safety metadata
  is_paper_trade      BOOLEAN NOT NULL DEFAULT TRUE,
  live_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE,

  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS paper_trade_journal_strategy_date
  ON paper_trade_journal(strategy_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS paper_trade_journal_asset_outcome
  ON paper_trade_journal(asset_class, outcome);
CREATE INDEX IF NOT EXISTS paper_trade_journal_date
  ON paper_trade_journal(entry_date DESC);

-- Constraint: ensure no live trading can ever be recorded
ALTER TABLE paper_trade_journal
  ADD CONSTRAINT paper_trade_only
  CHECK (is_paper_trade = TRUE AND live_trading_enabled = FALSE);

-- RLS: service_role only (no client reads)
ALTER TABLE paper_trade_journal ENABLE ROW LEVEL SECURITY;

CREATE POLICY paper_trade_service_only ON paper_trade_journal
  FOR ALL TO service_role USING (true);

-- Seed 3 sample paper trade entries (educational simulation)
INSERT INTO paper_trade_journal (
  strategy_id, strategy_version, market, asset_class, session, timeframe,
  direction, entry_date, entry_price, entry_reason,
  stop_loss, take_profit_1, take_profit_2,
  risk_pct, position_size, risk_usd,
  outcome, result_r, paper_pnl_usd,
  market_condition, setup_quality, followed_rules,
  notes, is_paper_trade, live_trading_enabled
) VALUES
-- London Breakout demo trade 1 (win)
(
  'forex_london_breakout_v1', '1.0', 'GBP/USD', 'forex', 'london', '15m',
  'long', '2026-05-19', 1.2847, 'Breakout above pre-session range high — ATR filter passed',
  1.2812, 1.2882, 1.2900,
  0.01, 33333, 116.67,
  'win', 1.5, 175.00,
  'trending', 4, TRUE,
  'PAPER TRADE SIMULATION — educational only. Range height 35 pips. ATR = 42 pips (above 7-day avg). No news in window.',
  TRUE, FALSE
),
-- EMA Pullback demo trade (loss — rule adherence test)
(
  'forex_trend_pullback_v1', '1.0', 'EUR/USD', 'forex', 'overlap', '15m',
  'long', '2026-05-19', 1.0892, 'EMA 20 retest on 15M — RSI at 48, bullish close from EMA zone',
  1.0868, 1.0938, 1.0960,
  0.01, 41666, 100.00,
  'loss', -1.0, -100.00,
  'trending', 3, TRUE,
  'PAPER TRADE SIMULATION — educational only. EMA 20 slope flattened mid-trade — should have exited sooner per invalidation rule.',
  TRUE, FALSE
),
-- Crypto trend continuation demo (open)
(
  'crypto_trend_continuation_v1', '1.0', 'BTC/USD', 'crypto', NULL, '4h',
  'long', '2026-05-19', 104200.00, 'All EMAs aligned bullish, MACD cross above signal, volume above 20-period average',
  101800.00, 111400.00, 118000.00,
  0.01, 0.0096, 100.00,
  'open', NULL, NULL,
  'trending', 4, TRUE,
  'PAPER TRADE SIMULATION — educational only. Monitoring for TP1 at 3x ATR. BTC dominance stable.',
  TRUE, FALSE
);
