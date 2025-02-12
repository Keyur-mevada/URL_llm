from django.db import models

# Create your models here.

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url_in_domain = models.IntegerField(default=0) 

    def __str__(self):
        return self.name

class URL(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    url = models.URLField(unique=True)
    captured_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    published_date = models.CharField(max_length=100, blank=True, null=True)
    meta_fetched = models.BooleanField(default=False)

    def __str__(self):
        return self.url
    
class URLSummary(models.Model):
    date = models.DateField(auto_now_add=True)  # Stores only the date
    unique_urls_added = models.IntegerField(default=0)  # Count of new URLs added

    def __str__(self):
        return f"{self.date} - {self.unique_urls_added} new URLs"