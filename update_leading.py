#!/usr/bin/env python3
"""Módulo INDEPENDIENTE: solo escribe leading_data.json; no modifica data.json."""
from datetime import datetime, timezone
from pathlib import Path
import json, os, requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'leading_data.json'
KEY = os.environ.get('FRED_API_KEY','').strip()
# Señales: increase=mejora cuando aumenta; decrease=mejora cuando disminuye.
SERIES = {
 'permit': ('PERMIT','Permisos de construcción','monthly','increase',90),
 'claims': ('ICSA','Solicitudes iniciales de desempleo','weekly','decrease',21),
 'anfci': ('ANFCI','Condiciones financieras ajustadas','weekly','decrease',21),
 'baa': ('BAA10YM','Spread crédito Baa–Treasury','monthly','decrease',90),
 'hours': ('AWHMAN','Horas semanales manufactura','monthly','increase',90),
 'curve': ('T10Y3M','Curva Treasury 10 años–3 meses','daily','context',12),
}

def get_series(sid):
    if not KEY:
        raise RuntimeError('Falta FRED_API_KEY en GitHub Actions')
    response = requests.get('https://api.stlouisfed.org/fred/series/observations',
        params={'series_id':sid,'api_key':KEY,'file_type':'json','observation_start':'2018-01-01'},
        headers={'User-Agent':'MacroLeadingRadar/1.0 (personal macroeconomic research)'},
        timeout=(8,25))
    response.raise_for_status()
    payload=response.json()
    if payload.get('error_message'):
        raise RuntimeError(payload['error_message'])
    vals=[]
    for x in payload.get('observations',[]):
        try: vals.append({'date':x['date'],'value':float(x['value'])})
        except (ValueError,KeyError,TypeError): pass
    if len(vals)<4:
        raise RuntimeError('No hay suficientes observaciones')
    return vals[-600:]

def main():
    old={}
    if OUT.exists():
        try: old=json.loads(OUT.read_text(encoding='utf-8')).get('series',{})
        except (OSError,ValueError): pass
    doc={'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'version':'leading-1.0','series':{},'errors':{},
         'description':'Indicadores adelantados independientes del clasificador de 6 fases; no es un predictor calibrado.'}
    for key,(sid,name,frequency,direction,maxage) in SERIES.items():
        try:
            values=get_series(sid)
            doc['series'][key]={'id':sid,'name':name,'frequency':frequency,
                'direction':direction,'max_age_days':maxage,'values':values,
                'status':'ok','url':f'https://fred.stlouisfed.org/series/{sid}'}
            print(f'OK {sid}: {values[-1]}',flush=True)
        except Exception as exc:
            doc['errors'][key]=str(exc)
            if key in old:
                doc['series'][key]={**old[key],'status':'stale'}
            print(f'ERROR {sid}: {exc}',flush=True)
    OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Escrito leading_data.json',flush=True)

if __name__=='__main__':
    main()
