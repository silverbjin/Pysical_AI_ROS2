"""A geometric candidate is not permission to crawl; native evidence is required."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import uuid

import yaml

from .geometry import (footprint_bounds, native_geometry,
                       navigation_mjcf, physics_digest, trig_bounds as trig_bounds)
from .model import ModelContract
from .samples import Vec3


G1_REQUIRED = frozenset({
    'joint_tf_ownership', 'contact_frames_force', 'imu_frame', 'scan_world_not_self',
    'native_com_consistent', 'carry_collision_free', 'carry_terminal_received',
    'carry_measured_settle', 'unvalidated_crawl_rejected', 'normal_runtime_exit',
    'normal_engine_exit', 'parent_reaped', 'no_residual_members',
})
G1_NATIVE_REQUIRED = G1_REQUIRED | frozenset({
    'native_observations','sensor_freshness','stability','contact_support',
    'native_com_consistent','stance_slip','joint_envelope','contact_lift',
    'native_ctrl_observed','native_library_loaded','tf_observer_owned',
})


def _file_digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def _native_artifacts(evidence,root,model_sha256):
    """Read the real EvidenceRun list; never fabricate a role-based PASS file."""
    if not isinstance(evidence.get('artifacts'),list):return False
    verified={};resolved=set()
    for artifact in evidence['artifacts']:
        relative=Path(artifact['path'])
        if relative.is_absolute() or '..' in relative.parts:return False
        target=(root/relative).resolve(strict=True)
        if not target.is_relative_to(root) or target in resolved:return False
        if (type(artifact['size']) is not int or artifact['size']<=0
                or target.stat().st_size!=artifact['size'] or _file_digest(target)!=artifact['sha256']):
            return False
        resolved.add(target);verified[str(relative)]=target
    required={'frames.json','action_results.json','source_manifest.json','install_manifest.json','teardown.json'}
    if not required.issubset(verified):return False
    action=json.loads(verified['action_results.json'].read_text())
    if not (action.get('terminal') is True and action.get('result_future_done') is True
            and action.get('result_status')==4 and action.get('result_error_code')==0
            and action.get('pending_uuid','missing') is None
            and action.get('model_sha256')==model_sha256 and not action.get('fault')):
        return False
    teardown=json.loads(verified['teardown.json'].read_text())
    if (not all(teardown.get(key) is True for key in ('runtime_exit','engine_exit','parent_reaped'))
            or teardown.get('launch_returncode')!=0 or teardown.get('engine_returncodes')!=[0]
            or teardown.get('forced_cleanup') is not False or teardown.get('residual_live_pids')!=[]):
        return False
    source=json.loads(verified['source_manifest.json'].read_text())
    installed=json.loads(verified['install_manifest.json'].read_text())
    return isinstance(source.get('files'),dict) and bool(source['files']) and isinstance(installed,dict) and bool(installed)


@dataclass(frozen=True)
class CarryProfile:
    model_sha256: str
    config_sha256: str
    physics_sha256: str
    arm_q: tuple[float, ...]
    limits: dict
    footprint: tuple[Vec3, ...]
    inflation_radius: float
    offline_checks: tuple[dict, ...]
    state: str = 'offline'
    native_evidence: dict | None = None


def default_limits() -> dict:
    local = Path(__file__).resolve().parents[1] / 'config/crawl_limits.yaml'
    if not local.is_file():
        from ament_index_python.packages import get_package_share_directory
        local = Path(get_package_share_directory('integrated_robot_navigation')) / 'config/crawl_limits.yaml'
    return yaml.safe_load(local.read_text())


def _digest(limits, arm_q, physics_sha256, footprint, inflation_radius):
    value = dict(limits=limits, arm_q=arm_q, physics_sha256=physics_sha256,
                 footprint=footprint, inflation_radius=inflation_radius)
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def _validate_limits(limits):
    maxima = {
        'max_vx': .01, 'max_wz': .03, 'max_accel_x': .02, 'max_accel_wz': .06,
        'max_support_shift_accel_mps2': .10,
        'unload_speed_mps': .002, 'max_unload_height_m': .010,
        'max_roll_pitch': .15, 'swing_height_m': .02, 'max_foot_displacement_m': .08,
        'max_swing_speed_mps': .02,
        'sensor_max_age_s': .20, 'raw_max_age_s': .20, 'scan_max_age_s': .30,
        'stop_landing_s': 1., 'stopped_v_mps': .003, 'stopped_wz_rps': .01,
        'carry_error_rad': .03, 'carry_velocity_rps': .02, 'max_body_height_m': .70,
    }
    minima = {'footprint_margin_m': .05, 'min_contact_force_n': 2.,
              'min_support_margin_m': .01, 'settle_s': 1., 'min_body_height_m': .30}
    try:
        for key, maximum in maxima.items():
            value = limits[key]
            if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= maximum:
                raise ValueError(key)
        for key, minimum in minima.items():
            value = limits[key]
            if type(value) not in (float, int) or not math.isfinite(value) or value < minimum:
                raise ValueError(key)
        if (limits['max_vy'] != 0. or limits['control_hz'] != 50.
                or limits['cycle_s'] != 8.
                or not limits['min_body_height_m'] <= limits['nominal_body_height_m']
                <= limits['max_body_height_m']):
            raise ValueError('gait timing or nominal body height')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('limits violate safety contract: '+str(exc)) from exc


def prepare_profile(model: ModelContract, arm_q: tuple[float, ...],
                    *, limits: dict | None = None) -> CarryProfile:
    limits = default_limits() if limits is None else json.loads(json.dumps(limits, allow_nan=False))
    _validate_limits(limits)
    q = tuple(float(v) for v in arm_q)
    if len(q) != 6 or not all(math.isfinite(v) for v in q):
        raise ValueError('six finite carry angles required')
    for i, value in enumerate(q, 1):
        lo, hi = model.limits['arm_joint_'+str(i)][:2]
        if not lo <= value <= hi:
            raise ValueError('carry target outside joint limits')
    records, checks, physical = native_geometry(model, q)
    footprint = footprint_bounds(model, q, limits, records)
    inflation = max(math.hypot(x, y) for x, y, _ in footprint) + .05
    digest = _digest(limits, q, physical, footprint, inflation)
    return CarryProfile(model.model_sha256, digest, physical, q, limits, footprint,
                        inflation, tuple(checks), native_evidence={})


def swept_footprint(model: ModelContract, profile: CarryProfile, limits: dict) -> list[Vec3]:
    if model.model_sha256 != profile.model_sha256:
        raise ValueError('model hash mismatch')
    if _digest(limits, profile.arm_q, profile.physics_sha256,
               profile.footprint, profile.inflation_radius) != profile.config_sha256:
        raise ValueError('config hash mismatch')
    return list(profile.footprint)


def validate_profile(profile: CarryProfile, model: ModelContract,
                     engine: str, *, execution_profile=None) -> tuple[bool, str]:
    if profile.model_sha256 != model.model_sha256:
        return False, 'model_hash'
    try:
        _validate_limits(profile.limits)
        swept_footprint(model, profile, profile.limits)
    except (TypeError, ValueError):
        return False, 'config_hash'
    if engine not in ('mujoco', 'gazebo'):
        return False, 'engine'
    if profile.state != 'native_validated' or not profile.native_evidence:
        return False, 'native_validation_required'
    # The runner, not a ROS caller's ready flag, produces this complete record.
    try:
        if physics_digest(navigation_mjcf(model)) != profile.physics_sha256:
            return False, 'physics_hash'
        reference = profile.native_evidence[engine]
        path = Path(reference['path']).resolve(strict=True)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != reference['sha256']:
            return False, 'evidence_hash'
        evidence = json.loads(raw)
        uuid.UUID(evidence['run_id'])
        if (evidence['schema_version'] != 1 or evidence['kind'] != 'native'
                or evidence['gate'] != 'G1' or evidence['engine'] != engine
                or evidence['status'] != 'PASS'
                or evidence['model_sha256'] != profile.model_sha256
                or evidence['config_sha256'] != profile.config_sha256
                or evidence['physics_sha256'] != profile.physics_sha256):
            return False, 'evidence_binding'
        required=evidence.get('required_checks')
        if (not isinstance(required,list) or not G1_NATIVE_REQUIRED.issubset(required)
                or evidence.get('errors')!=[]
                or not all(evidence['checks'].get(key) is True for key in required)):
            return False, 'evidence_checks'
        mode=evidence.get('execution_mode',{})
        scene=evidence.get('scene',{})
        if mode.get('diagnostic_profile_node') is not None or mode.get('validation_only') is not True:
            return False, 'evidence_execution_profile'
        if execution_profile is not None:
            from .execution_contract import normalize_execution_profile
            expected=normalize_execution_profile(execution_profile,engine)
            actual=dict(control_clock=mode.get('control_clock'),
                position_reference_mode=scene.get('position_reference_mode','native'),
                dart_contact=mode.get('dart_contact'),native_physics_sha256=evidence.get('native_physics_sha256'))
            if actual!=expected or scene.get('dart_contact_mode','native')!=actual['dart_contact']:
                return False, 'evidence_execution_profile'
            mode_checks=({'control_clock_contract'} if actual['control_clock']=='relay100' else set()) | (
                {'dart_contact_contract'} if actual['dart_contact']=='allowance50um' else set())
            if not mode_checks.issubset(required):return False, 'evidence_checks'
        elif (mode.get('control_clock')!='native' or mode.get('dart_contact')!='native'
                or scene.get('position_reference_mode','native')!='native'
                or scene.get('dart_contact_mode','native')!='native'):
            return False, 'g1_experiment_not_crawl_admission'
        if not _native_artifacts(evidence,path.parent,profile.model_sha256):
            return False, 'evidence_artifact'
    except (OSError, ValueError, KeyError, TypeError,AttributeError):
        return False, 'invalid_native_evidence'
    return True, ''
