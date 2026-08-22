from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths
from test_operation_simulation import demo_connections
from actual_wiring_test_utils import actual_connections, source_definition


def test_free_circuit_workspace_uses_common_engine_without_answer_data(tmp_path):
    headers = {"X-User-Id": "free_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        package = client.app.state.problem_repository._get_package_internal("operation_demo_001")
        payload = {
            "name": "자기유지 자유회로",
            "circuit": package.problem.circuit.model_dump(mode="json"),
            "operation": package.problem.operation.model_dump(by_alias=True, mode="json"),
            "connections": demo_connections(),
        }
        saved = client.put("/api/free-circuits/self_hold", headers=headers, json=payload)
        assert saved.status_code == 200
        assert saved.json()["workspace_id"] == "self_hold"
        assert client.get(
            "/api/free-circuits/self_hold", headers={"X-User-Id": "other_user"}
        ).status_code == 404

        created = client.post("/api/free-circuits/self_hold/sessions", headers=headers)
        assert created.status_code == 201
        assert created.json()["problem_id"] == "free:self_hold"
        session_id = created.json()["session_id"]
        client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "set_power", "value": True},
        )
        started = client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "press_control", "control_id": "PB1"},
        )
        assert started.status_code == 200
        assert started.json()["coils"]["MC1-COIL"] is True
        released = client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "release_control", "control_id": "PB1"},
        )
        assert released.json()["coils"]["MC1-COIL"] is True


