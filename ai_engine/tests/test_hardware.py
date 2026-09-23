def test_hardware_shape():
    from ai_engine.hardware import inspect_hardware
    info = inspect_hardware()
    assert "gpu_available" in info
    assert "vram_gb" in info
