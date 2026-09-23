"""
CrowdEye AI - Phase 6 End-to-End Test Suite
Tests:
1. Risk score 90 -> Expected: Critical alert created
2. Duplicate alert generation -> Expected: Only one active alert
3. Operator login -> Expected: Can resolve alerts
4. Operator camera creation -> Expected: Permission denied (403)
5. Multiple cameras -> Expected: Camera grid updates & overview metrics
"""

import sys
import os
import uuid

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from app.main import app
from app.services.alert_service import AlertService, _alerts_cache
from app.services.camera_service import CameraService, _cameras_cache

client = TestClient(app)


def test_scenario_1_critical_alert_on_score_90():
    print("\n--- TEST 1: Risk score 90 -> Critical alert created ---")
    test_cam_id = str(uuid.uuid4())
    risk_payload = {
        "zone": "Zone-Test-Crit",
        "risk_score": 90.0,
        "risk_level": "CRITICAL",
        "reasons": ["Extreme crowd density exceeding 4.5 ppl/m²"]
    }
    
    alerts = AlertService.evaluate_and_create_alert(risk_payload, camera_id=test_cam_id)
    assert len(alerts) >= 1, "Expected at least 1 alert generated"
    created = alerts[0]
    print(f"Generated alert: {created}")
    assert created["level"] == "CRITICAL", f"Expected level CRITICAL, got {created['level']}"
    assert "High crowd risk detected" in created["message"] or "Extreme crowd density" in created["message"]
    
    # Verify in alert query
    active_alerts = AlertService.get_alerts(status="ACTIVE", camera_id=test_cam_id)
    assert any(a["id"] == created["id"] for a in active_alerts), "Created alert not found in active list"
    print("[PASS] Test 1: Risk score 90 successfully generated CRITICAL alert.")
    return created["id"], test_cam_id


def test_scenario_2_duplicate_alert_protection(cam_id: str):
    print("\n--- TEST 2: Duplicate alert generation -> Only one active alert ---")
    # Count active alerts for this zone
    zone_name = "Zone-Test-Crit"
    initial_actives = [a for a in AlertService.get_alerts(status="ACTIVE") if (a.get("zone_name") == zone_name or a.get("zone") == zone_name)]
    initial_count = len(initial_actives)
    assert initial_count == 1, f"Expected 1 active alert before duplicate test, found {initial_count}"

    # Re-evaluate with score 94 for same camera and same zone
    duplicate_payload = {
        "zone": zone_name,
        "risk_score": 94.0,
        "risk_level": "CRITICAL",
        "reasons": ["Continued extreme crowd bottleneck"]
    }
    second_eval = AlertService.evaluate_and_create_alert(duplicate_payload, camera_id=cam_id)
    print(f"Second evaluation result: {second_eval}")
    assert len(second_eval) == 1
    assert second_eval[0].get("duplicate_suppressed") is True or second_eval[0]["id"] == initial_actives[0]["id"]

    # Verify still exactly 1 active alert for this zone
    current_actives = [a for a in AlertService.get_alerts(status="ACTIVE") if (a.get("zone_name") == zone_name or a.get("zone") == zone_name)]
    print(f"Current active alerts count for {zone_name}: {len(current_actives)}")
    assert len(current_actives) == 1, f"Expected exactly 1 active alert, but found {len(current_actives)}"
    print("[PASS] Test 2: Duplicate alert successfully suppressed (constraint maintained).")


