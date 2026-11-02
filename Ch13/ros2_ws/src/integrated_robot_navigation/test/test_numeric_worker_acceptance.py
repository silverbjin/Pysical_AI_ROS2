"""The new worker adds evidence; existing engine acceptance stays required."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def test_gazebo_g2_requires_numerical_close_without_relabelling_other_roles():
    for scenario in ('crawl-cycle','crawl-reverse'):
        required=runner.g2_required_checks('relay100','allowance50um','gazebo',scenario)
        assert {'numeric_worker_normal_close','numeric_worker_job_contract'}<=required
        assert {'normal_runtime_exit','normal_engine_exit','sensor_freshness','stopped'}<=required
        assert 'numeric_worker_normal_close' not in runner.g2_required_checks('relay100','native','mujoco',scenario)
    assert 'numeric_worker_normal_close' not in runner.native_required_checks('relay100','allowance50um','gazebo')


def test_numeric_worker_closes_after_terminal_before_ros_consumer_exit():
    events=[]
    def stage(name):
        def run():events.append(name);return True
        return run
    result=runner.shutdown_runtime_in_order(measured_stop=stage('measured'),deactivate=stage('deactivate'),
        carry_terminal=stage('terminal'),numeric_stop=stage('numeric'),
        consumers_stop=stage('consumers'),clock_stop=stage('clock'))
    assert events==['measured','deactivate','terminal','numeric','consumers','clock']
    assert result['runtime_exit'] is True
