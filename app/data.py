"""Election data collector. Open America counts are partial-coverage, NOT race calls."""
import asyncio
import copy
import datetime as dt
import logging
import os
import re
import time
from html import unescape
from urllib.parse import quote

import feedparser
import httpx

log = logging.getLogger(__name__)
BASE = 'https://openamerica.io/elections/results.json'
# Publisher feeds are best-effort, with multiple independent fallbacks.
# Headline links are attribution, not rights to reproduce publisher video or copy.
NEWS_SOURCES = [
    ('NPR Politics', 'https://feeds.npr.org/1014/rss.xml'),
    ('PBS NewsHour Politics', 'https://www.pbs.org/newshour/feeds/rss/politics'),
    ('Virginia Mercury', 'https://virginiamercury.com/feed/'),
    ('WTOP', 'https://wtop.com/feed/'),
    ('Google News', 'https://news.google.com/rss/search?q=' + quote('2026 midterm election results when:2d') + '&hl=en-US&gl=US&ceid=US:en'),
]
REGION_TERMS = ('virginia','fairfax','loudoun','prince william','arlington','alexandria','district 7','district 8','district 10','district 11','vindman','beyer','walkinshaw','subramanyam','warner','mizusawa','northern va','nova')

OFFICES = ('House', 'Senate', 'Governor')


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def normalize(office, data):
    if not isinstance(data, dict) or data.get('year') != 2026 or str(data.get('office', '')).lower() != office.lower():
        raise ValueError('Unexpected election year or office in API response')
    records = []
    for key, race in (data.get('races') or {}).items():
        if not isinstance(race, dict):
            continue
        candidates = []
        for c in race.get('cands', []):
            if not isinstance(c, dict):
                continue
            candidates.append({'name': str(c.get('n', ''))[:100], 'party': str(c.get('p', ''))[:8],
                               'votes': int(c.get('v') or 0), 'pct': c.get('pct')})
        candidates.sort(key=lambda c: c['votes'], reverse=True)
        records.append({'key': str(key)[:32], 'office': office, 'leader': str(race.get('leader') or ''),
                        'total': int(race.get('total') or 0), 'pct_in': race.get('pct_in'),
                        'candidates': candidates, 'called': False, 'winner': None,
                        'as_of': data.get('as_of')})
    records.sort(key=lambda r: r['total'], reverse=True)
    return {'office': office, 'live': bool(data.get('live')), 'stale': bool(data.get('stale')),
            'counting': bool(data.get('counting')), 'final': bool(data.get('final')),
            'as_of': data.get('as_of'), 'races': records,
            'coverage_count': len(records), 'source': 'Open America / official state election feeds'}


