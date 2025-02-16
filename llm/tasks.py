from django_q.tasks import async_task, schedule
from django_q.models import Schedule
from datetime import datetime, timedelta
from django.utils import timezone


# Trigger tasks manually (e.g., from views)
def schedule_url_fetching():
    async_task('llm.utils.fetch_and_store_urls')


def schedule_metadata_fetching():
    async_task('llm.utils.fetch_metadata_for_pending_urls')


# Schedule periodic tasks (e.g., every day)
def setup_scheduled_tasks():

    next_run_url = timezone.make_aware(datetime(2025, 2, 14, 1, 0, 0))
    next_run_meta = timezone.make_aware(datetime(2025, 2, 14, 4, 0, 0))
    
    # URL Fetching Task - Daily at 9 AM
    Schedule.objects.update_or_create(
        name='fetch_urls_daily',
        func='llm.utils.fetch_and_store_urls',
        defaults={
            'schedule_type': Schedule.DAILY,
            'next_run': next_run_url,
            'repeats': -1,  # Infinite
        }
    )

    # Metadata Fetching Task - Every 6 Hours
    Schedule.objects.update_or_create(
        name='fetch_metadata_daily',
        func='llm.utils.fetch_metadata_for_pending_urls',
        defaults={
            'schedule_type': Schedule.DAILY,
            'minutes': 0,  # Start at the top of the hour
            'next_run': next_run_meta,  # Adjust as needed
            'repeats': -1,
        }
    )