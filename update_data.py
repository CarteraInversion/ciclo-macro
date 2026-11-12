#!/usr/bin/env python3
"""Actualiza los indicadores macro en data.json desde FRED e ISM.

Necesita FRED_API_KEY como secreto de GitHub Actions.
Cuando una fuente falla, conserva los datos previos y los marca stale.
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
SESSION.headers.update({'User-Agent': 'CicloMacroDashboard/2.1 (personal research)'})
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
        raise RuntimeError('Falta el secreto FRED_API_KEY en GitHub Actions')
    resp = SESSION.get(
        'https://api.stlouisfed.org/fred/series/observations',
        params={
            'series_id': series_id,
            'api_key': KEY,
            'file_type': 'json',
            'observation_start': '2018-01-01',
            'sort_order': 'asc',
        },
        timeout=(8, 18),
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error_message' in data:
        raise RuntimeError(data['error_message'])
    observations = []
    for row in data.get('observations', []):
        try:
            observations.append({'date': row['date'], 'value': float(row['value'])})
        except (KeyError, ValueError, TypeError):
            continue
    if not observations:
        raise RuntimeError(f'FRED no devolvió observaciones para {series_id}')
    return observations[-1600:]


def ism_report():
    """Intenta verificar el PMI manufacturero en las páginas oficiales de ISM."""
    now = datetime.now(timezone.utc)
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']
    candidates = []
    for offset in (1, 2, 0):
        year, month = now.year, now.month - offset
        while month < 1:
            year -= 1
            month += 12
        url = ('https://www.ismworld.org/supply-management-news-and-reports/'
               f'reports/ism-pmi-reports/pmi/{months[month - 1]}/')
        label = f'{months[month - 1]} {year}'
        try:
            response = SESSION.get(url, timeout=(7, 12))
            response.raise_for_status()
            text = ' '.join(BeautifulSoup(response.text, 'html.parser').stripped_strings)
            if not re.search(r'\b' + re.escape(label) + r'\b', text, re.IGNORECASE):
                continue
            patterns = [
                r'Manufacturing PMI[^.]{0,100}?registered\s+(\d{2}(?:\.\d+)?)\s+percent',
                r'Manufacturing PMI[^.]{0,75}?at\s+(\d{2}(?:\.\d+)?)\s*%',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and 25 < float(match.group(1)) < 75:
                    candidates.append({'date': f'{year}-{month:02d}-01',
                                       'value': float(match.group(1)), 'url': url})
                    break
        except requests.RequestException as exc:
            print(f'AVISO ISM {label}: {exc}', flush=True)
    if not candidates:
        raise RuntimeError('No se pudo verificar el PMI de ISM en las páginas oficiales')
    return max(candidates, key=lambda item: item['date'])


def main():
    old = json.loads(DEST.read_text(encoding='utf-8')) if DEST.exists() else {'series': {}}
    prior = old.get('series', {})
    result = {
        'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'series': {}, 'errors': {}, 'method_version': '2.1',
    }
    success = 0
    for name, (sid, source, frequency) in SERIES.items():
        try:
            print(f'Consultando FRED {sid}...', flush=True)
            values = fred_series(sid)
            result['series'][name] = {
                'id': sid, 'source': source, 'frequency': frequency,
                'values': values, 'status': 'ok',
                'url': f'https://fred.stlouisfed.org/series/{sid}',
            }
            success += 1
            print(f'OK {name}: {values[-1]}', flush=True)
        except Exception as exc:
            result['errors'][name] = str(exc)
            if name in prior:
                result['series'][name] = {**prior[name], 'status': 'stale'}
            print(f'ERROR {name}: {exc}', flush=True)

    try:
        print('Consultando PMI de ISM...', flush=True)
        pmi = ism_report()
        historic = prior.get('pmi', {}).get('values', [])
        deduplicated = {entry['date']: entry for entry in historic}
        deduplicated[pmi['date']] = {'date': pmi['date'], 'value': pmi['value']}
        result['series']['pmi'] = {
            'id': 'ISM-PMI', 'source': 'ISM official', 'frequency': 'monthly',
            'values': sorted(deduplicated.values(), key=lambda item: item['date']),
            'status': 'ok', 'url': pmi['url'],
        }
        success += 1
        print(f'OK pmi: {pmi}', flush=True)
    except Exception as exc:
        result['errors']['pmi'] = str(exc)
        if 'pmi' in prior:
            result['series']['pmi'] = {**prior['pmi'], 'status': 'stale'}
        print(f'ERROR pmi: {exc}', flush=True)

    # Evitar actualizar la fecha del archivo cuando no se ha descargado nada.
    if success == 0:
        print('ERROR: Ninguna fuente ha respondido. Se conservan los datos anteriores.', flush=True)
        raise SystemExit(1)

    DEST.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')),
                    encoding='utf-8')
    print(f'Wrote {DEST.name}: {success}/8 fuentes actualizadas, '
          f'{len(result["errors"])} errores', flush=True)


if __name__ == '__main__':
    main()
