"""Small physical-observation protocol; cannot produce a G2 admission proof."""
import numpy as np
from dataclasses import asdict
from .samples import Sample,sample_valid
from .projection import body_rotation
from .leg_kinematics import fk_leg


class ComponentCaptureJoiner:
    """C1 read-only association, never a control cache or admission proof.

    Baseline may start at a recent coherent contact. Once armed, every new
    contact is consumed in order: no expired/mismatched/high-force skipping.
    All original stamps/receipts and 40ms/dual200ms checks remain unchanged.
    The caller serializes receive/take with its existing ingress lock.
    """
    keys=('joints','body','contacts')
    capacity=32

    def __init__(self):
        self.history={k:{} for k in self.keys};self.latest={};self.armed=False;self.closed=False
        self.last_capture=None;self.last_ros=None;self.last_wall=None;self.error=''
        self.received={k:0 for k in self.keys};self.duplicates=0;self.emitted=0;self.waiting=0
        self.maximum_span_ns=0;self.baseline_capture=None;self.pending_when_closed=0

    def _fail(self,reason):
        self.error=reason;raise ValueError(reason)

    def receive(self,key,sample):
        if self.closed:return
        if self.error:raise ValueError('component join latched: '+self.error)
        if key not in self.history or not isinstance(sample,Sample):self._fail('component join stream/type')
        good,reason=sample_valid(sample,sample.stamp_ns,sample.received_ns,0,max_age_ns=0)
        if not good:self._fail('component join input:'+reason)
        previous=self.latest.get(key)
        if previous is not None:
            if (sample.stamp_ns,sample.sequence)==(previous.stamp_ns,previous.sequence):
                self.duplicates+=1;return  # first receipt cannot be renewed
            if (sample.stamp_ns<=previous.stamp_ns or sample.sequence<=previous.sequence
                    or sample.received_ns<previous.received_ns):self._fail('component join capture/receipt rollback')
        self.latest[key]=sample;self.history[key][sample.stamp_ns]=sample;self.received[key]+=1
        if len(self.history[key])>self.capacity:
            if key=='contacts' and self.armed:self._fail('component join pending contact overflow')
            del self.history[key][min(self.history[key])]

    def _validate_clock_and_streams(self,ros,wall):
        if self.error:raise ValueError('component join latched: '+self.error)
        if (type(ros) is not int or type(wall) is not int or ros<0 or wall<0
                or self.last_ros is not None and (ros<self.last_ros or wall<self.last_wall)):
            self._fail('component join evaluation clock rollback/metadata')
        self.last_ros,self.last_wall=ros,wall
        for key in self.keys:
            eligible=[s for s in self.history[key].values() if s.stamp_ns<=ros and s.received_ns<=wall]
            # Consumed contacts leave the queue, but their original receipt
            # must still expire if the stream stops producing captures.
            last=self.latest.get(key)
            if key=='contacts' and not eligible and last is not None and last.stamp_ns<=ros and last.received_ns<=wall:
                eligible=[last]
            if not eligible:return False
            newest=max(eligible,key=lambda s:s.stamp_ns)
            good,reason=sample_valid(newest,ros,wall,0,max_age_ns=200_000_000)
            if not good:self._fail('component join '+key+':'+reason)
        return True

    def _select(self,contact,ros,wall):
        good,reason=sample_valid(contact,ros,wall,0,max_age_ns=200_000_000)
        if not good:self._fail('component pending contact expired:'+reason)
        near={}
        for key in ('joints','body'):
            near[key]=[s for s in self.history[key].values()
                if abs(s.stamp_ns-contact.stamp_ns)<=40_000_000
                and sample_valid(s,ros,wall,0,max_age_ns=200_000_000)[0]]
        choices=[]
        for joints in near['joints']:
            for body in near['body']:
                stamps=(contact.stamp_ns,joints.stamp_ns,body.stamp_ns);span=max(stamps)-min(stamps)
                if span<=40_000_000:
                    score=(span,abs(joints.stamp_ns-contact.stamp_ns)+abs(body.stamp_ns-contact.stamp_ns),
                        -joints.stamp_ns,-body.stamp_ns)
                    choices.append((score,joints,body))
        if not choices:return None
        _,joints,body=min(choices,key=lambda v:v[0])
        return dict(joints=joints,body=body,contacts=contact)

    def _emit(self,selected,ros,wall):
        contact=selected['contacts'];span=max(s.stamp_ns for s in selected.values())-min(s.stamp_ns for s in selected.values())
        for stamp in list(self.history['contacts']):
            if stamp<=contact.stamp_ns:del self.history['contacts'][stamp]
        self.last_capture=contact.stamp_ns;self.emitted+=1;self.maximum_span_ns=max(self.maximum_span_ns,span)
        return dict(ros_ns=ros,wall_ns=wall,samples={k:asdict(s) for k,s in selected.items()})

    def begin(self,ros,wall):
        if self.closed:return None
        if self.armed:self._fail('component join baseline already selected')
        if not self._validate_clock_and_streams(ros,wall):return None
        for stamp in sorted(self.history['contacts'],reverse=True):
            contact=self.history['contacts'][stamp]
            if contact.stamp_ns>ros or contact.received_ns>wall:continue
            selected=self._select(contact,ros,wall)
            if selected is not None:
                self.armed=True;self.baseline_capture=stamp
                return self._emit(selected,ros,wall)
        return None

    def take(self,ros,wall):
        if self.closed:return None
        if not self.armed:self._fail('component join baseline required')
        if not self._validate_clock_and_streams(ros,wall):return None
        eligible=[s for s in self.history['contacts'].values() if s.stamp_ns<=ros and s.received_ns<=wall]
        if not eligible:return None
        contact=min(eligible,key=lambda s:s.stamp_ns)
        selected=self._select(contact,ros,wall)
        if selected is None:self.waiting+=1;return None
        return self._emit(selected,ros,wall)

    def close(self):
        if not self.closed:self.pending_when_closed=len(self.history['contacts'])
        self.closed=True

    def report(self):
        return dict(scope='C1_capture_association_no_commands_or_G2_admission',capacity_per_stream=self.capacity,
            capture_slop_ns=40_000_000,dual_max_age_ns=200_000_000,received=dict(self.received),
            duplicates=self.duplicates,emitted=self.emitted,waiting_for_matching_capture=self.waiting,
            maximum_emitted_span_ns=self.maximum_span_ns,baseline_capture_ns=self.baseline_capture,
            last_contact_capture_ns=self.last_capture,pending_when_closed=self.pending_when_closed,
            closed=self.closed,error=self.error,contact_skip_after_baseline=False)