def test_free_circuit_workspace_rejects_invalid_id(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/free-circuits/not%20valid")
        assert response.status_code in {404, 422}


def test_free_circuit_templates_create_list_and_keep_users_separate(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        templates = client.get("/api/free-circuits/templates")
        assert templates.status_code == 200
        assert [item["template_id"] for item in templates.json()] == ["basic_board_001", "empty_board_001"]
        created = client.post(
            "/api/free-circuits/templates/operation_demo_001/workspaces/self_hold_01",
            headers={"X-User-Id": "student_a"}, json={"name": "자기유지 실험"},
        )
        assert created.status_code == 201
        assert created.json()["board"]["board_id"]
        assert created.json()["connections"] == []
        own = client.get("/api/free-circuits", headers={"X-User-Id": "student_a"})
        other = client.get("/api/free-circuits", headers={"X-User-Id": "student_b"})
        assert own.json()[0]["workspace_id"] == "self_hold_01"
        assert other.json() == []


def test_free_circuit_template_generates_unique_workspace_ids_from_name_only(tmp_path):
    headers = {"X-User-Id": "automatic_id_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        created = [
            client.post(
                "/api/free-circuits/workspaces",
                headers=headers,
                json={"name": f"  자동 작업공간 {index}  "},
            )
            for index in range(3)
        ]
        assert all(response.status_code == 201 for response in created)
        ids = {response.json()["workspace_id"] for response in created}
        assert len(ids) == 3
        assert all(re.fullmatch(r"fc_[A-Za-z0-9_-]+", workspace_id) for workspace_id in ids)
        assert created[0].json()["name"] == "자동 작업공간 0"
        listed = client.get("/api/free-circuits", headers=headers).json()
        assert {item["workspace_id"] for item in listed} == ids
        blank = client.post(
            "/api/free-circuits/workspaces",
            headers=headers,
            json={"name": "   "},
        )
        assert blank.status_code == 422


def test_basic_board_definition_is_independent_actual_wiring_without_answer(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/free-circuits/templates")
        assert response.status_code == 200, response.text
        template = response.json()[0]
        assert template["template_id"] == "basic_board_001"
        assert template["operation"]["simulation_mode"] == "actual_wiring"
        assert "answer" not in response.text
        assert "expected_nets" not in response.text
        device_ids = {item["device_id"] for item in template["circuit"]["devices"]}
        assert {"MCCB", "F", "X1", "X2", "T1", "T2", "MC1", "MC2", "EOCR"} <= device_ids
        assert all(item["behavior_model_id"] for item in template["circuit"]["devices"])
        external_ids = {
            item["device_id"] for item in template["wiring_semantics"]["external_devices"]
        }
        assert {"PWR", "PB0", "PB1", "PB2", "LS1", "LS2", "GL", "RL", "M1"} == external_ids
        assert "basic_board_001" not in {
            item["problem_id"] for item in client.get("/api/problems").json()
        }


def test_empty_board_palette_install_move_delete_and_power_gate(tmp_path):
    headers = {"X-User-Id": "empty_board_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        palette = client.get("/api/free-circuits/palette", headers=headers)
        assert palette.status_code == 200
        assert {item["palette_id"] for item in palette.json()["items"]} >= {
            "relay_8p", "timer_8p", "contactor_12p", "power", "pb_no", "motor"
        }
        assert "answer" not in palette.text
        assert "expected_nets" not in palette.text

        created = client.post(
            "/api/free-circuits/workspaces", headers=headers,
            json={"name": "빈 보드 시험", "template_id": "empty_board_001"},
        )
        assert created.status_code == 201, created.text
        workspace = created.json()
        assert workspace["editor"]["template_id"] == "empty_board_001"
        assert {item["item_id"] for item in workspace["board"]["items"]} == {"TB5", "TB6"}
        assert workspace["assembly"]["installed_devices"] == []
        assert client.post(f"/api/free-circuits/{workspace['workspace_id']}/sessions", headers=headers).status_code == 422

        added = client.post(
            f"/api/free-circuits/{workspace['workspace_id']}/devices", headers=headers,
            json={"palette_id": "relay_8p", "placement": {"zone": "internal_upper", "row": 0, "column": 0}},
        )
        assert added.status_code == 201, added.text
        relay = added.json()["assembly"]["installed_devices"][0]
        assert relay["instance_id"] == "X1"
        assert any(item["item_id"] == "X1" for item in added.json()["board"]["items"])
        relay_item = next(item for item in added.json()["board"]["items"] if item["item_id"] == "X1")
        relay_area = next(area for area in added.json()["board"]["forbidden_areas"] if area["area_id"] == "X1_body")
        assert (relay_area["x"], relay_area["y"], relay_area["width"], relay_area["height"]) == (
            relay_item["x"], relay_item["y"], relay_item["width"], relay_item["height"],
        )
        assert all(
            pin["y"] in {relay_area["y"], relay_area["y"] + relay_area["height"]}
            for pin in relay_item["pins"]
        )

        moved = client.put(
            f"/api/free-circuits/{workspace['workspace_id']}/devices/X1", headers=headers,
            json={"placement": {"zone": "internal_lower", "row": 0, "column": 2}},
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()["assembly"]["installed_devices"][0]["instance_id"] == "X1"
        assert moved.json()["assembly"]["installed_devices"][0]["placement"]["column"] == 2

        powered = client.post(
            f"/api/free-circuits/{workspace['workspace_id']}/devices", headers=headers,
            json={"palette_id": "power", "placement": {"zone": "external_top", "row": 0, "column": 0}},
        )
        assert powered.status_code == 201, powered.text
        session = client.post(f"/api/free-circuits/{workspace['workspace_id']}/sessions", headers=headers)
        assert session.status_code == 201, session.text
        assert session.json()["catalog_composed"] is True

        deleted = client.delete(
            f"/api/free-circuits/{workspace['workspace_id']}/devices/X1", headers=headers,
        )
        assert deleted.status_code == 200
        assert [item["instance_id"] for item in deleted.json()["assembly"]["installed_devices"]] == ["PWR1"]


def test_empty_board_rejects_overlap_wrong_zone_unknown_model_and_preserves_old_workspace(tmp_path):
    headers = {"X-User-Id": "assembly_validation"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        workspace = client.post(
            "/api/free-circuits/workspaces", headers=headers,
            json={"name": "배치 검증", "template_id": "empty_board_001"},
        ).json()
        path = f"/api/free-circuits/{workspace['workspace_id']}/devices"
        placement = {"zone": "internal_upper", "row": 0, "column": 0}
        assert client.post(path, headers=headers, json={"palette_id": "relay_8p", "placement": placement}).status_code == 201
        assert client.post(path, headers=headers, json={"palette_id": "timer_8p", "placement": placement}).status_code == 422
        assert client.post(path, headers=headers, json={"palette_id": "pb_no", "placement": placement}).status_code == 422
        assert client.post(path, headers=headers, json={"palette_id": "not_allowed", "placement": placement}).status_code == 422

        timer = client.post(
            path, headers=headers,
            json={"palette_id": "timer_8p", "placement": {"zone": "internal_lower", "row": 0, "column": 1}},
        ).json()["assembly"]["installed_devices"][-1]
        changed = client.put(
            f"/api/free-circuits/{workspace['workspace_id']}/devices/{timer['instance_id']}",
            headers=headers, json={"properties": {**timer["properties"], "delay_ms": 2500}},
        )
        assert changed.status_code == 200, changed.text
        assert next(item for item in changed.json()["assembly"]["installed_devices"] if item["instance_id"] == timer["instance_id"])["properties"]["delay_ms"] == 2500
        invalid = client.put(
            f"/api/free-circuits/{workspace['workspace_id']}/devices/{timer['instance_id']}",
            headers=headers, json={"properties": {**timer["properties"], "delay_ms": 0}},
        )
        assert invalid.status_code == 422

        legacy = client.post(
            "/api/free-circuits/templates/operation_demo_001/workspaces/old_free",
            headers=headers, json={"name": "기존 작업공간"},
        )
        assert legacy.status_code == 201
        assert legacy.json()["assembly"] is None


def test_basic_board_same_name_gets_distinct_ids_and_legacy_api_remains(tmp_path):
    headers = {"X-User-Id": "basic_board_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        first = client.post("/api/free-circuits/workspaces", headers=headers, json={"name": "같은 이름"})
        second = client.post("/api/free-circuits/workspaces", headers=headers, json={"name": "같은 이름"})
        assert first.status_code == second.status_code == 201
        assert first.json()["workspace_id"] != second.json()["workspace_id"]
        assert first.json()["editor"]["template_id"] == "basic_board_001"
        assert first.json()["connections"] == []
        legacy = client.post(
            "/api/free-circuits/templates/operation_demo_001/workspaces/legacy_saved",
            headers=headers, json={"name": "기존 형식"},
        )
        assert legacy.status_code == 201
        assert legacy.json()["editor"]["template_id"] == "operation_demo_001"


def test_free_circuit_rejects_unknown_duplicate_and_tb_bank_over_capacity(tmp_path):
    headers = {"X-User-Id": "free_validation"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        created = client.post(
            "/api/free-circuits/templates/operation_demo_001/workspaces/validate_wires",
            headers=headers, json={"name": "검증"},
        ).json()
        created["connections"] = [{"from": "NO-SUCH", "to": "TB5-01", "wire_color": "yellow", "pair_display_color": "#64748b"}]
        assert client.put("/api/free-circuits/validate_wires", headers=headers, json={key: value for key, value in created.items() if key not in {"workspace_id", "updated_at"}}).status_code == 422

        created = client.get("/api/free-circuits/validate_wires", headers=headers).json()
        wire = {"from": "PWR-L1", "to": "TB5-01", "wire_color": "brown", "pair_display_color": "#64748b"}
        created["connections"] = [wire, wire]
        response = client.put("/api/free-circuits/validate_wires", headers=headers, json={key: value for key, value in created.items() if key not in {"workspace_id", "updated_at"}})
        assert response.status_code == 422
        assert "중복" in response.json()["detail"]


def test_free_circuit_diagnostics_do_not_grade_answer(tmp_path):
    headers = {"X-User-Id": "diagnostic_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        client.post(
            "/api/free-circuits/templates/operation_demo_001/workspaces/diagnostic",
            headers=headers, json={"name": "진단"},
        )
        response = client.get("/api/free-circuits/diagnostic/diagnostics", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "attention"
        assert any(item["code"] == "empty_wiring" for item in response.json()["diagnostics"])
        assert "expected_nets" not in response.text


def test_free_circuit_session_composes_catalog_for_actual_wiring(tmp_path):
    headers = {"X-User-Id": "actual_wiring_user"}
    circuit, operation = source_definition()
    payload = {
        "name": "실제 결선 엔진 시험",
        "circuit": circuit.model_dump(mode="json"),
        "operation": operation.model_dump(by_alias=True, mode="json"),
        "connections": [
            item.model_dump(by_alias=True, mode="json") for item in actual_connections()
        ],
    }
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put("/api/free-circuits/actual_runtime", headers=headers, json=payload)
        assert saved.status_code == 200, saved.text
        created = client.post(
            "/api/free-circuits/actual_runtime/sessions", headers=headers
        )
        assert created.status_code == 201, created.text
        state = created.json()
        assert state["simulation_mode"] == "actual_wiring"
        assert state["catalog_composed"] is True
        assert "MC1-MAIN1" in state["contacts"]
        assert "expected_nets" not in created.text
