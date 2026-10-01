"""Read-only runtime audit against PDF page 9; never changes saved wiring.

These isolated witness circuits are diagnostic probes, NOT answer keys.
The output deliberately does not claim full problem-sequence coverage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.api.operation import _practice_runtime_source
from app.domain import OperationAction, WiringConnection
from app.repositories.problem_repository import ProblemRepository
from app.services import DeviceBehaviorRuntimeComposer
from app.simulation import OperationEngine


def run(reference_models=False):
    repo = ProblemRepository(ROOT / "problems", ROOT / "schemas", ROOT / "catalog")
    repo.reload()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(problem_repository=repo)))
    results = []
    runtimes = {}

    def check(number, name, actual, expected):
        results.append(dict(problem=number, check=name, actual=actual,
                            expected=expected, passed=actual == expected))

    def engine(runtime, pairs):
        return OperationEngine(
            session_id="pdf-audit", problem_id="isolated-probe", wiring_attempt_id=0,
            circuit=runtime.circuit.model_copy(deep=True),
            definition=runtime.operation.model_copy(deep=True),
            connections=[WiringConnection(from_terminal=a, to=b) for a, b in pairs],
            catalog_composed=runtime.catalog_composed, gradable=False,
        )

    def action(e, name, **kwargs):
        return e.apply(OperationAction(action=name, **kwargs))

    for n in range(1, 19):
        number = f"{n:03}"
        package = repo._get_package_internal(f"qnet_electrician_practical_{number}")
        circuit, operation = _practice_runtime_source(request, package)
        runtime = DeviceBehaviorRuntimeComposer(repo.catalog).compose(circuit, operation)
        if reference_models:
            # Counterfactual only: copies are never saved to catalog or problems.
            for timer in runtime.operation.timers:
                instant = next(c for c in runtime.circuit.contacts
                               if c.controlled_by_coil_id == timer.coil_id and c.contact_id.endswith("-C1"))
                instant.contact_type = "NO"
                instant.nc_terminal_id = None
                instant.no_terminal_id = None
                instant.controller_type = "coil"
                instant.controller_id = timer.coil_id
                instant.normal_state = "open"
                timer.timed_contact_ids = [c for c in timer.timed_contact_ids if c != instant.contact_id]
            for contact in runtime.circuit.contacts:
                if contact.owner_device_id == "FR":
                    contact.contact_type = "CHANGEOVER"
                    contact.common_terminal_id = "FR-8"
                    contact.switched_terminal_id = "FR-6"
                    contact.nc_terminal_id = "FR-5"
                    contact.no_terminal_id = "FR-6"
                if contact.owner_device_id == "FLS":
                    contact.contact_type = "CHANGEOVER"
                    contact.common_terminal_id = "FLS-4"
                    contact.switched_terminal_id = "FLS-3"
                    contact.nc_terminal_id = "FLS-2"
                    contact.no_terminal_id = "FLS-3"
        runtimes[number] = runtime
        line, ret = operation.power.line_terminal_id, operation.power.return_terminal_id
        for coil in runtime.circuit.coils:
            owner = coil.owner_device_id
            if not owner.startswith(("X", "MC")):
                continue
            pin_pairs = ([(1, 7, True), (2, 8, True), (3, 9, True),
                          (4, 10, True), (5, 11, False)] if owner.startswith("MC")
                         else [(1, 3, True), (1, 4, False), (8, 6, True), (8, 5, False)])
            for reverse in (False, True):
                a, b = coil.terminal_a_id, coil.terminal_b_id
                e = engine(runtime, [(line, b if reverse else a), (ret, a if reverse else b)])
                for powered in (False, True, False):
                    action(e, "set_power", value=powered)
                    check(number, f"{owner}: contacts power={powered} reversed={reverse}", [
                        e._conductive_graph().connected(f"{owner}-{x}", f"{owner}-{y}")
                        for x, y, no in pin_pairs
                    ], [powered if no else not powered for x, y, no in pin_pairs])
        for control in runtime.operation.controls:
            e = engine(runtime, [])
            for active in (True, False):
                action(e, "press_control" if active else "release_control", control_id=control.control_id)
                graph = e._conductive_graph()
                check(number, f"{control.control_id}: contact active={active}",
                      graph.connected(control.terminal_a_id, control.terminal_b_id),
                      active if control.contact_type == "NO" else not active)
                if control.alternate_terminal_a_id:
                    check(number, f"{control.control_id}: alternate active={active}",
                          graph.connected(control.alternate_terminal_a_id, control.alternate_terminal_b_id), not active)
        e = engine(runtime, [])
        for tripped in (False, True, False):
            # Isolate EOCR contact topology, not the UI fault-injection prerequisites.
            e.protection_status["EOCR"] = "tripped" if tripped else "normal"
            graph = e._conductive_graph()
            check(number, f"EOCR: changeover tripped={tripped}", [
                graph.connected("EOCR-95", "EOCR-96"),
                graph.connected("EOCR-95", "EOCR-98"),
                graph.connected("EOCR-95", "EOCR-97"),
            ], [not tripped, tripped, True])
        short = engine(runtime, [(line, ret)])
        action(short, "set_power", value=True)
        check(number, "direct short trips", short.tripped, True)
        for timer in runtime.operation.timers:
            owner = next(c.owner_device_id for c in runtime.circuit.coils if c.coil_id == timer.coil_id)
            pairs = [(line, f"{owner}-2"), (ret, f"{owner}-7")]
            e = engine(runtime, pairs)
            connected = lambda a, b: e._conductive_graph().connected(f"{owner}-{a}", f"{owner}-{b}")
            check(number, f"{owner}: pin 4 unused", connected(1, 4), False)
            check(number, f"{owner}: timed NC at rest", connected(8, 5), True)
            action(e, "set_power", value=True)
            check(number, f"{owner}: instant NO immediately", connected(1, 3), True)
            check(number, f"{owner}: timed NO initially open", connected(8, 6), False)
            action(e, "advance_time", milliseconds=timer.delay_ms - 1)
            check(number, f"{owner}: timed NO before deadline", connected(8, 6), False)
            action(e, "advance_time", milliseconds=1)
            check(number, f"{owner}: timed NO at deadline", connected(8, 6), True)
            action(e, "set_power", value=False)
            check(number, f"{owner}: timer resets", e.timers[timer.timer_id].elapsed_ms, 0)
            check(number, f"{owner}: instant releases", connected(1, 3), False)
            # AC coil direction is not polarized in this simulator.
            reverse = engine(runtime, [(line, f"{owner}-7"), (ret, f"{owner}-2")])
            action(reverse, "set_power", value=True)
            action(reverse, "advance_time", milliseconds=timer.delay_ms)
            check(number, f"{owner}: reversed coil supply", reverse.timers[timer.timer_id].completed, True)

        for flasher in runtime.operation.flashers:
            e = engine(runtime, [(line, "FR-2"), (ret, "FR-7")])
            pair = lambda a, b: e._conductive_graph().connected(f"FR-{a}", f"FR-{b}")
            check(number, "FR: NC 8-5 at rest", pair(8, 5), True)
            action(e, "set_power", value=True)
            # Both phases must have exactly one output, irrespective of start phase.
            phases = []
            for _ in range(2):
                phases.append((pair(8, 5), pair(8, 6)))
                action(e, "advance_time", milliseconds=flasher.interval_ms)
            check(number, "FR: complementary alternating outputs", sorted(phases), [(False, True), (True, False)])

        for level in runtime.operation.level_relays:
            pairs = [(line, level.supply_terminal_a_id), (ret, level.supply_terminal_b_id)]
            pairs += list(zip(level.electrode_terminal_ids, level.external_electrode_terminal_ids))
            e = engine(runtime, pairs)
            check(number, "FLS: NC 4-2 at rest", e._conductive_graph().connected("FLS-4", "FLS-2"), True)
            action(e, "set_power", value=True)
            action(e, "set_level", target_id=level.level_relay_id, value=True)
            check(number, "FLS: powered/wired sensor closes NO", e._conductive_graph().connected("FLS-4", "FLS-3"), True)
            action(e, "set_level", target_id=level.level_relay_id, value=False)
            check(number, "FLS: sensor release opens NO", e._conductive_graph().connected("FLS-4", "FLS-3"), False)

        for fuse in runtime.operation.fuse_channels:
            e = engine(runtime, [])
            action(e, "set_fuse_state", target_id=fuse.channel_id, value=False)
            check(number, f"{fuse.channel_id}: opens only its channel", [
                e._conductive_graph().connected(f.terminal_a_id, f.terminal_b_id)
                for f in runtime.operation.fuse_channels
            ], [f.channel_id != fuse.channel_id for f in runtime.operation.fuse_channels])

    # A real two-stage timer path: T1 timed NO supplies T2. A single large
    # time advance must agree with advances split at the contact transition.
    r = runtimes["018"]
    line, ret = r.operation.power.line_terminal_id, r.operation.power.return_terminal_id
    pairs = [(line, "T1-2"), (ret, "T1-7"), (line, "T1-8"),
             ("T1-6", "T2-2"), (ret, "T2-7")]
    timers = {t.coil_id: t for t in r.operation.timers}
    first, second = timers["T1-COIL"], timers["T2-COIL"]
    bulk, split = engine(r, pairs), engine(r, pairs)
    for e in (bulk, split):
        action(e, "set_power", value=True)
    action(bulk, "advance_time", milliseconds=first.delay_ms + second.delay_ms)
    action(split, "advance_time", milliseconds=first.delay_ms)
    action(split, "advance_time", milliseconds=second.delay_ms)
    check("common", "cascaded timers: bulk equals split", bulk.timers[second.timer_id].completed,
          split.timers[second.timer_id].completed)

    return {"scope": "18 runtime compositions; isolated component probes, not full 18 problem acceptance",
            "reference_models_in_memory_only": reference_models,
            "passed": sum(r["passed"] for r in results), "total": len(results), "results": results}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(run(reference_models="--reference-models" in sys.argv), ensure_ascii=False, indent=2))
