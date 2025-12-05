from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.schemas import (CameraNetworkInfo, CameraUpdate, FeedUpdate,
                                NewCameraData, VideoFeedSetup)


# CAMERA TESTS
def test_add_camera(service, camera_payload):
    cam = service.add_camera(camera_payload)
    assert cam.camera_id is not None
    assert cam.camera_model == camera_payload.camera_model
    assert len(cam.available_feeds) == 1


def test_add_camera_duplicate_ip(service, camera_payload):
    """Should fail if another camera with same IP is added"""
    service.add_camera(camera_payload)

    dup = camera_payload.model_copy()
    dup.camera_name = "AnotherCam"  # name can differ but IP same

    with pytest.raises(ConflictError):
        service.add_camera(dup)


def test_add_camera_duplicate_name_model(service, camera_payload):
    """Should fail if camera with same name+model exists"""
    service.add_camera(camera_payload)

    dup = camera_payload.model_copy()
    dup.network_setup = CameraNetworkInfo(ip_address="10.0.0.1")  # IP is different

    with pytest.raises(ConflictError):
        service.add_camera(dup)


def test_get_camera_success(service, camera_payload):
    cam = service.add_camera(camera_payload)
    retrieved = service.get_camera(cam.camera_id)
    assert retrieved.camera_id == cam.camera_id


def test_get_camera_not_found(service):
    with pytest.raises(NotFoundError):
        service.get_camera(uuid4())


def test_remove_camera_success(service, camera_payload):
    cam = service.add_camera(camera_payload)
    assert service.remove_camera(cam.camera_id) is True

    with pytest.raises(NotFoundError):
        service.get_camera(cam.camera_id)


def test_remove_camera_not_found(service):
    with pytest.raises(NotFoundError):
        service.remove_camera(uuid4())


def test_update_camera(service, camera_payload):
    cam = service.add_camera(camera_payload)

    updates = CameraUpdate(camera_name="UpdatedCam")
    updated = service.update_camera(cam.camera_id, updates)

    assert updated.camera_name == "UpdatedCam"


def test_update_camera_not_found(service):
    with pytest.raises(NotFoundError):
        service.update_camera(uuid4(), CameraUpdate(camera_name="X"))


# FEED TESTS
def test_add_feed_success(service, camera_payload):
    cam = service.add_camera(camera_payload)

    feed = service.add_feed(
        cam.camera_id,
        VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/new"),
    )

    assert feed.feed_id is not None
    assert len(service.get_camera(cam.camera_id).available_feeds) == 2


def test_add_feed_duplicate_same_camera(service, camera_payload):
    """Cannot add same (protocol + port) on same camera"""
    cam = service.add_camera(camera_payload)
    f = camera_payload.available_feeds[0]

    with pytest.raises(ConflictError):
        service.add_feed(
            cam.camera_id,
            VideoFeedSetup(
                feed_protocol=f.feed_protocol,
                feed_port=f.feed_port,
                feed_path="/main2",
            ),
        )


def test_add_feed_reuse_port_across_cameras_allowed(service, camera_payload):
    cam1 = service.add_camera(camera_payload)

    cam2_payload = camera_payload.model_copy()
    cam2_payload.camera_name = "AnotherCam"
    cam2_payload.camera_model = "AnotherModel"
    cam2_payload.network_setup = CameraNetworkInfo(ip_address="10.0.0.2")
    cam2_payload.available_feeds = []

    cam2 = service.add_camera(cam2_payload)

    # Reuse port 554 → SHOULD NOT raise error
    feed = service.add_feed(
        cam2.camera_id,
        VideoFeedSetup(feed_protocol="rtsp", feed_port=554, feed_path="/x"),
    )

    assert feed.feed_port == 554


def test_add_feed_camera_not_found(service):
    with pytest.raises(NotFoundError):
        service.add_feed(
            uuid4(),
            VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/"),
        )


def test_update_feed_success(service, camera_payload):
    cam = service.add_camera(camera_payload)
    feed_id = cam.available_feeds[0].feed_id

    updated = service.update_feed(cam.camera_id, feed_id, FeedUpdate(feed_port=9999))
    assert updated.feed_port == 9999


def test_update_feed_not_found(service, camera_payload):
    cam = service.add_camera(camera_payload)

    with pytest.raises(NotFoundError):
        service.update_feed(cam.camera_id, uuid4(), FeedUpdate(feed_path="/x"))


