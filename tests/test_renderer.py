# tests/test_renderer.py
try:
    from snapframe.renderer import FINISH_PRESETS, generate_frame
except ImportError:
    FINISH_PRESETS = None
    generate_frame = None


def test_placeholder():
    pass
