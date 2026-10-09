"""Monitor de procesos: memoria privada, conjunto de trabajo y CPU."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from . import plat
from .plat import know


@dataclass
class ProcInfo:
    pid: int
    name: str
    path: str
    private: int
    working_set: int
    cpu_pct: float
    threads: int
    accessible: bool
    count: int = 1
    pids: list[int] = field(default_factory=list)
    service: bool = False   # lo lanzó el Administrador de servicios (services.exe)


class ProcessMonitor:
    """Mantiene la muestra anterior para calcular el % de CPU entre refrescos."""

    def __init__(self) -> None:
        self._prev: dict[int, float] = {}
        self._prev_t = 0.0
        self._ncpu = os.cpu_count() or 1

    def sample(self) -> list[ProcInfo]:
        now = time.monotonic()
        raw = plat.list_processes()
        dt = now - self._prev_t if self._prev_t else 0.0
        out = []
        new_prev = {}
        by_pid = {r.pid: r for r in raw}
        for r in raw:
            new_prev[r.pid] = r.cpu_time
            cpu = 0.0
            if dt > 0 and r.pid in self._prev:
                cpu = max(0.0, (r.cpu_time - self._prev[r.pid]) / (dt * self._ncpu) * 100)
            out.append(ProcInfo(r.pid, r.name, r.path, r.private, r.working_set,
                                min(cpu, 100.0), r.threads, r.accessible, 1, [r.pid],
                                service=r.ppid != r.pid and know.is_service(r, by_pid.get(r.ppid))))
        self._prev = new_prev
        self._prev_t = now
        return out


def group_by_program(procs: list[ProcInfo]) -> list[ProcInfo]:
    groups: dict[str, ProcInfo] = {}
    for p in procs:
        key = (p.path or p.name).lower()
        g = groups.get(key)
        if g is None:
            groups[key] = ProcInfo(p.pid, p.name, p.path, p.private, p.working_set, p.cpu_pct,
                                   p.threads, p.accessible, 1, [p.pid], p.service)
        else:
            g.private += p.private
            g.working_set += p.working_set
            g.cpu_pct += p.cpu_pct
            g.threads += p.threads
            g.count += 1
            g.pids.append(p.pid)
            g.accessible = g.accessible or p.accessible
            g.service = g.service or p.service
    return list(groups.values())
