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


def test_add_feed_duplicate_port_global(service, camera_payload):
    """Feed port cannot be reused across cameras"""
    cam1 = service.add_camera(camera_payload)

    cam2_payload = camera_payload.model_copy()
    cam2_payload.camera_name = "AnotherCam"
    cam2_payload.camera_model = "AnotherModel"
    cam2_payload.network_setup = CameraNetworkInfo(ip_address="10.0.0.2")
    cam2_payload.available_feeds = []

    cam2 = service.add_camera(cam2_payload)

    # reuse port 554 → should fail
    with pytest.raises(ConflictError):
        service.add_feed(
            cam2.camera_id,
            VideoFeedSetup(feed_protocol="rtsp", feed_port=554, feed_path="/x"),
        )


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


def test_is_online(service, camera_payload):
    cam = service.add_camera(camera_payload)

    service.heartbeat(cam.camera_id)
    assert service.is_online(cam.camera_id) is True

    cam.last_known_checkin = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert service.is_online(cam.camera_id) is False


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
