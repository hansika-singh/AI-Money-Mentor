"""
Anomaly Detection Engine for Bank Transactions
Real-time fraud detection and unusual pattern identification
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
from collections import defaultdict


class AnomalyDetector:
    """
    Advanced Anomaly Detection for Financial Transactions
    """
    
    def __init__(self):
        # Thresholds (in INR)
        self.thresholds = {
            'daily_spent': 50000,
            'single_transaction': 25000,
            'unusual_category': 10000,
            'frequency': 5,
            'velocity': 3,
            'amount_variance': 3.0,
            'weekend_spike': 2.0,
            'new_merchant': 15000,
        }
        
        # Category risk levels
        self.category_risk = {
            'Entertainment': 0.8,
            'Shopping': 0.7,
            'Travel': 0.6,
            'Food': 0.3,
            'Utilities': 0.1,
            'Rent': 0.1,
            'Transport': 0.3,
            'Healthcare': 0.2,
            'Education': 0.2,
            'Other': 0.5
        }
    
    def detect_anomalies(self, transactions: List[Dict], user_history: List[Dict] = None) -> List[Dict]:
        """Detect anomalies in a list of transactions"""
        anomalies = []
        
        if not transactions:
            return anomalies
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].astype(float)
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
        # 1. Single Transaction Amount Anomaly
        anomalies.extend(self._detect_amount_anomalies(df))
        
        # 2. Category-based Anomalies
        anomalies.extend(self._detect_category_anomalies(df))
        
        # 3. Frequency Anomalies
        anomalies.extend(self._detect_frequency_anomalies(df))
        
        # 4. Merchant-based Anomalies
        anomalies.extend(self._detect_merchant_anomalies(df, user_history))
        
        # 5. Pattern Anomalies
        anomalies.extend(self._detect_pattern_anomalies(df))
        
        return anomalies
    
    def _detect_amount_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect amount-based anomalies"""
        anomalies = []
        
        for _, row in df.iterrows():
            if row['amount'] > self.thresholds['single_transaction']:
                anomalies.append({
                    'transaction': row.to_dict(),
                    'type': 'high_amount',
                    'severity': 'high',
                    'reason': f"Transaction amount ₹{row['amount']:,.2f} exceeds threshold of ₹{self.thresholds['single_transaction']:,.2f}"
                })
        
        if 'transaction_date' in df.columns:
            for date, group in df.groupby(df['transaction_date'].dt.date):
                daily_total = group['amount'].sum()
                if daily_total > self.thresholds['daily_spent']:
                    anomalies.append({
                        'transaction': group.iloc[0].to_dict(),
                        'type': 'high_daily_spending',
                        'severity': 'medium',
                        'reason': f"Daily spending ₹{daily_total:,.2f} exceeds threshold of ₹{self.thresholds['daily_spent']:,.2f}"
                    })
        
        return anomalies
    
    def _detect_category_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect category-based anomalies"""
        anomalies = []
        
        for _, row in df.iterrows():
            category = row.get('category', 'Other')
            amount = row['amount']
            
            if category in ['Entertainment', 'Shopping'] and amount > self.thresholds['unusual_category']:
                anomalies.append({
                    'transaction': row.to_dict(),
                    'type': 'unusual_category',
                    'severity': 'medium',
                    'reason': f"Unusual spending of ₹{amount:,.2f} in category '{category}'"
                })
            
            risk_score = self.category_risk.get(category, 0.5)
            if risk_score > 0.7 and amount > 5000:
                anomalies.append({
                    'transaction': row.to_dict(),
                    'type': 'high_risk_category',
                    'severity': 'medium',
                    'reason': f"High-risk transaction in category '{category}' for ₹{amount:,.2f}"
                })
        
        return anomalies
    
    def _detect_frequency_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect frequency-based anomalies"""
        anomalies = []
        
        if 'transaction_date' not in df.columns:
            return anomalies
        
        df['hour'] = df['transaction_date'].dt.hour
        hourly_counts = df.groupby('hour').size()
        
        for hour, count in hourly_counts.items():
            if count > self.thresholds['velocity']:
                anomalies.append({
                    'transaction': df[df['hour'] == hour].iloc[0].to_dict(),
                    'type': 'high_velocity',
                    'severity': 'high',
                    'reason': f"{count} transactions in one hour (threshold: {self.thresholds['velocity']})"
                })
        
        daily_counts = df.groupby(df['transaction_date'].dt.date).size()
        for date, count in daily_counts.items():
            if count > self.thresholds['frequency']:
                anomalies.append({
                    'transaction': df[df['transaction_date'].dt.date == date].iloc[0].to_dict(),
                    'type': 'high_frequency',
                    'severity': 'medium',
                    'reason': f"{count} transactions in one day (threshold: {self.thresholds['frequency']})"
                })
        
        return anomalies
    
    def _detect_merchant_anomalies(self, df: pd.DataFrame, user_history: List[Dict] = None) -> List[Dict]:
        """Detect merchant-based anomalies"""
        anomalies = []
        
        if user_history:
            historical_merchants = set()
            for tx in user_history:
                merchant = tx.get('merchant')
                if merchant:
                    historical_merchants.add(merchant)
            
            for _, row in df.iterrows():
                merchant = row.get('merchant')
                amount = row['amount']
                
                if merchant and merchant not in historical_merchants and amount > self.thresholds['new_merchant']:
                    anomalies.append({
                        'transaction': row.to_dict(),
                        'type': 'new_merchant_high_amount',
                        'severity': 'medium',
                        'reason': f"New merchant '{merchant}' with high amount ₹{amount:,.2f}"
                    })
        
        return anomalies
    
    def _detect_pattern_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect pattern-based anomalies"""
        anomalies = []
        
        if len(df) < 3 or 'amount' not in df.columns:
            return anomalies
        
        mean_amount = df['amount'].mean()
        std_amount = df['amount'].std()
        
        for _, row in df.iterrows():
            if std_amount > 0:
                z_score = (row['amount'] - mean_amount) / std_amount
                if abs(z_score) > self.thresholds['amount_variance']:
                    anomalies.append({
                        'transaction': row.to_dict(),
                        'type': 'amount_variance',
                        'severity': 'medium',
                        'reason': f"Transaction amount ₹{row['amount']:,.2f} is {abs(z_score):.1f} standard deviations from mean"
                    })
        
        if 'transaction_date' in df.columns:
            df['is_weekend'] = df['transaction_date'].dt.dayofweek >= 5
            if len(df[df['is_weekend']]) > 0 and len(df[~df['is_weekend']]) > 0:
                avg_weekend = df[df['is_weekend']]['amount'].mean()
                avg_weekday = df[~df['is_weekend']]['amount'].mean()
                
                if avg_weekday > 0 and avg_weekend / avg_weekday > self.thresholds['weekend_spike']:
                    anomalies.append({
                        'transaction': df[df['is_weekend']].iloc[0].to_dict(),
                        'type': 'weekend_spike',
                        'severity': 'low',
                        'reason': f"Weekend spending {avg_weekend/avg_weekday:.1f}x higher than weekday average"
                    })
        
        return anomalies
    
    def get_risk_score(self, transaction: Dict) -> int:
        """Calculate risk score for a transaction (0-100)"""
        risk = 0
        amount = float(transaction.get('amount', 0))
        category = transaction.get('category', 'Other')
        
        if amount > self.thresholds['single_transaction']:
            risk += 40
        elif amount > 10000:
            risk += 20
        elif amount > 5000:
            risk += 10
        
        category_risk = self.category_risk.get(category, 0.5)
        risk += int(category_risk * 20)
        
        if transaction.get('location_change', False):
            risk += 20
        
        if transaction.get('is_new_merchant', False):
            risk += 15
        
        return min(risk, 100)