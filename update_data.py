#!/usr/bin/env python3
"""Actualiza las series macro con FRED API y el PMI de ISM.
Requiere FRED_API_KEY como secret de GitHub Actions.
Si una fuente falla, conserva la serie previa y la marca stale.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'data.json'
KEY = os.environ.get('FRED_API_KEY', '').strip()
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'CicloMacroDashboard/2.1 (personal economic research)'})
SERIES = {
    'core_pce_index': ('PCEPILFE', 'BEA/FRED', 'monthly'),
    'tips10': ('DFII10', 'Treasury/FRED', 'daily'),
    'ccc_spread': ('BAMLH0A3HYC', 'ICE BofA/FRED', 'daily'),
    'unemployment': ('UNRATE', 'BLS/FRED', 'monthly'),
    'claims': ('ICSA', 'DOL/FRED', 'weekly'),
    'industrial': ('INDPRO', 'Federal Reserve/FRED', 'monthly'),
    'yield_curve': ('T10Y2Y', 'Treasury/FRED', 'daily'),
}


def fred_series(series_id):
    if not KEY:
        raise RuntimeError('Falta FRED_API_KEY en GitHub Actions Secrets')
    response = SESSION.get(
        'https://api.stlouisfed.org/fred/series/observations',
        params={'series_id': series_id, 'api_key': KEY, 'file_type': 'json',
                'observation_start': '2018-01-01'},
        timeout=(8, 18),
    )
    response.raise_for_status()
    observations = response.json().get('observations', [])
    values = []
    for item in observations:
        try:
            values.append({'date': item['date'], 'value': float(item['value'])})
        except (KeyError, ValueError, TypeError):
            continue
    if not values:
        raise RuntimeError('La API no devolvio observaciones validas')
    return values[-1600:]


def ism_report():
    # El PMI del mes suele publicarse al comienzo del siguiente mes.
    now = datetime.now(timezone.utc)
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']
    candidates = []
    for offset in [1, 2, 0]:
        month_number = now.year * 12 + now.month - 1 - offset
        year, zero_based_month = divmod(month_number, 12)
        month = zero_based_month + 1
        url = ('https://www.ismworld.org/supply-management-news-and-reports/'
               f'reports/ism-pmi-reports/pmi/{months[zero_based_month]}/')
        try:
            response = SESSION.get(url, timeout=(6, 10))
            response.raise_for_status()
            text = ' '.join(BeautifulSoup(response.text, 'html.parser').stripped_strings)
            if not re.search(rf'\b{months[zero_based_month]}\s+{year}\b', text, re.I):
                continue
            patterns = [
                r'Manufacturing PMI[^.]{0,100}?registered\s+(\d{2}(?:\.\d+)?)\s+percent',
                r'Manufacturing PMI[^.]{0,75}?at\s+(\d{2}(?:\.\d+)?)\s*%',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.I)
                if match and 25 < float(match.group(1)) < 75:
                    candidates.append({'date': f'{year}-{month:02d}-01',
                                       'value': float(match.group(1)), 'url': url})
                    break
        except requests.RequestException as exc:
            print(f'ISM {year}-{month:02d}: {exc}', flush=True)
    if not candidates:
        raise RuntimeError('No se pudo verificar un nuevo dato ISM en la web oficial')
    return max(candidates, key=lambda x: x['date'])


def main():
    previous = json.loads(DEST.read_text(encoding='utf-8')) if DEST.exists() else {'series': {}}
    prior_series = previous.get('series', {})
    data = {
        'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'series': {}, 'errors': {}, 'method_version': '2.1',
    }
    for key, (series_id, source, frequency) in SERIES.items():
        try:
