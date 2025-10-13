"""
Notification Service for HomeServe Pro.
Handles WhatsApp, SMS, and email notifications for vendors.
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from app.models.notification import Notification
from app.models.vendor import Vendor
from app.models.user import User


class NotificationService:
    """Service for sending notifications via multiple channels."""
    
    # Notification channels
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_PUSH = 'push'
    
    # WhatsApp Business API Configuration (Mock)
    WHATSAPP_API_URL = "https://graph.facebook.com/v17.0/YOUR_PHONE_NUMBER_ID/messages"
    WHATSAPP_ACCESS_TOKEN = "YOUR_WHATSAPP_ACCESS_TOKEN"
    
    # SMS API Configuration (Mock)
    SMS_API_URL = "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json"
    SMS_AUTH_TOKEN = "YOUR_SMS_AUTH_TOKEN"
    
    @staticmethod
    def send_booking_notification(vendor_id: str, booking_data: Dict) -> Dict:
        """
        Send booking notification to vendor via preferred channels.
        
        Args:
            vendor_id (str): Vendor ID
            booking_data (Dict): Booking information
            
        Returns:
            Dict: Notification delivery results
        """
        try:
            vendor = Vendor.find_by_id(vendor_id)
            if not vendor:
                return {'success': False, 'error': 'Vendor not found'}
            
            user = User.find_by_id(str(vendor['user_id']))
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            preferences = vendor.get('notification_preferences', {})
            phone = user.get('phone', '')
            email = user.get('email', '')
            
            # Prepare notification content
            message = f"""
🔔 New Booking Alert!

Customer: {booking_data.get('customer_name', 'N/A')}
Service: {booking_data.get('service_name', 'N/A')}
Date: {booking_data.get('service_date', 'N/A')}
Time: {booking_data.get('service_time', 'N/A')}
Location: {booking_data.get('address', 'N/A')}

Please accept or reject this booking in your dashboard.
            """.strip()
            
            results = {}
            
            # Send WhatsApp notification
            if preferences.get('whatsapp_notifications', False) and phone:
                whatsapp_result = NotificationService._send_whatsapp(phone, message)
                results['whatsapp'] = whatsapp_result
            
            # Send SMS notification
            if preferences.get('sms_notifications', True) and phone:
                sms_result = NotificationService._send_sms(phone, message)
                results['sms'] = sms_result
            
            # Send email notification
            if preferences.get('email_notifications', True) and email:
                email_result = NotificationService._send_email(
                    email, 
                    "New Booking Alert - HomeServe Pro", 
                    message
                )
                results['email'] = email_result
            
            # Create in-app notification
            notification_id = Notification.create({
                'user_id': str(vendor['user_id']),
                'type': Notification.TYPE_BOOKING_CREATED,
                'title': 'New Booking Request',
                'message': f"New booking for {booking_data.get('service_name')}",
                'data': booking_data
            })
            results['in_app'] = {'success': True, 'notification_id': notification_id}
            
            return {
                'success': True,
                'results': results,
                'channels_used': len([r for r in results.values() if r.get('success')])
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_payment_notification(vendor_id: str, payment_data: Dict) -> Dict:
        """Send payment notification to vendor."""
        try:
            vendor = Vendor.find_by_id(vendor_id)
            if not vendor:
                return {'success': False, 'error': 'Vendor not found'}
            
            user = User.find_by_id(str(vendor['user_id']))
            preferences = vendor.get('notification_preferences', {})
            
            message = f"""
💰 Payment Received!

Amount: ₹{payment_data.get('amount', 0)}
Booking ID: {payment_data.get('booking_id', 'N/A')}
Payment Method: {payment_data.get('method', 'N/A')}
Status: {payment_data.get('status', 'N/A')}