def test_scenario_3_operator_resolve_alert(alert_id: str):
    print("\n--- TEST 3: Operator login -> Can resolve alerts ---")
    # Resolve via HTTP API with OPERATOR role
    response = client.put(
        f"/alerts/{alert_id}/resolve",
        headers={"X-User-Role": "OPERATOR"}
    )
    print(f"Operator resolve HTTP status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "RESOLVED", f"Expected status RESOLVED, got {data.status}"
    assert data.get("resolved_at") is not None, "Expected resolved_at timestamp"

    # Verify no longer returned in active list
    active_now = [a for a in AlertService.get_alerts(status="ACTIVE") if a["id"] == alert_id]
    assert len(active_now) == 0, f"Alert {alert_id} should not be in ACTIVE list anymore"
    print("[PASS] Test 3: Operator successfully resolved alert.")


def test_scenario_4_operator_camera_creation_forbidden():
    print("\n--- TEST 4: Operator camera creation -> Permission denied (403) ---")
    cam_payload = {
        "camera_name": "Unauthorized Operator Cam",
        "zone": "Zone X",
        "location": "Unauthorized Area",
        "status": "ACTIVE"
    }

    # 1. Attempt creation as OPERATOR -> Expected: 403 Forbidden
    resp_op = client.post(
        "/cameras",
        json=cam_payload,
        headers={"X-User-Role": "OPERATOR"}
    )
    print(f"Operator camera creation HTTP status: {resp_op.status_code}")
    assert resp_op.status_code == 403, f"Expected 403 Forbidden, got {resp_op.status_code}: {resp_op.text}"
    print(f"Forbidden detail: {resp_op.json().get('detail')}")

    # 2. Attempt creation as ADMIN -> Expected: 201 Created
    resp_admin = client.post(
        "/cameras",
        json=cam_payload,
        headers={"X-User-Role": "ADMIN"}
    )
    print(f"Admin camera creation HTTP status: {resp_admin.status_code}")
    assert resp_admin.status_code == 201, f"Expected 201 Created, got {resp_admin.status_code}: {resp_admin.text}"
    created_cam = resp_admin.json()
    assert created_cam["camera_name"] == cam_payload["camera_name"]
    print(f"Admin registered camera ID: {created_cam['id']}")
    print("[PASS] Test 4: RBAC properly blocks OPERATOR camera creation and permits ADMIN.")


def test_scenario_5_multiple_cameras_grid_and_overview():
    print("\n--- TEST 5: Multiple cameras -> Camera grid updates & overview ---")
    # 1. Query cameras list
    resp_cams = client.get("/cameras", headers={"X-User-Role": "OPERATOR"})
    assert resp_cams.status_code == 200
    cams = resp_cams.json()
    print(f"Total cameras returned: {len(cams)}")
    assert len(cams) >= 2, f"Expected multiple cameras, got {len(cams)}"
    for c in cams[:3]:
        print(f"  Camera: {c['camera_name']} | Status: {c['status']} | People: {c.get('people_count')} | Risk: {c.get('risk_level')}")

    # 2. Query Dashboard Overview (TASK 6)
    resp_overview = client.get("/dashboard/overview", headers={"X-User-Role": "OPERATOR"})
    assert resp_overview.status_code == 200
    overview = resp_overview.json()
    print(f"Dashboard Overview: {overview}")
    assert "total_cameras" in overview
    assert "active_alerts" in overview
    assert "high_risk_zones" in overview
    assert "detected_people" in overview
    assert overview["total_cameras"] >= 1

    # 3. Query 1-minute aggregated analytics (TASK 13)
    resp_analytics = client.get("/analytics/timeline?window_minutes=15")
    assert resp_analytics.status_code == 200
    analytics = resp_analytics.json()
    print(f"Analytics Aggregation: {analytics.get('aggregation')}, points: {analytics.get('data_points')}")
    assert analytics.get("aggregation") == "1-minute averages"
    assert len(analytics.get("timeline", [])) > 0

    print("[PASS] Test 5: Camera grid, dashboard overview, and 1-minute aggregation fully operational.")


if __name__ == "__main__":
    print("==================================================")
    print("Running CrowdEye AI Phase 6 Pipeline Verification")
    print("==================================================")
    
    alert_id, cam_id = test_scenario_1_critical_alert_on_score_90()
    test_scenario_2_duplicate_alert_protection(cam_id)
    test_scenario_3_operator_resolve_alert(alert_id)
    test_scenario_4_operator_camera_creation_forbidden()
    test_scenario_5_multiple_cameras_grid_and_overview()

    print("\n==================================================")
    print("ALL 5 PHASE 6 TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("==================================================")
