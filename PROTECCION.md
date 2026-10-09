# Idioma, tamaño y blindaje de la distribución

Resumen de las capacidades añadidas y cómo usarlas.

## 1. Idioma (español / inglés)

- La interfaz está internacionalizada. Todas las cadenas viven en
  `app/superlimpio/i18n.py` (`clave -> {"en", "es"}`).
- **Idioma inicial:** la primera vez se detecta del sistema (Windows en español →
  español; en otro caso → inglés). La elección se guarda y se respeta después.
- **Selector:** abajo en la barra lateral. Al cambiarlo, la ventana se reconstruye
  entera en el nuevo idioma (se pierde un análisis en curso, nada más).
- Los números y fechas se formatean según el idioma (1.5 GB / 1,5 GB; 2026-10-09 /
  09/10/2026).

Para añadir un idioma: agrega su código en `i18n.LANGUAGES` y una entrada por clave
en `CATALOG`.

## 2. Tamaño de la interfaz y cajas redimensionables

- **Zoom global:** controles `A−` / `A+` en la barra lateral. Reescala fuentes y
  medidas de toda la interfaz. Se recuerda entre sesiones.
- **Divisores arrastrables:** en «Limpieza» (lista de categorías ↔ resultados) y en
  «Analizador de disco» (tablas ↔ panel de detalles) puedes arrastrar el borde para
  agrandar o reducir cada caja. La posición se recuerda por sección.
- Las descripciones que antes se cortaban ahora ajustan su ancho al de su caja.

Las preferencias se guardan en `superlimpio.config.json` (junto a la app, o en
`%LOCALAPPDATA%\SuperLimpio` si la carpeta de la app es de solo lectura). Ese archivo
**no** forma parte de la distribución firmada.

## 3. Progreso y aviso al terminar una limpieza

- Todo borrado (Papelera o definitivo, en «Analizador de disco» y en «Librerías de
  desarrollo») muestra ahora un indicador de operación en curso y deshabilita los
  botones mientras se ejecuta.
- Al terminar, la pantalla se actualiza de inmediato: se quitan los elementos
  borrados, se recalculan los tamaños de las carpetas padre y la barra de estado
  indica cuánto se liberó y cuántos elementos se quitaron.

## 4. Blindaje contra ingeniería inversa y manipulación

Tres capas, de mayor a menor efecto, **sin dependencias de pago**:

### a) Manifiesto de integridad firmado (clave) + autochequeo

1. Genera tu par de claves Ed25519 (una sola vez). La privada se guarda **fuera** del
   repositorio; la pública se incrusta en `app/superlimpio/integrity.py`:

   ```
   runtime\python\python.exe tools\firmar.py --generar-claves
   ```

2. Crea la distribución blindada (bytecode sin fuente + firma):

   ```
   runtime\python\python.exe tools\crear_zip.py --protegido
   ```

3. (Opcional) Verifica una copia como lo hace la app al arrancar:

   ```
   runtime\python\python.exe tools\firmar.py --verificar <carpeta_descomprimida>\SuperLimpio
   ```

Al arrancar, la app comprueba que la firma del manifiesto es válida para la clave
pública incrustada y que cada archivo conserva su hash. Si alguien **modifica, añade o
sustituye** un archivo de una copia publicada, la firma deja de cuadrar y la app se
niega a continuar. La clave privada solo la tienes tú, así que nadie puede volver a
firmar una versión manipulada en tu nombre.

### b) Bytecode sin fuente

`--protegido` compila el paquete `superlimpio` a `.pyc` y **borra los `.py`**: la
distribución no lleva el código fuente legible (solo se conserva `app/main.py`, un
arranque trivial que necesita el lanzador). Dificulta la lectura directa, aunque el
bytecode sigue siendo descompilable.

### c) Ofuscación con PyArmor (opcional)

Para subir mucho más el listón de la descompilación:

```
pip install pyarmor            (en el Python del runtime)
runtime\python\python.exe tools\crear_zip.py --protegido --pyarmor
```

Si PyArmor no está instalado, la build continúa sin ofuscar y lo avisa.

### Límite honesto

Cualquier protección que se ejecute en el equipo del usuario puede, en teoría,
desactivarse editando el verificador y volviendo a firmar con otra clave. Estas capas
**suben el listón** e **impiden distribuir una copia manipulada que siga validándose**
con tu clave, pero no convierten a Python en algo imposible de revertir. La firma
Authenticode del propio `SuperLimpio.exe` (requiere un certificado de pago) es el
complemento natural y queda fuera de este script.
