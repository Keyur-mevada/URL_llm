from django.contrib import admin
from .models import Domain, URL, URLSummary

# Register your models here.

admin.site.register(Domain)
admin.site.register(URL)
admin.site.register(URLSummary)