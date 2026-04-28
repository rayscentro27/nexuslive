import json
import os
from datetime import datetime

class NexusRiskManager:
    """AI Risk Management System - Enforces trading risk rules"""

    def __init__(self, config_file="risk_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.positions = []
        self.daily_pnl = 0.0
        self.max_daily_loss = self.config.get('max_daily_loss', 100.0)
        self.max_position_size = self.config.get('max_position_size', 0.01)  # 1% of account
        self.max_open_positions = self.config.get('max_open_positions', 3)

    def load_config(self):
        """Load risk management configuration"""
        default_config = {
            'max_daily_loss': 100.0,  # Max loss per day in account currency
            'max_position_size': 0.01,  # Max position size as % of account
            'max_open_positions': 3,  # Max concurrent positions
            'max_drawdown': 0.05,  # Max drawdown before stopping
            'risk_per_trade': 0.02,  # Max risk per trade (2%)
            'reward_risk_ratio': 2.0,  # Minimum reward/risk ratio
            'max_correlation': 0.7,  # Max correlation between positions
            'volatility_filter': True,  # Filter high volatility periods
            'news_filter': True  # Avoid trading during major news
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)

        return default_config

    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def validate_signal(self, signal):
        """Validate a trading signal against risk rules"""

        issues = []

        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            issues.append(f"Daily loss limit reached: {self.daily_pnl}")

        # Check max open positions
        if len(self.positions) >= self.max_open_positions:
            issues.append(f"Max open positions reached: {len(self.positions)}/{self.max_open_positions}")

        # Check position size
        position_size = signal.get('position_size', 0.01)
        if position_size > self.max_position_size:
            issues.append(f"Position size too large: {position_size} > {self.max_position_size}")

        # Check reward/risk ratio
        entry = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)

        if entry and stop_loss and take_profit:
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr_ratio = reward / risk if risk > 0 else 0

            if rr_ratio < self.config['reward_risk_ratio'] - 0.001:
                issues.append(f"Reward/risk ratio too low: {rr_ratio:.2f} < {self.config['reward_risk_ratio']}")

        # Check correlation (simplified - would need more sophisticated correlation matrix)
        symbol = signal.get('symbol', '')
        for pos in self.positions:
            if pos['symbol'] == symbol:
                issues.append(f"Position already open for {symbol}")

        return {
            'approved': len(issues) == 0,
            'issues': issues,
            'risk_score': self.calculate_risk_score(signal)
        }

    def calculate_risk_score(self, signal):
        """Calculate a risk score for the signal (0-100, higher = riskier)"""
        score = 0

        # Position size risk
        size = signal.get('position_size', 0.01)
        if size > 0.02: score += 30
        elif size > 0.01: score += 15

        # Volatility risk (simplified)
        indicators = signal.get('indicators', '')
        if 'high volatility' in indicators.lower(): score += 20

        # Time-based risk (simplified)
        now = datetime.now()
        if now.hour < 8 or now.hour > 20: score += 10  # Outside major session

        return min(score, 100)

    def approve_trade(self, signal):
        """Approve or reject a trade based on risk rules"""
        validation = self.validate_signal(signal)

        if validation['approved']:
            # Add to positions
            position = {
                'symbol': signal.get('symbol'),
                'entry_price': signal.get('entry_price'),
                'stop_loss': signal.get('stop_loss'),
                'take_profit': signal.get('take_profit'),
                'position_size': signal.get('position_size', 0.01),
                'opened_at': datetime.now().isoformat(),
                'risk_score': validation['risk_score']
            }
            self.positions.append(position)

            return {
                'approved': True,
                'position_id': len(self.positions),
                'message': f"Trade approved. Risk score: {validation['risk_score']}"
            }
        else:
            return {
                'approved': False,
                'issues': validation['issues'],
                'message': f"Trade rejected: {', '.join(validation['issues'])}"
            }

    def update_pnl(self, pnl_change):
        """Update daily P&L"""
        self.daily_pnl += pnl_change

    def close_position(self, position_id, exit_price):
        """Close a position and update P&L"""
        if 0 <= position_id - 1 < len(self.positions):
            position = self.positions[position_id - 1]

            # Calculate P&L (simplified)
            entry = position['entry_price']
            pnl = (exit_price - entry) * position['position_size'] * 100000  # Assuming forex

            self.update_pnl(pnl)
            self.positions.pop(position_id - 1)

            return {'pnl': pnl, 'total_daily_pnl': self.daily_pnl}
        return {'error': 'Position not found'}

    def get_risk_status(self):
        """Get current risk status"""
        return {
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.positions),
            'max_daily_loss': self.max_daily_loss,
            'risk_limit_hit': self.daily_pnl <= -self.max_daily_loss,
            'positions': self.positions
        }