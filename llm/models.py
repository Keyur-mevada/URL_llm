from django.db import models
from django.utils import timezone
# Create your models here.

class JobRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")],
        default="running"
    )
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.status} | Started: {self.started_at} | Finished: {self.finished_at}"

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class SitemapScan(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    sitemap_url = models.URLField(unique=True)
    last_scanned_at = models.DateTimeField(auto_now=True)
    last_modified_header = models.DateTimeField(null=True, blank=True)  # From HTTP header
    lastmod_from_sitemap = models.DateTimeField(null=True, blank=True)  # From sitemap content

    def __str__(self):
        return f"{self.domain.name} - {self.sitemap_url}"


class URL(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE,related_name='url')
    url = models.URLField(unique=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    published_date = models.DateField(null=True, blank=True)
    meta_fetched = models.BooleanField(default=False)

    def __str__(self):
        return self.url
    
class URLSummary(models.Model):
    date = models.DateField(auto_now_add=True)  # Stores only the date
    unique_urls_added = models.IntegerField(default=0)  # Count of new URLs added

    def __str__(self):
        return f"{self.date} - {self.unique_urls_added} new URLs"