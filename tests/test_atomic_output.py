from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from core.filesystem import atomic_output_path


def test_competing_writers_publish_only_one_complete_result(tmp_path):
    destination = tmp_path / "result"
    ready = Barrier(2, timeout=5)

    def write(payload):
        try:
            with atomic_output_path(destination) as temporary:
                with open(temporary, "wb") as output:
                    output.write(payload)
                ready.wait()
        except FileExistsError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        winners = list(pool.map(write, (b"first", b"second")))
    assert sum(winners) == 1
    assert destination.read_bytes() == (b"first" if winners[0] else b"second")
    assert list(tmp_path.iterdir()) == [destination]


def test_cancelled_write_cleans_only_its_temporary_file(tmp_path):
    destination = tmp_path / "result"
    destination.write_bytes(b"existing")
    with pytest.raises(InterruptedError), atomic_output_path(destination):
        raise InterruptedError
    assert destination.read_bytes() == b"existing"
    assert list(tmp_path.iterdir()) == [destination]
