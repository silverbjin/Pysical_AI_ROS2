"""Closed C1 first-receipt boundary, not a replacement acceptance decision."""
import hashlib,json,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
trial=base/'native-contact-component-gazebo-76838bec-808d-4199-afd1-8c01589486fb'
report=json.loads((trial/'controller_report.json').read_bytes());fault=report['first_fault']
wall,ros=fault['wall_ns'],fault['ros_ns']
native=json.loads((trial/'native_controls.json').read_bytes())['records']
frames=json.loads((trial/'all_frames.json').read_bytes())['frames']
out=dict(scope='closed_actual_transport_gap_not_physical_acceptance_override',
 trial=trial.name,first_fault=dict(reason=fault['reason'],wall_ns=wall,ros_ns=ros),
 controller_contact_ingress=fault['contact_ingress'],
 native_packets=[dict(capture_ns=r['capture_ns'],state_capture_ns=r['state_capture_ns'],
  received_ns=r['received_ns'],receipt_from_fault_ms=(r['received_ns']-wall)/1e6)
  for r in native if ros-60_000_000<=r['capture_ns']<=ros+60_000_000],
 independent_samples=[dict(ros_ns=r['ros_ns'],wall_ns=r['wall_ns'],
  samples={k:dict(stamp_ns=s['stamp_ns'],received_ns=s['received_ns'])
   for k,s in r['samples'].items() if s and k in ('contacts','joints','body','imu')})
  for r in frames if wall-300_000_000<=r['wall_ns']<=wall+100_000_000],
 interpretation=[
  'Controller and independent receiver retain the same old normalized contact capture while joints continue.',
  'Native pre-physics packet 26.324s is received before fault; normalized contacts next observed at26.344s after fault.',
  'Existing packet log does not record separate feet/contacts bridge delivery. Exact missing pair member or publication loss is unproven.',
  'Current failure precedes numerical submission and cannot assess late-result collection fix.',
  'Runtime RAW comparison excludes earlier clock-rate drift for this run; thread probe perturbation is not excluded.',
  'Synthetic executor comparison is a bounded CPU improvement experiment, not proof of physical fault resolution.'],
 source_sha256={name:hashlib.sha256((trial/name).read_bytes()).hexdigest()
  for name in ('controller_report.json','native_controls.json','all_frames.json')})
target=base/('contact-delivery-gap-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(target)
