#!/usr/bin/env python3
"""Upload a Markdown or HTML document to Claude Boy Service and print its URL."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--name')
    parser.add_argument('--server', help='base URL or host:port; overrides CLAUDE_BOY_API_URL')
    args = parser.parse_args()
    source = args.file.expanduser()
    name = args.name or source.name
    if not name or name.startswith('.') or len(name.encode()) > 255 or any(c in '/\\' or ord(c) < 32 or ord(c) == 127 for c in name):
        parser.error('name must be a plain filename')
    if Path(name).suffix.lower() not in ('.md', '.markdown', '.html', '.htm'):
        parser.error('only Markdown and HTML files are supported')
    if source.stat().st_size > 5 * 1024 * 1024:
        parser.error('preview exceeds 5 MiB')
    data = source.read_bytes()
    data.decode('utf-8')
    server = args.server or os.environ.get('CLAUDE_BOY_API_URL', 'http://10.30.0.164:8080')
    if '://' not in server:
        server = 'http://' + server
    server = server.rstrip('/')
    parsed = urllib.parse.urlsplit(server)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        parser.error('server must be an HTTP(S) origin or host:port')
    request = urllib.request.Request(server + '/v1/previews/' + urllib.parse.quote(name, safe=''), data=data, method='PUT', headers={'Content-Type': 'text/plain; charset=utf-8'})
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.load(response)
    print(server + result['url'])


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f'Upload failed: HTTP {error.code}: {error.read().decode()}', file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError) as error:
        print(f'Upload failed: {error}', file=sys.stderr)
        sys.exit(1)
