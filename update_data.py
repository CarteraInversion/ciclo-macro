#!/usr/bin/env python3
"""Generates data.json from public official series. No API key required.
Requires: requests beautifulsoup4 (see requirements.txt).
When a source fails, retains previously dated data and marks its status.
"""
import csv, io, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'data.json'
HEADERS={'User-Agent':'MacroCycleDashboard/1.0 (public series downloader)'}
SERIES={
 'core_pce_index':('PCEPILFE','BEA/FRED','monthly'),
 'tips10':('DFII10','Treasury/FRED','daily'),
 'ccc_spread':('BAMLH0A3HYC','ICE BofA/FRED','daily'),
 'unemployment':('UNRATE','BLS/FRED','monthly'),
 'claims':('ICSA','DOL/FRED','weekly'),
 'industrial':('INDPRO','Federal Reserve/FRED','monthly'),
 'yield_curve':('T10Y2Y','Treasury/FRED','daily'),
}

def download_series(series_id):
    urls=[f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote(series_id)}',
          f'https://fred.stlouisfed.org/graph/fredgraph.csv?cosd=2018-01-01&id={quote(series_id)}']
    last_exc=None
    for url in urls:
        try:
            r=requests.get(url,headers=HEADERS,timeout=25);r.raise_for_status()
            parsed=list(csv.DictReader(io.StringIO(r.text)))
            out=[]
            for row in parsed:
                ds=row.get('DATE') or row.get('observation_date'); s=row.get(series_id)
                if ds and s and s!='.':
                    try: out.append({'date':ds,'value':float(s)})
                    except ValueError: continue
            if len(out)>4: return out[-1600:]
            raise RuntimeError('Serie vacía o CSV inválido')
        except Exception as ex: last_exc=ex;time.sleep(1)
    raise RuntimeError(str(last_exc))

def ism_report():
    # Official page currently has a stable /pmi/<month>/ slug, but may change.
    now=datetime.now(timezone.utc)
    pages=['https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/'+m+'/'
           for m in ['november','october','september','august','july','june','may','april','march','february','january','december']]
    candidates=[]
    for url in pages:
        try:
            r=requests.get(url,headers=HEADERS,timeout=15);r.raise_for_status()
            soup=BeautifulSoup(r.text,'html.parser')
            text=soup.get_text(' ',strip=True)
            meta=re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b',text,re.I)
            if not meta: continue
            month=datetime.strptime(meta.group(1),'%B').month;year=int(meta.group(2))
            if (year,month)>(now.year,now.month): continue
            # Prefer 'Manufacturing PMI® registered 55.5 percent' phrase; alternate headline
            value=None
            pats=[r'Manufacturing PMI[^\n]{0,55}?registered\s+(\d{2}\.\d)\s+percent',
                  r'Manufacturing PMI[^\n]{0,22}?at\s+(\d{2}\.\d)\s*%',
                  r'Manufacturing PMI[^\n]{0,25}?(\d{2}\.\d)\s*%']
            for pat in pats:
                m=re.search(pat,text,re.I)
                if m and 25<float(m.group(1))<75: value=float(m.group(1));break
            if value is not None:
                candidates.append({'date':f'{year}-{month:02d}-01','value':value,'url':url})
        except Exception: pass
    if not candidates:raise RuntimeError('No se pudo extraer el PMI de ISM; verificar página')
    return max(candidates,key=lambda x:x['date'])

def main():
    old=json.loads(DEST.read_text(encoding='utf8')) if DEST.exists() else {'series':{}}
    data={'updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
          'series':{},'errors':{},'method_version':'1.0'}
    for key,(sid,agency,freq) in SERIES.items():
        try:
            obs=download_series(sid)
            data['series'][key]={'id':sid,'source':agency,'frequency':freq,'values':obs,'status':'ok',
                                 'url':f'https://fred.stlouisfed.org/series/{sid}'}
            print('OK',key,obs[-1])
        except Exception as e:
            data['errors'][key]=str(e)
            if key in old['series']:
                data['series'][key]={**old['series'][key],'status':'stale'}
            print('ERROR',key,e)
    try:
        ism=ism_report()
        prior=old['series'].get('pmi',{}).get('values',[])
        values={x['date']:x for x in prior}
        values[ism['date']]={'date':ism['date'],'value':ism['value']}
        values=sorted(values.values(),key=lambda x:x['date'])
        data['series']['pmi']={'id':'ISM-PMI','source':'ISM official','frequency':'monthly','values':values,
                                'status':'ok','url':ism['url']}
        print('OK PMI',ism)
    except Exception as e:
        data['errors']['pmi']=str(e)
        if 'pmi' in old['series']:data['series']['pmi']={**old['series']['pmi'],'status':'stale'}
        print('ERROR PMI',e)
    # The ICE BofA series is quoted in percentage points by FRED, e.g. 12.83 pp = 1283 bp.
    DEST.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    print('Wrote',DEST)

if __name__=='__main__':main()