def observe_contact_cycle(tracker,take_frame):
    """One bounded read cycle; consume existing captures, never acquire more.

    Contact events must not be coalesced: a high-force pulse resets dwell.
    Every selection still checks its original capture/receipt ages. A queued
    expired frame fails immediately instead of being replaced by a newer one.
    """
    for _ in range(ComponentCaptureJoiner.capacity):
        frame=take_frame()
        if frame is None:return False
        if tracker.update(frame):return True
    return False


class ContactTransitionTracker:
    def __init__(self,model,baseline):
        self.model=model;self.events=[];self.last_capture=None;self.samples=0
        centers,contact=self._read(baseline)
        if not all(v>=2. for v in contact.data['forces']):
            raise ValueError('component baseline requires four measured supports')
        self.baseline={f:float(p[2]) for f,p in centers.items()}
        self.maximum={f:0. for f in model.feet}
        self.low_since={f:None for f in model.feet}
        self.lifted=set();self.completed=set()

    def _read(self,frame):
        samples={key:Sample(**frame['samples'][key]) for key in ('joints','body','contacts')}
        for key,sample in samples.items():
            good,reason=sample_valid(sample,frame['ros_ns'],frame['wall_ns'],0,max_age_ns=200_000_000)
            if not good:raise ValueError('component '+key+':'+reason)
        captures=[s.stamp_ns for s in samples.values()]
        if max(captures)-min(captures)>40_000_000:
            raise ValueError('component body/joint/contact capture mismatch')
        contact=samples['contacts'];data=contact.data
        if (tuple(data['names'])!=self.model.feet or data['unexpected_contacts']!=0
                or data.get('force_vectors_valid') is not True):
            raise ValueError('component contact identity/vector attestation')
        vectors=np.asarray(data.get('forces_world'),dtype=float)
        if (vectors.shape!=(4,3) or not np.isfinite(vectors).all()
                or not np.allclose(vectors[:,2],data['forces'],rtol=1e-6,atol=1e-6)):
            raise ValueError('component signed force mismatch')
        q=samples['joints'].data['position'];body=samples['body']
        if body.frame_id!='odom' or body.data['child_frame_id']!='base_footprint':
            raise ValueError('component world body frame')
        pose=np.eye(4);pose[:3,:3]=body_rotation(body.data)[0];pose[:3,3]=body.data['position']
        centers={}
        for foot in self.model.feet:
            angles=tuple(q[foot[:2]+'_'+part+'_joint'] for part in ('hip','thigh','calf'))
            centers[foot]=(pose@np.r_[fk_leg(self.model,foot,angles),1.])[:3]
        return centers,contact

    def update(self,frame):
        centers,contact=self._read(frame);token=contact.stamp_ns
        if self.last_capture is not None:
            if token<self.last_capture:raise ValueError('component capture rollback')
            if token==self.last_capture:return len(self.completed)==4
        self.last_capture=token;self.samples+=1
        for foot,force in zip(self.model.feet,contact.data['forces']):
            lift=float(centers[foot][2]-self.baseline[foot]);self.maximum[foot]=max(self.maximum[foot],lift)
            if force<2.:
                if self.low_since[foot] is None:self.low_since[foot]=(token,contact.received_ns)
                start=self.low_since[foot]
                if (token-start[0]>=100_000_000 and contact.received_ns-start[1]>=100_000_000
                        and lift>=.005 and foot not in self.lifted):
                    self.lifted.add(foot)
                    self.events.append(dict(foot=foot,event='measured_unload_and_lift',
                        capture_ns=token,received_ns=contact.received_ns,lift_m=lift))
            else:
                if foot in self.lifted and foot not in self.completed and lift<=.005:
                    self.completed.add(foot)
                    self.events.append(dict(foot=foot,event='measured_return',capture_ns=token,
                        received_ns=contact.received_ns,lift_m=lift,normal_force_n=float(force)))
                self.low_since[foot]=None
        return len(self.completed)==4

    def report(self):
        return dict(scope='observed_contact_component_not_full_G2_acceptance',
            all_four_contacts_completed=len(self.completed)==4,
            completed_feet=sorted(self.completed),maximum_lift_m=dict(self.maximum),
            baseline_center_z_m=dict(self.baseline),unique_contact_captures=self.samples,events=list(self.events))


def component_outcome(original,tracker,*,protocol_finished,dart_observed):
    """Keep original G2 FAIL and all its checks intact, never mint admission."""
    unexecuted={'forward','left','right','dart_contact_contract'}
    mandatory={'normal_runtime_exit','normal_engine_exit','carry_terminal_received',
        'joint_tf_ownership','contact_support','sensor_freshness','stability','native_ctrl_observed'}
    required=set(original.get('required_checks',()))
    checks=original.get('checks',{})
    failed=sorted(k for k in required-unexecuted if checks.get(k) is not True)
    complete=(original.get('gate')=='G2' and original.get('status')=='FAIL'
        and mandatory|unexecuted<=required and not failed and bool(protocol_finished)
        and dart_observed is True and tracker.get('all_four_contacts_completed') is True)
    return dict(scope='contact_component_only_original_G2_incomplete',observations_complete=bool(complete),
        full_G2_acceptance=False,original_G2_status=original.get('status'),
        predeclared_unexecuted_G2_checks=sorted(unexecuted),unexpected_failed_checks=failed,
        protocol_finished=bool(protocol_finished),dart_component_observed=dart_observed is True,tracker=tracker)
