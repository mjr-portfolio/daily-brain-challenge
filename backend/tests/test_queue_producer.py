from scripts.run_queue_producer import producer_exit_code
from app.services.queue_manager import SKIPPED_LOCK_HELD


def test_producer_exits_nonzero_when_horizon_has_failures() -> None:
    assert producer_exit_code({"failures": [{"phase": "horizon"}]}) == 1


def test_producer_exits_zero_when_lock_is_held() -> None:
    assert (
        producer_exit_code({"failures": [], "skipped": SKIPPED_LOCK_HELD}) == 0
    )


def test_producer_exits_zero_when_queue_is_full() -> None:
    assert producer_exit_code({"failures": []}) == 0
