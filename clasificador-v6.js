/* Modelo proxy V6: traducción fiel de classify_proxy() e inputs_at() del notebook V2.
   No es DRACO original ni un modelo punto-en-tiempo ALFRED.
   Las fases son mensuales; ver decisionDate y fechas efectivas abajo. */
(function(g){
'use strict';
const MONTHLY=['core_pce_index','industrial','unemployment','credit_baa'];
const lag={core_pce_index:2,industrial:2,unemployment:1,credit_baa:1};
function monthEndOf(date){const [y,m]=date.slice(0,7).split('-').map(Number);return new Date(Date.UTC(y,m,0));}
function endPlusMonths(date,n){const [y,m]=date.slice(0,7).split('-').map(Number);return new Date(Date.UTC(y,m+n,0));}
function pad(x){return String(x).padStart(2,'0');}
function iso(d){return d.toISOString().slice(0,10);}
function completedMonthEnd(asOf=new Date()){
 return new Date(Date.UTC(asOf.getUTCFullYear(),asOf.getUTCMonth(),0));
}
function accepted(s){return s&&['ok','confirmed'].includes(s.status)&&Array.isArray(s.values);}
function observed(data,key,cutoff){
 const s=data?.series?.[key];
 if(!accepted(s))return [];
 const delay=lag[key]||0;
 const raw=s.values.filter(x=>Number.isFinite(Number(x.value))&&typeof x.date==='string');
 const result=raw.map(x=>{
  const effective=delay?endPlusMonths(x.date,delay):new Date(Date.parse(x.date+'T00:00:00Z')+5*86400000);
  return {date:x.date,effective,value:Number(x.value)};
 }).filter(x=>x.effective<=cutoff).sort((a,b)=>a.effective-b.effective);
 return result;
}
function last(v){return v.length?v[v.length-1]:null;}
function yoy(v){return v.length>=13?(last(v).value/v[v.length-13].value-1)*100:null;}
function change(v,n){return v.length>n?last(v).value-v[v.length-1-n].value:null;}
function growth(v,n){return v.length>n?(last(v).value/v[v.length-1-n].value-1)*100:null;}
function inputs(data,asOf=new Date()){
 // No usar observaciones publicadas después del cierre mensual estudiado.
 const decisionDate=completedMonthEnd(asOf);
 const pce=observed(data,'core_pce_index',decisionDate);
 const ind=observed(data,'industrial',decisionDate);
 const un=observed(data,'unemployment',decisionDate);
 const credit=observed(data,'credit_baa',decisionDate);
 const tips=observed(data,'tips10',decisionDate);
 const series={pce,ind,un,credit,tips};
 const values={core:yoy(pce),tips:last(tips)?.value??null,credit:last(credit)?.value??null,
  ind_yoy:yoy(ind),ind_3m:growth(ind,3),unempd:change(un,3)};
 const dates={core:last(pce)?.date??null,tips:last(tips)?.date??null,
  credit:last(credit)?.date??null,ind_yoy:last(ind)?.date??null,ind_3m:last(ind)?.date??null,
  unempd:last(un)?.date??null};
 return {values,dates,decisionDate:iso(decisionDate),missing:Object.entries(values).filter(([_,x])=>x===null||!Number.isFinite(x)).map(([k])=>k)};
}
function classify(v){
 const {core,tips,credit,ind_yoy:ind,ind_3m:imp,unempd:du}=v;
 if([core,tips,credit,ind,imp,du].some(x=>x==null||!Number.isFinite(x)))return null;
 if(ind < -3 && (du > .5 || credit > 3.0))return 5;
 if(ind < 0 || (du > .25 && imp < 0) || (credit > 2.5 && imp < 0)){
  if(imp > 0 && du <= .2 && credit < 3.0)return 0;
  return 4;
 }
 if(core > 2.7 && (tips > 2 || credit > 3.0 || core > 3.2))return 2;
 if(core <= 2.7 && credit < 2.5 && tips < 2.4)return 3;
 if(imp > 0 && du <= .1 && ind < 2)return 0;
 return 1;
}
function evaluate(data,asOf=new Date()){
 const i=inputs(data,asOf);
 return {...i,phase:classify(i.values),model:'V6_PROXY_BAA',historicalPointInTime:false};
}
g.MacroV6=Object.freeze({inputs,classify,evaluate,completedMonthEnd});
})(window);
