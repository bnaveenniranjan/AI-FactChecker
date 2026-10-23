"""
Source retrieval service — pluggable connectors for external data.

Each connector implements the SourceConnector interface.
Connectors are registered in CONNECTORS and can be enabled/disabled
via settings without touching business logic.

Protection against SSRF:
- Only whitelisted domains are fetched.
- Retrieved content is treated as untrusted data, not instructions.
- Content is sanitised before being passed to the AI.
"""

from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

log = logging.getLogger('apps.sources')

# ---------------------------------------------------------------------------
# SSRF protection — only fetch from these domains
# ---------------------------------------------------------------------------
ALLOWED_DOMAINS = {
    'pib.gov.in',
    'india.gov.in',
    'indiabudget.gov.in',
    'finmin.nic.in',
    'pmkisan.gov.in',
    'mgnregs.nic.in',
    'nrega.nic.in',
    'pmjay.gov.in',
    'ayushmanbharat.pmjay.gov.in',
    'nha.gov.in',
    'pmindia.gov.in',
    'pmay-urban.gov.in',
    'pmayg.nic.in',
    'jaljeevanmission.gov.in',
    'uidai.gov.in',
    'epfindia.gov.in',
    'vikaspedia.in',
    'myscheme.gov.in',
    'data.gov.in',
    'prsindia.org',
    'wikipedia.org',
    'en.wikipedia.org',
    'thehindu.com',
    'hindustantimes.com',
    'indianexpress.com',
    'ndtv.com',
    'timesofindia.indiatimes.com',
    'livemint.com',
    'business-standard.com',
    'economictimes.indiatimes.com',
    'cagreports.nic.in',
    'loksabha.nic.in',
    'rajyasabha.tv',
    'eci.gov.in',
}

FETCH_TIMEOUT_S = 3
MAX_CONTENT_BYTES = 200_000  # 200 KB per source


def _is_allowed_url(url: str) -> bool:
    """Return True only if the URL's domain is in the allowlist."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip('www.')
        return any(domain == d or domain.endswith('.' + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def _sanitise_text(raw: str) -> str:
    """Remove HTML tags and normalise whitespace from retrieved text."""
    # Strip HTML
    try:
        soup = BeautifulSoup(raw, 'lxml')
        text = soup.get_text(separator=' ')
    except Exception:
        text = re.sub(r'<[^>]+>', ' ', raw)

    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:MAX_CONTENT_BYTES]


# ---------------------------------------------------------------------------
# Connector interface
# ---------------------------------------------------------------------------

class SourceConnector(ABC):
    """Abstract base for all source connectors."""

    name: str = 'base'
    description: str = ''

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[dict]:
        """
        Search for sources relevant to a query.

        Returns a list of dicts with at minimum:
            url, title, publisher, published_date (str or None), snippet (str)
        """
        ...

    @abstractmethod
    def fetch(self, url: str) -> Optional[dict]:
        """
        Fetch full content for a URL.

        Returns a dict with:
            url, title, publisher, published_date, text (sanitised)
        or None on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Web connector — generic HTTP fetcher
# ---------------------------------------------------------------------------

class WebConnector(SourceConnector):
    """
    Generic HTTP connector.

    Uses Python requests to fetch URLs from the allowlist.
    Does NOT use a search engine API — only fetches known URLs.
    """

    name = 'web'
    description = 'Generic allowlisted HTTP fetcher'

    def search(self, query: str, max_results: int = 5) -> List[dict]:
        """
        Web connector does not implement autonomous search.

        URL discovery is handled by the SearchOrchestrator
        which builds candidate URLs from the scheme name.
        """
        return []

    def fetch(self, url: str) -> Optional[dict]:
        """Fetch and sanitise content from an allowlisted URL."""
        if not _is_allowed_url(url):
            log.warning('Blocked fetch attempt for non-allowlisted URL: %s', url)
            return None

        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT_S, allow_redirects=True)
            resp.raise_for_status()

            # Parse metadata from response
            soup = BeautifulSoup(resp.text, 'lxml')
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''

            text = _sanitise_text(resp.text)
            return {
                'url': url,
                'title': title_text,
                'publisher': urlparse(url).netloc,
                'published_date': None,
                'text': text,
            }

        except requests.Timeout:
            log.warning('Fetch timeout for URL: %s', url)
            return None
        except requests.RequestException as exc:
            log.warning('Fetch failed for %s: %s', url, exc)
            return None


# ---------------------------------------------------------------------------
# PIB connector — Press Information Bureau
# ---------------------------------------------------------------------------

class PIBConnector(SourceConnector):
    """
    Connector for Press Information Bureau press releases.

    PIB is a primary source for government scheme announcements.
    """

    name = 'pib'
    description = 'Press Information Bureau (PIB) press releases'
    BASE_URL = 'https://pib.gov.in'

    def search(self, query: str, max_results: int = 5) -> List[dict]:
        """Search PIB for press releases matching the query."""
        # PIB search endpoint (may require adjustments to match live API)
        search_url = f'{self.BASE_URL}/allRel.aspx'
        try:
            resp = requests.get(
                search_url,
                params={'query': query},
                timeout=FETCH_TIMEOUT_S,
            )
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'lxml')
            results = []
            for a in soup.select('a[href*="PressReleasePage"]')[:max_results]:
                href = a.get('href', '')
                full_url = href if href.startswith('http') else f'{self.BASE_URL}/{href.lstrip("/")}'
                results.append({
                    'url': full_url,
                    'title': a.get_text(strip=True),
                    'publisher': 'Press Information Bureau',
                    'published_date': None,
                    'snippet': '',
                })
            return results
        except Exception as exc:
            log.warning('PIB search failed: %s', exc)
            return []

    def fetch(self, url: str) -> Optional[dict]:
        web = WebConnector()
        result = web.fetch(url)
        if result:
            result['publisher'] = 'Press Information Bureau'
        return result


# ---------------------------------------------------------------------------
# Connector registry
# ---------------------------------------------------------------------------

CONNECTORS: dict[str, SourceConnector] = {
    'web': WebConnector(),
    'pib': PIBConnector(),
}


def get_connector(name: str) -> Optional[SourceConnector]:
    """Return a registered connector by name."""
    return CONNECTORS.get(name)


def fetch_url_content(url: str) -> Optional[dict]:
    """
    Fetch content for a URL using the appropriate connector.

    Always validates against the allowlist first.
    """
    connector = WebConnector()
    return connector.fetch(url)
