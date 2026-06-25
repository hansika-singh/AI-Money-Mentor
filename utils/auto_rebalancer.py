"""
Automated Portfolio Rebalancing with Market Timing Signals
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class AutoRebalancer:
    """
    Automated Portfolio Rebalancing with Market Timing
    """
    
    def __init__(self, holdings: List[Dict], target_allocation: Dict):
        """
        Initialize rebalancer
        
        Args:
            holdings: List of holdings dicts with symbol, quantity, current_price
            target_allocation: Dict of asset: target_percentage
        """
        self.holdings = holdings
        self.target = target_allocation
        self.threshold = 0.05  # 5% drift trigger
        self.portfolio_value = sum(h['quantity'] * h['current_price'] for h in holdings)
        
    def get_current_allocation(self) -> Dict:
        """Calculate current portfolio allocation"""
        allocation = {}
        for h in self.holdings:
            value = h['quantity'] * h['current_price']
            allocation[h['symbol']] = value / self.portfolio_value
        return allocation
    
    def check_rebalance_needed(self) -> Tuple[bool, Dict]:
        """Check if rebalancing is needed"""
        current = self.get_current_allocation()
        drift = {}
        
        for asset, target_pct in self.target.items():
            current_pct = current.get(asset, 0)
            drift[asset] = abs(current_pct - target_pct)
        
        needs_rebalance = any(v > self.threshold for v in drift.values())
        return needs_rebalance, drift
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return 0, 0, 0
        
        ema12 = pd.Series(prices).ewm(span=12, adjust=False).mean().iloc[-1]
        ema26 = pd.Series(prices).ewm(span=26, adjust=False).mean().iloc[-1]
        macd_line = ema12 - ema26
        
        signal_line = pd.Series(prices).ewm(span=9, adjust=False).mean().iloc[-1]
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def get_market_signal(self, symbol: str) -> Dict:
        """Get market timing signal for a symbol"""
        try:
            # Fetch historical data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='3mo')
            
            if hist.empty:
                return {'signal': 'HOLD', 'reason': 'No data available'}
            
            prices = hist['Close'].tolist()
            current_price = prices[-1]
            
            # Calculate indicators
            rsi = self.calculate_rsi(prices)
            macd_line, signal_line, hist_line = self.calculate_macd(prices)
            
            # Simple moving averages
            sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else current_price
            sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else current_price
            
            # Generate signal
            signals = []
            
            # RSI signal
            if rsi < 30:
                signals.append('BUY')
            elif rsi > 70:
                signals.append('SELL')
            else:
                signals.append('HOLD')
            
            # MACD signal
            if macd_line > signal_line and hist_line > 0:
                signals.append('BUY')
            elif macd_line < signal_line and hist_line < 0:
                signals.append('SELL')
            else:
                signals.append('HOLD')
            
            # SMA signal
            if sma_20 > sma_50 and current_price > sma_20:
                signals.append('BUY')
            elif sma_20 < sma_50 and current_price < sma_20:
                signals.append('SELL')
            else:
                signals.append('HOLD')
            
            # Majority vote
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            
            if buy_count >= 2:
                signal = 'BUY'
            elif sell_count >= 2:
                signal = 'SELL'
            else:
                signal = 'HOLD'
            
            return {
                'signal': signal,
                'rsi': round(rsi, 2),
                'macd_line': round(macd_line, 2),
                'signal_line': round(signal_line, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'current_price': round(current_price, 2),
                'reason': f'RSI: {rsi:.1f}, MACD: {macd_line:.2f}'
            }
            
        except Exception as e:
            return {'signal': 'HOLD', 'reason': str(e)}
    
    def generate_rebalance_trades(self) -> Dict:
        """Generate rebalancing trades"""
        needs_rebalance, drift = self.check_rebalance_needed()
        
        if not needs_rebalance:
            return {
                'needs_rebalance': False,
                'message': 'Portfolio is within target allocation',
                'trades': []
            }
        
        current = self.get_current_allocation()
        trades = []
        
        for asset, target_pct in self.target.items():
            current_pct = current.get(asset, 0)
            diff = target_pct - current_pct
            
            if abs(diff) > self.threshold:
                amount = diff * self.portfolio_value
                action = 'BUY' if diff > 0 else 'SELL'
                
                trades.append({
                    'asset': asset,
                    'action': action,
                    'amount': round(abs(amount), 2),
                    'current_weight': round(current_pct * 100, 2),
                    'target_weight': round(target_pct * 100, 2),
                    'difference': round(diff * 100, 2)
                })
        
        return {
            'needs_rebalance': True,
            'trades': trades,
            'portfolio_value': round(self.portfolio_value, 2),
            'drift': {k: round(v * 100, 2) for k, v in drift.items()}
        }
    
    def get_tax_harvesting_opportunities(self) -> List[Dict]:
        """Identify tax-loss harvesting opportunities"""
        opportunities = []
        
        for h in self.holdings:
            invested = h['quantity'] * h.get('buy_price', h['current_price'])
            current = h['quantity'] * h['current_price']
            pnl = current - invested
            
            if pnl < 0:
                opportunities.append({
                    'symbol': h['symbol'],
                    'loss': round(abs(pnl), 2),
                    'invested': round(invested, 2),
                    'current': round(current, 2),
                    'harvestable_loss': min(abs(pnl), 3000),  # IRS limit
                    'suggestion': f'Consider selling {h["symbol"]} to realize ₹{min(abs(pnl), 3000):,.2f} loss'
                })
        
        return sorted(opportunities, key=lambda x: x['loss'], reverse=True)
    
    def optimize_execution(self, trades: List[Dict]) -> List[Dict]:
        """Optimize trade execution"""
        optimized = []
        
        for trade in trades:
            amount = trade['amount']
            
            # Split large orders into smaller chunks
            if amount > 100000:
                chunks = []
                remaining = amount
                chunk_size = 25000
                
                while remaining > 0:
                    chunk = min(chunk_size, remaining)
                    chunks.append(chunk)
                    remaining -= chunk
                
                optimized.append({
                    **trade,
                    'chunks': chunks,
                    'execution_strategy': 'DCA'  # Dollar Cost Averaging
                })
            else:
                optimized.append({
                    **trade,
                    'chunks': [amount],
                    'execution_strategy': 'Market'
                })
        
        return optimized