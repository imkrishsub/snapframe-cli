from snapframe.config import DeviceFrameConfig, _make_device_frame


def test_device_frame_config_default_finish():
    cfg = DeviceFrameConfig()
    assert cfg.finish == "black"


def test_make_device_frame_reads_finish():
    cfg = _make_device_frame({"finish": "natural-titanium"})
    assert cfg.finish == "natural-titanium"


def test_make_device_frame_finish_defaults_to_black():
    cfg = _make_device_frame({})
    assert cfg.finish == "black"


def test_make_device_frame_reads_model_and_enabled():
    cfg = _make_device_frame({"enabled": True, "model": "iphone-16-pro", "finish": "matte-gray"})
    assert cfg.enabled is True
    assert cfg.model == "iphone-16-pro"
    assert cfg.finish == "matte-gray"
