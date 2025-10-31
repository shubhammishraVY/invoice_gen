"""
Background Scheduler Service for Invoice Management

This service runs scheduled tasks automatically:
- Updates overdue invoices from 'pending' to 'due' daily at midnight
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz


# Global scheduler instance
scheduler = None


def update_overdue_invoices_job():
    """
    Scheduled job that runs daily to update all overdue invoices.
    Updates 'pending' invoices past their due date to 'due' status.
    """
    try:
        print(f"\n🕐 [{datetime.now()}] Running scheduled task: Update Overdue Invoices")
        
        from repositories.bill_repo import update_all_overdue_invoices
        
        result = update_all_overdue_invoices()
        
        print(f"✅ Scheduled task completed:")
        print(f"   - Companies processed: {result.get('companies_processed', 0)}")
        print(f"   - Invoices updated: {result.get('total_updated', 0)}")
        print(f"   - Invoices skipped: {result.get('total_skipped', 0)}")
        
    except Exception as e:
        print(f"❌ Error in scheduled task 'update_overdue_invoices_job': {e}")


def check_payment_reminders_job():
    """
    Scheduled job that runs daily to check for payment reminders.
    Sends reminder emails for:
    - Invoices 3 days after invoice_date (first reminder)
    - Invoices on due_date (final reminder)
    """
    try:
        print(f"\n🕐 [{datetime.now()}] Running scheduled task: Check Payment Reminders")
        
        from services.invoice_service import check_and_send_payment_reminders
        
        result = check_and_send_payment_reminders()
        
        print(f"✅ Scheduled task completed:")
        print(f"   - First reminders sent: {result.get('first_reminders_sent', 0)}")
        print(f"   - Final reminders sent: {result.get('final_reminders_sent', 0)}")
        
    except Exception as e:
        print(f"❌ Error in scheduled task 'check_payment_reminders_job': {e}")


def start_scheduler(run_on_startup=False):
    """
    Initializes and starts the background scheduler.
    Schedules the overdue invoice update to run daily at midnight (IST).
    
    Args:
        run_on_startup: If True, runs the update job immediately on startup (default: True)
    """
    global scheduler
    
    if scheduler is not None:
        print("⚠️ Scheduler already running")
        return scheduler
    
    try:
        # 🔥 RUN IMMEDIATELY ON STARTUP (for testing/immediate update)
        if run_on_startup:
            print("\n🔥 Running overdue invoice update on startup...")
            update_overdue_invoices_job()
            print("\n🔥 Running payment reminders check on startup...")
            check_payment_reminders_job()
            print("")
        
        # Create scheduler
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        
        # Schedule: Run daily at midnight IST (00:00)
        scheduler.add_job(
            func=update_overdue_invoices_job,
            trigger=CronTrigger(hour=0, minute=0, timezone='Asia/Kolkata'),
            id='update_overdue_invoices',
            name='Update Overdue Invoices to Due Status',
            replace_existing=True,
            misfire_grace_time=3600  # If missed, can run within 1 hour
        )
        
        # Schedule: Check payment reminders at 9:00 AM IST daily
        scheduler.add_job(
            func=check_payment_reminders_job,
            trigger=CronTrigger(hour=9, minute=0, timezone='Asia/Kolkata'),
            id='check_payment_reminders',
            name='Check and Send Payment Reminders',
            replace_existing=True,
            misfire_grace_time=3600  # If missed, can run within 1 hour
        )
        
        # Start the scheduler
        scheduler.start()
        
        print("✅ Background Scheduler Started Successfully")
        print("📅 Scheduled Tasks:")
        print("   - Update Overdue Invoices: Daily at 00:00 IST (midnight)")
        print("   - Check Payment Reminders: Daily at 09:00 IST")
        for job in scheduler.get_jobs():
            print(f"   - {job.name}: Next run at {job.next_run_time}")
        print("\n💡 TIP: To disable startup update, set run_on_startup=False in main.py\n")
        
        return scheduler
        
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")
        raise


def stop_scheduler():
    """
    Gracefully stops the background scheduler.
    Should be called on application shutdown.
    """
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        scheduler = None
        print("✅ Background Scheduler stopped")
    else:
        print("⚠️ Scheduler was not running")


def get_scheduler_status():
    """
    Returns the current status of the scheduler and scheduled jobs.
    Useful for health checks and monitoring.
    """
    global scheduler
    
    if scheduler is None:
        return {
            "status": "stopped",
            "jobs": []
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time),
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "timezone": str(scheduler.timezone),
        "jobs": jobs
    }


# For testing: Run the job immediately
# def run_overdue_update_now():
#     """
#     Manually triggers the overdue invoice update job immediately.
#     Useful for testing or on-demand updates.
#     """
#     print("🔄 Manually triggering overdue invoice update...")
#     update_overdue_invoices_job()


# def run_payment_reminders_now():
#     """
#     Manually triggers the payment reminders check job immediately.
#     Useful for testing or on-demand checks.
#     """
#     print("🔄 Manually triggering payment reminders check...")
#     check_payment_reminders_job()
