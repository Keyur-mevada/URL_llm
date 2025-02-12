#________________APP URL FILE____________________#

from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('',manage_domains,name='manage_domains'),
    path('fetch-urls/', fetch_urls_view, name='fetch_urls'),
    path('fetch-meta/', fetch_metadata, name='fetch_metadata'),
]
