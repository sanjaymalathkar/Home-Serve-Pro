"""
Background task to monitor signature timeouts and escalate expired requests.
"""

from datetime import datetime, timedelta
from app.models.booking import Booking
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.user import User
from app import socketio
import logging

logger = logging.getLogger(__name__)


def check_signature_timeouts():
    """
    Check for expired signature requests and escalate them.
    This should be run periodically (e.g., every hour) as a background task.
    """
    try:
        # Get all bookings with expired signature requests
        expired_bookings = Booking.get_expired_signatures()
        
        escalated_count = 0
        
        for booking in expired_bookings:
            booking_id = str(booking['_id'])
            
            # Escalate the booking
            escalated = Booking.escalate_signature_timeout(booking_id)
            
            if escalated:
                escalated_count += 1
                
                # Get customer and vendor info
                customer = User.find_by_id(booking['customer_id'])
                vendor = User.find_by_id(booking['vendor_id'])
                
                # Create escalation notification for admin
                admin_users = User.find_all({'role': 'super_admin'})
                for admin in admin_users:
                    Notification.create({
                        'user_id': str(admin['_id']),
                        'type': Notification.TYPE_ESCALATION,
                        'title': 'Signature Request Expired',
                        'message': f'Customer signature request expired for booking {booking_id}. Manual intervention required.',
                        'data': {
                            'booking_id': booking_id,
                            'customer_name': customer.get('name', 'Unknown') if customer else 'Unknown',
                            'vendor_name': vendor.get('name', 'Unknown') if vendor else 'Unknown',
                            'service_name': booking.get('service_name', 'Service'),
                            'expired_at': booking.get('signature_timeout_at'),
                            'escalation_reason': 'signature_timeout'
                        }
                    })
                
                # Send real-time notification to admins
                socketio.emit('signature_escalation', {
                    'booking_id': booking_id,
                    'customer_name': customer.get('name', 'Unknown') if customer else 'Unknown',
                    'vendor_name': vendor.get('name', 'Unknown') if vendor else 'Unknown',
                    'service_name': booking.get('service_name', 'Service'),
                    'reason': 'signature_timeout'
                }, room='admin')
                
                # Notify customer about escalation
                if customer:
                    Notification.create({
                        'user_id': str(customer['_id']),
                        'type': Notification.TYPE_ESCALATION,
                        'title': 'Signature Request Expired',
                        'message': 'Your signature request has expired. Our support team will contact you shortly.',
                        'data': {
                            'booking_id': booking_id,
                            'escalation_reason': 'signature_timeout',
                            'support_contact': 'support@homeservepro.com'
                        }
                    })
                
                # Notify vendor about escalation
                if vendor:
                    Notification.create({
                        'user_id': str(vendor['_id']),
                        'type': Notification.TYPE_ESCALATION,
                        'title': 'Customer Signature Expired',
                        'message': f'Customer signature request expired for booking {booking_id}. Payment is on hold pending resolution.',
                        'data': {
                            'booking_id': booking_id,
                            'escalation_reason': 'signature_timeout',
                            'customer_name': customer.get('name', 'Unknown') if customer else 'Unknown'
                        }
                    })
                
                # Log the escalation
                AuditLog.log(
                    action=AuditLog.ACTION_ESCALATION,
                    entity_type='booking',
                    entity_id=booking_id,
                    user_id='system',
                    details={
                        'escalation_reason': 'signature_timeout',
                        'original_timeout': booking.get('signature_timeout_at'),
                        'customer_id': str(booking['customer_id']),
                        'vendor_id': str(booking['vendor_id'])
                    },
                    ip_address='system'
                )
                
                logger.info(f"Escalated signature timeout for booking {booking_id}")
        
        if escalated_count > 0:
            logger.info(f"Escalated {escalated_count} signature timeouts")
        
        return escalated_count
        
    except Exception as e:
        logger.error(f"Error checking signature timeouts: {str(e)}")
        return 0


