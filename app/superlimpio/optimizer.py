"""Optimización: análisis exhaustivo de memoria/CPU y «Modo eficiente».

Se inspira en lo que hacen las herramientas actuales, quedándose con lo que es
reversible y transparente:

  * Modo de eficiencia de Windows 11 (Administrador de tareas) y ProBalance de
    Process Lasso: en vez de cerrar, se baja la prioridad del proceso y se activa
    EcoQoS. Es la acción por defecto aquí («ralentizar») y se puede deshacer.
  * «Boost» de Microsoft PC Manager y Razer Cortex: ofrecen cerrar lo que no hace
    falta mientras se juega y restaurarlo después. Aquí cada programa se propone
    por separado y nada se cierra sin que el usuario lo vea y lo confirme.
  * Liberadores de RAM tipo Mem Reduct: recortar el conjunto de trabajo. Se ofrece
    como opción, explicando que no es memoria «gratis».

Lo que Super Limpio NO hace a propósito: detener servicios de Windows, tocar
procesos del sistema, del antivirus o anti-trampas, asignar prioridad «Alta» o
«Tiempo real», ni dejar nada residente: todo dura lo que dure la sesión.

Este módulo solo contiene lógica (sin interfaz), para poder probarla con tests.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum

from . import i18n, winapi
from .safety import PROTECTED_PROCESSES, SENSITIVE_PROCESSES, Risk, check_process_kill, log_action
from .util import fmt_count, fmt_size

MB = 1024 ** 2
GB = 1024 ** 3


# =========================================================================
# Catálogo de programas conocidos
# =========================================================================

# Nunca se ofrecen: seguridad y anti-trampas (cerrarlos desprotege el equipo o
# provoca expulsiones en juegos en línea).
_UNTOUCHABLE = {
    "securityhealthsystray.exe", "smartscreen.exe", "mbam.exe", "mbamservice.exe", "mbamtray.exe",
    "avp.exe", "avpui.exe", "avgsvc.exe", "avgui.exe", "avastsvc.exe", "avastui.exe", "ekrn.exe",
    "egui.exe", "bdagent.exe", "bdservicehost.exe", "vsserv.exe", "mcshield.exe", "mcuicnt.exe",
    "nortonsecurity.exe", "sophosui.exe", "savservice.exe", "wrsa.exe", "psanhost.exe",
    "easyanticheat.exe", "easyanticheat_eos.exe", "beservice.exe", "beservice_x64.exe", "vgc.exe",
    "vgtray.exe", "faceit.exe", "faceitclient.exe",
}
_UNTOUCHABLE_PATHS = ("\\windows defender", "\\microsoft defender")

_CATALOG: dict[str, tuple[str, ...]] = {
    "updater": (
        "googleupdate.exe", "microsoftedgeupdate.exe", "braveupdate.exe", "adobearm.exe", "acrotray.exe",
        "jusched.exe", "jucheck.exe", "ccxprocess.exe", "adobenotificationclient.exe",
        "opera_autoupdate.exe", "ituneshelper.exe", "dropboxupdate.exe", "onedrivestandaloneupdater.exe",
    ),
    "widget": (
        "widgets.exe", "widgetservice.exe", "phoneexperiencehost.exe", "yourphone.exe", "copilot.exe",
        "cortana.exe", "hxtsr.exe", "widgetboard.exe", "microsoftstartfeedprovider.exe",
        "crossdeviceservice.exe",
    ),
    "cloud": (
        "onedrive.exe", "dropbox.exe", "googledrivefs.exe", "iclouddrive.exe", "icloudservices.exe",
        "megasync.exe", "pcloud.exe", "nextcloud.exe", "box.exe", "coresync.exe",
    ),
    "browser": (
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe", "arc.exe",
        "librewolf.exe", "waterfox.exe", "iexplore.exe",
    ),
    "comms": (
        "discord.exe", "discordptb.exe", "discordcanary.exe", "ms-teams.exe", "teams.exe", "slack.exe",
        "zoom.exe", "skype.exe", "telegram.exe", "whatsapp.exe", "whatsapp.root.exe", "signal.exe",
        "ts3client_win64.exe", "teamspeak.exe", "mumble.exe", "element.exe",
    ),
    "media": (
        "spotify.exe", "obs64.exe", "obs32.exe", "streamlabs obs.exe", "vlc.exe", "itunes.exe",
        "applemusic.exe", "foobar2000.exe", "musicbee.exe", "tidal.exe", "audacity.exe",
    ),
    "launcher": (
        "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "battle.net.exe", "eadesktop.exe",
        "origin.exe", "upc.exe", "ubisoftconnect.exe", "galaxyclient.exe", "riotclientservices.exe",
        "riotclientux.exe", "xboxpcapp.exe", "xboxapp.exe", "playnite.desktopapp.exe", "gamebar.exe",
        "gamebarftserver.exe",
    ),
    "gpu": (
        "nvidia share.exe", "nvidia web helper.exe", "nvidia overlay.exe", "nvcontainer.exe",
        "nvdisplay.container.exe", "nvsphelper64.exe", "nvidia geforce experience.exe",
        "radeonsoftware.exe", "amdrsserv.exe", "amdow.exe", "cncmd.exe", "igfxem.exe", "igcc.exe",
        "msiafterburner.exe", "rtss.exe",
    ),
    "peripheral": (
        "lghub.exe", "lghub_agent.exe", "lghub_system_tray.exe", "razer synapse 3.exe",
        "razer synapse.exe", "razerappengine.exe", "razer central.exe", "icue.exe", "steelseriesgg.exe",
        "steelseriesengine.exe", "steelseriessonar.exe", "armourycrate.exe", "streamdeck.exe",
        "voicemeeter.exe", "voicemeeterpro.exe", "voicemeeter8.exe", "nahimicsvc64.exe",
        "rtkauduservice64.exe", "ds4windows.exe", "joytokey.exe", "autohotkey.exe", "autohotkey64.exe",
        "autohotkeyu64.exe", "powertoys.exe",
    ),
    "network": (
        "openvpn-gui.exe", "nordvpn.exe", "protonvpn.client.exe", "wireguard.exe", "expressvpn.exe",
        "mullvad vpn.exe", "tailscale-ipn.exe",
    ),
}
_CATEGORY_OF = {name: cat for cat, names in _CATALOG.items() for name in names}

# Procesos auxiliares que siempre pertenecen al programa que los lanzó, aunque su
# ejecutable esté en otra carpeta (p. ej. la vista web incrustada de Teams o Widgets).
_HELPERS = {"msedgewebview2.exe", "crashpad_handler.exe", "cefsharp.browsersubprocess.exe"}


class Action(str, Enum):
    KEEP = "keep"            # no tocar
    THROTTLE = "throttle"    # modo de eficiencia (reversible)
    CLOSE = "close"          # pedir el cierre / finalizar


# Utilidades de dispositivos que no están en el catálogo: se reconocen por el nombre.
_PERIPHERAL_HINTS = ("tablet", "wacom", "audio", "hotkey", "touchpad", "synaptics", "logi", "razer",
                     "corsair", "steelseries")

# Por debajo de esto, ralentizar un proceso en segundo plano no aporta nada apreciable.
SMALL_PRIVATE = 50 * MB
SMALL_CPU = 1.0


def category_of(name: str) -> str:
    name = name.lower()
    cat = _CATEGORY_OF.get(name)
    if cat:
        return cat
    return "peripheral" if any(h in name for h in _PERIPHERAL_HINTS) else "other"


def suggest(category: str, has_window: bool, profile: str, private: int = SMALL_PRIVATE,
            cpu: float = 0.0) -> tuple[Action, str]:
    """Acción propuesta para un programa y la clave i18n del motivo."""
    if category in ("updater", "widget"):
        return Action.CLOSE, f"opt.reason.{category}"
    if category in ("comms", "media", "peripheral", "gpu", "network"):
        return Action.KEEP, f"opt.reason.{category}"
    if category == "launcher":
        return (Action.KEEP, "opt.reason.launcher_game") if profile == "game" \
            else (Action.THROTTLE, "opt.reason.launcher")
    if category in ("cloud", "browser"):
        return Action.THROTTLE, f"opt.reason.{category}"
    if has_window:
        return Action.KEEP, "opt.reason.open_app"
    if private < SMALL_PRIVATE and cpu < SMALL_CPU:
        return Action.KEEP, "opt.reason.small"
    return Action.THROTTLE, "opt.reason.background"


# =========================================================================
# Modo eficiente: qué se puede proponer y qué no
# =========================================================================

@dataclass
class Candidate:
    key: str
    name: str
    path: str
    members: list = field(default_factory=list)   # RawProcess de todo el árbol del programa
    windows: list = field(default_factory=list)   # WindowInfo
    category: str = "other"
    suggested: Action = Action.KEEP
    action: Action = Action.KEEP
    reason: str = ""
    cpu_pct: float = 0.0

    @property
    def count(self) -> int:
        return len(self.members)

    @property
    def private(self) -> int:
        return sum(m.private for m in self.members)

    @property
    def working_set(self) -> int:
        return sum(m.working_set for m in self.members)

    @property
    def has_window(self) -> bool:
        return bool(self.windows)


@dataclass
class Plan:
    candidates: list[Candidate]
    kept: dict[str, int]              # motivo -> nº de procesos que nunca se tocan
    target_key: str = ""
    target_name: str = ""
    target_members: list = field(default_factory=list)
    profile: str = "game"

    def chosen(self, action: Action) -> list[Candidate]:
        return [c for c in self.candidates if c.action == action]


def program_key(p) -> str:
    return (p.path or p.name).lower()


def _norm(path: str) -> str:
    return path.replace("/", "\\").lower().rstrip("\\")


def _under(path: str, folder: str) -> bool:
    if not path or not folder:
        return False
    path, folder = _norm(path), _norm(folder)
    return path == folder or path.startswith(folder + "\\")


def _install_dir(path: str) -> str:
    """Carpeta del ejecutable; '' si cuelga directamente de la raíz de una unidad (ahí
    «la misma carpeta» sería el disco entero)."""
    folder = _norm(path).rpartition("\\")[0]
    return folder if "\\" in folder else ""


def _valid_parent(p, by_pid: dict):
    """El padre real de un proceso. Si el PID del padre se ha reutilizado (el supuesto
    padre nació después que el hijo), no cuenta."""
    q = by_pid.get(p.ppid)
    if q is None or q.pid == p.pid or q.pid == 0:
        return None
    if q.create_time and p.create_time and q.create_time > p.create_time + 1:
        return None
    return q


def _exclusion(p, by_pid: dict, self_chain: set[int], self_keys: set[str], windir: str) -> str:
    """Motivo por el que un proceso jamás se propone ('' = se puede proponer)."""
    name = p.name.lower()
    if p.pid in (0, 4) or name in PROTECTED_PROCESSES or name in SENSITIVE_PROCESSES:
        return "system"
    if p.pid in self_chain or program_key(p) in self_keys:
        return "self"
    if name in _UNTOUCHABLE or any(h in _norm(p.path) for h in _UNTOUCHABLE_PATHS):
        return "security"
    if not p.accessible:
        return "no_access"
    if not p.path or _under(p.path, windir):
        return "system"
    parent = _valid_parent(p, by_pid)
    if parent is not None and parent.name.lower() == "services.exe":
        return "service"
    return ""


def cpu_percent(prev: list, cur: list, dt: float, ncpu: int) -> dict[int, float]:
    """% de CPU (sobre el total del equipo) de cada proceso entre dos muestras."""
    if dt <= 0:
        return {}
    before = {(p.pid, p.create_time): p.cpu_time for p in prev}
    out = {}
    for p in cur:
        old = before.get((p.pid, p.create_time))
        if old is not None:
            out[p.pid] = max(0.0, min(100.0, (p.cpu_time - old) / (dt * max(1, ncpu)) * 100))
    return out


def window_targets(procs: list, windows: list) -> list[tuple[str, str]]:
    """Programas con ventana a la vista: [(clave, etiqueta)], para elegir el objetivo."""
    by_pid = {p.pid: p for p in procs}
    seen: dict[str, str] = {}
    for w in windows:
        p = by_pid.get(w.pid)
        if p is None or p.pid == os.getpid() or p.name.lower() in SENSITIVE_PROCESSES:
            continue
        key = program_key(p)
        if key not in seen:
            title = w.title if len(w.title) <= 60 else w.title[:57] + "…"
            seen[key] = f"{p.name}  —  {title}"
    return sorted(seen.items(), key=lambda kv: kv[1].lower())


def _exclusions(procs: list, self_pid: int | None = None, windir: str | None = None) -> dict[int, str]:
    """PID -> motivo por el que no se toca ('' = se puede proponer)."""
    self_pid = os.getpid() if self_pid is None else self_pid
    windir = windir if windir is not None else os.environ.get("WINDIR", r"C:\Windows")
    by_pid = {p.pid: p for p in procs}

    # La propia aplicación y quien la lanzó (consola, VS Code...) no se tocan.
    self_chain: set[int] = set()
    cur = by_pid.get(self_pid)
    while cur is not None and cur.pid not in self_chain:
        self_chain.add(cur.pid)
        cur = _valid_parent(cur, by_pid)

    self_keys = {program_key(by_pid[pid]) for pid in self_chain
                 if by_pid[pid].path and not _under(by_pid[pid].path, windir)}

    excluded = {p.pid: _exclusion(p, by_pid, self_chain, self_keys, windir) for p in procs}
    # Un auxiliar (vista web incrustada...) de algo que no se toca tampoco se toca.
    for p in procs:
        if excluded[p.pid] or p.name.lower() not in _HELPERS:
            continue
        host, hops = _valid_parent(p, by_pid), 0
        while host is not None and host.name.lower() in _HELPERS and hops < 16:
            host, hops = _valid_parent(host, by_pid), hops + 1
        if host is not None and excluded[host.pid] and host.name.lower() not in _HELPERS:
            excluded[p.pid] = excluded[host.pid]
    return excluded


def selection_plan(usages: list, procs: list, windows: list, self_pid: int | None = None,
                   windir: str | None = None) -> tuple[Plan, list[str]]:
    """Plan de cierre para los programas elegidos a mano en el resultado del análisis.

    Devuelve (plan, omitidos). Lo protegido (Windows, servicios, seguridad, la propia app,
    lo inaccesible) se aparta con su motivo y nunca entra en el plan, se elija o no."""
    excluded = _exclusions(procs, self_pid, windir)
    by_pid: dict[int, list] = {}
    for w in windows:
        by_pid.setdefault(w.pid, []).append(w)
    plan, blocked = Plan([], {}), []
    for u in usages:
        ok = [m for m in u.members if not excluded.get(m.pid, "system")]
        for why in sorted({excluded.get(m.pid, "system") for m in u.members} - {""}):
            plan.kept[why] = plan.kept.get(why, 0) + 1
            blocked.append(f"{u.name}: {i18n.t(f'opt.kept.{why}')}")
        if ok:
            plan.candidates.append(Candidate(
                u.key, u.name, u.path, members=ok, windows=[w for m in ok for w in by_pid.get(m.pid, [])],
                category=category_of(u.name), suggested=Action.CLOSE, action=Action.CLOSE))
    return plan, blocked


def build_plan(procs: list, windows: list, target_key: str = "", profile: str = "game",
               cpu: dict[int, float] | None = None, self_pid: int | None = None,
               windir: str | None = None) -> Plan:
    """Clasifica los procesos en ejecución y propone una acción para cada programa.

    Un «programa» es todo su árbol de procesos (el navegador y sus pestañas, Steam y sus
    ayudantes...). Se dejan fuera, sin excepción: Windows, servicios, seguridad, la propia
    aplicación, lo que no se puede abrir y todo lo relacionado con el programa objetivo."""
    cpu = cpu or {}
    by_pid = {p.pid: p for p in procs}
    excluded = _exclusions(procs, self_pid, windir)

    # Raíz de cada proceso: sube por los padres mientras sigan siendo del mismo programa.
    roots: dict[int, object] = {}

    def root_of(p, depth: int = 0):
        if p.pid in roots:
            return roots[p.pid]
        roots[p.pid] = p   # corta posibles ciclos
        parent = _valid_parent(p, by_pid)
        if parent is not None and not excluded[parent.pid] and depth < 64:
            r = root_of(parent, depth + 1)
            if p.name.lower() in _HELPERS or _under(p.path, _install_dir(r.path)):
                roots[p.pid] = r
        return roots[p.pid]

    groups: dict[str, Candidate] = {}
    kept: dict[str, int] = {}
    for p in procs:
        why = excluded[p.pid]
        if why:
            kept[why] = kept.get(why, 0) + 1
            continue
        r = root_of(p)
        key = program_key(r)
        g = groups.get(key)
        if g is None:
            g = groups[key] = Candidate(key, r.name, r.path, category=category_of(r.name))
        g.members.append(p)
        g.cpu_pct += cpu.get(p.pid, 0.0)

    member_group = {m.pid: g for g in groups.values() for m in g.members}
    for w in windows:
        g = member_group.get(w.pid)
        if g is not None:
            g.windows.append(w)

    # Familia del objetivo: su árbol, quien lo lanzó y todo lo que viva en su carpeta.
    plan = Plan([], kept, target_key, profile=profile)
    family: set[str] = set()
    target_proc = next((p for p in procs if program_key(p) == target_key), None) if target_key else None
    if target_proc is not None:
        plan.target_name = target_proc.name
        plan.target_members = [p for p in procs if program_key(p) == target_key]
        target_dir = _install_dir(target_proc.path)
        for g in groups.values():
            if any(program_key(m) == target_key or _under(m.path, target_dir) for m in g.members):
                family.add(g.key)
        for tp in plan.target_members:   # lanzadores: los antepasados del objetivo
            cur, hops = _valid_parent(tp, by_pid), 0
            while cur is not None and hops < 64:
                if cur.pid in member_group:
                    family.add(member_group[cur.pid].key)
                cur, hops = _valid_parent(cur, by_pid), hops + 1

    for g in groups.values():
        if g.key in family:
            kept["target"] = kept.get("target", 0) + g.count
            continue
        g.suggested, g.reason = suggest(g.category, g.has_window, profile, g.private, g.cpu_pct)
        g.action = g.suggested
        plan.candidates.append(g)
    plan.candidates.sort(key=lambda c: c.private, reverse=True)
    return plan


def reclaimable(plan: Plan) -> tuple[int, int]:
    """(bytes en RAM, nº de programas) sobre los que actuaría la propuesta por defecto."""
    chosen = [c for c in plan.candidates if c.suggested != Action.KEEP]
    return sum(c.working_set for c in chosen), len(chosen)


# =========================================================================
# Modo eficiente: aplicar, deshacer
# =========================================================================

@dataclass
class Options:
    trim: bool = False           # recortar la RAM de lo ralentizado
    boost_target: bool = False   # prioridad «Por encima de lo normal» al objetivo
    force: bool = False          # finalizar a la fuerza lo que no se cierre solo
    grace: float = 6.0           # segundos que se espera a que un programa se cierre


@dataclass
class Touched:
    pid: int
    create_time: float
    name: str
    prev_priority: int


@dataclass
class Session:
    """Lo que el Modo eficiente ha cambiado, para poder deshacerlo. Vive en memoria."""
    throttled: list[Touched] = field(default_factory=list)
    boosted: list[Touched] = field(default_factory=list)
    closed: list[tuple[str, str]] = field(default_factory=list)   # (nombre, ruta)

    @property
    def active(self) -> bool:
        return bool(self.throttled or self.boosted)

    def prune(self, api=winapi) -> None:
        """Olvida los procesos que ya han terminado."""
        self.throttled = [t for t in self.throttled if api.process_alive(t.pid, t.create_time)]
        self.boosted = [t for t in self.boosted if api.process_alive(t.pid, t.create_time)]

    def has(self, pid: int, create_time: float) -> bool:
        return any(t.pid == pid and t.create_time == create_time for t in self.throttled)


SESSION = Session()


@dataclass
class ApplyResult:
    throttled: int = 0
    closed: int = 0
    boosted: int = 0
    pending: list[str] = field(default_factory=list)    # siguen abiertos (¿preguntan si guardar?)
    failures: list[str] = field(default_factory=list)
    available_before: int = 0
    available_after: int = 0


def plan_risk(plan: Plan, options: Options) -> Risk:
    closing = plan.chosen(Action.CLOSE)
    if not closing:
        return Risk.BAJO
    if options.force and any(c.has_window for c in closing):
        return Risk.ALTO   # se pueden perder datos sin guardar
    return Risk.MEDIO


def describe_plan(plan: Plan, options: Options, limit: int = 60) -> str:
    """Texto exacto de lo que se va a hacer, para la ventana de confirmación."""
    lines = []
    for c in plan.chosen(Action.CLOSE):
        verb = "opt.do.ask_close" if c.has_window else "opt.do.end"
        lines.append((i18n.t(verb), c))
    for c in plan.chosen(Action.THROTTLE):
        lines.append((i18n.t("opt.do.throttle"), c))
    width = max((len(v) for v, _c in lines), default=0)
    out = [f"{v:<{width}}  {c.name}{f' ×{c.count}' if c.count > 1 else ''}  ({fmt_size(c.private)})"
           for v, c in lines[:limit]]
    if len(lines) > limit:
        out.append(i18n.t("dialog.more_items", n=len(lines) - limit))
    if options.boost_target and plan.target_members:
        out.append(f"{i18n.t('opt.do.boost'):<{width}}  {plan.target_name}")
    return "\n".join(out)


def _may_touch(m) -> bool:
    """Segunda barrera, justo antes de actuar: nunca procesos esenciales ni la propia app."""
    allowed, _risk, _why = check_process_kill(m.name, m.pid)
    return allowed and m.name.lower() not in SENSITIVE_PROCESSES and m.name.lower() not in _UNTOUCHABLE


def apply_plan(plan: Plan, options: Options, session: Session = SESSION, api=winapi, log=log_action,
               sleep=time.sleep, clock=time.monotonic) -> ApplyResult:
    """Ejecuta lo que el usuario ha confirmado. Cada proceso se identifica por PID e
    instante de creación: si ya no es el mismo, se salta."""
    res = ApplyResult()
    mem = api.memory_status()
    res.available_before = mem.available if mem else 0

    for c in plan.chosen(Action.THROTTLE):
        done, first_error = 0, ""
        for m in c.members:
            if not _may_touch(m) or session.has(m.pid, m.create_time):
                continue
            ok, msg, prev = api.set_efficiency(m.pid, m.create_time)
            if ok:
                done += 1
                session.throttled.append(Touched(m.pid, m.create_time, m.name, prev))
                if options.trim:
                    api.trim_working_set(m.pid, m.create_time)
            else:
                first_error = first_error or msg
        log("modo_eficiente_ralentizar", f"{c.name} ×{c.count}", first_error or f"{done}/{c.count}",
            ok=done > 0, recorte=options.trim)
        if done:
            res.throttled += 1
        elif first_error:
            res.failures.append(f"{c.name}: {first_error}")

    def alive(c: Candidate) -> list:
        return [m for m in c.members if api.process_alive(m.pid, m.create_time)]

    def end(c: Candidate, how: str) -> None:
        errors = []
        for m in alive(c):
            if not _may_touch(m):
                continue
            ok, msg = api.terminate_process(m.pid, m.create_time)
            if not ok and api.process_alive(m.pid, m.create_time):
                errors.append(msg)
        ok = not alive(c)
        log("modo_eficiente_finalizar", f"{c.name} ×{c.count}", errors[0] if errors else how, ok=ok)
        if ok:
            _closed(c)
        else:
            res.failures.append(f"{c.name}: {errors[0] if errors else how}")

    def _closed(c: Candidate) -> None:
        res.closed += 1
        if (c.name, c.path) not in session.closed:
            session.closed.append((c.name, c.path))

    asked: list[Candidate] = []
    for c in plan.chosen(Action.CLOSE):
        if not all(_may_touch(m) for m in c.members):
            continue
        if c.has_window:   # como pulsar la X: el programa puede preguntar si guardar
            for w in c.windows:
                api.close_window(w.hwnd)
            asked.append(c)
        else:              # sin ventana no hay forma de pedirlo: se finaliza
            end(c, i18n.t("opt.log.ended"))

    deadline = clock() + options.grace
    waiting = list(asked)
    while waiting and clock() < deadline:
        sleep(0.4)
        waiting = [c for c in waiting if alive(c)]
    for c in asked:
        if c not in waiting:
            log("modo_eficiente_cerrar", f"{c.name} ×{c.count}", i18n.t("opt.log.closed"))
            _closed(c)
        elif options.force:
            end(c, i18n.t("opt.log.forced"))
        else:
            log("modo_eficiente_cerrar", f"{c.name} ×{c.count}", i18n.t("opt.log.still_open"), ok=False)
            res.pending.append(c.name)

    if options.boost_target:
        for m in plan.target_members:
            if not m.accessible or not _may_touch(m) or m.priority not in (0, winapi.PRIORITY_NORMAL):
                continue
            ok, msg, prev = api.set_priority(m.pid, winapi.PRIORITY_ABOVE_NORMAL, m.create_time)
            if ok:
                res.boosted += 1
                session.boosted.append(Touched(m.pid, m.create_time, m.name, prev))
        if plan.target_members:
            log("modo_eficiente_priorizar", plan.target_name, f"{res.boosted}/{len(plan.target_members)}",
                ok=res.boosted > 0)

    mem = api.memory_status()
    res.available_after = mem.available if mem else 0
    return res


def restore(session: Session = SESSION, api=winapi, log=log_action) -> tuple[int, list[str]]:
    """Deshace lo ralentizado y lo priorizado. Devuelve (procesos restaurados, fallos)."""
    done, failures = 0, []
    for t in session.throttled:
        if not api.process_alive(t.pid, t.create_time):
            continue   # ya se cerró: nada que deshacer
        ok, msg = api.restore_efficiency(t.pid, t.prev_priority, t.create_time)
        done += ok
        if not ok:
            failures.append(f"{t.name} ({t.pid}): {msg}")
    for t in session.boosted:
        if not api.process_alive(t.pid, t.create_time):
            continue
        ok, msg, _prev = api.set_priority(t.pid, t.prev_priority, t.create_time)
        done += ok
        if not ok:
            failures.append(f"{t.name} ({t.pid}): {msg}")
    log("modo_eficiente_restaurar", "", f"{done}", ok=not failures)
    session.throttled, session.boosted = [], []
    return done, failures


def reopen(session: Session = SESSION, api=winapi, log=log_action) -> list[str]:
    """Vuelve a abrir los programas que se cerraron. Devuelve los que no se pudo."""
    failures = []
    for name, path in session.closed:
        ok, msg = api.shell_execute(path) if path else (False, i18n.t("winapi.not_found"))
        log("modo_eficiente_reabrir", path or name, msg, ok=ok)
        if not ok:
            failures.append(f"{name}: {msg}")
    session.closed = []
    return failures


# =========================================================================
# Análisis exhaustivo
# =========================================================================

@dataclass
class ProgramUsage:
    key: str
    name: str
    path: str
    count: int = 0
    private: int = 0
    working_set: int = 0
    threads: int = 0
    handles: int = 0          # el máximo de un solo proceso
    cpu_avg: float = 0.0
    cpu_peak: float = 0.0
    growth: int = 0           # variación de memoria privada durante el análisis
    steady: bool = False      # creció en todas las muestras
    has_window: bool = False
    accessible: bool = True
    members: list = field(default_factory=list)   # RawProcess de la última muestra


@dataclass
class Finding:
    severity: int             # 0 informativo · 1 aviso leve · 2 a revisar · 3 urgente
    title: str
    detail: str = ""
    advice: str = ""
    goto: str = ""            # sección a la que lleva («memory», «startup», «efficient»)


@dataclass
class Report:
    findings: list[Finding]
    programs: list[ProgramUsage]
    seconds: float
    mem: object = None
    perf: object = None
    procs: list = field(default_factory=list)     # última muestra, para actuar sobre el resultado

    @property
    def severity(self) -> int:
        return max((f.severity for f in self.findings), default=0)


def take_samples(count: int = 10, interval: float = 1.0, should_stop=None, progress=None,
                 api=winapi, sleep=time.sleep, clock=time.monotonic) -> list[tuple[float, list]]:
    """Toma varias muestras de todos los procesos. Solo lee contadores."""
    samples = []
    for i in range(max(2, count)):
        if should_stop and should_stop():
            break
        if i:
            sleep(interval)
        samples.append((clock(), api.list_processes()))
        if progress:
            progress(i + 1, max(2, count))
    return samples


def _pct(x: float) -> str:
    return i18n.percent(f"{x:.0f}")


def analyze(samples: list[tuple[float, list]], mem=None, perf=None, window_pids: set[int] | None = None,
            ncpu: int | None = None, startup_enabled: int | None = None,
            reclaim: tuple[int, int] | None = None, is_admin: bool = False,
            self_pid: int | None = None) -> Report:
    """Convierte las muestras en un diagnóstico: quién consume, quién crece y qué hacer."""
    window_pids = window_pids or set()
    ncpu = ncpu or os.cpu_count() or 1
    self_pid = os.getpid() if self_pid is None else self_pid
    if not samples:
        return Report([], [], 0.0, mem, perf)
    seconds = samples[-1][0] - samples[0][0]
    last = samples[-1][1]

    usage: dict[str, ProgramUsage] = {}
    for p in last:
        if p.pid == 0:
            continue
        key = program_key(p)
        u = usage.get(key)
        if u is None:
            u = usage[key] = ProgramUsage(key, p.name, p.path, accessible=False)
        u.count += 1
        u.private += p.private
        u.working_set += p.working_set
        u.threads += p.threads
        u.handles = max(u.handles, p.handles)
        u.has_window = u.has_window or p.pid in window_pids
        u.accessible = u.accessible or p.accessible
        u.members.append(p)

    # CPU por intervalo, sumada por programa
    intervals: dict[str, list[float]] = {}
    for (t0, prev), (t1, cur) in zip(samples, samples[1:]):
        per_pid = cpu_percent(prev, cur, t1 - t0, ncpu)
        totals: dict[str, float] = {}
        for p in cur:
            if p.pid in per_pid:
                totals[program_key(p)] = totals.get(program_key(p), 0.0) + per_pid[p.pid]
        for key, value in totals.items():
            intervals.setdefault(key, []).append(value)
    for key, values in intervals.items():
        if key in usage:
            usage[key].cpu_avg = sum(values) / len(values)
            usage[key].cpu_peak = max(values)

    # Crecimiento: solo con los procesos presentes en todas las muestras
    stable = set.intersection(*({(p.pid, p.create_time) for p in procs} for _t, procs in samples))
    series: dict[str, list[int]] = {}
    for _t, procs in samples:
        totals = {}
        for p in procs:
            if (p.pid, p.create_time) in stable and p.accessible:
                totals[program_key(p)] = totals.get(program_key(p), 0) + p.private
        for key, value in totals.items():
            series.setdefault(key, []).append(value)
    for key, values in series.items():
        if key in usage and len(values) >= 2:
            usage[key].growth = values[-1] - values[0]
            usage[key].steady = len(values) >= 3 and all(b >= a for a, b in zip(values, values[1:]))

    programs = sorted(usage.values(), key=lambda u: u.private, reverse=True)
    own_key = next((program_key(p) for p in last if p.pid == self_pid), "")
    findings: list[Finding] = []
    t = i18n.t

    if mem and mem.total:
        load = mem.used / mem.total
        args = dict(pct=_pct(load * 100), used=fmt_size(mem.used), total=fmt_size(mem.total),
                    avail=fmt_size(mem.available))
        if load >= 0.90:
            findings.append(Finding(3, t("opt.find.ram_crit", **args), t("opt.find.ram_detail", **args),
                                    t("opt.find.ram_crit_advice"), "efficient"))
        elif load >= 0.75:
            findings.append(Finding(2, t("opt.find.ram_warn", **args), t("opt.find.ram_detail", **args),
                                    t("opt.find.ram_warn_advice"), "efficient"))
        else:
            findings.append(Finding(0, t("opt.find.ram_ok", **args), t("opt.find.ram_detail", **args)))

    commit_used = perf.commit_total if perf else (mem.commit_total - mem.commit_available if mem else 0)
    commit_limit = perf.commit_limit if perf else (mem.commit_total if mem else 0)
    if commit_limit and commit_used / commit_limit >= 0.80:
        ratio = commit_used / commit_limit
        findings.append(Finding(3 if ratio >= 0.90 else 2,
                                t("opt.find.commit", pct=_pct(ratio * 100)),
                                t("opt.find.commit_detail", used=fmt_size(commit_used),
                                  total=fmt_size(commit_limit)),
                                t("opt.find.commit_advice"), "memory"))

    total_ram = mem.total if mem and mem.total else 0
    hog_floor = max(1.5 * GB, 0.20 * total_ram)
    for u in [u for u in programs if u.private >= hog_floor][:3]:
        share = _pct(u.private / total_ram * 100) if total_ram else "—"
        findings.append(Finding(2, t("opt.find.hog", name=u.name, size=fmt_size(u.private), pct=share),
                                i18n.plural(u.count, "opt.find.procs"),
                                t("opt.find.hog_browser_advice") if category_of(u.name) == "browser"
                                else t("opt.find.hog_advice"), "memory"))

    for u in programs:
        if u.key == own_key:
            continue
        if u.steady and u.growth >= max(100 * MB, 0.10 * (u.private - u.growth)):
            findings.append(Finding(2, t("opt.find.growth", name=u.name, size=fmt_size(u.growth),
                                         s=f"{seconds:.0f}"),
                                    t("opt.find.growth_detail", size=fmt_size(u.private)),
                                    t("opt.find.growth_advice"), "memory"))
        if not u.has_window and u.cpu_avg >= 5.0:
            findings.append(Finding(2, t("opt.find.bg_cpu", name=u.name, pct=_pct(u.cpu_avg)),
                                    t("opt.find.bg_cpu_detail", peak=_pct(u.cpu_peak)),
                                    t("opt.find.bg_cpu_advice"), "efficient"))
        if u.handles >= 20000:
            findings.append(Finding(1, t("opt.find.handles", name=u.name, n=fmt_count(u.handles)),
                                    "", t("opt.find.handles_advice"), "memory"))

    if perf and total_ram and perf.kernel_nonpaged > max(GB, 0.08 * total_ram):
        findings.append(Finding(2, t("opt.find.kernel", size=fmt_size(perf.kernel_nonpaged)), "",
                                t("opt.find.kernel_advice")))

    if startup_enabled is not None and startup_enabled >= 8:
        findings.append(Finding(1, t("opt.find.startup", n=startup_enabled), "",
                                t("opt.find.startup_advice"), "startup"))

    blind = sum(1 for p in last if p.pid != 0 and not p.accessible)
    if blind and not is_admin:
        findings.append(Finding(0, t("opt.find.blind", n=blind), "", t("opt.find.blind_advice")))

    if reclaim and reclaim[1]:
        findings.append(Finding(0, t("opt.find.reclaim", n=reclaim[1], size=fmt_size(reclaim[0])), "",
                                t("opt.find.reclaim_advice"), "efficient"))

    if not any(f.severity >= 2 for f in findings):
        findings.append(Finding(0, t("opt.find.all_ok"), "", t("opt.find.all_ok_advice")))

    findings.sort(key=lambda f: f.severity, reverse=True)
    return Report(findings, programs, seconds, mem, perf, last)
