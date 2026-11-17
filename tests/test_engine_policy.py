from core.workers.engine_policy import adaptive_timeout


def test_large_documents_get_more_time_with_a_fixed_upper_limit():
    assert adaptive_timeout(0) == 120
    assert adaptive_timeout(8 * 1024 * 1024) == 180
    assert adaptive_timeout(24 * 1024 * 1024) == 300
    assert adaptive_timeout(1000 * 1024 * 1024) == 600
