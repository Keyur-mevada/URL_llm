#________________APP URL FILE____________________#

from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('',manage_domains,name='manage_domains'),
    path('fetch-urls/', trigger_url_fetching, name='fetch_urls'),
    path('fetch-meta/', trigger_metadata_fetching, name='fetch_metadata'),
    path('add-domain/', add_domain, name='add-domain'),
    path('delete-domain/<int:domain_id>/', delete_domain, name='delete-domain'),
]
