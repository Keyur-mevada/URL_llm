from django.core.management.base import BaseCommand
from llm.utils import fetch_and_store_urls

class Command(BaseCommand):
    help = 'Fetch URLs from all domains and store them in the database'
    
    def handle(self, *args, **kwargs):
        fetch_and_store_urls()
        self.stdout.write(self.style.SUCCESS('URLs fetched successfully'))
