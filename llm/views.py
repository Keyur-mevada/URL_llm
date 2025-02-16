from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django_q.tasks import async_task
from django.shortcuts import render,HttpResponse,get_object_or_404
from .tasks import schedule_url_fetching,schedule_metadata_fetching
from .models import Domain
from django.db.models import Count,Q, F
import re
from django.contrib import messages
from django.template.loader import render_to_string


def trigger_url_fetching(request):
    """Trigger background task to fetch URLs from sitemaps."""
    schedule_url_fetching()
    return JsonResponse({"message": "URL fetching task has been scheduled."})


def trigger_metadata_fetching(request):
    """Trigger background task to fetch metadata for pending URLs."""
    schedule_metadata_fetching()
    return JsonResponse({"message": "Metadata fetching task has been scheduled."})

def manage_domains(request):

    domain_summary = get_domain_summary()

    return render(request, 'index.html', {'domain_summary': domain_summary})






#________________HTMX views________________________#

def is_valid_domain(domain):
    pattern = r'^(www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, domain) is not None

def add_domain(request):
    if request.method == 'POST':
        domain_name = request.POST.get('domainName').strip().lower()
        domain_summary = get_domain_summary()

        if not is_valid_domain(domain_name):
            return JsonResponse({'status': 'error', 'message': 'Invalid domain format. Use www.example.com'})

        if Domain.objects.filter(name=domain_name).exists():
            return JsonResponse({'status': 'error', 'message': 'Domain already exists!'})

        # Create domain
        Domain.objects.create(name=domain_name)
        updated_table = render_to_string('partials/domain_table.html', {'domain_summary': domain_summary}, request=request)

        return JsonResponse({'status': 'success', 'message': 'Domain added successfully!', 'table_html': updated_table})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def delete_domain(request, domain_id):
    if request.method == 'POST':
        domain = get_object_or_404(Domain, id=domain_id)
        domain.delete()

        # Updated summary after deletion
        domain_summary = get_domain_summary()
        table_html = render_to_string('partials/domain_table.html', {'domain_summary': domain_summary})

        return JsonResponse({'status': 'success', 'message': 'Domain deleted successfully!', 'table_html': table_html})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


#_______________HELPER FUNCTION____________________#

def get_domain_summary():
    domains = Domain.objects.annotate(
        url_count=Count('url'),
        meta_fetched_count=Count('url', filter=Q(url__meta_fetched=True)),
        known_author_count=Count(
            'url',
            filter=Q(url__meta_fetched=True) & ~Q(url__author__iexact='unknown') & Q(url__author__isnull=False)
        )
    ).annotate(
        meta_fetched_percentage=F('meta_fetched_count') * 100.0 / F('url_count'),
        known_author_percentage=F('known_author_count') * 100.0 / F('url_count')
    )

    # Handle divide-by-zero cases (e.g., domains with no URLs)
    for domain in domains:
        print(domain.name)
        print(domain.url_count)
        print(domain.meta_fetched_count)
        print(domain.known_author_count)
        if domain.url_count == 0:
            domain.meta_fetched_percentage = 0.0
            domain.known_author_percentage = 0.0

    return domains