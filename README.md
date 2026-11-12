# Radar del ciclo económico — EE. UU.

Dashboard web de seis fases basado en la taxonomía de la captura aportada. **No es una implementación oficial ni validada del modelo DRACO**.

## Publicar en GitHub Pages (sin instalar programas)

1. Crea un repositorio público en GitHub llamado, por ejemplo, `ciclo-macro` con la rama `main`.
2. Sube `index.html`, `data.json`, `update_data.py`, `requirements.txt` y `README.md` a la raíz. El fichero `.github/workflows/update.yml` debe conservar **exactamente** esa ruta oculta; créalo con **Add file → Create new file** y pega el contenido del ZIP si no puedes subir la carpeta oculta.
3. En **Settings → Pages → Build and deployment → Source** selecciona **GitHub Actions** (no "Deploy from a branch" en esta versión).
4. En **Settings → Actions → General → Workflow permissions** selecciona **Read and write permissions**, y guarda los cambios; el workflow necesita escribir el nuevo `data.json`.
5. En **Actions → Actualizar indicadores macro y publicar web → Run workflow → Run workflow**, ejecuta la primera actualización. Alternativamente, una confirmación de archivos en `main` lanzará el workflow.
6. Una vez finalizado correctamente, en **Settings → Pages → Visit site** abre tu dashboard; la dirección habitual es `https://USUARIO.github.io/ciclo-macro/`.

El workflow ejecuta el actualizador y publica el sitio en la misma ejecución, de forma que los cambios de datos se ven en GitHub Pages. Se ejecuta automáticamente de lunes a viernes a las **14:17 UTC**, con el retraso posible propio de GitHub Actions.

**Importante:** el botón **Actualizar** del dashboard solo vuelve a leer `data.json` en la web; no lanza el workflow. Las series reflejan la última observación publicada de cada fuente, no un flujo en tiempo real. Si alguna fuente falla, consulta el log del workflow y las advertencias del dashboard.

## Probar localmente

```bash
pip install -r requirements.txt
python update_data.py
python -m http.server 8000
```

Abre http://localhost:8000 . No abras el HTML mediante `file://`: el navegador bloqueará `fetch('data.json')`.

## Fuentes

| Variable | Origen | ID | Frecuencia |
|---|---|---|---|
| Core PCE (índice; dashboard calcula variación interanual) | BEA/FRED | PCEPILFE | mensual |
| Tipo real 10 años | Treasury/FRED | DFII10 | diaria |
| Spread CCC, puntos porcentuales | ICE BofA/FRED | BAMLH0A3HYC | diaria |
| PMI Manufacturero | ISM página oficial | extracción HTML | mensual |
| Desempleo | BLS/FRED | UNRATE | mensual |
| Solicitudes iniciales de desempleo | DOL/FRED | ICSA | semanal |
| Producción industrial | Fed/FRED | INDPRO | mensual |
| Curva 10y-2y | Treasury/FRED | T10Y2Y | diaria |

Para el spread, se convierten puntos porcentuales a puntos básicos multiplicando por 100. FRED y ISM ofrecen datos publicados, no cotización tick a tick. La serie de ICE BofA puede tener restricciones de acceso o uso. La extracción de ISM depende de la estructura de su sitio, que podría cambiar. Cuando falla una descarga se mantiene la observación anterior pero se etiqueta `Fuente falló` y el algoritmo excluye esa serie del diagnóstico. La serie ISM inicial verificada corresponde a octubre de 2026.

## Reglas de clasificación v1.0

El modelo necesita **cuatro datos vigentes**: PMI (no más de 70 días), Core PCE calculado desde 13 observaciones mensuales (no más de 95 días), tipo real TIPS 10 años y spread CCC (no más de 12 días cada uno). Las demás series aportan confirmación opcional.

Se aplica por orden:

- Recesión: PMI < 46 y spread CCC > 900 pb o paro aumenta más de 0,4 pp en tres meses.
- Recuperación: PMI < 50 pero mejora > 0,6 puntos en dos meses, y CCC < 1.100 pb.
- Desaceleración: PMI < 50; o PMI cae > 2,5 puntos en dos meses con CCC > 800 pb o paro al alza > 0,2 pp.
- Reflación avanzada: PMI >= 50, Core PCE > 2,7%, con TIPS > 2%, CCC > 1.000 pb o Core PCE > 3,2%.
- Goldilocks: PMI >= 50, Core PCE <= 2,7%, CCC < 900 pb y TIPS < 2,4%.
- En los demás casos: expansión.

**Las reglas son hipótesis iniciales y no están calibradas ni validadas con backtesting.** La ausencia de señales de caída no es una prueba de expansión: los umbrales se deben mejorar con métodos de difusión y señales de empleo, crédito y actividad. Evita emplear por sí solas estas fases para decidir inversiones.

## Datos de ejemplo

`data.json` se entrega inicialmente con PMI oficial oct-2026 (55,5) y otros valores de la captura identificados como referencia, no como verificados. Antes de calcular una fase actual, ejecuta el updater para sustituir las referencias por observaciones reales. El workflow no requiere una clave FRED porque utiliza las descargas públicas CSV; si el servidor restringe las peticiones, indicará el error de esa fuente.
