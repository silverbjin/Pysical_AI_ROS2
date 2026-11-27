# G05 RED4 — 실제 scan 발행 공백과 기록기 관측 범위 분리

## 실행 증거
- Run 45947575404 / job 140335694517 / artifact 15175486140.
- 실행 SHA 5e8c2cd1345d1f17865492b41447a56dd825e224; ZIP 76,462 bytes, SHA256 f91a55b12d6db461ef220f73286058d8f44fa0dfb7216430aa12d4299186a30f; manifest 내부 33/33 실제 독립 확인.
- T12: clean build 6/6, installed imports 6/6, explicit pure tests 8/8 (lock2, analysis4, replay2); 기존 Git/LFS receipt 재사용. colcon test-result 자체는 등록된 테스트 0, 별도 테스트 결과와 혼동하지 않는다.
- C15 actual synthetic MCAP/CDR fixture PASS: String 10 messages, record elapsed .9 s, wrong demo type rejected, demo-as-typed rejected. 실제 normal mission MCAP 판독/재생 PASS가 아니다.
- T13 normal FAIL: IDLE, start_admission null, start_wall_ns null, observed_events 0. Watchdog/mock/executor/readiness/recorder 5/5 clean; Arbiter never launched, therefore no 6-child acceptance. Bag closed, metadata 688 messages / 8 topics including 0 mission_event and 0 cmd_vel_in. Actual mission bag payload 111,466 bytes; total bag directory 118,006 bytes; receipt match. F01/F06/T14 mission replay NOT_RUN.
- Public artifact excludes actual mission raw MCAP; includes harmless generated synthetic demo and wrong-type MCAP fixtures.

## 최초 원인 경계 (실제 trace)
| observation | monotonic ns / result |
|---|---|
| recorder_ready | 240501431068 |
| scan_stable | 241435338835 |
| last scan probe receipt before latch | 241726815911 |
| last source stamp | 1795758373474487529 |
| watchdog first_latch | 242070146879; age_s .34221039 |
| next probe scan receipt | 242236585523 |
| next source stamp | 1795758373983497701 |
| receipt gap | 509.769612 ms |
| source stamp gap | 509.010172 ms |
| max observed source stamp gap | 519.746609 ms |
| stop trace | 147/147 true |

Source timestamps also gap, not merely a receiving-side delay in the probe. Watchdog enforces original 300ms receipt limit. The recorded gap is a sufficient immediate explanation for this watchdog latch; the cause of the source callback pause (CPU scheduling/quota, executor starvation or publication blocking) is NOT established. Earlier RED3 goal rejection preceded later Arbiter latch and remains a separate unresolved event. Recorder Best Effort alone did not qualify runtime. No guard relaxation, synthetic sensor injection or automatic reset.

## 판정 및 다음 최소 검증
T12 scoped PASS; T13 normal FAIL, F01/F06 NOT_RUN; T14 pure/synthetic MCAP PASS only, actual mission CSV/plot/replay NOT_RUN. G05 PARTIAL_PASS / L1 BLOCKED_TIMING. G04 accepted evidence unchanged, G06–09 not started, owner L3 NOT_RUN.
Stop broad full-mission retries. Next run a bounded isolated no-motion scheduling diagnostic: same ROS image and source, scan producer/watchdog and recorder only; compare recorder off/on, capture producer callback enter/exit and publisher wall/thread CPU time, source/receive stamps, cgroup cpu.stat/CPU quota and affinity. Keep 300ms and 150ms original limits. If measured source pause, isolate scheduler/producer before changing RMW. If source cadence stays healthy while receipt stalls, compare transport in separate diagnostic. Only after a clean isolated timing result resume one actual normal record, then F01/F06 and isolated replay. Do not infer success from absence of new faults without full required evidence. New diagnostic not run in this cycle.

## 교육 포인트
Safety gate가 잘 작동하는 것과 임무가 성공하는 것은 별개다. Source stamp와 receipt time을 구분하고, 최초 latch 전후를 비교해 가설을 좁힌다. 파일 파서 테스트의 PASS를 실제 DDS 미션 기록이나 재생의 PASS로 확대하지 않는다. 4회 실제 실패를 보존하고 동일한 전체 미션 반복을 중단한다.
