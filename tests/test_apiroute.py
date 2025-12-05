from uuid import uuid4

from fastapi.encoders import jsonable_encoder


# CREATE CAMERA (POST)
def test_add_camera_api(client, camera_payload_json):
    resp = client.post("/cameras/", json=camera_payload_json)
    assert resp.status_code == 200

    data = resp.json()
    assert data["camera_name"] == camera_payload_json["camera_name"]
    assert "camera_id" in data


# GET CAMERA (GET)
def test_get_camera_api_success(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    resp = client.get(f"/cameras/{cid}")
    assert resp.status_code == 200
    assert resp.json()["camera_id"] == cid


def test_get_camera_api_not_found(client):
    resp = client.get(f"/cameras/{uuid4()}")
    assert resp.status_code == 404


# DELETE CAMERA
def test_delete_camera_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    resp = client.delete(f"/cameras/{cid}")
    assert resp.status_code == 200

    # verify deleted
    resp2 = client.get(f"/cameras/{cid}")
    assert resp2.status_code == 404


# UPDATE CAMERA
def test_update_camera_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    resp = client.patch(f"/cameras/{cid}", json={"camera_name": "UpdatedAPI"})
    assert resp.status_code == 200
    assert resp.json()["camera_name"] == "UpdatedAPI"


def test_update_camera_api_not_found(client):
    resp = client.patch(f"/cameras/{uuid4()}", json={"camera_name": "X"})
    assert resp.status_code == 404


# LIST CAMERAS (GET)
def test_list_cameras_api(client, camera_payload_json):
    # Create three cameras with different IP addresses
    for i in range(3):
        cam_json = camera_payload_json.copy()
        cam_json["camera_name"] = f"Cam{i}"
        cam_json["network_setup"]["ip_address"] = f"192.168.0.{20 + i}"
        client.post("/cameras/", json=cam_json)

    resp = client.get("/cameras/")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) >= 3


# LIST CAMERAS WITH FILTER (model)
def test_list_cameras_filter_model_api(client, camera_payload_json):
    payload1 = camera_payload_json.copy()
    payload1["camera_model"] = "ModelA"
    payload1["network_setup"]["ip_address"] = "192.168.0.50"
    client.post("/cameras/", json=payload1)

    payload2 = camera_payload_json.copy()
    payload2["camera_model"] = "SpecialModel"
    payload2["network_setup"]["ip_address"] = "192.168.0.51"
    client.post("/cameras/", json=payload2)

    resp = client.get("/cameras/?model=SpecialModel")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["camera_model"] == "SpecialModel"


# LIST CAMERAS- IP RANGE FILTER.
def test_list_cameras_filter_ip_range_api(client, camera_payload_json):
    payload1 = camera_payload_json.copy()
    payload1["camera_name"] = "CamA"
    payload1["network_setup"]["ip_address"] = "192.168.0.10"
    client.post("/cameras/", json=payload1)

    payload2 = camera_payload_json.copy()
    payload2["camera_name"] = "CamB"
    payload2["network_setup"]["ip_address"] = "192.168.0.20"
    client.post("/cameras/", json=payload2)

    # Filter from 192.168.0.15 to 192.168.0.25 → should return only CamB
    resp = client.get("/cameras/?ip_from=192.168.0.15&ip_to=192.168.0.25")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["network_setup"]["ip_address"] == "192.168.0.20"


# LIST CAMERAS- ONLINE/OFFLINE :
from datetime import datetime, timedelta, timezone


# ADD FEED
def test_add_feed_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    feed = {"feed_protocol": "rtsp", "feed_port": 9000, "feed_path": "/new"}

    resp = client.post(f"/cameras/{cid}/feeds", json=feed)
    assert resp.status_code == 200

    body = resp.json()
    assert "feed" in body
    assert body["feed"] is not None


def test_add_feed_api_duplicate(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    # Same protocol + port as existing feed
    f = camera_payload_json["available_feeds"][0]

    resp = client.post(
        f"/cameras/{cid}/feeds",
        json={
            "feed_protocol": f["feed_protocol"],
            "feed_port": f["feed_port"],
            "feed_path": "/dup",
        },
    )

    assert resp.status_code == 409


# LIST FEEDS
def test_list_feeds_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    resp = client.get(f"/cameras/{cid}/feeds")
    assert resp.status_code == 200

    feeds = resp.json()
    assert len(feeds) == 1


# UPDATE FEED
def test_update_feed_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    feeds = client.get(f"/cameras/{cid}/feeds").json()
    fid = feeds[0]["feed_id"]

    resp = client.patch(f"/cameras/{cid}/feeds/{fid}", json={"feed_port": 9999})
    assert resp.status_code == 200

    updated = resp.json()["feed"]
    assert updated["feed_port"] == 9999


# DELETE FEED
def test_delete_feed_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    feeds = client.get(f"/cameras/{cid}/feeds").json()
    fid = feeds[0]["feed_id"]

    resp = client.delete(f"/cameras/{cid}/feeds/{fid}")
    assert resp.status_code == 200

    resp2 = client.get(f"/cameras/{cid}/feeds")
    assert len(resp2.json()) == 0


# FEED FILTERING
def test_list_feeds_filter_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    client.post(
        f"/cameras/{cid}/feeds",
        json={"feed_protocol": "rtsp", "feed_port": 1234, "feed_path": "/hd"},
    )

    resp = client.get(f"/cameras/{cid}/feeds?port=1234")
    assert resp.status_code == 200

    feeds = resp.json()
    assert len(feeds) == 1
    assert feeds[0]["feed_port"] == 1234


# LIST FEEDS-PAGINATION:
def test_list_feeds_pagination_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    # Add 4 feeds
    for i in range(4):
        client.post(
            f"/cameras/{cid}/feeds",
            json={
                "feed_protocol": "rtsp",
                "feed_port": 8000 + i,
                "feed_path": f"/f{i}",
            },
        )

    resp_page1 = client.get(f"/cameras/{cid}/feeds?page=1&page_size=2")
    resp_page2 = client.get(f"/cameras/{cid}/feeds?page=2&page_size=2")

    assert resp_page1.status_code == 200
    assert resp_page2.status_code == 200

    page1 = resp_page1.json()
    page2 = resp_page2.json()

    assert len(page1) == 2
    assert len(page2) == 2


# HEARTBEAT AND STATUS
def test_heartbeat_and_status_api(client, camera_payload_json):
    created = client.post("/cameras/", json=camera_payload_json).json()
    cid = created["camera_id"]

    hb = client.post(f"/cameras/{cid}/heartbeat")
    assert hb.status_code == 200

    status = client.get(f"/cameras/{cid}/status")
    assert status.status_code == 200
    assert "is_online" in status.json()
