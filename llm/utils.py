import requests
from xml.etree import ElementTree
from datetime import datetime, timedelta
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from newspaper import Article
import concurrent.futures
import random
from .models import Domain, URL, JobRun, SitemapScan
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import close_old_connections
import time

UNWANTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".mp4", ".mp3", ".webp"}
DATE_THRESHOLD = timezone.now() - timedelta(days=180)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F)...",
]


def fetch_robots_txt(domain):
    robots_url = f"https://{domain}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=10)
        response.raise_for_status()
        return [line.split(": ")[1].strip() for line in response.text.splitlines() if line.lower().startswith("sitemap:")]
    except requests.RequestException as e:
        print(f"Failed to fetch robots.txt for {domain}: {e}")
        return []


def fetch_urls_from_sitemap(sitemap_url, domain, visited_sitemaps=None):
    if visited_sitemaps is None:
        visited_sitemaps = set()

    if sitemap_url in visited_sitemaps:
        return set()

    visited_sitemaps.add(sitemap_url)
    sitemap_scan, created = SitemapScan.objects.get_or_create(domain=domain, sitemap_url=sitemap_url)

    try:
        head_response = requests.head(sitemap_url, timeout=10)
        last_modified_header = head_response.headers.get("Last-Modified")

        if last_modified_header:
            last_modified_dt = datetime.strptime(last_modified_header, "%a, %d %b %Y %H:%M:%S %Z")
            if sitemap_scan.last_modified_header and last_modified_dt <= sitemap_scan.last_modified_header:
                return set()
    except requests.RequestException:
        pass

    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)

        urls = set()
        nested_sitemaps = set()
        lastmod_dates = []

        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall(".//{*}sitemap"):
                loc_tag = sitemap.find("{*}loc")
                if loc_tag is not None:
                    nested_sitemaps.add(loc_tag.text.strip())
        else:
            for url_entry in root.findall(".//{*}url"):
                loc_tag = url_entry.find("{*}loc")
                lastmod_tag = url_entry.find("{*}lastmod")
                if loc_tag is not None:
                    url = loc_tag.text.strip()
                    if any(url.lower().endswith(ext) for ext in UNWANTED_EXTENSIONS):
                        continue
                    if lastmod_tag is not None:
                        try:
                            lastmod_date = datetime.fromisoformat(lastmod_tag.text.strip().replace("Z", "+00:00"))
                            if lastmod_date < DATE_THRESHOLD:
                                continue
                            lastmod_dates.append(lastmod_date)
                        except ValueError:
                            pass
                    urls.add(url)

        sitemap_scan.last_scanned_at = timezone.now()
        if last_modified_header:
            sitemap_scan.last_modified_header = last_modified_dt
        if lastmod_dates:
            sitemap_scan.lastmod_from_sitemap = max(lastmod_dates)
        sitemap_scan.save()

        for nested_sitemap in nested_sitemaps:
            urls.update(fetch_urls_from_sitemap(nested_sitemap, domain, visited_sitemaps))

        return urls

    except requests.RequestException:
        return set()


def fetch_and_store_urls():
    job_run = JobRun.objects.create(status="running")
    total_new_urls = 0

    try:
        domains = Domain.objects.all()
        visited_sitemaps_per_domain = {}

        for domain in domains:
            sitemap_urls = fetch_robots_txt(domain.name)
            visited_sitemaps = visited_sitemaps_per_domain.get(domain.name, set())

            for sitemap_url in sitemap_urls:
                urls = fetch_urls_from_sitemap(sitemap_url, domain, visited_sitemaps)
                for url in urls:
                    if not URL.objects.filter(url=url).exists():
                        URL.objects.create(domain=domain, url=url)
                        total_new_urls += 1

            visited_sitemaps_per_domain[domain.name] = visited_sitemaps

        job_run.status = "completed"
        job_run.details = f"Total new URLs: {total_new_urls}"
    except Exception as e:
        job_run.status = "failed"
        job_run.details = f"URL fetching failed due to: {str(e)}"
    finally:
        job_run.finished_at = timezone.now()
        job_run.save()

    return total_new_urls


def extract_article_data(url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        article = Article(url)
        article.download(input_html=response.text)
        article.parse()
        if not article.text or len(article.text) < 300:
            raise ValueError("Empty content")
        return {
            "title": article.title, 
            "author": article.authors[0] if article.authors else "Unknown", 
            "content": article.text[:5000],
            "published_date": article.publish_date.date() if article.publish_date else None
            }
    except Exception:
        return extract_with_selenium(url)


def extract_with_selenium(url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        article = Article(url)
        article.download(input_html=driver.page_source)
        article.parse()
        return {
            "title": article.title, 
            "author": article.authors[0] if article.authors else "Unknown", 
            "content": article.text[:5000],
            "published_date": article.publish_date.date() if article.publish_date else None
            }
    finally:
        driver.quit()


def fetch_metadata_for_pending_urls():
    job_run = JobRun.objects.create(status="running")
    batch_size = 50
    max_workers = 5

    try:
        pending_urls = URL.objects.filter(meta_fetched=False)

        while pending_urls.exists():
            urls_batch = pending_urls[:batch_size]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(extract_article_data, url_obj.url): url_obj for url_obj in urls_batch}

                for future in as_completed(futures):
                    url_obj = futures[future]
                    try:
                        data = future.result()
                        if data:
                            url_obj.title = data.get("title", "")
                            url_obj.author = data.get("author", "")
                            url_obj.content = data.get("content", "")
                            url_obj.published_date = data.get("published_date")
                            url_obj.meta_fetched = True
                            url_obj.save()
                    except Exception as e:
                        print(f"Failed to fetch metadata for {url_obj.url}: {e}")

                    # Avoid overwhelming websites with too many requests
                    time.sleep(random.uniform(1, 3))

                    # Ensure DB connections are refreshed periodically
                    close_old_connections()

            # Refresh queryset after batch completion
            pending_urls = URL.objects.filter(meta_fetched=False)

        job_run.status = "completed"
    except Exception as e:
        job_run.status = "failed"
        job_run.details = f"Meta fetching failed: {str(e)}"
    finally:
        job_run.finished_at = timezone.now()
        job_run.save()

