"""Merge this channel's public Atom feed into its persistent website catalog.

Standard library only. No API key, paid API, or private-channel data.
Prints JSON on stdout with --stdout; otherwise writes --catalog atomically.
"""
import argparse
import copy
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL_ID = 'UCjq6Yf2kgwXbHvtNNY3K_WA'
FEED_URL = 'https://www.youtube.com/feeds/videos.xml?channel_id=' + CHANNEL_ID
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def valid_video(video):
    return (isinstance(video, dict)
            and bool(re.fullmatch(r'[A-Za-z0-9_-]{11}', video.get('id', '')))
            and isinstance(video.get('title'), str) and 0 < len(video['title']) <= 500
            and video.get('language') in ('hi', 'en')
            and video.get('format') in ('short', 'story', 'video')
            and video.get('topic') in ('krishna', 'gita', 'wisdom'))


def validate_catalog(catalog):
    videos = catalog.get('videos', [])
    if catalog.get('channelId', CHANNEL_ID) != CHANNEL_ID:
        raise ValueError('Catalog is for another channel.')
    if not isinstance(videos, list) or not videos or not all(valid_video(v) for v in videos):
        raise ValueError('Invalid or empty catalog; refusing to replace saved videos.')
    if len({v['id'] for v in videos}) != len(videos):
        raise ValueError('Duplicate video IDs in catalog.')


def classify(title, old=None):
    # Preserve reviewed metadata on known videos. Atom does not expose duration,
    # so new uploads without an explicit Shorts label stay generically "video".
    old = old or {}
    language = 'hi' if re.search(r'[\u0900-\u097f]|\bhindi\b', title, re.I) else 'en'
    topic = ('gita' if re.search(r'\bgita\b|गीता', title, re.I) else
             'wisdom' if re.search(r'avatar|narasimha|ganesha|neelkanth|narada|dhruva|parikshit|prahlad|अवतार', title, re.I) else 'krishna')
    return {'language': old.get('language', language),
            'topic': old.get('topic', topic),
            'format': old.get('format', 'short' if re.search(r'#shorts?\b', title, re.I) else 'video')}


def merge_feed(catalog, xml, checked_at=None):
    validate_catalog(catalog)
    # A malformed/empty/wrong-channel response must never erase the catalog.
    if len(xml) > 2_000_000 or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
        raise ValueError('Unsupported feed response.')
    root = ET.fromstring(xml)
    # YouTube can omit the UC prefix from Atom channelId; the author URI is
    # checked independently against the canonical channel URL.
    allowed_ids = (CHANNEL_ID, CHANNEL_ID[2:])
    if (root.findtext('yt:channelId', namespaces=NS) not in allowed_ids
            or root.findtext('a:author/a:uri', namespaces=NS) != 'https://www.youtube.com/channel/' + CHANNEL_ID):
        raise ValueError('Feed channel does not match Dharma Tales Junior.')
    entries = root.findall('a:entry', NS)
    if not entries:
        raise ValueError('Empty feed; keeping the previous catalog.')
    videos = {v['id']: copy.deepcopy(v) for v in catalog['videos']}
    baseline = copy.deepcopy(list(videos.values()))
    for entry in entries:
        if entry.findtext('yt:channelId', namespaces=NS) not in allowed_ids:
            raise ValueError('Entry belongs to another channel.')
        vid = entry.findtext('yt:videoId', '', NS)
        title = entry.findtext('a:title', '', NS).strip()
        published = entry.findtext('a:published', '', NS)
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid) or not 0 < len(title) <= 500:
            raise ValueError('Invalid feed entry.')
        try:
            published = dt.datetime.fromisoformat(published.replace('Z', '+00:00')).astimezone(dt.timezone.utc).isoformat()
        except ValueError as error:
            raise ValueError('Invalid publication date.') from error
        old = videos.get(vid)
        videos[vid] = {**(old or {}), 'id': vid, 'title': title, **classify(title, old), 'publishedAt': published}
    ordered = list(videos.values())
    ordered.sort(key=lambda v: v.get('publishedAt', ''), reverse=True)
    now = checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    result = {**catalog, 'schemaVersion': 1, 'channelId': CHANNEL_ID,
              'checkedAt': now, 'videos': ordered, 'syncCadence': 'daily'}
    if ordered != baseline or not result.get('updatedAt'):
        result['updatedAt'] = now
    validate_catalog(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--feed-file', type=Path)
    parser.add_argument('--stdout', action='store_true')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    if args.feed_file:
        xml = args.feed_file.read_bytes()
    else:
        request = urllib.request.Request(FEED_URL, headers={'User-Agent': 'DharmaTalesJunior-Catalog/1.0', 'Accept': 'application/atom+xml'})
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200:
                raise RuntimeError('YouTube feed is unavailable; saved catalog was kept.')
            xml = response.read(2_000_001)
    updated = merge_feed(catalog, xml)
    output = json.dumps(updated, ensure_ascii=False, indent=2) + '\n'
    if args.stdout:
        print(output, end='')
    else:
        temporary = args.catalog.with_suffix('.pending.json')
        temporary.write_text(output)
        temporary.replace(args.catalog)
        print(f"Catalog checked: {len(updated['videos'])} public videos.")


if __name__ == '__main__':
    main()
