import re
import threading
from django.shortcuts import render
from django.http import JsonResponse
from .models import Domain, URL
from .utils import fetch_and_store_urls,extract_article_data

# Create your views here.

DOMAIN_REGEX = r"^www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$"

def fetch_urls_view(request):
    """Fetch URLs for all domains asynchronously and update URLSummary"""

    def run_fetch():
        fetch_and_store_urls()

    threading.Thread(target=run_fetch).start()
    
    return JsonResponse({"status": "success", "message": "Fetching URLs for all domains"})


def manage_domains(request):
    """Handles adding new domains and triggering URL fetching"""
    if request.method == "POST":
        domain_name = request.POST.get("domain_name").strip().lower()

        # Validate domain format
        if not re.match(DOMAIN_REGEX, domain_name):
            return JsonResponse({"error": "Invalid domain format! Use format: www.xyz.com"}, status=400)

        # Check if domain already exists
        domain, created = Domain.objects.get_or_create(name=domain_name)
        
        if created:
            return fetch_urls_view(request, domain.id)

    return render(request, "index.html", {"domains": Domain.objects.all()})

#__________________Fetch url meta______________________________#

def fetch_metadata(request):
    """Fetch metadata for URLs that haven't been processed yet."""
    urls = URL.objects.filter(meta_fetched=False)

    if not urls.exists():
        return JsonResponse({"message": "No URLs found for metadata extraction."}, status=200)

    updated_count = 0

    for url_obj in urls:
        metadata = extract_article_data(url_obj.url)

        if metadata:
            url_obj.title = metadata.get("title", "")
            url_obj.author = metadata.get("author", "")
            url_obj.content = metadata.get("content", "")
            url_obj.published_date = metadata.get("published_date", "")
            url_obj.meta_fetched = True  # Mark as processed
            url_obj.save()
            updated_count += 1

    return JsonResponse({"message": f"Metadata fetched for {updated_count} URLs."}, status=200)