"""Recorrido automático por la interfaz real, en cualquier sistema.

    python tests/smoke_gui.py [carpeta_para_capturas]

Abre la aplicación, visita todas las secciones, selecciona filas, analiza una carpeta
de prueba, hace un análisis corto de procesos y cambia el tamaño. NO pulsa nada que
borre, cierre o ejecute algo: solo comprueba que la interfaz se construye y responde
sin errores. Sale con código 1 si alguna parte falla.

En Linux sin escritorio se ejecuta bajo un servidor gráfico virtual:
    xvfb-run -a python3 tests/smoke_gui.py capturas
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
SHOTS = sys.argv[1] if len(sys.argv) > 1 else ""

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

from superlimpio import config, i18n, plat  # noqa: E402

i18n.set_language("es")
from superlimpio.ui.app import App  # noqa: E402

errors: list[str] = []
start_scale = config.get_scale()
config.set_scale(1.0)
app = App()
root = app.root
root.report_callback_exception = lambda e, v, tb: errors.append("".join(traceback.format_exception(e, v, tb)))


def pump(seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.02)


def shot(name: str) -> None:
    """Captura de la pantalla (solo en Linux, con ImageMagick): sirve para revisar el aspecto."""
    if not SHOTS or not shutil.which("import"):
        return
    os.makedirs(SHOTS, exist_ok=True)
    pump(0.3)
    subprocess.run(["import", "-window", "root", os.path.join(SHOTS, name + ".png")], check=False, timeout=30)


def check(label: str, condition: bool) -> None:
    print(("ok   " if condition else "FALLO") + " " + label)
    if not condition:
        errors.append(label)


try:
    pump(1.5)
    print("plataforma:", plat.NAME, "| capacidades:", plat.capabilities())
    print("discos:", plat.list_drives())
    shot("01_resumen")

    for key in ("disk", "programs", "memory", "optimizer", "startup", "cleaner", "devdeps", "tools", "log"):
        before = len(errors)
        app.show(key)
        pump(1.5)
        check(f"sección {key}", len(errors) == before and app.current == key)
        shot(f"02_{key}")

    # ---- Programas: seleccionar filas (el fallo de la beta) y ver el comando de desinstalación
    app.show("programs")
    pump(3.0)
    page = app.page("programs")
    rows = page.tree.get_children()
    print("programas:", len(rows))
    for iid in rows[:5]:
        page.tree.selection_set(iid)
        pump(0.1)
    if rows:
        print("  detalle:", page.detail.cget("text").replace("\n", " | ")[:160])
    shot("03_programas")

    # ---- Memoria: importancia de los procesos y panel de detalle
    app.show("memory")
    pump(2.5)
    mem = app.page("memory")
    levels: dict[str, int] = {}
    for row in mem.table.visible.values():
        label = mem._assess(row).label
        levels[label] = levels.get(label, 0) + 1
    print("procesos por importancia:", levels)
    check("hay procesos", sum(levels.values()) > 3)
    own = next((i for i, r in mem.table.visible.items() if os.getpid() in r.pids), None)
    check("la propia aplicación se reconoce", own is not None)
    if own:
        mem.tree.selection_set(own)
        pump(0.3)
        print("  propio:", mem.det_title.cget("text"), "|", mem.det_text.cget("text"))
    shot("04_memoria")

    # ---- Disco: una carpeta de prueba y la importancia de una ruta del sistema
    work = tempfile.mkdtemp(prefix="superlimpio_smoke_")
    for i in range(6):
        os.makedirs(os.path.join(work, f"carpeta{i}"), exist_ok=True)
        with open(os.path.join(work, f"carpeta{i}", "datos.bin"), "wb") as fh:
            fh.write(b"x" * (50_000 * (i + 1)))
    app.show("disk")
    disk = app.page("disk")
    disk.start_scan(work)
    for _ in range(60):
        pump(0.25)
        if disk.cancel_ev is None:
            break
    check("análisis de disco", disk.result is not None and disk.result.root.files == 6)
    top = disk.tree.get_children()
    if top:
        kids = disk.tree.get_children(top[0])
        check("el árbol se despliega", len(kids) == 6)
        disk.tree.selection_set(kids[0])
        pump(0.3)
        print("  riesgo:", disk.sel_risk.cget("text"))
    disk.nb.select(1)
    pump(0.3)
    disk.nb.select(2)
    pump(0.3)
    check("la pestaña «por tipo» no deja nada seleccionado", disk._selected() == [])
    disk.nb.select(0)
    shot("05_disco")
    shutil.rmtree(work, ignore_errors=True)

    from superlimpio import criticality
    system_path = os.environ.get("WINDIR", "/usr/bin") if plat.IS_WINDOWS else "/usr/bin"
    found = criticality.assess_path(system_path)
    print("  ruta del sistema:", system_path, "->", found.label, "|", found.text)
    check("una carpeta del sistema se marca como dañina", found.system and found.level >= criticality.Level.IMPORTANT)

    # ---- Optimizar: análisis de 10 s y pestaña del Modo eficiente
    app.show("optimizer")
    opt = app.page("optimizer")
    opt.analyze()
    pump(13.0)
    check("análisis de procesos", opt._report is not None and len(opt._report.programs) > 3)
    if opt._report:
        for finding in opt._report.findings:
            print("  hallazgo:", finding.severity, finding.title)
    shot("06_optimizar")
    opt.nb.select(opt.tab_eff)
    pump(2.5)
    check("plan del Modo eficiente", opt.plan is not None)
    if opt.plan:
        print("  candidatos:", len(opt.plan.candidates), "| no se tocan:", opt.plan.kept)
    shot("07_modo_eficiente")

    # ---- Limpieza: solo el análisis (no borra nada)
    app.show("cleaner")
    cleaner_page = app.page("cleaner")
    cleaner_page.analyze()
    for _ in range(120):
        pump(0.25)
        if "disabled" not in cleaner_page.an_btn.state():
            break
    check("análisis de limpieza", len(cleaner_page.estimates) > 0)
    print("  categorías:", {k: v.size for k, v in cleaner_page.estimates.items() if v.size})
    shot("08_limpieza")

    # ---- Herramientas e Inicio: que se listen
    app.show("startup")
    pump(1.5)
    print("arranque:", len(app.page("startup").table.rows), "entradas")
    shot("09_inicio")
    app.show("tools")
    pump(0.5)
    shot("10_herramientas")

    # ---- Tamaño de la interfaz y vuelta al 100 %
    app.show("summary")
    for _ in range(6):
        app._set_zoom(app.zoom + config.SCALE_STEP)
        pump(0.2)
    check("zoom máximo", abs(app.zoom - config.MAX_SCALE) < 1e-6)
    shot("11_zoom_maximo")
    root.event_generate("<Control-Key-0>")
    pump(0.5)
    check("Ctrl 0 vuelve al 100 %", abs(app.zoom - 1.0) < 1e-6)

    # ---- Diálogo de confirmación: se abre, cabe y se cancela
    from superlimpio.safety import Risk
    from superlimpio.ui import dialogs

    def cancel_dialog() -> None:
        for w in root.winfo_children():
            if isinstance(w, dialogs.ConfirmDialog):
                w._cancel()

    root.after(600, cancel_dialog)
    answer = dialogs.confirm(root, "Prueba", "Mensaje", "\n".join(f"línea {i}" for i in range(20)), risk=Risk.CRITICO)
    check("el diálogo de confirmación se cancela", answer is False)
finally:
    config.set_scale(start_scale)
    try:
        app._shutdown()
    except Exception:  # noqa: BLE001
        pass

print("ERRORES:", len(errors))
for e in errors:
    print(e)
sys.exit(1 if errors else 0)
