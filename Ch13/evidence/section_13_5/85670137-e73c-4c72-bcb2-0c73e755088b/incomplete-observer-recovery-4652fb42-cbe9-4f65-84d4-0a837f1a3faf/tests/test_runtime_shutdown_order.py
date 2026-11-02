"""A failed physical stop must remain failed, not skip owned resource cleanup."""
import pytest
import run_navigation_13_5 as runner


@pytest.mark.parametrize('failed', ['', 'measured_stop', 'deactivate', 'carry_terminal',
                                  'native_stop', 'consumers_stop'])
def test_failed_stage_does_not_skip_consumers_but_clock_waits_for_consumer_exit(failed):
    assert hasattr(runner, 'shutdown_runtime_in_order'), 'failure-safe runtime teardown missing'
    calls = []
    def operation(name):
        def invoke():
            calls.append(name)
            if name == failed:
                raise TimeoutError('controlled failure '+name)
            return True
        return invoke
    names = ['measured_stop','deactivate','carry_terminal','native_stop','consumers_stop','clock_stop']
    report = runner.shutdown_runtime_in_order(**{name: operation(name) for name in names})
    assert calls == names[:5] if failed == 'consumers_stop' else calls == names
    assert report['runtime_exit'] is (not bool(failed))
    assert report['consumers_exited'] is (failed != 'consumers_stop')
    assert bool(report['errors']) is bool(failed)
    if failed == 'measured_stop':
        assert report['steps']['clock_stop'] is True
        assert report['steps']['measured_stop'] is False  # never relabel physical failure


def test_false_or_missing_terminal_is_not_a_successful_stop_or_retry():
    assert hasattr(runner, 'shutdown_runtime_in_order'), 'failure-safe runtime teardown missing'
    calls = []
    def carry():
        calls.append('carry')
        return None
    report = runner.shutdown_runtime_in_order(measured_stop=lambda: True,
        deactivate=lambda: True, carry_terminal=carry, consumers_stop=lambda: True)
    assert calls == ['carry'] and report['runtime_exit'] is False
    assert report['consumers_exited'] is True
    assert report['steps']['carry_terminal'] is False
