from django.core.management.base import BaseCommand
from llm.utils import fetch_metadata_for_pending_urls

class Command(BaseCommand):
    help = 'Fetch metadata for pending URLs'

    def handle(self, *args, **kwargs):
        fetch_metadata_for_pending_urls()
        self.stdout.write(self.style.SUCCESS('Metadata fetched successfully'))