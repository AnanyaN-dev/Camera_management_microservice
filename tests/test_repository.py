# Tests specific to the repository layer.
# The repository should:
#   - store data in-memory
#   - update correctly
#   - return None/False for missing items

from uuid import uuid4

from app.models.schemas import CameraUpdate, FeedUpdate, VideoFeedSetup


def test_add_camera(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    assert cam.camera_id is not None
    assert cam.camera_name == camera_payload.camera_name
    assert len(cam.available_feeds) == 1


def test_get_camera_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    retrieved = repo.get_camera(cam.camera_id)

    assert retrieved is not None
    assert retrieved.camera_id == cam.camera_id


def test_get_camera_not_found(repo):
    assert repo.get_camera(uuid4()) is None


def test_remove_camera_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    assert repo.remove_camera(cam.camera_id) is True
    assert repo.get_camera(cam.camera_id) is None


def test_remove_camera_not_found(repo):
    assert repo.remove_camera(uuid4()) is False


def test_update_camera(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    updates = CameraUpdate(camera_name="UpdatedCam")
    updated = repo.update_camera(cam.camera_id, updates)

    assert updated is not None
    assert updated.camera_name == "UpdatedCam"


def test_update_camera_not_found(repo):
    updates = CameraUpdate(camera_name="X")
    assert repo.update_camera(uuid4(), updates) is None


def test_add_feed(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    new_feed = repo.add_feed(
        cam.camera_id,
        VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/abc"),
    )

    assert new_feed is not None
    assert len(repo.get_camera(cam.camera_id).available_feeds) == 2


def test_add_feed_camera_not_found(repo):
    feed = repo.add_feed(
        uuid4(), VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/abc")
    )
    assert feed is None


def test_update_feed_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    feed_id = cam.available_feeds[0].feed_id

    updated = repo.update_feed(cam.camera_id, feed_id, FeedUpdate(feed_port=9999))

    assert updated is not None
    assert updated.feed_port == 9999


def test_update_feed_not_found(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    assert repo.update_feed(cam.camera_id, uuid4(), FeedUpdate(feed_path="/x")) is None


def test_remove_feed_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    feed_id = cam.available_feeds[0].feed_id

    assert repo.remove_feed(cam.camera_id, feed_id) is True
    assert len(repo.get_camera(cam.camera_id).available_feeds) == 0


def test_remove_feed_not_found(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    assert repo.remove_feed(cam.camera_id, uuid4()) is False


def test_get_feed_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    feed = cam.available_feeds[0]

    retrieved = repo.get_feed(cam.camera_id, feed.feed_id)
    assert retrieved is not None
    assert retrieved.feed_id == feed.feed_id


def test_get_feed_not_found(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    assert repo.get_feed(cam.camera_id, uuid4()) is None


from uuid import uuid4

from app.models.schemas import CameraUpdate, FeedUpdate, VideoFeedSetup


def test_add_camera(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    assert cam.camera_id is not None
    assert cam.camera_name == camera_payload.camera_name
    assert cam.camera_model == camera_payload.camera_model
    assert len(cam.available_feeds) == 1


def test_get_camera_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    retrieved = repo.get_camera(cam.camera_id)

    assert retrieved is not None
    assert retrieved.camera_id == cam.camera_id


def test_get_camera_not_found(repo):
    assert repo.get_camera(uuid4()) is None


def test_remove_camera_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    assert repo.remove_camera(cam.camera_id) is True
    assert repo.get_camera(cam.camera_id) is None


def test_remove_camera_not_found(repo):
    assert repo.remove_camera(uuid4()) is False


def test_update_camera(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    updates = CameraUpdate(camera_name="Updated")
    updated = repo.update_camera(cam.camera_id, updates)

    assert updated is not None
    assert updated.camera_name == "Updated"


def test_update_camera_not_found(repo):
    updates = CameraUpdate(camera_name="NewName")
    assert repo.update_camera(uuid4(), updates) is None


def test_add_feed(repo, camera_payload):
    cam = repo.add_camera(camera_payload)

    new_feed = repo.add_feed(
        cam.camera_id,
        VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/cam2"),
    )

    assert new_feed is not None
    assert len(repo.get_camera(cam.camera_id).available_feeds) == 2


def test_add_feed_camera_not_found(repo):
    feed = repo.add_feed(
        uuid4(), VideoFeedSetup(feed_protocol="rtsp", feed_port=9000, feed_path="/abc")
    )
    assert feed is None


def test_update_feed_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    fid = cam.available_feeds[0].feed_id

    updated = repo.update_feed(cam.camera_id, fid, FeedUpdate(feed_port=9999))

    assert updated is not None
    assert updated.feed_port == 9999


def test_update_feed_not_found(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    assert (
        repo.update_feed(cam.camera_id, uuid4(), FeedUpdate(feed_path="/wrong")) is None
    )


def test_remove_feed_success(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    fid = cam.available_feeds[0].feed_id

    result = repo.remove_feed(cam.camera_id, fid)
    assert result is True
    assert len(repo.get_camera(cam.camera_id).available_feeds) == 0


def test_remove_feed_not_found(repo, camera_payload):
    cam = repo.add_camera(camera_payload)
    assert repo.remove_feed(cam.camera_id, uuid4()) is False
