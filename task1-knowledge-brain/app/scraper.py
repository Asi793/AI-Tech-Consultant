import asyncio
import hashlib
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from app.storage import save_article

SITEMAP_URL = (
    "https://support.brilliantdirectories.com/support/sitemap.xml"
)

ALLOWED_HOST = "support.brilliantdirectories.com"


async def get_sitemap_urls(client, sitemap_url):
    response = await client.get(sitemap_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    urls = []

    for node in root:
        loc = node.find("{*}loc")
        if loc is None or not loc.text:
            continue

        url = loc.text.strip()

        if node.tag.endswith("sitemap"):
            urls.extend(await get_sitemap_urls(client, url))
        elif url.startswith("https://"):
            from urllib.parse import urlparse
            if urlparse(url).hostname == ALLOWED_HOST:
                urls.append(url)

    return urls


async def scrape_article(client, url):
    response = await client.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    for element in soup.select(
        "script, style, nav, footer, header, noscript"
    ):
        element.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else url

    article = (
        soup.select_one("article")
        or soup.select_one("main")
        or soup.body
    )

    if article is None:
        return None

    content = article.get_text(" ", strip=True)
    if len(content) < 100:
        return None

    content_hash = hashlib.sha256(
        f"{title}\n{content}".encode("utf-8")
    ).hexdigest()

    return {
        "url": url,
        "title": title,
        "content": content,
        "content_hash": content_hash,
    }


async def ingest(max_pages=10):
    headers = {"User-Agent": "AITechConsultantStudentProject/1.0"}

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        urls = await get_sitemap_urls(client, SITEMAP_URL)
        urls = list(dict.fromkeys(urls))[:max_pages]

        successful = 0
        failed = []

        for url in urls:
            try:
                article = await scrape_article(client, url)

                if article:
                    save_article(**article)
                    successful += 1

            except (httpx.HTTPError, ValueError) as exc:
                failed.append({
                    "url": url,
                    "error": str(exc)[:200],
                })

            await asyncio.sleep(1.0)

    return {
        "discovered": len(urls),
        "saved": successful,
        "failed_count": len(failed),
        "failures": failed[:10],
    }