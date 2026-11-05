# 단계 2 — Level 2 관측·영상 상태 수명 진단

2026-11-05 KST. 단계1 d4c9a1d3 이후. **300ms 기준을 실제 초과한3건을재현했고,촬영제출앞에직렬로놓인상태/TF발행지연을최소분리했다.** 아직새실제임무에서만료가해결됐다는증거는없다.

## 최초 만료의 시간 연계

증거 `../evidence/section_13_8_repair/step2_timing_v1.json`은기존v28 slot1/9/5의첫fault와원본촬영·renderer발행·수신·vision추론·engine처리시각을연결한다. 전체trial과원본판정을수정하지않았다.

|사례|최초fault|그때보유3D의촬영age|관측receipt age|그때health|
|---|---|---:|---:|---|
|610482f4|OBSERVATION_EXPIRED|335.419ms|210.975ms|더새capture80302000000ns|
|dc937a83|OBSERVATION_EXPIRED|314.944ms|180.170ms|더새capture64942000000ns|
|abfa9990|CAPTURE_HEALTH_EXPIRED|3D393.616ms(운반중3D는불필수)|133.450ms|capture230694000000ns,원본age317.414ms|

관측receipt가300ms이내여도원래촬영age를늘릴수없으므로두관측실패는타당하다. 운반은새3D대신기존freshcamerahealth+tactile권한을쓰지만그health원본도만료됐다. 검출없음과센서고장을구분한v28정책과다른원인이다.

slot5의촬영230694000000ns에서는producer의state_publish가약170ms,pre-offer약180ms였다. renderer는그뒤약80ms CPU를썼으며capture→publish는약260ms였다. 다음relay/TF검증과health도달까지포함하면300ms여유가없었다. scan은같은frame약10ms였다. 따라서scan만의문제나inference만의문제로단정하지않는다. slot1/9도원본촬영→관측소비까지누적지연됐고,당시저장된inference_wall은추론시작시각이어서완료/발행지연을정확히분해할수없다. OS선점/GC를확정원인으로표현하지않는다.

## 공식·기존 구현과 변경

설치rclpy는7.1.12-1noble.20260912.162354다. 먼저조회한7.1.6은채택근거에서제외하고[공식7.1.12 executors.py](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/executors.py)의SingleThreadedExecutor 콜백실행경계를다시확인했다. 같은node를여러thread에서spin하거나MultiThreadedExecutor로바꾸지않는다.

기존CameraWorker는불변qpos를기존별도renderer process로넘기고원본stamp/wall을유지한다. 이검증된경계를재사용해**carry_v1만capture를state/TF발행보다먼저제출**한다. 렌더와상태발행을겹쳐직렬합을줄이며새thread/process를추가하지않는다. 동일engine step의qpos복사·원본stamp/wall이입력이다. 역사TF가늦게도착하면기존cache가동일한검사로대기하며100ms과거TF/300ms수명/소유자·hash·bytes검사를그대로유지한다. 시각치환이나미검증TF사용은없다. legacy는원래순서다.

capture_stage_timing에는offered_before_state_publish와분리된발행/제출시간을남긴다. vision관측에inference_finished_wall을추가해다음실제사례에서시작/완료지연을구분한다. 제어는이새진단필드를사용하지않는다.

## 검증과 한계

원본stamp/촬영wall·스냅샷복사·legacy순서를시험했다. 먼저1 FAIL/1 PASS(2.97초),수정뒤camera/lease/transport포함71 PASS/27.06초였다. 시험중CPython resource_tracker의재진입정리경고17건을보존했다. 이를engine수명성공으로해석하지않으며단계4전실제잔여를재검사한다. GC/OS정책을변경하지않았다.

직렬지연분리는확인됐지만wall지연의상한/반복만료해결은증명되지않았다. 특히slot1/9의정확한관측완료→relay→engine각지연은새계측이필요하다. 전체회귀·설치·같은동결소스의실제사례는단계4에서확인한다. 실패해도수명을늘려통과시키지않는다.
## 실제 v30 이후의 판단 변경

v30 실제 실행에서 빠른 capture 제출을 켠 상태의 처리 지연이 커졌다. 이 한 사례만으로 overlap의 인과를 확정하지 않았다. v31부터 기본 순서는 기존 직렬 방식으로 되돌렸으며 `CH13_CAPTURE_OVERLAP=1`일 때만 실험 경로를 선택한다. 실제 후속 검증은 명시적으로 0을 사용한다. 원래 촬영 시각·TF·300ms 수명은 그대로다. 따라서 앞선 부품 PASS를 관측 만료 해결 완료로 해석하면 안 된다. 원래 관측/health 만료의 실제 강건성은 아직 미검증이다. v33 432개, v34 433개 전체 회귀 PASS와 개별 물리 성공도 구분한다.
