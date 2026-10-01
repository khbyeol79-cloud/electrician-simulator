"""Public behavioral checks, reviewed against 2025-08-04 Q-Net p8 and p7.

These contain operating instructions, NOT wiring answers. Every checkpoint
replays its prefix against the user's actual wires in an isolated engine.
Training milliseconds are not claimed to be official prescribed settings.
"""
from app.domain.operation_definition import OperationDefinition, OperationExpectation, OperationRequirement


def press(name):
    return {"action": "press_control", "control_id": name}


def release(name):
    return {"action": "release_control", "control_id": name}


def wait(ms):
    return {"action": "advance_time", "milliseconds": ms}


def level(value):
    return {"action": "set_level", "target_id": "FLS-LEVEL", "value": value}


def pulse(name):
    return [press(name), release(name)]


def motors(*running, tripped=False):
    result = {}
    for i, lamp in ((1, "RL"), (2, "GL")):
        result[f"coils.MC{i}-COIL"] = i in running
        result[f"motors.M{i}"] = "forward" if i in running else "protection_trip" if tripped else "stopped"
        result[f"indicators.{lamp}"] = "on" if i in running else "off"
    return result


def coil(name, value=True):
    return {f"coils.{name}-COIL": value}


def lamp(name, value=True):
    return {f"indicators.{name}": "on" if value else "off"}


class Scenario:
    def __init__(self, rows, key, label, hint, manual=False):
        self.rows, self.key, self.label, self.hint = rows, key, label, hint
        self.actions = [{"action": "set_power", "value": True}]
        if manual:
            self.actions.append(release("SS"))
        self.count = 0

    def do(self, *actions):
        self.actions.extend(actions)
        return self

    def check(self, label, *states):
        self.count += 1
        expected = {"stable": True, "power_state": "on"}
        for state in states:
            expected.update(state)
        self.rows.append(OperationRequirement.model_validate({
            "requirement_id": f"P8_{self.key}_{self.count:02}", "label": label,
            "scenario_id": f"P8_{self.key}", "scenario_label": self.label,
            "next_action": self.hint, "actions": list(self.actions),
            "expectations": [{"path": k, "expected": v} for k, v in expected.items()],
        }))
        return self


