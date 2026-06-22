"""
Predictive Financial Models & Smart Alerts System
Machine Learning-based financial forecasting and proactive alerts
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


class FinancialPredictor:
    """
    Advanced Financial Prediction System with Machine Learning
    """
    
    def __init__(self):
        self.models = {
            'spending': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            ),
            'balance': LinearRegression()
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_dir = 'models'
        
        # Create model directory if not exists
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # Load existing models if available
        self._load_models()
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            for model_name in self.models.keys():
                model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
                if os.path.exists(model_path):
                    self.models[model_name] = joblib.load(model_path)
                    print(f"✅ Loaded {model_name} model")
            self.is_trained = True
        except Exception as e:
            print(f"⚠️ Could not load models: {e}")
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            for model_name, model in self.models.items():
                model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
                joblib.dump(model, model_path)
            print("✅ Models saved successfully")
        except Exception as e:
            print(f"⚠️ Could not save models: {e}")
    
    def _prepare_training_data(self, transactions: List[Dict]) -> pd.DataFrame:
        """
        Prepare transaction data for ML training
        
        Args:
            transactions: List of transaction dicts
        
        Returns:
            DataFrame with features
        """
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = df['amount'].astype(float)
        
        # Create date features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['year'] = df['date'].dt.year
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        df['is_month_start'] = df['day_of_month'].apply(lambda x: 1 if x <= 3 else 0)
        df['is_month_end'] = df['day_of_month'].apply(lambda x: 1 if x >= 28 else 0)
        
        # Add lag features
        df = df.sort_values('date')
        for lag in [1, 7, 14, 30]:
            df[f'amount_lag_{lag}'] = df['amount'].shift(lag)
        
        # Add rolling features
        for window in [7, 14, 30]:
            df[f'rolling_mean_{window}'] = df['amount'].rolling(window=window).mean()
            df[f'rolling_std_{window}'] = df['amount'].rolling(window=window).std()
        
        # Add category encoding
        if 'category' in df.columns:
            df['category_encoded'] = pd.Categorical(df['category']).codes
        
        # Drop rows with NaN values
        df = df.dropna()
        
        return df
    
    def train_models(self, transactions: List[Dict]) -> Dict:
        """
        Train ML models on transaction data
        
        Args:
            transactions: List of transaction dicts
        
        Returns:
            Training metrics
        """
        if len(transactions) < 30:
            return {
                'success': False,
                'error': 'Need at least 30 transactions for training'
            }
        
        df = self._prepare_training_data(transactions)
        if df.empty:
            return {
                'success': False,
                'error': 'No data available for training'
            }
        
        # Feature columns
        feature_cols = [
            'day_of_week', 'day_of_month', 'month', 'quarter',
            'is_weekend', 'is_month_start', 'is_month_end',
            'amount_lag_1', 'amount_lag_7', 'amount_lag_14', 'amount_lag_30',
            'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_30',
            'rolling_std_7', 'rolling_std_14', 'rolling_std_30'
        ]
        
        # Add category if available
        if 'category_encoded' in df.columns:
            feature_cols.append('category_encoded')
        
        X = df[feature_cols]
        y = df['amount']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Train Random Forest for spending prediction
        self.models['spending'].fit(X_train, y_train)
        
        # Train Linear Regression for balance prediction
        self.models['balance'].fit(X_train, y_train)
        
        # Evaluate models
        spending_pred = self.models['spending'].predict(X_test)
        balance_pred = self.models['balance'].predict(X_test)
        
        spending_mae = mean_absolute_error(y_test, spending_pred)
        balance_mae = mean_absolute_error(y_test, balance_pred)
        
        spending_r2 = r2_score(y_test, spending_pred)
        balance_r2 = r2_score(y_test, balance_pred)
        
        self.is_trained = True
        self._save_models()
        
        return {
            'success': True,
            'metrics': {
                'spending': {
                    'mae': round(spending_mae, 2),
                    'r2': round(spending_r2, 4),
                    'samples': len(y_test)
                },
                'balance': {
                    'mae': round(balance_mae, 2),
                    'r2': round(balance_r2, 4),
                    'samples': len(y_test)
                }
            }
        }
    
    def predict_spending(self, transactions: List[Dict], days: int = 30) -> Dict:
        """
        Predict future spending
        
        Args:
            transactions: Historical transactions
            days: Number of days to forecast
        
        Returns:
            Dict with predictions
        """
        if not self.is_trained:
            return {
                'success': False,
                'error': 'Models not trained yet'
            }
        
        if len(transactions) < 30:
            return {
                'success': False,
                'error': 'Need at least 30 transactions for prediction'
            }
        
        df = self._prepare_training_data(transactions)
        if df.empty:
            return {
                'success': False,
                'error': 'No data available for prediction'
            }
        
        # Get latest transaction date
        latest_date = pd.to_datetime(df['date'].max())
        
        # Create future dates
        future_dates = [latest_date + timedelta(days=i+1) for i in range(days)]
        
        # Predict for each future date
        predictions = []
        for future_date in future_dates:
            # Create feature row for future date
            future_features = {
                'day_of_week': future_date.weekday(),
                'day_of_month': future_date.day,
                'month': future_date.month,
                'quarter': (future_date.month - 1) // 3 + 1,
                'is_weekend': 1 if future_date.weekday() >= 5 else 0,
                'is_month_start': 1 if future_date.day <= 3 else 0,
                'is_month_end': 1 if future_date.day >= 28 else 0,
                'amount_lag_1': df['amount'].iloc[-1] if len(df) > 0 else 0,
                'amount_lag_7': df['amount'].iloc[-7] if len(df) >= 7 else 0,
                'amount_lag_14': df['amount'].iloc[-14] if len(df) >= 14 else 0,
                'amount_lag_30': df['amount'].iloc[-30] if len(df) >= 30 else 0,
                'rolling_mean_7': df['rolling_mean_7'].iloc[-1] if 'rolling_mean_7' in df.columns else 0,
                'rolling_mean_14': df['rolling_mean_14'].iloc[-1] if 'rolling_mean_14' in df.columns else 0,
                'rolling_mean_30': df['rolling_mean_30'].iloc[-1] if 'rolling_mean_30' in df.columns else 0,
                'rolling_std_7': df['rolling_std_7'].iloc[-1] if 'rolling_std_7' in df.columns else 0,
                'rolling_std_14': df['rolling_std_14'].iloc[-1] if 'rolling_std_14' in df.columns else 0,
                'rolling_std_30': df['rolling_std_30'].iloc[-1] if 'rolling_std_30' in df.columns else 0,
            }
            
            # Add category if available
            if 'category_encoded' in df.columns:
                future_features['category_encoded'] = df['category_encoded'].mode()[0]
            
            # Convert to DataFrame
            future_df = pd.DataFrame([future_features])
            
            # Align columns with training data
            feature_cols = self._get_feature_cols(df)
            for col in feature_cols:
                if col not in future_df.columns:
                    future_df[col] = 0
            
            future_df = future_df[feature_cols]
            
            # Scale features
            future_scaled = self.scaler.transform(future_df)
            
            # Predict
            predicted = self.models['spending'].predict(future_scaled)[0]
            
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_amount': round(max(predicted, 0), 2)
            })
        
        # Calculate total predicted spending
        total_spending = sum(p['predicted_amount'] for p in predictions)
        
        return {
            'success': True,
            'predictions': predictions,
            'total_spending': round(total_spending, 2),
            'days': days,
            'start_date': future_dates[0].strftime('%Y-%m-%d'),
            'end_date': future_dates[-1].strftime('%Y-%m-%d')
        }
    
    def _get_feature_cols(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns from DataFrame"""
        feature_cols = [
            'day_of_week', 'day_of_month', 'month', 'quarter',
            'is_weekend', 'is_month_start', 'is_month_end',
            'amount_lag_1', 'amount_lag_7', 'amount_lag_14', 'amount_lag_30',
            'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_30',
            'rolling_std_7', 'rolling_std_14', 'rolling_std_30'
        ]
        
        if 'category_encoded' in df.columns:
            feature_cols.append('category_encoded')
        
        return [col for col in feature_cols if col in df.columns]
    
    def predict_balance(self, income: float, expenses: float, transactions: List[Dict], days: int = 30) -> Dict:
        """
        Predict future balance
        
        Args:
            income: Monthly income
            expenses: Current monthly expenses
            transactions: Historical transactions
            days: Forecast period
        
        Returns:
            Dict with balance predictions and alerts
        """
        # Get spending prediction
        spending_pred = self.predict_spending(transactions, days)
        
        if not spending_pred.get('success'):
            return spending_pred
        
        # Calculate daily balance
        daily_income = income / 30
        daily_spending = spending_pred['total_spending'] / days
        
        daily_net = daily_income - daily_spending
        
        # Generate balance forecast
        balance_forecast = []
        current_balance = expenses  # Starting balance
        for pred in spending_pred['predictions']:
            current_balance += daily_income - pred['predicted_amount']
            balance_forecast.append({
                'date': pred['date'],
                'balance': round(current_balance, 2)
            })
        
        final_balance = balance_forecast[-1]['balance'] if balance_forecast else current_balance
        
        # Generate alerts
        alerts = []
        recommendations = []
        
        # Check for overspending
        if final_balance < 0:
            alerts.append({
                'type': 'overspend',
                'severity': 'high',
                'message': f"⚠️ You may overspend ₹{abs(final_balance):,.2f} in the next {days} days!",
                'action_required': True
            })
            recommendations.append({
                'type': 'reduce_spending',
                'message': f"💡 Try to reduce daily spending by ₹{abs(final_balance) / days:.2f} to stay within budget"
            })
        
        # Check for low balance
        elif final_balance < (income * 0.1):
            alerts.append({
                'type': 'low_balance',
                'severity': 'medium',
                'message': f"⚠️ Your balance may drop to ₹{final_balance:,.2f} in {days} days",
                'action_required': False
            })
            recommendations.append({
                'type': 'increase_savings',
                'message': f"💡 Consider saving an extra ₹{(income * 0.1) - final_balance:.2f} this month"
            })
        
        # Check for surplus
        elif final_balance > (income * 0.3):
            alerts.append({
                'type': 'surplus',
                'severity': 'low',
                'message': f"✅ You may have a surplus of ₹{final_balance:,.2f} after {days} days",
                'action_required': False
            })
            recommendations.append({
                'type': 'invest_surplus',
                'message': f"💡 Consider investing ₹{final_balance * 0.5:,.2f} in a short-term FD or mutual fund"
            })
        
        return {
            'success': True,
            'balance_forecast': balance_forecast,
            'final_balance': round(final_balance, 2),
            'daily_income': round(daily_income, 2),
            'daily_spending': round(daily_spending, 2),
            'daily_net': round(daily_net, 2),
            'alerts': alerts,
            'recommendations': recommendations,
            'summary': {
                'income': income,
                'projected_expenses': spending_pred['total_spending'],
                'net_flow': round(income - spending_pred['total_spending'], 2),
                'days': days
            }
        }
    
    def analyze_seasonal_patterns(self, transactions: List[Dict]) -> Dict:
        """
        Analyze seasonal spending patterns
        
        Args:
            transactions: List of transaction dicts
        
        Returns:
            Dict with seasonal analysis
        """
        if len(transactions) < 30:
            return {
                'success': False,
                'error': 'Need at least 30 transactions for analysis'
            }
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = df['amount'].astype(float)
        
        # Group by month
        monthly_spending = df.groupby(df['date'].dt.month)['amount'].sum().to_dict()
        monthly_avg = df.groupby(df['date'].dt.month)['amount'].mean().to_dict()
        
        # Group by day of week
        weekly_pattern = df.groupby(df['date'].dt.dayofweek)['amount'].sum().to_dict()
        weekly_avg = df.groupby(df['date'].dt.dayofweek)['amount'].mean().to_dict()
        
        # Group by category
        category_spending = df.groupby('category')['amount'].sum().to_dict() if 'category' in df.columns else {}
        
        # Find peak spending months
        if monthly_spending:
            peak_month = max(monthly_spending.items(), key=lambda x: x[1])[0]
        else:
            peak_month = None
        
        # Find highest spending day of week
        if weekly_pattern:
            peak_day = max(weekly_pattern.items(), key=lambda x: x[1])[0]
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            peak_day_name = day_names[peak_day] if peak_day < len(day_names) else 'Unknown'
        else:
            peak_day_name = None
        
        return {
            'success': True,
            'monthly_spending': monthly_spending,
            'monthly_average': monthly_avg,
            'weekly_pattern': weekly_pattern,
            'weekly_average': weekly_avg,
            'category_spending': category_spending,
            'peak_month': peak_month,
            'peak_day': peak_day_name,
            'total_transactions': len(transactions),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            }
        }
    
    def get_savings_recommendations(self, transactions: List[Dict], income: float) -> Dict:
        """
        Get personalized savings recommendations
        
        Args:
            transactions: List of transaction dicts
            income: Monthly income
        
        Returns:
            Dict with recommendations
        """
        if len(transactions) < 10:
            return {
                'success': False,
                'error': 'Need at least 10 transactions for recommendations'
            }
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].astype(float)
        
        total_spent = df['amount'].sum()
        savings_rate = (income - total_spent) / income * 100 if income > 0 else 0
        
        # Find top spending categories
        category_spending = df.groupby('category')['amount'].sum().to_dict() if 'category' in df.columns else {}
        sorted_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        
        # Recommendation 1: General savings advice
        if savings_rate < 20:
            recommendations.append({
                'type': 'savings_rate',
                'priority': 'high',
                'message': f"Your savings rate is {savings_rate:.1f}%. Aim for at least 20%",
                'suggestion': f"Try to save an additional ₹{(income * 0.2 - total_spent):.2f} per month"
            })
        
        # Recommendation 2: Category-specific advice
        for category, amount in sorted_categories[:3]:
            if amount > (total_spent * 0.3):
                recommendations.append({
                    'type': 'category_spending',
                    'priority': 'medium',
                    'category': category,
                    'message': f"You spend ₹{amount:,.2f} on {category} ({amount/total_spent*100:.1f}% of total)",
                    'suggestion': f"Consider reducing {category} spending by 10% to save ₹{amount*0.1:.2f}"
                })
        
        # Recommendation 3: Emergency fund
        if income > 0 and total_spent > 0:
            monthly_expenses = total_spent / (len(transactions) / 30) if len(transactions) > 0 else 0
            emergency_fund_needed = monthly_expenses * 6
            recommendations.append({
                'type': 'emergency_fund',
                'priority': 'medium',
                'message': f"Your monthly expenses are ₹{monthly_expenses:,.2f}",
                'suggestion': f"Target emergency fund: ₹{emergency_fund_needed:,.2f} (6 months of expenses)"
            })
        
        return {
            'success': True,
            'savings_rate': round(savings_rate, 1),
            'total_spent': round(total_spent, 2),
            'top_categories': sorted_categories[:3],
            'recommendations': recommendations
        }
    
    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect anomalous transactions
        
        Args:
            transactions: List of transaction dicts
        
        Returns:
            List of anomalies
        """
        if len(transactions) < 10:
            return []
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].astype(float)
        df['date'] = pd.to_datetime(df['date'])
        
        anomalies = []
        
        # Statistical anomaly detection (Z-score)
        mean_amount = df['amount'].mean()
        std_amount = df['amount'].std()
        
        if std_amount > 0:
            df['z_score'] = (df['amount'] - mean_amount) / std_amount
            suspicious = df[df['z_score'].abs() > 2.5]
            
            for _, row in suspicious.iterrows():
                anomalies.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'amount': float(row['amount']),
                    'category': row.get('category', 'Unknown'),
                    'reason': f"Amount is {abs(row['z_score']):.1f} standard deviations from mean",
                    'severity': 'high' if abs(row['z_score']) > 3 else 'medium'
                })
        
        return anomalies