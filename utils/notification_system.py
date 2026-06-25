"""
Smart Notification System with WebSocket Real-Time Alerts
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask_socketio import emit, join_room, leave_room

from models import db, Notification, NotificationPreference


class NotificationSystem:
    """
    Real-time Notification System with WebSocket Support
    """
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.user_channels = {}
        
        # Alert importance levels
        self.important_types = {
            'high': ['overspend', 'anomaly', 'fraud_alert', 'critical_budget'],
            'medium': ['goal_completed', 'investment_opportunity', 'budget_alert'],
            'low': ['expense_added', 'goal_progress', 'weekly_summary']
        }
    
    def set_socketio(self, socketio):
        """Set SocketIO instance"""
        self.socketio = socketio
    
    def send_notification(self, user_id: int, notification_data: Dict) -> Dict:
        """
        Send a notification to a user
        
        Args:
            user_id: User ID
            notification_data: Notification data
        
        Returns:
            Dict with notification details
        """
        try:
            # Create notification record
            notification = Notification(
                user_id=user_id,
                type=notification_data.get('type', 'general'),
                title=notification_data.get('title', 'Notification'),
                message=notification_data.get('message', ''),
                severity=notification_data.get('severity', 'medium'),
                category=notification_data.get('category', 'general'),
                action_url=notification_data.get('action_url'),
                action_label=notification_data.get('action_label'),
                metadata_json=json.dumps(notification_data.get('metadata', {})) if notification_data.get('metadata') else None
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Check if user wants this notification type
            pref = NotificationPreference.query.filter_by(
                user_id=user_id,
                type=notification_data.get('type', 'general')
            ).first()
            
            if pref and not pref.enabled:
                return {'success': True, 'sent': False, 'reason': 'Disabled by user'}
            
            # Send real-time notification via WebSocket
            if self.socketio:
                try:
                    room = f'user_{user_id}'
                    self.socketio.emit('notification', {
                        'id': notification.id,
                        'type': notification.type,
                        'title': notification.title,
                        'message': notification.message,
                        'severity': notification.severity,
                        'category': notification.category,
                        'created_at': notification.created_at.isoformat() if notification.created_at else None,
                        'action_url': notification.action_url,
                        'action_label': notification.action_label
                    }, room=room)
                except Exception as e:
                    print(f"WebSocket emit error: {e}")
            
            return {
                'success': True,
                'sent': True,
                'notification_id': notification.id,
                'notification': notification.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def send_bulk_notifications(self, user_ids: List[int], notification_data: Dict) -> Dict:
        """
        Send notifications to multiple users
        
        Args:
            user_ids: List of user IDs
            notification_data: Notification data
        
        Returns:
            Dict with results
        """
        results = []
        for user_id in user_ids:
            result = self.send_notification(user_id, notification_data)
            results.append(result)
        
        return {
            'success': True,
            'total': len(results),
            'sent': sum(1 for r in results if r.get('sent', False)),
            'results': results
        }
    
    def get_notifications(self, user_id: int, limit: int = 50, offset: int = 0, only_unread: bool = False) -> Dict:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            limit: Number of notifications
            offset: Pagination offset
            only_unread: Only fetch unread notifications
        
        Returns:
            Dict with notifications and metadata
        """
        query = Notification.query.filter_by(user_id=user_id)
        
        if only_unread:
            query = query.filter_by(is_read=False, is_dismissed=False)
        
        total = query.count()
        notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'notifications': [n.to_dict() for n in notifications]
        }
    
    def mark_read(self, user_id: int, notification_id: int = None) -> Dict:
        """
        Mark notification(s) as read
        
        Args:
            user_id: User ID
            notification_id: Specific notification ID or None for all
        
        Returns:
            Dict with results
        """
        try:
            if notification_id:
                notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
                if not notification:
                    return {'success': False, 'error': 'Notification not found'}
                
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                db.session.commit()
                
                return {'success': True, 'marked': 1}
            else:
                # Mark all as read
                notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
                count = len(notifications)
                
                for n in notifications:
                    n.is_read = True
                    n.read_at = datetime.utcnow()
                
                db.session.commit()
                
                return {'success': True, 'marked': count}
                
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def dismiss_notification(self, user_id: int, notification_id: int) -> Dict:
        """
        Dismiss a notification
        
        Args:
            user_id: User ID
            notification_id: Notification ID
        
        Returns:
            Dict with results
        """
        try:
            notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
            if not notification:
                return {'success': False, 'error': 'Notification not found'}
            
            notification.is_dismissed = True
            notification.dismissed_at = datetime.utcnow()
            db.session.commit()
            
            return {'success': True, 'dismissed': 1}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_unread_count(self, user_id: int) -> Dict:
        """
        Get unread notification count
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with count
        """
        count = Notification.query.filter_by(user_id=user_id, is_read=False, is_dismissed=False).count()
        return {'success': True, 'count': count}
    
    def setup_preferences(self, user_id: int, preferences: Dict) -> Dict:
        """
        Set up notification preferences for a user
        
        Args:
            user_id: User ID
            preferences: Dict of preferences
        
        Returns:
            Dict with results
        """
        try:
            for type_name, settings in preferences.items():
                pref = NotificationPreference.query.filter_by(user_id=user_id, type=type_name).first()
                if pref:
                    pref.enabled = settings.get('enabled', True)
                    pref.email_notification = settings.get('email_notification', True)
                    pref.push_notification = settings.get('push_notification', True)
                    pref.in_app_notification = settings.get('in_app_notification', True)
                    pref.updated_at = datetime.utcnow()
                else:
                    pref = NotificationPreference(
                        user_id=user_id,
                        type=type_name,
                        enabled=settings.get('enabled', True),
                        email_notification=settings.get('email_notification', True),
                        push_notification=settings.get('push_notification', True),
                        in_app_notification=settings.get('in_app_notification', True)
                    )
                    db.session.add(pref)
            
            db.session.commit()
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_preferences(self, user_id: int) -> Dict:
        """
        Get notification preferences for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with preferences
        """
        prefs = NotificationPreference.query.filter_by(user_id=user_id).all()
        return {
            'success': True,
            'preferences': [p.to_dict() for p in prefs]
        }
    
    def is_important(self, notification: Dict) -> bool:
        """Check if a notification is important"""
        severity = notification.get('severity', 'medium')
        notif_type = notification.get('type', 'general')
        
        if severity == 'high':
            return True
        
        if severity == 'medium' and notif_type in self.important_types['medium']:
            return True
        
        return False
    
    def generate_financial_alerts(self, user_id: int, data: Dict) -> Dict:
        """
        Generate financial alerts based on user data
        
        Args:
            user_id: User ID
            data: User financial data
        
        Returns:
            Dict with generated alerts
        """
        alerts = []
        
        # Overspend alert
        if data.get('spending_percentage', 0) > 80:
            alerts.append({
                'type': 'overspend',
                'severity': 'high',
                'title': '⚠️ Overspending Alert',
                'message': f"You've used {data['spending_percentage']}% of your monthly budget",
                'action_url': '/expense',
                'action_label': 'View Expenses'
            })
        
        # Goal completion alert
        if data.get('goal_progress', 0) >= 100:
            alerts.append({
                'type': 'goal_completed',
                'severity': 'high',
                'title': '🎉 Goal Completed!',
                'message': f"Congratulations! You completed '{data.get('goal_name', 'your goal')}'",
                'action_url': '/goal-planner',
                'action_label': 'View Goals'
            })
        
        # Anomaly alert
        if data.get('anomaly_detected', False):
            alerts.append({
                'type': 'anomaly',
                'severity': 'high',
                'title': '🚨 Anomaly Detected',
                'message': data.get('anomaly_message', 'Unusual transaction detected'),
                'action_url': '/expense',
                'action_label': 'Review'
            })
        
        # Investment opportunity
        if data.get('investment_opportunity', False):
            alerts.append({
                'type': 'investment_opportunity',
                'severity': 'medium',
                'title': '📈 Investment Opportunity',
                'message': data.get('investment_message', 'New investment opportunity available'),
                'action_url': '/portfolio',
                'action_label': 'Explore'
            })
        
        return {
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': alerts
        }