class ElectionStore:
    def __init__(self):
        self.feeds = {o: {'office': o, 'live': False, 'stale': False, 'as_of': None,
                          'races': [], 'coverage_count': 0, 'source': 'Open America / official state election feeds'} for o in OFFICES}
        self.headlines = []
        self.regional_headlines = []
        self.news_sources = []
        self.events = []
        self.status = {'last_attempt': None, 'last_success': None, 'errors': {}, 'mode': 'demo' if os.getenv('DEMO_MODE') == '1' else 'live'}
        self.etags = {}
        self.last_audio_id = 0
        self.prev = {}
        self.lock = asyncio.Lock()

    def snapshot(self):
        feeds = copy.deepcopy(self.feeds)
        return {'offices': feeds, 'headlines': copy.deepcopy(self.headlines),
                'events': copy.deepcopy(self.events[-12:][::-1]), 'regional_headlines': copy.deepcopy(self.regional_headlines), 'news_sources': copy.deepcopy(self.news_sources), 'status': copy.deepcopy(self.status),
                'generated_at': utcnow(), 'disclaimer': 'Unofficial election-night counts. Partial state coverage. Leads are not race calls.'}

    def process(self, office, normalized):
        old = self.prev.get(office, {})
        new = {r['key']: r for r in normalized['races']}
        if old:
            for key, race in new.items():
                before = old.get(key)
                if before and race['total'] > before['total'] and race['total'] >= 100:
                    a = race['candidates'][0] if race['candidates'] else None
                    if not a:
                        continue
                    # Only announce substantive updates; never imply a winner.
                    diff = race['total'] - before['total']
                    if diff >= max(500, before['total'] * 0.03):
                        self.events.append({'id': f'{office}:{key}:{race["total"]}', 'office': office,
                                            'seat': key, 'leader': a['name'], 'party': a['party'],
                                            'votes': a['votes'], 'total': race['total'],
                                            'as_of': normalized.get('as_of'), 'at': utcnow(),
                                            'text': f'In the {key} {office} race, {a["name"]} currently leads with {a["votes"]:,} votes counted for that candidate. This is a lead, not a projected winner.'})
            self.events = self.events[-40:]
        self.prev[office] = new
        self.feeds[office] = normalized

    async def fetch_office(self, client, office):
        headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'ElectionCastRender/1.0 (election reporting, 60s polling)'}
        if office in self.etags:
            headers['If-None-Match'] = self.etags[office]
        res = await client.get(BASE, params={'year': 2026, 'office': office}, headers=headers)
        if res.status_code == 304:
            return
        res.raise_for_status()
        normalized = normalize(office, res.json())
        if res.headers.get('etag'):
            self.etags[office] = res.headers['etag']
        async with self.lock:
            self.process(office, normalized)
            self.status['last_success'] = utcnow()
            self.status['errors'].pop(office, None)

    async def fetch_news(self, client):
        """Collect independently; a single failed publisher cannot blank the news wall."""
        import email.utils
        import calendar
        async def one(source, url):
            try:
                resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0 (ElectionCast/2.0; syndicated headline reader)'}, timeout=12)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.content)
                if not parsed.entries:
                    raise ValueError('RSS returned no entries')
                found = []
                for entry in parsed.entries[:16]:
                    title = unescape(re.sub('<[^>]+>', '', entry.get('title', ''))).strip()
                    link = entry.get('link', '')
                    if not title or not (link.startswith('http://') or link.startswith('https://')):
                        continue
                    # Do not auto-repeat fabricated/unsourced polling percentage claims.
                    found.append({'title': title[:190], 'source': source, 'url': link,
                                  'published': entry.get('published', '') or entry.get('updated', '')})
                return found, None
            except Exception as exc:
                return [], str(exc)[:125]

        responses = await asyncio.gather(*(one(name, url) for name,url in NEWS_SOURCES))
        articles, healthy, failures = [], [], {}
        for (source, _), (items, error) in zip(NEWS_SOURCES, responses):
            if items: healthy.append(source); articles.extend(items)
            if error: failures[source] = error
        seen, unique = set(), []
        for article in articles:
            key = re.sub(r'[^a-z0-9]+', '', article['title'].lower())[:85]
            if key in seen: continue
            seen.add(key); unique.append(article)
        # Preserve last good news during transient upstream outages.
        if unique:
            self.headlines = unique[:45]
            self.regional_headlines = [a for a in unique if any(t in a['title'].lower() for t in REGION_TERMS)][:15]
            self.status['last_news_success'] = utcnow()
        self.news_sources = healthy
        if healthy:
            self.status['errors'].pop('news', None)
            if failures: self.status['news_warnings'] = failures
        else:
            self.status['errors']['news'] = 'All publisher RSS sources are unavailable; cached headlines retained'

    async def demo(self):
        # Clearly labeled SIMULATED results, never mixed with actual results.
        samples = [('VA-10', 'House'), ('TX-23', 'House'), ('AZ', 'Senate'), ('MI', 'Governor')]
        for i, (key, office) in enumerate(samples):
            a, b = 84000 + i * 21000, 81000 + i * 16000
            race = {'key': key, 'office': office, 'leader': 'D', 'total': a+b, 'pct_in': 54 + i*5,
                    'candidates': [{'name': 'Sample Candidate A', 'party': 'D', 'votes': a, 'pct': round(100*a/(a+b),1)},
                                   {'name': 'Sample Candidate B', 'party': 'R', 'votes': b, 'pct': round(100*b/(a+b),1)}],
                    'called': False, 'winner': None, 'as_of': utcnow()}
            self.feeds[office]['races'].append(race)
            self.feeds[office]['coverage_count'] += 1
        self.headlines = [{'title': 'DEMO MODE — live news is disabled', 'source': 'ElectionCast demo', 'url': '', 'published': ''}]
        self.status['last_success'] = utcnow()

    async def run(self):
        if os.getenv('DEMO_MODE') == '1':
            await self.demo()
            return
        async with httpx.AsyncClient(timeout=22, follow_redirects=True) as client:
            news_at = 0
            while True:
                self.status['last_attempt'] = utcnow()
                tasks = [(office, self.fetch_office(client, office)) for office in OFFICES]
                if time.monotonic() - news_at >= 180:
                    tasks.append(('news', self.fetch_news(client)))
                    news_at = time.monotonic()
                results = await asyncio.gather(*(t for _, t in tasks), return_exceptions=True)
                for (name, _), result in zip(tasks, results):
                    if isinstance(result, BaseException):
                        log.warning('Feed %s failed: %s', name, result)
                        self.status['errors'][name] = str(result)[:160]
                await asyncio.sleep(max(60, int(os.getenv('POLL_SECONDS', '60'))))

store = ElectionStore()
