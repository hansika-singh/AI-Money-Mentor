"""
Real-Time Portfolio Optimization & Stress Testing Engine
Modern Portfolio Theory implementation for Indian markets
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize, Bounds, LinearConstraint
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class PortfolioOptimizer:
    """
    Advanced Portfolio Optimization Engine
    Implements Modern Portfolio Theory with Indian market context
    """
    
    def __init__(self, holdings: List[Dict], risk_free_rate: float = 0.06):
        """
        Initialize optimizer with portfolio holdings
        
        Args:
            holdings: List of holdings dicts with symbol, quantity, buy_price
            risk_free_rate: Risk-free rate (default 6% for India)
        """
        self.holdings = holdings
        self.risk_free_rate = risk_free_rate
        self.symbols = [h['symbol'] for h in holdings]
        self.prices = [h['current_price'] for h in holdings]
        self.quantities = [h['quantity'] for h in holdings]
        self.current_values = [p * q for p, q in zip(self.prices, self.quantities)]
        self.total_value = sum(self.current_values)
        self.current_weights = [v / self.total_value for v in self.current_values]
        self.returns_data = None
        self.cov_matrix = None
        self.mean_returns = None
        
    def fetch_historical_data(self, period: str = '1y') -> pd.DataFrame:
        """Fetch historical price data for all holdings"""
        data = {}
        for symbol in self.symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                data[symbol] = hist['Close']
            except Exception as e:
                print(f"Could not fetch data for {symbol}: {e}")
                # Use random data for demo if fetch fails
                data[symbol] = self._generate_demo_data()
        
        self.returns_data = pd.DataFrame(data)
        self.returns_data = self.returns_data.fillna(method='ffill')
        
        # Calculate daily returns
        self.returns_data = self.returns_data.pct_change().dropna()
        self.mean_returns = self.returns_data.mean() * 252  # Annualized
        self.cov_matrix = self.returns_data.cov() * 252  # Annualized
        
        return self.returns_data
    
    def _generate_demo_data(self) -> pd.Series:
        """Generate demo data for testing"""
        np.random.seed(42)
        price = 100
        prices = []
        for i in range(252):  # 1 year of trading days
            price *= (1 + np.random.normal(0.0005, 0.02))
            prices.append(price)
        return pd.Series(prices)
    
    def calculate_returns(self) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate mean returns and covariance matrix"""
        if self.returns_data is None:
            self.fetch_historical_data()
        return self.mean_returns, self.cov_matrix
    
    def optimize_portfolio(self, method: str = 'sharpe') -> Dict:
        """
        Optimize portfolio using Modern Portfolio Theory
        
        Args:
            method: 'sharpe' for max Sharpe ratio, 'min_vol' for min volatility
        
        Returns:
            Dict with optimized weights and metrics
        """
        if self.returns_data is None:
            self.fetch_historical_data()
        
        n_assets = len(self.symbols)
        
        # Constraints: sum of weights = 1
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        
        # Bounds: weights between 0 and 1 (no short selling)
        bounds = Bounds(0, 1)
        
        # Initial weights (equal distribution)
        initial_weights = np.array([1/n_assets] * n_assets)
        
        if method == 'sharpe':
            # Maximize Sharpe Ratio
            def objective(weights):
                return -self._sharpe_ratio(weights)
        else:
            # Minimize volatility
            def objective(weights):
                return self._portfolio_volatility(weights)
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        optimized_weights = result.x
        
        return {
            'weights': optimized_weights,
            'symbols': self.symbols,
            'expected_return': self._portfolio_return(optimized_weights),
            'volatility': self._portfolio_volatility(optimized_weights),
            'sharpe_ratio': self._sharpe_ratio(optimized_weights),
            'method': method
        }
    
    def _portfolio_return(self, weights: np.ndarray) -> float:
        """Calculate expected portfolio return"""
        return np.dot(weights, self.mean_returns)
    
    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        """Calculate portfolio volatility"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def _sharpe_ratio(self, weights: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        return (self._portfolio_return(weights) - self.risk_free_rate) / self._portfolio_volatility(weights)
    
    def calculate_efficient_frontier(self, points: int = 50) -> Dict:
        """
        Calculate efficient frontier for visualization
        
        Returns:
            Dict with returns, volatility, and optimal portfolios
        """
        if self.returns_data is None:
            self.fetch_historical_data()
        
        n_assets = len(self.symbols)
        target_returns = np.linspace(
            self.mean_returns.min(),
            self.mean_returns.max() * 1.5,
            points
        )
        
        frontiers = []
        
        for target in target_returns:
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: self._portfolio_return(x) - target}
            ]
            bounds = Bounds(0, 1)
            initial = np.array([1/n_assets] * n_assets)
            
            result = minimize(
                lambda x: self._portfolio_volatility(x),
                initial,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                frontiers.append({
                    'return': target,
                    'volatility': self._portfolio_volatility(result.x),
                    'weights': result.x
                })
        
        # Add the max Sharpe portfolio
        sharpe_portfolio = self.optimize_portfolio('sharpe')
        
        # Add min volatility portfolio
        min_vol_portfolio = self.optimize_portfolio('min_vol')
        
        return {
            'frontier': frontiers,
            'max_sharpe': sharpe_portfolio,
            'min_volatility': min_vol_portfolio,
            'current_weights': self.current_weights,
            'symbols': self.symbols
        }
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate correlation matrix between assets"""
        if self.returns_data is None:
            self.fetch_historical_data()
        return self.returns_data.corr()
    
    def stress_test(self, scenario: str = 'mild_crash') -> Dict:
        """
        Stress test portfolio under different scenarios
        
        Scenarios:
        - 'mild_crash': -15% market drop
        - 'severe_crash': -30% market drop
        - 'recession': -20% market drop
        - 'bull_run': +25% market rally
        - 'inflation': +10% inflation impact
        - 'rate_hike': +2% interest rate hike
        """
        scenarios = {
            'mild_crash': {
                'name': 'Mild Market Crash',
                'impact': -0.15,
                'description': '15% market correction'
            },
            'severe_crash': {
                'name': 'Severe Market Crash',
                'impact': -0.30,
                'description': '30% market crash (like 2008)'
            },
            'recession': {
                'name': 'Economic Recession',
                'impact': -0.20,
                'description': '20% decline during recession'
            },
            'bull_run': {
                'name': 'Bull Market Run',
                'impact': 0.25,
                'description': '25% market rally'
            },
            'inflation': {
                'name': 'High Inflation',
                'impact': -0.10,
                'description': '10% erosion due to inflation'
            },
            'rate_hike': {
                'name': 'Interest Rate Hike',
                'impact': -0.08,
                'description': '8% impact from rate hike'
            }
        }
        
        scenario_data = scenarios.get(scenario, scenarios['mild_crash'])
        
        # Calculate impact on each holding (assuming beta=1 for simplicity)
        current_value = self.total_value
        impacted_value = current_value * (1 + scenario_data['impact'])
        
        # Calculate loss amount
        loss = current_value - impacted_value
        
        return {
            'scenario': scenario_data['name'],
            'description': scenario_data['description'],
            'impact_percent': scenario_data['impact'] * 100,
            'current_value': current_value,
            'impacted_value': impacted_value,
            'loss': loss,
            'loss_percent': (loss / current_value) * 100 if current_value > 0 else 0,
            'holdings': [
                {
                    'symbol': h['symbol'],
                    'current_value': h['quantity'] * h['current_price'],
                    'stressed_value': (h['quantity'] * h['current_price']) * (1 + scenario_data['impact']),
                    'loss': (h['quantity'] * h['current_price']) * scenario_data['impact']
                }
                for h in self.holdings
            ]
        }
    
    def get_rebalancing_suggestions(self, threshold: float = 0.05) -> Dict:
        """
        Get rebalancing suggestions based on current vs target weights
        
        Args:
            threshold: Deviation threshold to trigger rebalancing (default 5%)
        
        Returns:
            Dict with rebalancing suggestions
        """
        # Calculate target weights (using max Sharpe portfolio)
        target_portfolio = self.optimize_portfolio('sharpe')
        target_weights = target_portfolio['weights']
        
        # Current weights
        current_weights = np.array(self.current_weights)
        
        # Calculate deviations
        deviations = target_weights - current_weights
        
        suggestions = []
        for i, symbol in enumerate(self.symbols):
            if abs(deviations[i]) > threshold:
                action = 'BUY' if deviations[i] > 0 else 'SELL'
                amount = abs(deviations[i]) * self.total_value
                suggestions.append({
                    'symbol': symbol,
                    'action': action,
                    'current_weight': current_weights[i] * 100,
                    'target_weight': target_weights[i] * 100,
                    'deviation': deviations[i] * 100,
                    'amount': amount,
                    'priority': abs(deviations[i])
                })
        
        # Sort by priority (largest deviation first)
        suggestions.sort(key=lambda x: x['priority'], reverse=True)
        
        return {
            'needs_rebalancing': len(suggestions) > 0,
            'suggestions': suggestions,
            'current_weights': {s: w*100 for s, w in zip(self.symbols, current_weights)},
            'target_weights': {s: w*100 for s, w in zip(self.symbols, target_weights)}
        }
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        if self.returns_data is None:
            self.fetch_historical_data()
        
        # Calculate metrics
        current_return = self._portfolio_return(np.array(self.current_weights))
        current_volatility = self._portfolio_volatility(np.array(self.current_weights))
        current_sharpe = self._sharpe_ratio(np.array(self.current_weights))
        
        # Max Sharpe portfolio
        max_sharpe = self.optimize_portfolio('sharpe')
        
        # Min volatility portfolio
        min_vol = self.optimize_portfolio('min_vol')
        
        # Correlation matrix
        correlation = self.calculate_correlation_matrix()
        
        return {
            'current_portfolio': {
                'total_value': self.total_value,
                'return': current_return * 100,
                'volatility': current_volatility * 100,
                'sharpe_ratio': current_sharpe
            },
            'max_sharpe_portfolio': {
                'return': max_sharpe['expected_return'] * 100,
                'volatility': max_sharpe['volatility'] * 100,
                'sharpe_ratio': max_sharpe['sharpe_ratio'],
                'weights': {s: w*100 for s, w in zip(self.symbols, max_sharpe['weights'])}
            },
            'min_volatility_portfolio': {
                'return': min_vol['expected_return'] * 100,
                'volatility': min_vol['volatility'] * 100,
                'sharpe_ratio': min_vol['sharpe_ratio'],
                'weights': {s: w*100 for s, w in zip(self.symbols, min_vol['weights'])}
            },
            'correlation_matrix': correlation.to_dict(),
            'symbols': self.symbols
        }