Your earnings have been updated.
            """.strip()
            
            results = {}
            
            if preferences.get('payment_alerts', True):
                # Send notifications via preferred channels
                if preferences.get('whatsapp_notifications', False):
                    results['whatsapp'] = NotificationService._send_whatsapp(
                        user.get('phone', ''), message
                    )
                
                if preferences.get('sms_notifications', True):
                    results['sms'] = NotificationService._send_sms(
                        user.get('phone', ''), message
                    )
            
            # Always create in-app notification for payments
            notification_id = Notification.create({
                'user_id': str(vendor['user_id']),
                'type': Notification.TYPE_PAYMENT_RECEIVED,
                'title': 'Payment Received',
                'message': f"Payment of ₹{payment_data.get('amount', 0)} received",
                'data': payment_data
            })
            results['in_app'] = {'success': True, 'notification_id': notification_id}
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_whatsapp(phone: str, message: str) -> Dict:
        """
        Send WhatsApp message (Mock implementation).
        In production, integrate with WhatsApp Business API.
        """
        try:
            # Mock WhatsApp API call
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            headers = {
                "Authorization": f"Bearer {NotificationService.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # In production, uncomment this:
            # response = requests.post(
            #     NotificationService.WHATSAPP_API_URL,
            #     headers=headers,
            #     json=payload
            # )
            
            # Mock successful response
            return {
                'success': True,
                'channel': 'whatsapp',
                'phone': phone,
                'message_id': f'whatsapp_mock_{datetime.now().timestamp()}',
                'status': 'sent'
            }
            
        except Exception as e:
            return {
                'success': False,
                'channel': 'whatsapp',
                'error': str(e)
            }
    
    @staticmethod
    def _send_sms(phone: str, message: str) -> Dict:
        """
        Send SMS message (Mock implementation).
        In production, integrate with Twilio or similar SMS service.
        """
        try:
            # Mock SMS API call
            payload = {
                "To": phone,
                "From": "+1234567890",  # Your Twilio phone number
                "Body": message
            }
            
            # In production, uncomment this:
            # response = requests.post(
            #     NotificationService.SMS_API_URL,
            #     auth=('YOUR_ACCOUNT_SID', NotificationService.SMS_AUTH_TOKEN),
            #     data=payload
            # )
            
            # Mock successful response
            return {
                'success': True,
                'channel': 'sms',
                'phone': phone,
                'message_id': f'sms_mock_{datetime.now().timestamp()}',
                'status': 'sent'
            }
            
        except Exception as e:
            return {
                'success': False,
                'channel': 'sms',
                'error': str(e)
            }
    
    @staticmethod
    def _send_email(email: str, subject: str, message: str) -> Dict:
        """
        Send email notification (Mock implementation).
        In production, integrate with SendGrid, AWS SES, or similar.
        """
        try:
            # Mock email sending
            return {
                'success': True,
                'channel': 'email',
                'email': email,
                'subject': subject,
                'message_id': f'email_mock_{datetime.now().timestamp()}',
                'status': 'sent'
            }
            
        except Exception as e:
            return {
                'success': False,
                'channel': 'email',
                'error': str(e)
            }
    
    @staticmethod
    def send_bulk_notification(vendor_ids: List[str], message: str, channels: List[str] = None) -> Dict:
        """
        Send bulk notifications to multiple vendors.
        
        Args:
            vendor_ids (List[str]): List of vendor IDs
            message (str): Notification message
            channels (List[str]): Preferred channels (optional)
            
        Returns:
            Dict: Bulk notification results
        """
        if channels is None:
            channels = [NotificationService.CHANNEL_PUSH]  # Default to in-app only
        
        results = {
            'total_vendors': len(vendor_ids),
            'successful_notifications': 0,
            'failed_notifications': 0,
            'details': []
        }
        
        for vendor_id in vendor_ids:
            try:
                vendor = Vendor.find_by_id(vendor_id)
                if not vendor:
                    results['details'].append({
                        'vendor_id': vendor_id,
                        'success': False,
                        'error': 'Vendor not found'
                    })
                    results['failed_notifications'] += 1
                    continue
                
                user = User.find_by_id(str(vendor['user_id']))
                if not user:
                    results['details'].append({
                        'vendor_id': vendor_id,
                        'success': False,
                        'error': 'User not found'
                    })
                    results['failed_notifications'] += 1
                    continue
                
                # Send in-app notification
                notification_id = Notification.create({
                    'user_id': str(vendor['user_id']),
                    'type': Notification.TYPE_SYSTEM_ANNOUNCEMENT,
                    'title': 'System Notification',
                    'message': message,
                    'data': {'bulk_notification': True}
                })
                
                vendor_result = {
                    'vendor_id': vendor_id,
                    'success': True,
                    'notification_id': notification_id,
                    'channels': ['in_app']
                }
                
                # Send via additional channels if requested
                preferences = vendor.get('notification_preferences', {})
                
                if NotificationService.CHANNEL_SMS in channels and preferences.get('sms_notifications', True):
                    sms_result = NotificationService._send_sms(user.get('phone', ''), message)
                    if sms_result['success']:
                        vendor_result['channels'].append('sms')
                
                if NotificationService.CHANNEL_WHATSAPP in channels and preferences.get('whatsapp_notifications', False):
                    whatsapp_result = NotificationService._send_whatsapp(user.get('phone', ''), message)
                    if whatsapp_result['success']:
                        vendor_result['channels'].append('whatsapp')
                
                results['details'].append(vendor_result)
                results['successful_notifications'] += 1
                
            except Exception as e:
                results['details'].append({
                    'vendor_id': vendor_id,
                    'success': False,
                    'error': str(e)
                })
                results['failed_notifications'] += 1
        
        return results
