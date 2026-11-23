# Sistema V7.4 — Radar macro y asignación sectorial

**Versión propuesta:** V7.4. **Fases:** seis regímenes de EE. UU.; reclasificación mensual al cierre del mes completo. **Datos:** FRED, con retrasos de disponibilidad aproximados y datos revisados, **no** vintages ALFRED punto-en-tiempo.

## Navegación
- `index.html`: radar macro V7.4; consulta las condiciones del régimen y sus indicadores.
- `asignacion-v74.html`: asignaciones de ETF V7.4 por régimen, calculadora de capital y rebalanceo teórico; importa automáticamente las posiciones del navegador guardadas por la antigua V6.
- `adelantados.html`: indicadores adelantados **independientes**; no intervienen en las fases V7.4.
- `asignacion-v6.html` / `clasificador-v6.js`: versión legada preservada para comparación.
- `clasificador-v74.js`: implementación versionada de las reglas del clasificador macro proxy; **mismas reglas y retrasos que la clasificación V6 proxy**. La diferencia de V7.4 consiste en la **asignación de ETF por fase**.

## Qué usa realmente el clasificador de fases
Las series utilizadas por el algoritmo son: Core PCE (variación interanual del índice `PCEPILFE`), producción industrial `INDPRO` (interanual y en tres meses), desempleo `UNRATE` (variación a tres meses), diferencial Baa–Treasury `BAA10YM` y tipo real Treasury 10 años `DFII10`. El PMI de ISM y el spread CCC se muestran **solo como contexto**, no son inputs de `classify()`.

Retardos aproximados aplicados a observaciones: PCE e industrial +2 meses, desempleo y Baa +1 mes, TIPS +5 días. No equivalen a fechas reales de publicación; la retrolectura con datos revisados puede diferir de la información disponible en cada fecha histórica.

Las fases se prueban en este orden:
1. **F5 Recesión:** producción industrial interanual < −3 % y (paro sube > 0,5 pp en tres meses o Baa > 3 pp).
2. **F4 Desaceleración:** industrial interanual < 0 %; o paro sube > 0,25 pp e impulso industrial negativo; o Baa > 2,5 pp e impulso industrial negativo. Excepción: si impulso industrial > 0, paro ≤ 0,2 pp y Baa < 3 pp se clasifica F0.
3. **F2 Reflación avanzada:** Core PCE > 2,7 % y (TIPS > 2 % o Baa > 3 pp o Core PCE > 3,2 %).
4. **F3 Goldilocks:** Core PCE ≤ 2,7 %, Baa < 2,5 pp y TIPS < 2,4 %.
5. **F0 Recuperación:** impulso industrial > 0, paro ≤ 0,1 pp y crecimiento industrial interanual < 2 %.
6. **F1 Expansión:** caso residual.

Sin seis inputs válidos no hay fase; el sitio debe mostrar “sin diagnóstico” en vez de inventar una fase. La fase F5 es una etiqueta del modelo, no un comunicado del NBER.

## Asignación V7.4
Para **F0** se preservan los pesos de **V6.2**; para **F1–F5** se usan los pesos del backtest **V7**. Los pesos originales en porcentaje se **normalizan por fila a 100 %**; véase `RAW_WEIGHTS` en `asignacion-v74.html`.

| Fase | Exposición |
|---|---|
| F0 | SPY 25, IWO 20, IWN 15, XLI 15, XLF 10, QQQ 5, GLD 10 |
| F1 | SHY 5, XLB 13.6, XLE 28.5, XLI 12.8, XLU 13.2, XLV 13.5, XLY 13.4 |
| F2 | SHY 5, XLB 11.4, XLE 28.5, XLF 19.1, XLP 13.7, XLU 11.7, XLV 10.6 |
| F3 | SPY 11.6, QQQ 17.1, TLT 15.8, SHY 5, XLK 21.3, XLU 14.5, XLV 14.7 |
| F4 | QQQ 17.8, GLD 12, SHY 14.5, XLK 18.1, XLP 12.2, XLC 25.5 |
| F5 | QQQ 18.4, GLD 14.5, SHY 5, XLB 16.4, XLI 12.1, XLK 18, XLY 15.7 |

Atención: el histórico V7.4 hasta junio de 2018 incluye **XLK como proxy para XLC**, porque XLC todavía no existía. El dashboard actual usa XLC real; **no reemplazarlo por XLK en la operativa contemporánea**.

## Histórico y límites
El archivo maestro del proyecto registra el backtest mensual **abril de 2007 – octubre de 2026** (235 meses) con CAGR V7.4 de **17,93 %**, Sharpe **1,266** y máximo drawdown **−35,27 %**; SPY muestra CAGR **10,91 %**. Estos son resultados **simulados, no auditados**: sujetos a revisiones macro, proxies históricos, riesgo de sobreajuste y costes fiscales y de ejecución no representados íntegramente. **El radar en producción no prueba automáticamente la paridad de las 235 señales históricas**; se debe completar una auditoría independiente de datos originales de publicación antes de atribuirle esos resultados como track record real.

## Automatización
- `.github/workflows/update.yml`: lunes a viernes, refresca `data.json` usando el secreto `FRED_API_KEY` y publica GitHub Pages.
- `.github/workflows/leading.yml`: actualiza `leading_data.json` y publica la página adelantada por separado.
- `tests/v74.test.cjs`: regresión sin dependencias externas. Ejecutar con `node --test tests/v74.test.cjs`.

La web es informativa: no compra ni vende activos; los importes de la calculadora son orientativos, sin divisas, costes, impuestos ni límites operativos de UCITS.

## Recuperación de V6
Versión congelada en la rama `backup/v6-2026-11-23`. Para volver a ella usar una reversión de la rama principal o desplegar la rama de respaldo; no borrar sin comprobar la publicación y la continuidad de los datos.
