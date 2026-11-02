"""Offline, exact-capture diagnostics. Never changes a native acceptance verdict."""
from collections import Counter, defaultdict
import json
from pathlib import Path
from uuid import UUID

from integrated_robot_vision.trace import decode_record, validate_record


def _uuid(value):
    try:
        if str(UUID(value)) != value:
            raise ValueError('canonical run UUID required')
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('canonical run UUID required') from exc
    return value


def _quantile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    lower = int(position)
    upper = min(lower+1, len(values)-1)
    return values[lower]+(values[upper]-values[lower])*(position-lower)


def analyze_trace(records: list[dict], *, expected_run_id: str, require_native: bool) -> dict:
    _uuid(expected_run_id)
    counts = Counter(seen=len(records), valid=0, malformed=0, unmatched=0, ambiguous=0,
                     no_target=0, duplicate=0)
    errors, groups, seen, producers = [], defaultdict(list), {}, defaultdict(set)
    quarantined = set()
    def capture_key(value):
        return tuple(value[k] for k in ('run_id', 'source_frame', 'capture_ns'))
    gate_losses, gaps, segments = [], [], defaultdict(list)
    for row in records:
        try:
            if (not isinstance(row, dict) or set(row) != {'received_ns', 'record'}
                    or type(row['received_ns']) is not int or row['received_ns'] < 0):
                raise ValueError('original observer receipt and record required')
            value = validate_record(row['record'])
            if value['run_id'] != expected_run_id or value['event_sequence'] > 20000:
                raise ValueError('foreign run or source record limit exceeded')
            event = value['producer_id'], value['event_sequence']
            if event in seen:
                if seen[event] != value:
                    quarantined.update((capture_key(seen[event]), capture_key(value)))
                    raise ValueError('same producer event has conflicting contents')
                counts['duplicate'] += 1
                continue
            seen[event] = value
            producers[value['producer_id']].add(value['event_sequence'])
            counts['valid'] += 1
            if value['capture_ns'] is None:
                counts['no_target'] += 1
                if value['stage'] == 'tracking' and value['outcome'] == 'GATE_LOST':
                    times = value['times_ns']
                    lost, receipt = times.get('gate_lost'), times.get('target_receive')
                    gate_losses.append(dict(capture_ns=None, source_frame=value['source_frame'],
                        producer_id=value['producer_id'], ros_age_ns=None,
                        receipt_age_ns=lost-receipt if lost is not None and receipt is not None else None,
                        decision_ns=times.get('decision'), gate_lost_ns=lost))
                continue
            groups[(value['run_id'], value['source_frame'], value['capture_ns'])].append(value)
        except (ValueError, TypeError, KeyError) as exc:
            counts['malformed'] += 1
            if len(errors) < 32:
                errors.append(str(exc))

    def add(name, start, end, value):
        if start is None or end is None:
            return
        if end < start:
            if len(errors) < 32:
                errors.append('negative segment: '+name)
            return
        capture = {key: value[key] for key in ('run_id', 'source_frame', 'capture_ns',
                                              'producer_id', 'local_epoch', 'native_sequence')}
        segments[name].append((end-start, capture))

    present_stages, fusion_publications = set(), defaultdict(list)
    for key, values in groups.items():
        stages = defaultdict(list)
        for value in values:
            stages[value['stage']].append(value)
        present_stages.update(stages)
        if key in quarantined:
            counts['ambiguous'] += len(values)
            continue
        # Multiple control decisions for one target are normal. Two source
        # snapshots/worker outcomes for the same capture are not disambiguated
        # by another process's local_epoch, by receipt order, or by nearest time.
        if any(len(stages.get(stage, ())) > 1 for stage in ('camera', 'detector', 'fusion')):
            counts['ambiguous'] += len(values)
            continue
        for value in values:
            times, stage = value['times_ns'], value['stage']
            pairs = {
                'camera': [('native_submit', 'submit_start', 'submit_end'),
                    ('native_queue', 'submit_end', 'acquire'),
                    ('native_scene', 'scene_start', 'render_start'),
                    ('native_render', 'render_start', 'render_end'),
                    ('native_readback', 'render_end', 'readback_end'),
                    ('native_rgb_publish', 'rgb_publish_start', 'rgb_publish_end'),
                    ('native_depth_publish', 'depth_publish_start', 'depth_publish_end'),
                    ('native_info_publish', 'info_publish_start', 'info_publish_end')],
                'detector': [('detector_queue', 'slot_put', 'work_take'),
                    ('detector_convert', 'convert_start', 'convert_end'),
                    ('detector_inference', 'inference_start', 'inference_end'),
                    ('detector_publish', 'publish_start', 'publish_end')],
                'fusion': [('fusion_queue', 'bundle_select', 'work_take'),
                    ('fusion_depth_span', 'depth_start', 'depth_end'),
                    ('fusion_tf_span', 'tf_start', 'tf_end'),
                    ('fusion_publish', 'publish_start', 'publish_end')],
                'tracking': [('tracking_decision_to_dispatch', 'decision', 'dispatch')],
            }[stage]
            for name, start, end in pairs:
                add(name, times.get(start), times.get(end), value)
            if stage == 'fusion' and value['outcome'] == 'PUBLISHED':
                domain = tuple(value[k] for k in ('producer_id', 'boot_id', 'clock_id', 'local_epoch'))
                fusion_publications[domain].append((times['publish_start'], value['capture_ns']))
            if stage == 'tracking' and value['outcome'] == 'GATE_LOST':
                lost, receipt = times.get('gate_lost'), times.get('target_receive')
                gate_losses.append(dict(capture_ns=value['capture_ns'],
                    source_frame=value['source_frame'], producer_id=value['producer_id'],
                    ros_age_ns=(value['ros_now_ns']-value['capture_ns']
                                if value['ros_now_ns'] is not None else None),
                    receipt_age_ns=lost-receipt if lost is not None and receipt is not None else None,
                    decision_ns=times.get('decision'), gate_lost_ns=lost))
        needed = {'detector', 'fusion', 'tracking'} | ({'camera'} if require_native else set())
        domains = {(v['boot_id'], v['clock_id']) for v in values}
        if not needed <= set(stages) or len(domains) != 1:
            counts['unmatched'] += len(values)
            if len(domains) != 1 and len(errors) < 32:
                errors.append('capture spans different boot/clock domains')
            continue
        detector, fusion = stages['detector'][0], stages['fusion'][0]
        camera = stages['camera'][0] if stages.get('camera') else None
        if (detector['outcome'] != 'PUBLISHED' or fusion['outcome'] != 'PUBLISHED'
                or (camera is not None and camera['outcome'] != 'PUBLISHED')):
            counts['unmatched'] += len(values)
            continue
        dt, ft = detector['times_ns'], fusion['times_ns']
        causal = [(dt['publish_start'], ft['detection_receive'])]
        if camera is not None:
            causal.append((camera['times_ns']['rgb_publish_start'], dt['rgb_receive']))
        if any(end < start for start, end in causal):
            errors.append('negative cross-stage causal interval')
            counts['unmatched'] += len(values)
            continue
        if camera is not None:
            add('native_to_detector_receive', camera['times_ns']['rgb_publish_start'],
                dt['rgb_receive'], detector)
        add('detector_to_fusion_receive', dt['publish_start'], ft['detection_receive'], fusion)
        for tracking in stages['tracking']:
            tt = tracking['times_ns']
            if tracking['outcome'] != 'DISPATCH' or 'dispatch' not in tt:
                continue
            if tt.get('target_receive', -1) < ft['publish_start']:
                errors.append('negative fusion-to-control causal interval')
                continue
            add('fusion_to_target_receive', ft['publish_start'], tt['target_receive'], tracking)
            add('detector_to_dispatch', dt['rgb_receive'], tt['dispatch'], tracking)
            if camera is not None:
                add('native_to_dispatch', camera['times_ns']['submit_start'], tt['dispatch'], tracking)

    for values in fusion_publications.values():
        ordered = sorted(values)
        for previous, current in zip(ordered, ordered[1:]):
            if current[1] <= previous[1]:
                errors.append('nonincreasing capture in fusion local epoch; gap excluded')
                continue
            gaps.append(current[0]-previous[0])
    summaries = {}
    for name, samples in segments.items():
        durations = [v[0] for v in samples]
        worst = max(samples, key=lambda v: (v[0], json.dumps(v[1], sort_keys=True)))
        summaries[name] = dict(count=len(samples), p50_ns=_quantile(durations, .5),
            p95_ns=_quantile(durations, .95), max_ns=worst[0], worst_capture=worst[1])
    missing = sorted(set(('camera', 'detector', 'fusion', 'tracking'))-present_stages)
    counts['sequence_gap_lower_bound'] = sum(max(events)-len(events) for events in producers.values())
    counts = dict(counts)
    counts['dropped'] = None  # sequence gaps cannot prove unreceived tail/error/limit totals
    return dict(analysis_status='PARTIAL' if summaries else 'UNVERIFIED',
        segments=summaries, counts=counts, missing_stages=missing,
        target_gaps_ns=gaps, gate_losses=gate_losses, errors=errors,
        native_boundary='OBSERVED' if 'camera' in present_stages else 'UNVERIFIED',
        note='Source-clock segments only; unknown producer totals keep coverage PARTIAL. '
             'Publish-to-receive includes DDS, scheduling and callback wait; not pure network latency. '
             'Depth/TF spans may interleave for multiple boxes, so do not add them as exclusive CPU time. '
             'Native render/readback are API spans, not isolated GPU-work measurements.')


