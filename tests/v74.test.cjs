'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = filename => fs.readFileSync(path.join(root, filename), 'utf8');

function classifier(filename, name) {
  const window = {};
  vm.runInNewContext(read(filename), {window, Date});
  assert.equal(typeof window[name].classify, 'function');
  return window[name];
}

test('V7.4 clasificador conserva la lógica original de fases V6', () => {
  const v6 = classifier('clasificador-v6.js','MacroV6');
  const v74 = classifier('clasificador-v74.js','MacroV74');
  const cases = [
    {v:{core:3,tips:2,credit:3.5,ind_yoy:-4,ind_3m:-2,unempd:0.6},phase:5},
    {v:{core:3,tips:2,credit:2.6,ind_yoy:-1,ind_3m:-1,unempd:0.1},phase:4},
    {v:{core:3.3,tips:2.5,credit:2,ind_yoy:2,ind_3m:1,unempd:0},phase:2},
    {v:{core:2,tips:1,credit:1.8,ind_yoy:2.4,ind_3m:0,unempd:0.2},phase:3},
    {v:{core:2.8,tips:1,credit:2.7,ind_yoy:1,ind_3m:1,unempd:0},phase:0},
    {v:{core:3,tips:1,credit:2.2,ind_yoy:2.1,ind_3m:0.3,unempd:0.1},phase:1},
  ];
  for (const {v,phase} of cases) {
    assert.equal(v74.classify(v), phase);
    assert.equal(v6.classify(v), phase);
  }
  assert.equal(v74.classify({core:null,tips:null,credit:null,ind_yoy:null,ind_3m:null,unempd:null}),null);
});

test('V7.4 usa pesos del backtest, seis fases y suma 100%', () => {
  const text = read('asignacion-v74.html');
  const weights = text.match(/const RAW_WEIGHTS=(\[[^\n]+\]);/);
  assert.ok(weights, 'RAW_WEIGHTS debe estar integrado en la página de asignación');
  const raw = JSON.parse(weights[1]);
  const expected = [
    {SPY:25,IWO:20,IWN:15,XLI:15,XLF:10,QQQ:5,GLD:10},
    {SHY:5,XLB:13.6,XLE:28.5,XLI:12.8,XLU:13.2,XLV:13.5,XLY:13.4},
    {SHY:5,XLB:11.4,XLE:28.5,XLF:19.1,XLP:13.7,XLU:11.7,XLV:10.6},
    {SPY:11.6,QQQ:17.1,TLT:15.8,SHY:5,XLK:21.3,XLU:14.5,XLV:14.7},
    {QQQ:17.8,GLD:12,SHY:14.5,XLK:18.1,XLP:12.2,XLC:25.5},
    {QQQ:18.4,GLD:14.5,SHY:5,XLB:16.4,XLI:12.1,XLK:18,XLY:15.7}
  ];
  assert.equal(raw.length, 6);
  for (let i=0; i<6; i++) {
    assert.deepEqual(raw[i], expected[i], 'Pesos incorrectos en fase ' + i);
    const sum = Object.values(raw[i]).reduce((a,b)=>a+b,0);
    const normalized = Object.fromEntries(Object.entries(raw[i]).map(([k,v])=>[k,100*v/sum]));
    assert.ok(Math.abs(Object.values(normalized).reduce((a,b)=>a+b,0)-100)<1e-10);
  }
  assert.match(text,/XLC:'Servicios de comunicación'/);
  assert.match(text,/XLY:'Consumo discrecional'/);
  assert.match(text,/XLU:'Utilities'/);
});

test('Radar y asignación apuntan a V7.4, sin alterar adelantados', () => {
  const radar=read('index.html'), allocation=read('asignacion-v74.html');
  for (const html of [radar,allocation]) {
    assert.match(html,/clasificador-v74\.js/);
    assert.match(html,/MacroV74/);
  }
  assert.match(radar,/asignacion-v74\.html/);
  assert.match(allocation,/carterainversion_v6_posiciones_v1/);
  assert.doesNotMatch(radar,/MacroV6/);
});
