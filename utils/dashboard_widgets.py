"""
Interactive Financial Dashboard with Customizable Widgets
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json


class DashboardWidgetManager:
    """
    Manage dashboard widgets and layouts
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.widgets = self._get_default_widgets()
        self.layouts = {}
    
    def _get_default_widgets(self) -> List[Dict]:
        """Get default widget definitions"""
        return [
            {
                'id': 'net_worth',
                'title': '💎 Net Worth',
                'type': 'net_worth',
                'size': 'medium',
                'icon': '💎',
                'is_default': True,
                'position': 0
            },
            {
                'id': 'spending_trend',
                'title': '📈 Spending Trend',
                'type': 'spending_trend',
                'size': 'large',
                'icon': '📈',
                'is_default': True,
                'position': 1
            },
            {
                'id': 'budget_health',
                'title': '🎯 Budget Health',
                'type': 'budget_health',
                'size': 'medium',
                'icon': '🎯',
                'is_default': True,
                'position': 2
            },
            {
                'id': 'recent_transactions',
                'title': '💳 Recent Transactions',
                'type': 'recent_transactions',
                'size': 'medium',
                'icon': '💳',
                'is_default': True,
                'position': 3
            },
            {
                'id': 'portfolio_summary',
                'title': '📊 Portfolio Summary',
                'type': 'portfolio_summary',
                'size': 'large',
                'icon': '📊',
                'is_default': True,
                'position': 4
            },
            {
                'id': 'goals_progress',
                'title': '🎯 Goals Progress',
                'type': 'goals_progress',
                'size': 'medium',
                'icon': '🎯',
                'is_default': True,
                'position': 5
            },
            {
                'id': 'cash_flow',
                'title': '💰 Cash Flow',
                'type': 'cash_flow',
                'size': 'medium',
                'icon': '💰',
                'is_default': True,
                'position': 6
            },
            {
                'id': 'upcoming_bills',
                'title': '📅 Upcoming Bills',
                'type': 'upcoming_bills',
                'size': 'small',
                'icon': '📅',
                'is_default': True,
                'position': 7
            },
            {
                'id': 'investment_returns',
                'title': '📈 Investment Returns',
                'type': 'investment_returns',
                'size': 'medium',
                'icon': '📈',
                'is_default': False,
                'position': 8
            },
            {
                'id': 'savings_rate',
                'title': '💾 Savings Rate',
                'type': 'savings_rate',
                'size': 'small',
                'icon': '💾',
                'is_default': False,
                'position': 9
            },
            {
                'id': 'credit_score',
                'title': '⭐ Credit Score',
                'type': 'credit_score',
                'size': 'small',
                'icon': '⭐',
                'is_default': False,
                'position': 10
            },
            {
                'id': 'market_news',
                'title': '📰 Market News',
                'type': 'market_news',
                'size': 'large',
                'icon': '📰',
                'is_default': False,
                'position': 11
            },
            {
                'id': 'tax_estimator',
                'title': '💸 Tax Estimator',
                'type': 'tax_estimator',
                'size': 'medium',
                'icon': '💸',
                'is_default': False,
                'position': 12
            },
            {
                'id': 'emergency_fund',
                'title': '🛡️ Emergency Fund',
                'type': 'emergency_fund',
                'size': 'small',
                'icon': '🛡️',
                'is_default': False,
                'position': 13
            },
            {
                'id': 'expense_categories',
                'title': '📊 Expense Categories',
                'type': 'expense_categories',
                'size': 'medium',
                'icon': '📊',
                'is_default': False,
                'position': 14
            }
        ]
    
    def get_widgets(self, layout_id: str = 'default') -> List[Dict]:
        """Get widgets for a specific layout"""
        if layout_id in self.layouts:
            return self.layouts[layout_id]['widgets']
        return self.widgets
    
    def get_available_widgets(self) -> List[Dict]:
        """Get all available widgets"""
        return self._get_default_widgets()
    
    def save_layout(self, layout_id: str, widgets: List[Dict], name: str = '') -> Dict:
        """Save a dashboard layout"""
        if layout_id not in self.layouts:
            self.layouts[layout_id] = {
                'id': layout_id,
                'name': name or f'Layout {len(self.layouts) + 1}',
                'widgets': widgets,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        else:
            self.layouts[layout_id]['widgets'] = widgets
            self.layouts[layout_id]['updated_at'] = datetime.now().isoformat()
            if name:
                self.layouts[layout_id]['name'] = name
        
        return self.layouts[layout_id]
    
    def get_layouts(self) -> Dict:
        """Get all saved layouts"""
        return self.layouts
    
    def delete_layout(self, layout_id: str) -> bool:
        """Delete a layout"""
        if layout_id in self.layouts:
            del self.layouts[layout_id]
            return True
        return False
    
    def get_widget_data(self, widget_type: str, user_data: Dict) -> Dict:
        """Get data for a specific widget type"""
        widget_handlers = {
            'net_worth': self._get_net_worth_data,
            'spending_trend': self._get_spending_trend_data,
            'budget_health': self._get_budget_health_data,
            'recent_transactions': self._get_recent_transactions_data,
            'portfolio_summary': self._get_portfolio_summary_data,
            'goals_progress': self._get_goals_progress_data,
            'cash_flow': self._get_cash_flow_data,
            'upcoming_bills': self._get_upcoming_bills_data,
            'investment_returns': self._get_investment_returns_data,
            'savings_rate': self._get_savings_rate_data,
            'credit_score': self._get_credit_score_data,
            'market_news': self._get_market_news_data,
            'tax_estimator': self._get_tax_estimator_data,
            'emergency_fund': self._get_emergency_fund_data,
            'expense_categories': self._get_expense_categories_data
        }
        
        handler = widget_handlers.get(widget_type)
        if handler:
            return handler(user_data)
        return {'error': 'Unknown widget type'}
    
    def _get_net_worth_data(self, data: Dict) -> Dict:
        total_assets = data.get('total_assets', 0)
        total_liabilities = data.get('total_liabilities', 0)
        return {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'net_worth': total_assets - total_liabilities,
            'change': data.get('net_worth_change', 0)
        }
    
    def _get_spending_trend_data(self, data: Dict) -> Dict:
        return {
            'current_month': data.get('current_spending', 0),
            'previous_month': data.get('previous_spending', 0),
            'trend': data.get('spending_trend', []),
            'change_percent': data.get('spending_change', 0)
        }
    
    def _get_budget_health_data(self, data: Dict) -> Dict:
        return {
            'total_budget': data.get('total_budget', 0),
            'total_spent': data.get('total_spent', 0),
            'remaining': data.get('remaining_budget', 0),
            'health_percent': data.get('budget_health', 0),
            'categories': data.get('budget_categories', [])
        }
    
    def _get_recent_transactions_data(self, data: Dict) -> Dict:
        return {
            'transactions': data.get('recent_transactions', [])
        }
    
    def _get_portfolio_summary_data(self, data: Dict) -> Dict:
        return {
            'total_value': data.get('portfolio_value', 0),
            'returns': data.get('portfolio_returns', 0),
            'holdings': data.get('holdings', [])
        }
    
    def _get_goals_progress_data(self, data: Dict) -> Dict:
        return {
            'goals': data.get('financial_goals', [])
        }
    
    def _get_cash_flow_data(self, data: Dict) -> Dict:
        return {
            'income': data.get('income', 0),
            'expenses': data.get('expenses', 0),
            'net': data.get('net_cash_flow', 0)
        }
    
    def _get_upcoming_bills_data(self, data: Dict) -> Dict:
        return {
            'bills': data.get('upcoming_bills', [])
        }
    
    def _get_investment_returns_data(self, data: Dict) -> Dict:
        return {
            'total_returns': data.get('total_returns', 0),
            'yield': data.get('yield', 0)
        }
    
    def _get_savings_rate_data(self, data: Dict) -> Dict:
        return {
            'savings_rate': data.get('savings_rate', 0),
            'target': data.get('savings_target', 20)
        }
    
    def _get_credit_score_data(self, data: Dict) -> Dict:
        return {
            'score': data.get('credit_score', 0),
            'rating': data.get('credit_rating', 'N/A')
        }
    
    def _get_market_news_data(self, data: Dict) -> Dict:
        return {
            'news': data.get('market_news', [])
        }
    
    def _get_tax_estimator_data(self, data: Dict) -> Dict:
        return {
            'estimated_tax': data.get('estimated_tax', 0),
            'savings': data.get('tax_savings', 0)
        }
    
    def _get_emergency_fund_data(self, data: Dict) -> Dict:
        return {
            'current': data.get('emergency_fund', 0),
            'target': data.get('emergency_target', 0)
        }
    
    def _get_expense_categories_data(self, data: Dict) -> Dict:
        return {
            'categories': data.get('expense_categories', [])
        }