class TraceCollector:
    MAX_PER_PRODUCER, MAX_TOTAL, MAX_PRODUCERS = 20000, 80000, 16

    def __init__(self, run_id):
        self.run_id = _uuid(run_id)
        self.records, self.producers, self.counts = [], {}, Counter()

    def add(self, payload, *, received_ns, expected_stage=None):
        self.counts['seen'] += 1
        try:
            value = decode_record(payload)
            if (value['run_id'] != self.run_id or value['event_sequence'] > 20000
                    or (expected_stage is not None and value['stage'] != expected_stage)
                    or type(received_ns) is not int or received_ns < 0):
                raise ValueError('wrong run/stage, record cap or observer time')
        except (ValueError, TypeError, KeyError):
            self.counts['malformed'] += 1
            return False
        identity = value['producer_id']
        if (len(self.records) >= self.MAX_TOTAL or
                (identity not in self.producers and len(self.producers) >= self.MAX_PRODUCERS)):
            self.counts['dropped'] += 1
            return False
        if identity not in self.producers:
            self.producers[identity] = 0
        if self.producers[identity] >= self.MAX_PER_PRODUCER:
            self.counts['dropped'] += 1
            return False
        self.producers[identity] += 1
        self.records.append(dict(received_ns=received_ns, record=value))
        self.counts['accepted'] += 1
        return True

    def save(self, output, *, require_native):
        output = Path(output)
        with (output/'trace.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
            for row in self.records:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')
        summary = analyze_trace(self.records, expected_run_id=self.run_id, require_native=require_native)
        summary['collector'] = dict(self.counts)
        summary['collector_limits'] = dict(per_producer=self.MAX_PER_PRODUCER,
            total=self.MAX_TOTAL, producers=self.MAX_PRODUCERS, payload_bytes=4096)
        (output/'trace_summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        return summary
