import requests
from xml.etree import ElementTree
from datetime import datetime, timedelta
from bs4 import BeautifulSoup  # Added for metadata extraction
from .models import Domain, URL, URLSummary
from newspaper import Article
from django.utils import timezone

# List of unwanted file extensions
UNWANTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".mp4", ".mp3", ".webp"}

# Date threshold (1 year ago from today)
DATE_THRESHOLD = datetime.now() - timedelta(days=0.5 * 365)


# _____________________ Extract Metadata from URL _______________________#
def extract_article_data(url):
    """Extract title, author, content, and publication date from a webpage."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Try fetching article with Newspaper3k library
        article = Article(url)
        article.download(headers=headers)  # Add headers to the download
        article.parse()

        # Extract metadata
        title = article.title if article.title else "Unknown Title"
        author = article.authors[0] if article.authors else "Unknown"
        content = article.text
        publish_date = article.publish_date

        # If `content` is empty, fallback to BeautifulSoup
        if not content:
            response = requests.get(url, timeout=10, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            content = " ".join([p.text for p in soup.find_all("p")])

        # Convert date to string format
        publish_date = publish_date.strftime("%Y-%m-%d") if publish_date else "Unknown"

        return {
            "url": url,
            "title": title,
            "author": author,
            "content": content[:5000],  # Limit content size to prevent database overflow
            "published_date": publish_date
        }

    except requests.exceptions.RequestException as req_err:
        print(f"Request error for {url}: {req_err}")
    except Exception as e:
        print(f"Error processing {url}: {e}")

    return None  # Return None if extraction fails

# _____________________ Fetch Sitemaps from robots.txt _______________________#
def fetch_robots_txt(domain):
    """Fetch sitemap URLs from robots.txt."""
    robots_url = f"https://{domain}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=10)
        response.raise_for_status()
        return [line.split(": ")[1].strip() for line in response.text.split("\n") if line.lower().startswith("sitemap:")]
    except requests.RequestException:
        return []

# _____________________ Fetch URLs from Sitemaps (Handles Nested) _______________________#
def fetch_urls_from_sitemap(sitemap_url, visited_sitemaps=None):
    """Extracts URLs from a sitemap, handling nested sitemaps properly."""
    if visited_sitemaps is None:
        visited_sitemaps = set()

    if sitemap_url in visited_sitemaps:
        return set()  # Avoid infinite loops

    visited_sitemaps.add(sitemap_url)

    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)

        urls = set()
        nested_sitemaps = set()

        # Detect if this is a sitemap index
        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall(".//{*}sitemap"):
                loc_tag = sitemap.find("{*}loc")
                if loc_tag is not None:
                    nested_sitemaps.add(loc_tag.text.strip())

        else:  # Process normal sitemaps with <url> entries
            for url_entry in root.findall(".//{*}url"):
                loc_tag = url_entry.find("{*}loc")
                lastmod_tag = url_entry.find("{*}lastmod")

                if loc_tag is not None:
                    url = loc_tag.text.strip()

                    # Skip unwanted file types
                    if any(url.lower().endswith(ext) for ext in UNWANTED_EXTENSIONS):
                        continue

                    # Check if the URL is too old
                    if lastmod_tag is not None:
                        try:
                            lastmod_date = datetime.strptime(lastmod_tag.text.strip(), "%Y-%m-%dT%H:%M:%SZ")
                            if lastmod_date < DATE_THRESHOLD:
                                continue
                        except ValueError:
                            pass  # Ignore invalid dates

                    urls.add(url)

        # Recursively process nested sitemaps
        for nested_sitemap in nested_sitemaps:
            urls.update(fetch_urls_from_sitemap(nested_sitemap, visited_sitemaps))

        return urls

    except requests.RequestException:
        return set()

# _____________________ Fetch and Store URLs from Sitemaps _______________________#
def fetch_and_store_urls():
    """Fetches and stores unique URLs from all domain sitemaps."""
    domains = Domain.objects.all()
    total_new_urls = 0

    for domain in domains:
        sitemap_urls = fetch_robots_txt(domain.name)
        domain_new_urls = 0
        visited_sitemaps = set()

        for sitemap_url in sitemap_urls:
            urls = fetch_urls_from_sitemap(sitemap_url, visited_sitemaps)

            for url in urls:
                if not URL.objects.filter(url=url).exists():  # Save only new URLs
                    URL.objects.create(domain=domain, url=url)
                    domain_new_urls += 1
                    total_new_urls += 1

        # Update domain with new URL count
        if domain_new_urls > 0:
            domain.url_in_domain += domain_new_urls
            domain.save()

        # Print summary per domain
        print(f"✅ Domain: {domain.name} | {domain_new_urls} unique URLs fetched")

    # Update URLSummary
    if total_new_urls > 0:
        url_summary, _ = URLSummary.objects.get_or_create(date=timezone.now().date())
        url_summary.unique_urls_added += total_new_urls
        url_summary.save()

    return total_new_urls