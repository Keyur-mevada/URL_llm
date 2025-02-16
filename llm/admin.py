from django.contrib import admin
from .models import Domain, URL, JobRun,SitemapScan

# Register your models here.

admin.site.register(JobRun)
admin.site.register(Domain)
admin.site.register(SitemapScan)
admin.site.register(URL)

