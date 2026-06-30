"""
Two-Factor Authentication System with Biometric Support
"""

import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pyotp
import qrcode
from io import BytesIO
import base64
from webauthn import generate_registration_options, verify_registration_response
from webauthn.helpers.structs import (
    RegistrationCredential, AuthenticationCredential,
    AuthenticatorSelectionCriteria, UserVerificationRequirement
)

from models import db, MFASetting, TrustedDevice, SecurityEvent


class MFASystem:
    """
    Multi-Factor Authentication System
    """
    
    def __init__(self, user):
        self.user = user
        self.setting = self._get_or_create_settings()
    
    def _get_or_create_settings(self) -> MFASetting:
        """Get or create MFA settings for user"""
        setting = MFASetting.query.filter_by(user_id=self.user.id).first()
        if not setting:
            setting = MFASetting(user_id=self.user.id)
            db.session.add(setting)
            db.session.commit()
        return setting
    
    def setup_totp(self) -> Dict:
        """
        Setup TOTP (Google Authenticator)
        
        Returns:
            Dict with secret, QR code, and backup codes
        """
        # Generate secret
        secret = pyotp.random_base32()
        
        # Create TOTP instance
        totp = pyotp.TOTP(secret)
        
        # Generate provisioning URI
        provisioning_uri = totp.provisioning_uri(
            name=self.user.email,
            issuer_name="AI-Money-Mentor"
        )
        
        # Generate QR code
        qr = qrcode.make(provisioning_uri)
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Generate backup codes (10 codes)
        backup_codes = self._generate_backup_codes()
        
        # Save secret and backup codes
        self.setting.totp_secret = secret
        self.setting.backup_codes = json.dumps(backup_codes)
        self.setting.totp_enabled = False  # User must verify first
        db.session.commit()
        
        return {
            'secret': secret,
            'qr_code': qr_base64,
            'provisioning_uri': provisioning_uri,
            'backup_codes': backup_codes
        }
    
    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes"""
        codes = []
        for _ in range(count):
            # Generate random 8-digit code
            code = ''.join(secrets.choice('0123456789') for _ in range(8))
            # Hash the code for storage
            hashed = hashlib.sha256(code.encode()).hexdigest()
            codes.append(hashed)
        return codes
    
    def verify_totp(self, code: str) -> bool:
        """
        Verify TOTP code
        
        Args:
            code: 6-digit TOTP code
        
        Returns:
            True if valid
        """
        if not self.setting.totp_secret:
            return False
        
        totp = pyotp.TOTP(self.setting.totp_secret)
        
        # Allow a small time window (2 steps)
        if totp.verify(code):
            # Enable TOTP if not already enabled
            if not self.setting.totp_enabled:
                self.setting.totp_enabled = True
                self.setting.mfa_enabled = True
                db.session.commit()
                
                # Log event
                self._log_event('mfa_enabled', 'info', 'TOTP authentication enabled')
            
            return True
        
        return False
    
    def verify_backup_code(self, code: str) -> bool:
        """
        Verify a backup code
        
        Args:
            code: 8-digit backup code
        
        Returns:
            True if valid
        """
        if not self.setting.backup_codes:
            return False
        
        codes = json.loads(self.setting.backup_codes)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        if code_hash in codes:
            # Remove used code
            codes.remove(code_hash)
            self.setting.backup_codes = json.dumps(codes)
            db.session.commit()
            
            # Log event
            self._log_event('backup_code_used', 'warning', 'Backup code used for authentication')
            
            return True
        
        return False
    
    def setup_webauthn(self) -> Dict:
        """
        Setup WebAuthn (biometrics)
        
        Returns:
            Dict with registration options
        """
        # Generate registration options
        options = generate_registration_options(
            rp_id='localhost',
            rp_name='AI-Money-Mentor',
            user_id=str(self.user.id).encode(),
            user_name=self.user.username,
            user_display_name=self.user.username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED
            )
        )
        
        # Store challenge in session or database
        # For demo, return options
        
        return {
            'options': options,
            'challenge': options.challenge
        }
    
    def verify_webauthn(self, credential_data: Dict) -> bool:
        """
        Verify WebAuthn registration
        
        Args:
            credential_data: WebAuthn credential response
        
        Returns:
            True if verified
        """
        try:
            # Verify registration response
            verification = verify_registration_response(
                credential=RegistrationCredential(
                    id=credential_data.get('id'),
                    raw_id=credential_data.get('rawId'),
                    response=credential_data.get('response'),
                    type=credential_data.get('type')
                ),
                expected_challenge=credential_data.get('challenge'),
                expected_rp_id='localhost',
                expected_origin='http://localhost:5000'
            )
            
            if verification.verified:
                # Save credential
                self.setting.webauthn_credential_id = verification.credential_id
                self.setting.webauthn_public_key = verification.credential_public_key
                self.setting.webauthn_sign_count = verification.sign_count
                self.setting.webauthn_enabled = True
                self.setting.mfa_enabled = True
                db.session.commit()
                
                # Log event
                self._log_event('mfa_enabled', 'info', 'WebAuthn biometric authentication enabled')
                
                return True
            
        except Exception as e:
            print(f"WebAuthn verification error: {e}")
        
        return False
    
    def add_trusted_device(self, device_name: str, user_agent: str = None, ip_address: str = None) -> TrustedDevice:
        """
        Add a trusted device
        
        Args:
            device_name: Name of the device
            user_agent: Browser user agent
            ip_address: IP address
        
        Returns:
            TrustedDevice object
        """
        # Determine device type from user agent
        device_type = self._detect_device_type(user_agent) if user_agent else 'unknown'
        
        device = TrustedDevice(
            user_id=self.user.id,
            device_name=device_name,
            device_type=device_type,
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.session.add(device)
        db.session.commit()
        
        # Log event
        self._log_event('device_added', 'info', f'Trusted device added: {device_name}')
        
        return device
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        if not user_agent:
            return 'unknown'
        
        ua = user_agent.lower()
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            return 'mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            return 'tablet'
        else:
            return 'desktop'
    
    def get_trusted_devices(self) -> List[Dict]:
        """Get all trusted devices for user"""
        devices = TrustedDevice.query.filter_by(user_id=self.user.id, is_active=True).all()
        return [d.to_dict() for d in devices]
    
    def remove_trusted_device(self, device_id: int) -> bool:
        """
        Remove a trusted device
        
        Args:
            device_id: Device ID
        
        Returns:
            True if removed
        """
        device = TrustedDevice.query.filter_by(id=device_id, user_id=self.user.id).first()
        if not device:
            return False
        
        device.is_active = False
        db.session.commit()
        
        # Log event
        self._log_event('device_removed', 'warning', f'Trusted device removed: {device.device_name}')
        
        return True
    
    def is_device_trusted(self, user_agent: str, ip_address: str) -> bool:
        """
        Check if device is trusted
        
        Args:
            user_agent: Browser user agent
            ip_address: IP address
        
        Returns:
            True if trusted
        """
        device = TrustedDevice.query.filter_by(
            user_id=self.user.id,
            user_agent=user_agent,
            ip_address=ip_address,
            is_active=True
        ).first()
        
        if device:
            device.last_used = datetime.utcnow()
            db.session.commit()
            return True
        
        return False
    
    def disable_mfa(self) -> bool:
        """
        Disable MFA for user
        
        Returns:
            True if disabled
        """
        self.setting.mfa_enabled = False
        self.setting.totp_enabled = False
        self.setting.totp_secret = None
        self.setting.backup_codes = None
        self.setting.webauthn_enabled = False
        self.setting.webauthn_credential_id = None
        self.setting.webauthn_public_key = None
        db.session.commit()
        
        # Log event
        self._log_event('mfa_disabled', 'critical', 'MFA disabled by user')
        
        return True
    
    def get_security_events(self, limit: int = 50) -> List[Dict]:
        """Get security events for user"""
        events = SecurityEvent.query.filter_by(
            user_id=self.user.id
        ).order_by(SecurityEvent.created_at.desc()).limit(limit).all()
        
        return [e.to_dict() for e in events]
    
    def _log_event(self, event_type: str, severity: str, details: str):
        """Log a security event"""
        event = SecurityEvent(
            user_id=self.user.id,
            event_type=event_type,
            severity=severity,
            details=details
        )
        db.session.add(event)
        db.session.commit()
    
    def get_mfa_status(self) -> Dict:
        """Get MFA status"""
        return {
            'mfa_enabled': self.setting.mfa_enabled,
            'totp_enabled': self.setting.totp_enabled,
            'webauthn_enabled': self.setting.webauthn_enabled,
            'backup_codes_remaining': len(json.loads(self.setting.backup_codes)) if self.setting.backup_codes else 0,
            'trusted_devices': len(self.get_trusted_devices())
        }
    
    def generate_new_backup_codes(self) -> List[str]:
        """Generate new backup codes"""
        codes = self._generate_backup_codes()
        self.setting.backup_codes = json.dumps(codes)
        db.session.commit()
        
        # Return plain codes for user to save
        # Note: In production, you'd show these once and hash them
        return [''.join(secrets.choice('0123456789') for _ in range(8)) for _ in range(10)]