def send_signature_reminders():
    """
    Send reminder notifications for pending signatures that are approaching timeout.
    This should be run periodically (e.g., every 6 hours).
    """
    try:
        # Get bookings with signature requests expiring in the next 12 hours
        reminder_threshold = datetime.utcnow() + timedelta(hours=12)
        
        pending_bookings = list(Booking.find_all({
            'signature_status': 'requested',
            'signature_timeout_at': {
                '$lt': reminder_threshold,
                '$gt': datetime.utcnow()
            },
            'signature_escalated': False
        }))
        
        reminder_count = 0
        
        for booking in pending_bookings:
            booking_id = str(booking['_id'])
            
            # Check if we've already sent a reminder (to avoid spam)
            recent_reminders = Notification.find_all({
                'user_id': str(booking['customer_id']),
                'type': Notification.TYPE_SIGNATURE_REMINDER,
                'data.booking_id': booking_id,
                'created_at': {'$gt': datetime.utcnow() - timedelta(hours=6)}
            })
            
            if len(list(recent_reminders)) > 0:
                continue  # Skip if we've sent a reminder in the last 6 hours
            
            # Get customer info
            customer = User.find_by_id(booking['customer_id'])
            if not customer:
                continue
            
            # Calculate hours remaining
            timeout_at = booking.get('signature_timeout_at')
            if isinstance(timeout_at, str):
                timeout_at = datetime.fromisoformat(timeout_at.replace('Z', '+00:00'))
            
            hours_remaining = max(0, (timeout_at - datetime.utcnow()).total_seconds() / 3600)
            
            # Send reminder notification
            Notification.create({
                'user_id': str(customer['_id']),
                'type': Notification.TYPE_SIGNATURE_REMINDER,
                'title': 'Signature Required - Reminder',
                'message': f'Please sign off on your completed service. Request expires in {int(hours_remaining)} hours.',
                'data': {
                    'booking_id': booking_id,
                    'service_name': booking.get('service_name', 'Service'),
                    'hours_remaining': int(hours_remaining),
                    'reminder_type': 'signature_timeout_approaching'
                }
            })
            
            # Send real-time reminder
            socketio.emit('signature_reminder', {
                'booking_id': booking_id,
                'service_name': booking.get('service_name', 'Service'),
                'hours_remaining': int(hours_remaining)
            }, room=str(customer['_id']))
            
            reminder_count += 1
            logger.info(f"Sent signature reminder for booking {booking_id}")
        
        if reminder_count > 0:
            logger.info(f"Sent {reminder_count} signature reminders")
        
        return reminder_count
        
    except Exception as e:
        logger.error(f"Error sending signature reminders: {str(e)}")
        return 0


def get_signature_statistics():
    """
    Get statistics about signature requests for monitoring and reporting.
    """
    try:
        current_time = datetime.utcnow()
        
        # Count signatures by status
        total_pending = Booking.count({
            'signature_status': 'requested',
            'signature_escalated': False
        })
        
        total_expired = Booking.count({
            'signature_status': 'expired',
            'signature_escalated': True
        })
        
        total_signed = Booking.count({
            'signature_status': 'signed'
        })
        
        # Count signatures expiring soon (next 24 hours)
        expiring_soon = Booking.count({
            'signature_status': 'requested',
            'signature_timeout_at': {
                '$lt': current_time + timedelta(hours=24),
                '$gt': current_time
            },
            'signature_escalated': False
        })
        
        return {
            'total_pending': total_pending,
            'total_expired': total_expired,
            'total_signed': total_signed,
            'expiring_soon': expiring_soon,
            'timestamp': current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting signature statistics: {str(e)}")
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


# CLI command to run signature monitoring tasks
def run_signature_monitor():
    """
    Run all signature monitoring tasks.
    This can be called from a CLI command or scheduled job.
    """
    logger.info("Starting signature monitoring tasks...")
    
    # Check for timeouts and escalate
    escalated = check_signature_timeouts()
    
    # Send reminders for approaching timeouts
    reminders = send_signature_reminders()
    
    # Get current statistics
    stats = get_signature_statistics()
    
    logger.info(f"Signature monitoring completed: {escalated} escalated, {reminders} reminders sent")
    logger.info(f"Current stats: {stats}")
    
    return {
        'escalated': escalated,
        'reminders_sent': reminders,
        'statistics': stats
    }
