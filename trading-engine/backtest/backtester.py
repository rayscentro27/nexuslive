#!/usr/bin/env python3
"""
Nexus AI Backtester
Replays historical signals through the risk manager and simulates trade outcomes.

Usage:
    python backtester.py --signals signals.json --balance 10000 --report

Signal file format (JSON array):
[
  {
    "symbol": "EURUSD",
    "action": "BUY",
    "entry_price": 1.0500,
    "stop_loss": 1.0450,
    "take_profit": 1.0600,
    "exit_price": 1.0600,   # actual exit (for simulation)
    "timestamp": "2026-01-01T10:00:00"
  },
  ...
]
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk.risk_manager import NexusRiskManager


class Backtester:
    def __init__(self, initial_balance: float = 10000.0, risk_config: dict = None):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades: List[Dict[str, Any]] = []
        self.risk_manager = NexusRiskManager()
        if risk_config:
            self.risk_manager.config.update(risk_config)

    def load_signals(self, path: str) -> List[Dict]:
        with open(path, 'r') as f:
            return json.load(f)

    def simulate_trade(self, signal: Dict) -> Dict:
        """
        Simulate a single trade. Uses exit_price if provided, otherwise
        assumes stop_loss hit (worst case).
        """
        entry = signal.get('entry_price', 0)
        stop = signal.get('stop_loss', 0)
        target = signal.get('take_profit', 0)
        exit_price = signal.get('exit_price')
        action = signal.get('action', 'BUY').upper()
        position_size = signal.get('position_size', 0.01)

        # Run through risk manager
        validation = self.risk_manager.validate_signal({**signal, 'position_size': position_size})

        if not validation['approved']:
            return {
                'symbol': signal.get('symbol'),
                'timestamp': signal.get('timestamp'),
                'status': 'rejected',
                'reason': validation['issues'],
                'pnl': 0.0
            }

        # Determine exit
        if exit_price is None:
            # Default: assume stop loss hit
            exit_price = stop

        # P&L calculation (forex pip value approximation)
        multiplier = 100000  # standard lot in pips
        if action == 'BUY':
            pnl = (exit_price - entry) * position_size * multiplier
        else:  # SELL
            pnl = (entry - exit_price) * position_size * multiplier

        self.balance += pnl
        self.risk_manager.update_pnl(pnl)

        # Add to risk manager positions briefly then close
        self.risk_manager.positions.append({
            'symbol': signal.get('symbol'),
            'entry_price': entry,
            'stop_loss': stop,
            'take_profit': target,
            'position_size': position_size,
            'opened_at': signal.get('timestamp', datetime.now().isoformat()),
            'risk_score': validation['risk_score']
        })
        self.risk_manager.positions.pop()

        return {
            'symbol': signal.get('symbol'),
            'timestamp': signal.get('timestamp'),
            'action': action,
            'entry': entry,
            'exit': exit_price,
            'stop': stop,
            'target': target,
            'position_size': position_size,
            'pnl': round(pnl, 2),
            'status': 'win' if pnl > 0 else 'loss',
            'balance_after': round(self.balance, 2),
            'risk_score': validation['risk_score']
        }

    def run(self, signals: List[Dict]) -> Dict:
        self.trades = []
        self.balance = self.initial_balance
        self.risk_manager.daily_pnl = 0.0
        self.risk_manager.positions = []

        for signal in signals:
            result = self.simulate_trade(signal)
            self.trades.append(result)

        return self.generate_report()

    def generate_report(self) -> Dict:
        executed = [t for t in self.trades if t['status'] in ('win', 'loss')]
        rejected = [t for t in self.trades if t['status'] == 'rejected']
        wins = [t for t in executed if t['status'] == 'win']
        losses = [t for t in executed if t['status'] == 'loss']

        total_pnl = sum(t['pnl'] for t in executed)
        win_rate = len(wins) / len(executed) * 100 if executed else 0
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses and sum(t['pnl'] for t in losses) != 0 else float('inf')

        # Max drawdown
        peak = self.initial_balance
        max_dd = 0.0
        running = self.initial_balance
        for t in executed:
            running += t['pnl']
            if running > peak:
                peak = running
            dd = (peak - running) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return {
            'summary': {
                'initial_balance': self.initial_balance,
                'final_balance': round(self.balance, 2),
                'total_pnl': round(total_pnl, 2),
                'return_pct': round(total_pnl / self.initial_balance * 100, 2),
                'total_signals': len(self.trades),
                'executed': len(executed),
                'rejected': len(rejected),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate_pct': round(win_rate, 1),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'max_drawdown_pct': round(max_dd, 2),
            },
            'trades': self.trades
        }

    def print_report(self, report: Dict):
        s = report['summary']
        print("\n" + "="*50)
        print("  NEXUS AI BACKTEST REPORT")
        print("="*50)
        print(f"  Initial Balance:  ${s['initial_balance']:>10,.2f}")
        print(f"  Final Balance:    ${s['final_balance']:>10,.2f}")
        print(f"  Total P&L:        ${s['total_pnl']:>10,.2f}  ({s['return_pct']:+.1f}%)")
        print(f"  Max Drawdown:     {s['max_drawdown_pct']:>10.1f}%")
        print("-"*50)
        print(f"  Signals:          {s['total_signals']:>10}")
        print(f"  Executed:         {s['executed']:>10}")
        print(f"  Rejected:         {s['rejected']:>10}")
        print(f"  Win Rate:         {s['win_rate_pct']:>9.1f}%")
        print(f"  Avg Win:          ${s['avg_win']:>10,.2f}")
        print(f"  Avg Loss:         ${s['avg_loss']:>10,.2f}")
        print(f"  Profit Factor:    {s['profit_factor']:>10.2f}")
        print("="*50)

        if s['rejected'] > 0:
            print(f"\n  ⚠️  {s['rejected']} signals rejected by risk manager")

        verdict = "✅ PROFITABLE" if s['total_pnl'] > 0 else "❌ UNPROFITABLE"
        print(f"\n  Verdict: {verdict}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Nexus AI Backtester')
    parser.add_argument('--signals', required=True, help='Path to signals JSON file')
    parser.add_argument('--balance', type=float, default=10000.0, help='Initial balance')
    parser.add_argument('--report', action='store_true', help='Print report to console')
    parser.add_argument('--output', help='Save full report to JSON file')
    args = parser.parse_args()

    bt = Backtester(initial_balance=args.balance)

    print(f"🧪 Loading signals from: {args.signals}")
    signals = bt.load_signals(args.signals)
    print(f"   Found {len(signals)} signals")

    report = bt.run(signals)

    if args.report:
        bt.print_report(report)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Full report saved to: {args.output}")

    return report


if __name__ == "__main__":
    main()
