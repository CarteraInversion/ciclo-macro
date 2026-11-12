#!/usr/bin/env python3
"""Actualiza data.json usando la API oficial de FRED y la web oficial de ISM.
Requiere el secreto FRED_API_KEY configurado en GitHub Actions.
Nunca sustituye observaciones verificadas por valores inventados.
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
KEY = os.getenv('FRED_API_KEY', '').strip()
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'CicloMacroDashboard/2.0 (public macro data)'})
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
        raise RuntimeError('Falta FRED_API_KEY: Settings > Secrets and variables > Actions')
    url = 'https://api.stlouisfed.org/fred/series/observations'
    resp = SESSION.get(url, params={
        'series_id': series_id, 'api_key': KEY, 'file_type': 'json',
        'observation_start': '2018-01-01', 'sort_order': 'asc',
    }, timeout=(8, 16))
    resp.raise_for_status()
    rows = resp.json().get('observations', [])
    values = []
    for row in rows:
        try:
            value = float(row['value'])
            date = row['date']
            values.append({'date': date, 'value': value})
        except (ValueError, TypeError, KeyError):
            continue
    if not values:
        raise RuntimeError(f'La API no devolvió observaciones válidas para {series_id}')
    return values[-1600:]


def ism_report():
    # El ISM manufacturero se publica el primer día laborable del mes SIGUIENTE.
    # Consultar mes anterior y, como respaldo, dos meses anteriores.
    now = datetime.now(timezone.utc)
    month_names = ['january','february','march','april','may','june',
                   'july','august','september','october','november','december']
    candidates = []
    for offset in [1, 2, 0]:
        year = now.year
        month = now.month - offset
        while month < 1:
            year -= 1
            month += 12
        url = ('https://www.ismworld.org/supply-management-news-and-reports/'
               f'reports/ism-pmi-reports/pmi/{month_names[month-1]}/')
        try:
            resp = SESSION.get(url, timeout=(7, 12))
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = ' '.join(soup.stripped_strings)
            # Verificar que el informe corresponde al mes y año, no a otro año.
            label = f'{month_names[month-1]} {year}'
            if not re.search(r'\b' + re.escape(label) + r'\b', text, re.I):
                continue
            patterns = [
                r'Manufacturing PMI[^.]{0,100}?registered\s+(\d{2}(?:\.\d+)?)\s+percent',
                r'Manufacturing PMI[^.]{0,75}?at\s+(\d{2}(?:\.\d+)?)\s*%',
            ]
            for pat in patterns:
                match = re.search(pat, text, re.I)
                if match and 25 < float(match.group(1)) < 75:
                    candidates.append({'date': f'{year}-{month:02d}-01',
                                       'value': float(match.group(1)), 'url': url})
                    break
        except requests.RequestException as exc:
            print(f'ISM {label}: {exc}', flush=True)
    if not candidates:
        raise RuntimeError('No se pudo verificar el ISM manufacturero en la web oficial')
    return max(candidates, key=lambda p: p['date'])


def main():
    old = json.loads(DEST.read_text(encoding='utf-8')) if DEST.exists() else {'series': {}}
    prior = old.get('series', {})