def reviewed_requirements(number: int, operation: OperationDefinition) -> list[OperationRequirement]:
    rows = []
    delays = {t.timer_id: t.delay_ms for t in operation.timers}
    t = delays.get("T-TIMER", 1000)
    t1, t2 = delays.get("T1-TIMER", 1000), delays.get("T2-TIMER", 1000)
    f = operation.flashers[0].interval_ms if operation.flashers else 1000

    def scene(key, title, hint="회로도와 현재 결선을 비교하고 입력·자기유지·출력 경로를 확인하세요.", manual=False):
        return Scenario(rows, key, f"PDF 8쪽 · {title}", hint, manual)

    def run_steps(s, steps):
        for ms, running in steps:
            if ms:
                s.do(wait(ms))
            state_label = "M1·M2 정지, RL·GL 소등" if not running else (
                "M1·M2 회전, RL·GL 점등" if len(running) == 2 else
                "M1 회전·RL 점등, M2 정지·GL 소등" if running == (1,) else
                "M2 회전·GL 점등, M1 정지·RL 소등")
            s.check(f"직전 단계에서 {ms}ms 진행: {state_label}", motors(*running))

    if number <= 9:
        manual_steps = {
            1: [(0, (1,)), (t - 1, (1,)), (1, (1, 2))],
            2: [(0, ()), (t - 1, ()), (1, (1,)), (f, (2,)), (f, (1,))],
            3: [(0, ()), (t - 1, ()), (1, (1,)), (f, (2,)), (f, (1,))],
            4: [(0, (1,)), (f, (2,)), (t, ()), (f - t, (1,))],
            5: [(0, (1,)), (f, (2,)), (f, (1,)), (t - 2 * f, (1, 2))],
            6: [(0, (1, 2)), (t - 1, (1, 2)), (1, (1,)), (f, (2,)), (f, (1,))],
            7: [(0, (1,)), (t, (2,)), (f - t, ()), (f, (1,))],
            8: [(0, (1, 2)), (t - 1, (1, 2)), (1, ())],
            9: [(0, (1,)), (t - 1, (1,)), (1, (1, 2))],
        }[number]
        s = scene("MANUAL", "수동 기동·자기유지·시간 동작", "SS를 M으로 놓고 PB1을 짧게 누른 뒤 표시된 시간을 진행하세요.", manual=True)
        s.check("SS=M, PB1 기동 전에는 타이머·모터 정지", motors(), coil("T", False), coil("FR", False))
        s.do(*pulse("PB1"))
        run_steps(s, manual_steps)
        if number == 5:
            s.check("T 완료 후 FR 소자, 두 모터 동시 운전", coil("FR", False), motors(1, 2))
        s.do(press("PB0")).check("PB0 누름: 모터·타이머 정지", motors(), coil("T", False), {"timers.T-TIMER.elapsed_ms": 0})
        s.do(release("PB0")).check("PB0 해제만으로 재기동하지 않음", motors())
        auto_steps = {
            1: [(0, (1,))], 2: manual_steps, 3: [(0, (1,)), (f, (2,)), (f, (1,))],
            4: manual_steps, 5: manual_steps, 6: [(0, (1, 2))], 7: manual_steps,
            8: [(0, (1, 2))], 9: [(0, (1,))],
        }[number]
        s = scene("AUTO", "자동 수위감지·운전·감지 해제", "SS=A에서 수위감지를 켠 뒤 끄고, 모터와 표시등을 확인하세요.")
        s.check("SS=A, 수위감지 전 모터 정지", motors(), {"level_relays.FLS-LEVEL.powered": True})
        s.do(level(True))
        run_steps(s, auto_steps)
        if number == 8:
            s.check("감지 직후 YL 점등", lamp("YL"))
            s.do(wait(f)).check("FR 한 주기 후 YL 소등, 모터 계속 운전", lamp("YL", False), motors(1, 2))
            s.do(wait(f)).check("다음 주기 YL 재점등", lamp("YL"), motors(1, 2))
        s.do(level(False)).check("수위감지 해제: 모터와 운전 타이머 정지", motors(), coil("T", False), coil("FR", False))
        s = scene("SELECTOR", "선택스위치 전환 정지", "자동/수동을 전환할 때 감지와 기동 버튼의 상태도 함께 확인하세요.", manual=True)
        s.do(*pulse("PB1"), press("SS")).check("수동 운전에서 A로 전환, 미감지 상태 정지", motors())
        s.do(level(True), wait(t), release("SS")).check("자동 운전에서 M으로 전환, PB1 미입력 상태 정지", motors())
    elif number in (10, 11):
        for i, delay in ((1, t1), (2, t2)):
            s = scene(f"BRANCH{i}", f"PB{i}·LS{i}·T{i}·MC{i}")
            if number == 10:
                s.do(*pulse(f"PB{i}")).check(f"PB{i} 후 X{i} 자기유지, 센서 대기 WL", coil(f"X{i}"), motors(), lamp("WL"))
                s.do(press(f"LS{i}"), wait(delay - 1)).check("센서 감지 후 설정시간 전 모터 정지", motors(), coil(f"T{i}"))
                s.do(wait(1)).check("설정시간 후 모터·운전등 점등, WL 소등", motors(i), lamp("WL", False))
            else:
                s.do(press(f"LS{i}"), *pulse(f"PB{i}")).check("시간 미달 짧은 PB 입력은 자기유지되지 않음", motors(), coil(f"X{i}", False))
                s.do(press(f"PB{i}"), wait(delay), release(f"PB{i}")).check("PB를 설정시간 이상 누른 뒤 해제: 자기유지", motors(i), coil(f"X{i}"))
            s.do(release(f"LS{i}")).check("센서 해제: 모터 정지·WL 점등, X 자기유지 유지", motors(), lamp("WL"), coil(f"X{i}"))
            s.do(press(f"LS{i}"))
            if number == 10:
                s.do(wait(delay))
            s.check("센서 재감지 후 정상 재운전", motors(i), lamp("WL", False))
        if number == 11:
            s = scene("TRANSFER", "PB1/PB2 타이머 자기유지 전환")
            s.do(press("PB1"), wait(t1), release("PB1"), press("PB2"), wait(t2), release("PB2"))
            s.check("PB2 전환 후 X1·T1 해제, X2·T2 유지", coil("X1", False), coil("T1", False), coil("X2"), coil("T2"))
    elif number in (12, 13):
        sensor = "LS1" if number == 12 else "LS2"
        s = scene("SENSOR", "PB1·센서 우선 운전과 타이머 재기동")
        s.do(*pulse("PB1")).check("PB1 후 X1·T1·WL", motors(), coil("X1"), coil("T1"), lamp("WL"))
        s.do(press(sensor)).check("센서 감지 시 MC1 운전, T1·WL 소등", motors(1), coil("T1", False), lamp("WL", False))
        s.do(release(sensor)).check("센서 해제 시 MC1 정지, T1·WL 재점등", motors(), coil("T1"), lamp("WL"))
        s.do(wait(t1 - 1)).check("T1 설정시간 전 MC2 정지", motors())
        s.do(wait(1)).check("T1 설정시간 후 X2·MC2", motors(2), coil("X2"))
        if number == 12:
            s.do(press("LS2"), wait(t2)).check("LS2 후 T2 완료: X1·T1 재기동", coil("X1"), coil("T1"), motors(2))
            s.do(press("LS1")).check("LS1 감지로 MC1 재운전·T1 해제", motors(1, 2), coil("T1", False))
        else:
            s.do(wait(t2)).check("T2 완료: X1·T1·T2·WL 해제, MC2 유지", motors(2), coil("X1", False), coil("T1", False), coil("T2", False), lamp("WL", False))
            scene("LS_START", "LS1에 의한 기동").do(*pulse("LS1")).check("LS1 입력도 X1·T1을 자기유지", coil("X1"), coil("T1"), lamp("WL"))
        scene("PB2", "PB2 직접 MC2 기동").do(*pulse("PB2")).check("PB2만으로 X2·MC2 운전", motors(2), coil("X2"))
    elif number in (14, 15, 17, 18):
        for i in ((1,) if number == 17 else (1, 2)):
            for a, b in ((False, False), (True, False), (False, True), (True, True)):
                if number == 14:
                    permitted = (a and b) if i == 1 else (a or b)
                elif number == 15:
                    permitted = (a or b) if i == 1 else (a and b)
                elif number == 17:
                    permitted = a != b
                else:
                    permitted = (a and not b) if i == 1 else (b and not a)
                s = scene(f"PERMIT_{i}_{int(a)}{int(b)}", f"PB{i} 허용조건 LS1={int(a)}·LS2={int(b)}")
                if a:
                    s.do(press("LS1"))
                if b:
                    s.do(press("LS2"))
                s.do(*pulse(f"PB{i}")).check("감지 조합에 따른 모터 기동/차단", motors(*((i,) if permitted else ())))
        for i in ((1,) if number == 17 else (1, 2)):
            s = scene(f"HOLD{i}", f"MC{i} 자기유지·센서 변화·시간 동작")
            sensors = ("LS1", "LS2") if (number, i) in ((14, 1), (15, 2)) else (f"LS{i}",)
            s.do(*(press(v) for v in sensors), *pulse(f"PB{i}"))
            s.check("PB 해제 후 모터 운전 유지", motors(i))
            if number in (15, 18):
                s.do(release("LS1"), release("LS2")).check("자기유지 후 센서가 해제되어도 운전 유지", motors(i))
            delay = t1 if i == 1 else t2
            s.do(wait(delay - 1)).check("설정시간 직전 상태 유지", motors(i))
            s.do(wait(1))
            if number in (14, 15):
                s.check("시간 경과 후 모터·타이머 정지, WL 점등", motors(), coil(f"T{i}", False), lamp("WL"))
            elif number == 18:
                s.check("시간 경과 후 모터 유지, WL 점등", motors(i), lamp("WL"))
            else:
                s.check("T1 완료 후에도 MC1 유지", motors(1))
        if number == 14:
            for i in (1, 2):
                s = scene(f"LOSS{i}", f"MC{i} 센서 허용조건 해제")
                s.do(press("LS1"), press("LS2"), *pulse(f"PB{i}"), release("LS1"))
                s.check("LS1 해제: MC1 정지 / MC2는 LS2로 유지", motors(*(() if i == 1 else (2,))))
                s.do(release("LS2")).check("두 센서 해제: 모터 정지", motors())
        if number == 17:
            s = scene("SECOND", "T1 완료 허가·T2 시간제한 운전")
            s.do(press("LS1"), *pulse("PB1"), *pulse("PB2")).check("T1 완료 전 PB2로 MC2를 기동할 수 없음", motors(1))
            s.do(wait(t1), *pulse("PB2")).check("T1 완료 후 PB2: MC2 운전", motors(1, 2))
            s.do(wait(t2)).check("T2 완료: MC2 정지·WL 점등", motors(1), lamp("WL"))
            s.do(press("LS2")).check("두 LS 동시 감지: 허용 해제·모터 정지", motors(), coil("T1", False), coil("T2", False))
        if number == 18:
            s = scene("INDEPENDENT", "독립 자기유지·두 모터 운전")
            s.do(press("LS1"), *pulse("PB1"), release("LS1"), press("LS2"), *pulse("PB2"))
            s.check("센서 조건 전환 후 두 모터 각각 자기유지", motors(1, 2))
    else:  # 016
        s = scene("M1", "PB1 또는 T1에 의한 MC1 기동")
        s.do(*pulse("PB1")).check("PB1만으로 X1·MC1 자기유지", motors(1), coil("X1"))
        s = scene("T1", "LS1·T1 지연 기동")
        s.do(press("LS1"), wait(t1 - 1)).check("LS1 후 T1 시간 전 MC1 정지", motors(), coil("T1"))
        s.do(wait(1), release("LS1")).check("T1 완료 후 LS1 해제에도 MC1 유지", motors(1), coil("X1"))
        s = scene("M2", "T1 순시 허용과 T2 정지·재기동")
        s.do(*pulse("PB2")).check("LS1 없으면 PB2로 MC2 기동 불가", motors())
        s.do(press("LS1"), *pulse("PB2")).check("LS1 감지 즉시 PB2 허용(T1 지연 완료 전)", motors(2))
        s.do(press("LS2"), wait(max(t1, t2))).check("T2 완료: MC2 정지·WL 점등", motors(1), lamp("WL"))
        s.do(release("LS2")).check("LS2 해제: MC2 재운전·WL 소등", motors(1, 2), lamp("WL", False))
        scene("LS2_START", "LS2 자동 MC2 기동").do(press("LS1"), press("LS2")).check("LS1·LS2 감지로 PB2 없이 MC2 기동", motors(2))

    # Running prefixes are explicitly chosen from the circuit, not from engine output.
    prefix = []
    if number <= 9:
        prefix += [release("SS"), *pulse("PB1")]
        if number in (2, 3):
            prefix += [wait(t)]
    else:
        if number in (10, 11, 12, 14, 15, 17, 18):
            prefix += [press("LS1")]
        if number in (13, 14):
            prefix += [press("LS2")]
        if number == 11:
            prefix += [press("PB1"), wait(t1), release("PB1")]
        else:
            prefix += pulse("PB1")
            if number == 10:
                prefix += [wait(t1)]
    running = (1, 2) if number in (6, 8) else (1,)
    s = scene("STOP", "PB0 정지·해제", "운전 중 PB0을 누르세요. 해제만으로 수동 재기동되면 자기유지 경로를 확인하세요.")
    s.do(*prefix).check("정지시험 전 모터 운전 확인", motors(*running))
    s.do(press("PB0")).check("PB0 누름: 모터 정지", motors())
    s.do(release("PB0")).check("PB0 해제 직후: 수동 모터 정지", motors())
    s = scene("EOCR", "EOCR 트립·경보·리셋", "EOCR 전원과 트립 접점, 경보 출력의 실제 연결을 확인하세요.")
    s.do(*prefix).check("EOCR 시험 전 운전 및 보호전원 확인", motors(*running), {"protections.EOCR.powered": True})
    s.do({"action": "trigger_fault", "target_id": "EOCR", "fault_type": "overload"})
    alarm = {"audible_outputs.BZ": "on"} if number <= 9 else {}
    alarm.update(lamp("YL", number not in (1, 8, 9)))
    s.check("EOCR 트립: 모터 정지 및 경보", motors(tripped=True), alarm, {"protections.EOCR.operating_state": "tripped"})
    if number in (1, 9):
        s.do(wait(f)).check("FR 경과 후 YL 점등·BZ 정지", lamp("YL"), {"audible_outputs.BZ": "off"})
        s.do(wait(f)).check("다음 FR 주기 BZ 출력·YL 소등", lamp("YL", False), {"audible_outputs.BZ": "on"})
    s.do({"action": "reset_fault", "target_id": "EOCR"})
    s.check("EOCR 리셋: 경보 해제·정지 초기상태", motors(), lamp("YL", False), {"protections.EOCR.status": "normal"}, {"audible_outputs.BZ": "off"} if number <= 9 else {})
    for channel in (1, 2):
        s = scene(f"FUSE{channel}", f"추가 고장시험 · FUSE {channel}회로 단선", "운전 중 선택한 FUSE 채널을 끊고 모터 정지를 확인하세요.")
        s.do(*prefix, {"action": "set_fuse_state", "target_id": f"F-CH{channel}", "value": False})
        s.check("해당 FUSE 단선 시 제어전원 차단·모터 정지", motors(), {f"fuses.F-CH{channel}.status": "open"})
        rows[-1].observations = [OperationExpectation(path="motors.M1", expected="forward")]
    return rows
