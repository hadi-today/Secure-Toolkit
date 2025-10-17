# File: feed_fetcher.py

import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from dateutil.parser import parse as parse_date

import cloudscraper
import ssl
import xml.etree.ElementTree as ET

# feedparser دیگر برای این سایت‌مپ خاص استفاده نمی‌شود، اما برای فیدهای دیگر ممکن است لازم باشد.
# ما آن را در اینجا نگه می‌داریم اما منطق اصلی از آن استفاده نخواهد کرد.
import feedparser 

class FetchFeedThread(QThread):
    result_ready = pyqtSignal(int, list)
    error_occurred = pyqtSignal(str)
    status_updated = pyqtSignal(str)

    def __init__(self, feed_id, feed_url, feed_timezone, fetch_days):
        super().__init__()
        self.feed_id = feed_id
        self.feed_url = feed_url
        self.feed_timezone = feed_timezone
        self.fetch_days = fetch_days

        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ciphers = [
                "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-ECDSA-CHACHA20-POLY1305", "ECDHE-RSA-CHACHA20-POLY1305",
                "AES128-GCM-SHA256", "AES256-GCM-SHA384"
            ]
            context.set_ciphers(':'.join(ciphers))
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.scraper = cloudscraper.create_scraper(ssl_context=context, browser='chrome')
        except Exception:
            self.scraper = cloudscraper.create_scraper(browser='chrome')

    def run(self):
        """منطق نهایی با استفاده کامل از پارسر XML برای هر دو لایه."""
        try:
            # مرحله ۱: دانلود فایل ایندکس اصلی
            self.status_updated.emit(f"Fetching sitemap index: {self.feed_url}...")
            index_response = self.scraper.get(self.feed_url, timeout=45)
            index_response.raise_for_status()
            index_content = index_response.text.encode('utf-8')

            # مرحله ۲: استخراج URL های لایه دوم
            sub_sitemap_urls = []
            namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            try:
                root = ET.fromstring(index_content)
                for sitemap_node in root.findall('sitemap:sitemap', namespaces):
                    loc_node = sitemap_node.find('sitemap:loc', namespaces)
                    if loc_node is not None and loc_node.text:
                        sub_sitemap_urls.append(loc_node.text)
            except ET.ParseError as e:
                self.error_occurred.emit(f"Could not parse XML index: {e}")
                return

            if not sub_sitemap_urls:
                 self.error_occurred.emit("No sub-sitemaps found in the index file.")
                 return

            # مرحله ۳: پردازش هر سایت‌مپ داخلی و استخراج مستقیم مقالات
            all_articles_data = []
            self.status_updated.emit(f"Found {len(sub_sitemap_urls)} sub-sitemaps. Parsing entries...")
            
            for sub_url in sub_sitemap_urls:
                try:
                    sub_response = self.scraper.get(sub_url, timeout=45)
                    sub_response.raise_for_status()
                    sub_content = sub_response.text.encode('utf-8')
                    
                    sub_root = ET.fromstring(sub_content)
                    for url_node in sub_root.findall('sitemap:url', namespaces):
                        loc_node = url_node.find('sitemap:loc', namespaces)
                        lastmod_node = url_node.find('sitemap:lastmod', namespaces)
                        
                        link = loc_node.text if loc_node is not None else None
                        date_str = lastmod_node.text if lastmod_node is not None else None
                        
                        if link and date_str:
                            all_articles_data.append({'link': link, 'published': date_str})

                except Exception as e:
                    self.error_occurred.emit(f"Failed to process sub-sitemap {sub_url}: {e}")

            # مرحله ۴: فیلتر کردن مقالات بر اساس تاریخ
            articles = []
            time_window = datetime.now(timezone.utc) - timedelta(days=self.fetch_days)
            
            for item in all_articles_data:
                published_time_utc = self._parse_date_utc(item.get('published'))
                
                if published_time_utc and published_time_utc > time_window:
                    link = item.get('link')
                    # ساختن یک عنوان پیش‌فرض از روی لینک
                    try:
                        path = urllib.parse.urlparse(link).path; slug = path.strip('/').split('/')[-1]
                        title = urllib.parse.unquote(slug).replace('-', ' ').replace('.html', '').capitalize()
                    except: 
                        title = link
                    
                    articles.append({
                        'title': title, 'link': link, 'summary': '',
                        'published_parsed': published_time_utc.isoformat(),
                    })
            
            self.status_updated.emit(f"Process finished. Found {len(all_articles_data)} total URLs, {len(articles)} are new.")
            self.result_ready.emit(self.feed_id, articles)

        except Exception as e:
            self.error_occurred.emit(f"A critical error occurred: {e}")

    def _parse_date_utc(self, date_str):
        """یک تابع ساده‌تر برای پارس کردن تاریخ از سایت‌مپ‌ها."""
        if not date_str:
            return None
        try:
            dt_aware = parse_date(date_str)
            if dt_aware.tzinfo is None:
                dt_aware = dt_aware.replace(tzinfo=timezone.utc)
            return dt_aware.astimezone(timezone.utc)
        except Exception:
            return None