def test_remove_feed_success(service, camera_payload):
    cam = service.add_camera(camera_payload)
    feed_id = cam.available_feeds[0].feed_id

    assert service.remove_feed(cam.camera_id, feed_id) is True
    assert len(service.get_camera(cam.camera_id).available_feeds) == 0


def test_remove_feed_not_found(service, camera_payload):
    cam = service.add_camera(camera_payload)

    with pytest.raises(NotFoundError):
        service.remove_feed(cam.camera_id, uuid4())


# HEARTBEAT + STATUS
def test_heartbeat(service, camera_payload):
    cam = service.add_camera(camera_payload)

    before = datetime.now(timezone.utc)
    res = service.heartbeat(cam.camera_id)
    after = datetime.now(timezone.utc)

    assert res["message"] == "Heartbeat updated"

    updated_cam = service.get_camera(cam.camera_id)
    assert before <= updated_cam.last_known_checkin <= after


def test_heartbeat_not_found(service):
    with pytest.raises(NotFoundError):
        service.heartbeat(uuid4())


# FILTERS + PAGINATION
def test_list_cameras_filter_model(service, camera_payload):
    cam1 = service.add_camera(camera_payload)

    other = camera_payload.model_copy()
    other.camera_model = "SpecialModel"
    other.camera_name = "SpecialCam"
    other.network_setup = CameraNetworkInfo(ip_address="10.0.0.2")

    cam2 = service.add_camera(other)

    result = service.list_cameras(model="SpecialModel")

    assert len(result) == 1
    assert result[0].camera_id == cam2.camera_id


def test_list_cameras_pagination(service, camera_payload):
    # Add 5 different cameras
    for i in range(5):
        temp = camera_payload.model_copy()
        temp.camera_name = f"Cam{i}"
        temp.camera_model = f"M{i}"
        temp.network_setup = CameraNetworkInfo(ip_address=f"192.168.0.{20+i}")
        temp.available_feeds = []
        service.add_camera(temp)

    page1 = service.list_cameras(page=1, page_size=2)
    page2 = service.list_cameras(page=2, page_size=2)

    assert len(page1) == 2
    assert len(page2) == 2


def test_list_cameras_filter_ip_range(service, camera_payload):
    # Camera 1 inside range
    cam1 = camera_payload.model_copy()
    cam1.camera_name = "Cam1"
    cam1.camera_model = "M1"
    cam1.network_setup = CameraNetworkInfo(ip_address="192.168.1.10")
    cam1.available_feeds = []
    c1 = service.add_camera(cam1)

    # Camera 2 inside range
    cam2 = camera_payload.model_copy()
    cam2.camera_name = "Cam2"
    cam2.camera_model = "M2"
    cam2.network_setup = CameraNetworkInfo(ip_address="192.168.1.20")
    cam2.available_feeds = []
    c2 = service.add_camera(cam2)

    # Camera 3 outside range
    cam3 = camera_payload.model_copy()
    cam3.camera_name = "Cam3"
    cam3.camera_model = "M3"
    cam3.network_setup = CameraNetworkInfo(ip_address="192.168.1.50")
    cam3.available_feeds = []
    service.add_camera(cam3)

    result = service.list_cameras(ip_from="192.168.1.10", ip_to="192.168.1.25")

    assert len(result) == 2
    assert {c.camera_id for c in result} == {c1.camera_id, c2.camera_id}


# STATUS:
def test_list_cameras_filter_online(service, camera_payload):
    # Camera 1 (online)
    cam1 = service.add_camera(camera_payload)
    service.heartbeat(cam1.camera_id)

    # Camera 2 (offline)
    cam2_payload = camera_payload.model_copy()
    cam2_payload.camera_name = "Other"
    cam2_payload.camera_model = "OtherModel"
    cam2_payload.network_setup = CameraNetworkInfo(ip_address="10.0.0.2")
    cam2 = service.add_camera(cam2_payload)
    cam2.last_known_checkin = None

    online_list = service.list_cameras(online=True)
    offline_list = service.list_cameras(online=False)

    assert cam1.camera_id in {c.camera_id for c in online_list}
    assert cam2.camera_id in {c.camera_id for c in offline_list}
