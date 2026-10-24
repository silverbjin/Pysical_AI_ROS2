# 13.5 실행 원장

## 2026-10-24 수정본 전체 회귀 및 MuJoCo 기본 경로

- 고정 수정본 navigation385PASS324.10초(`task8-control-clock-mailbox-full.log`), sensors45건(CTest wrapper포함)PASS10.7초(`task8-control-clock-mailbox-sensors-final.log`), 선택8패키지 소스/설치 감사PASS. 마지막 검증에서 재빌드/런타임 수정 없음.
- 동일78runtime 소스의 새 MuJoCo `c1ae8cd3-a240-4145-88bc-0cfd719a4033`, result UUID`de49988a-170c-48b7-9209-9d681fe7da92`: 기본native/single_worker G1 **23/23PASS**. 실제typedterminal/physicalsettle/IMU810고유·누락0·최대오차.0031418598rad/s/lift57고유. engine/runtime/launch0, receiverjoined,parentreaped,noforce,residual[]. relay100 또는G2/Nav2 성공으로 세지 않는다.
- 소스+MuJoCo 원본/준비 장면/최신 전체회귀/계측+Gazebo 시간예산 후분석을 `task8-control-clock-mailbox-mujoco-regression.zip`11,214,240bytes,SHA`089541abbb20c33c3f44fa9ca0ef316b01493e867279ddbcb544c848dc17a338`에 보존. 실행과 현재 source manifest 일치/member 해시 재독 검증. 원본 삭제 없음.
- Gazebo 후분석 최초5mm lift9.404706273wall초/최대lift.0102151m. 센서 비동기 후분석이며 정확한 owner replay가 아니다. 일반SWING 재사용 교정 구조의 예산 재설계가 다음 선택이다. G1 전용lift-return 제안은 사용자 답변 대기이며, 물리 궤적/게인/10wall·실제lift·속도·하중·settle 한계를 변경하지 않았다.
- 작성자 자체 검토: model→mailbox 잠금 순서/ingress에서Machine 직접변이 없음/기존Clock구독하나/원본receipt/최초fault와publish경계/정상종료 의미를 재확인. 서브에이전트나 독립리뷰를 사용한 것으로 표시하지 않는다. 전체13.5 미완료, main/PR/push 없음.

## 2026-10-24 메일박스 격리 실측 — 이전 센서 실패 미관측, 전체 인수는 FAIL

- actual44a97d81의 소유자 contacts wall208.579433ms/clockread36,561ns/독립 ingress 정상에서 최소 DDS 재현으로 default 제어 그룹+모델 잠금 병목을 판별했다. clock은 통과/contacts는 실패(1FAIL/2PASS11.69초), malformed input 경계1FAIL11.92초를 먼저 보존했다.
- relay100 검증 모드만 별도 센서 그룹/메일박스 잠금을 적용했다. 모델·라이프사이클·모터 발행은 제어 소유자 하나이며 오류 latch 확인과 최종 발행을 같은 메일박스 경계로 묶었다. native 기본 그룹/단일 실행기·촬영/시계·50Hz·안전 수치는 유지했다. 관련31PASS68.93초+N설치18.9초+8패키지 감사PASS.
- 새 실제 Gazebo `5f2a8463-2ae6-4bdd-acef-50e28e853a48`, result `3a2522c8-6905-4254-a873-6452a5554e6d`: 기존23+1 모두 유지, 전체FAIL. 정적/실제 carry terminal/settle/센서/접촉/발 lift/IMU/clock 통과, 교정10wall초 안에 착지/settle 미완료. controller 최초fault/stop null, 마지막CALIBRATING/SWING. 이전결함의3회 연속 성공이나G1완료가 아니다.
- 시계4020고유/최소10.134392ms/최초receipt→발행최대23.636744ms/4개MotionState양의stamp lineage누락0. 교정8.2ROS/10.1205wall(RTF.8102), Crawl94.00%/17threads. 정적9.98ROS/12.6246wall(RTF.7905), Crawl91.44%. CPU 개선 완료 주장 없음.
- STOPPED/deactivate 미확정FAIL을 유지하면서 consumers stop/relay ACK+actual0/native1140actual0/launch0/parentreaped/receiverjoined/noforce/residual[] 확인. 최초 종료 실패를 성공한 PID 반환으로 대체하지 않았다.
- 실행/78소스/준비 장면/시험/설치 고정본 `task8-control-clock-5f2a8463.zip`20,149,669bytes,SHA256 `3979b0af242b5d4b54ac8c884928a5805e471dddb063ae6e5d90d7dfe2447b62`; 원본은 삭제하지 않았다.
- 별도 CPU fixture inherited1.094ms/tick vs BLAS1 1.072ms/tick, 양쪽3threads. 실제 CPU 병목을 BLAS 탓으로 단정할 수 없어 스레드 설정을 바꾸지 않았다. 원본 `task8-sensor-cpu-characterization.json`은 물리 판정이 아니다.

## 2026-10-24 승인된100Hz 중계 실험 — 첫 실제 실패 보존

- 사용자가 고수준5개 노드 검증 전용 중계를 승인했다. native 기본/원본 엔진·TF·센서·
  probe 시각/50Hz steady 제어/200·300ms 원래 계약은 변경하지 않았다.
  source/rate/owner/close TDD→관련44통과→동결N366·S42보고(CTest wrapper포함)통과,
  선택8패키지 설치 감사 후 첫 실제Gazebo를 실행했다.
- `925d70ff-642d-458d-b34c-619248b18ab8`, result UUID
  `2fba0266-f5ff-44a2-9f52-eb0591f6c690`: 전체FAIL. 첫4ms 전달 뒤 시동 중200ms
  중단을 운전 손실로 간주해 중계가 고착됐다. JSB 활성화 전이며 carry/stand 단계에
  도달하지 못했다. CPU 개선이나 기존 물리 결함 해결을 판단할 수 없는 실행이다.
  accepted inputs1로 callback 부재를 단정하지 않는다. 실제 graph는 정확히5개였고
  relay PID1156/start127768/exe·lib SHA를 확인했다. native PID1140 exit0/launch0,
  noforce/reaped/residual[]지만 relay1·STOPPED 미확정이라 정상 필수 검사는FAIL이다.
- 원본77source·scene·실패·검증을 `task8-control-clock-925d70ff.zip`에 보존,
  13,187,215bytes/SHA949c2f1f2249a58826b8efb0f763608763a7818ba6c29fb0b7cf9fb9009ffa46.
  모든 member 재독 해시 확인. 원본/native원본도 유지. 기본 경로로 되돌려 성공 실행만
  고르거나 중단 시간을 늘리는 조치는 하지 않았다.
- Ruling: 원본 양의 첫 tick을 운전 활성으로 취급하지 않는다. 기존 StartupManager가
  fresh센서/guard/실제claims 뒤, 다리 활성화 전에 one-shot clock arm한다. 원본 receipt
  200ms 기준은 arm 때도 검사·갱신 금지. ACK 뒤 readiness 재확인. 운전200ms 고착·
  시동45s·재시도 금지 유지. bootstrap에도 source/rollback 오류 고착은 항상 적용한다.
  최소RED bootstrap1/기존8통과→10통과, 실제 startup RED2→8통과, unarmed판정RED1,
  수정 관련46통과60.58초. 현재 전체N 재검증은 아직 하지 않았다.
- 직접 ROS 시험에서 설치된 이전 lib가 build RPATH보다 먼저 로드된 도구 오류3통과/
  2실패를 보존했다. `~/arm`·`armed`가 없어 판별. 도구의 해당 프로세스만 build-lib
  우선/ldd기록으로 수정. 실제 설치 감사 경계는 유지한다. 새 동결 설치/센서 전체
  회귀/감사 중이며 다음 실제 실행 전에는 다른 엔진을 시작하지 않는다.

## 2026-10-24 재개 — native 판정 보완과 IMU 가설 교정

- 마지막 엄격 판정기로 `task8-strict-reference-navigation-full.log`
  **343passed/315.05초**. S colcon test-result28건(CTest wrapper포함)/실패0와
  frozen8패키지 감사는 별도 범위다. wholeCh13/13.3/13.4matrix/G2 성공으로 합치지 않는다.
  실패 원본 로그 `task8-gazebo-imu-history-red.log:60`의 pytest diff공백은 의도적으로
  보존했다. 로그를 제외한 staged 코드/문서 diff--check를 별도 확인한다.

- 1차 전체N 회귀 `task8-instant-reference-navigation-full.log`341passed321.89초,
  S28native통과와 합해 해당 범위369건이었다. 이후 자체 리뷰에서 동기 캐시 fallback을
  발견해 별도 RED2실패9.21초→관련62passed23.87초로 닫았다. 실제 f5 입력의 strict
  postmortem도410/누락0/오차0.0000342422를 유지하고 기준 삭제 음성을 거부했다.
  원본 FAIL과 그 시점 검증기/source hash는 변경하지 않았다.
- f5 조건부 역산 사후 분석:44native records/힘 포화0/팔목표 최대 오차
  1.35525e-20rad. arm2속도0.02610445,arm3속도0.02364773. 다리 역산목표20ms 차분
  0.00150797rad, odometry기반world속도 차분 가속도최대0.186899m/s². 이 값은
  모든 native2ms 명령 또는 순간 IMU가속도라고 부르지 않는다. `carry-excitation-analysis.json`
  원본 설명을 유지하며 팔 목표 소유권보다 base excitation 가설을 우선 검토한다.
- 한 실행의 정확한 보존본 `task8-gazebo-instantaneous-f5eff9bc.zip`14,278,979bytes/
  SHA256 `8afa141de8e1ef8a4fe0e5fc813913eaed38fa5cdc37366c3b13ebc97177c17c`.
  source71·실제FAIL/evidence/scene·시험 로그를 ZIP member별 재독 SHA 확인했다.
  원본/과거 실패/native 원본 삭제 없음. ZIP 후의 strict 순수 판정 변경은 현재 Git과
  별도 `task8-strict-native-reference-f5eff9bc.json`에 구분했다. 상세 복원/리뷰 안내는
  `Ch13/docs/SECTION_13_5_NATIVE_REFERENCE_REVIEW_KO.md`다.

- 새 실제 GZ `f5eff9bc-cc1a-49f1-a3d9-fc158b9b43db`는 **전체 FAIL 유지**:
  contact_calibration 중 carry `measured carry posture lost`, raw팔최대속도
  0.0261044473rad/s >0.02, 실제 lift0이다. 사라진 callback으로 추정하지 않는다.
  순간 ECM 기준은 **IMU410고유 capture/누락0/최대오차0.0000342422rad/s**로 통과했다.
  native scalar force538records/라이브러리 매핑/센서 신선도 등도 통과했지만 G1
  완료가 아니다. `joint_tf_ownership=false`는 성공 끝의 owner_attestation 단계에
  도달하지 못해 독립 graph 확인을 완성하지 못한 상태이며, 새 충돌의 증거가 아니다.
- 실제 종료: native관찰기 stopACK true → pause true → nativePID1141/부모1138
  **같은 PID exit0**, runtime/engine true, launch0, receiver joined, noforce/reaped/
  residual[] 확인. 실제 engine정리와바이트복사22파일의 `storage-copy-ledger.json`을
  확인한 뒤 다음 시험으로 넘어갔다. native원본도 보존했다. 추가clock계측기 없음,
  scopedLP2는 직전비교와 같으며 기본 채택 아님. source/설치 manifest는 해당UUID다.
- 순간기준 첫 build는 28native tests 통과했으나 build도중 REUSE수정 때문에 설치
  감사가 실패했다. 이를 무시하지 않았다. frozen 재build87초/native28 tests0실패/
  8패키지감사 통과 후 위 실제실행을 했다. 평균기준거부 포함 Python49passed27.75초.

- `task8-gazebo-controls-verdict-red.log` 누락 API15실패 뒤 GREEN35passed/13.53초.
  기존 be485/5dbc/571의68/851/539개 native packets를 새 메타데이터 검증기에 대입해
  모두 일치했다. 각 `native_controls_postmortem.json`에 입력·검증기SHA와 제한된 범위를
  적었다. 원본 result/manifest/실패는 수정하지 않았다.
- 운반 회귀 첫 RED는 test import 누락10실패였다. 이를 고친 confirmed RED10실패는
  실제 누락된 admission API였다. `task8-carry-owner-verdict-green.log`51passed/24.64초.
  이제 독립 raw 관측이 정상이어도 소유자 first_fault/FAULT/불명 결과/모델·세대 불일치가
  있으면 세부 carry 판정도 FAIL이다. 실제571의 raw만 PASS였던 맹점을 재현했다.
- GZ exact odometry history 첫 RED2fail7pass → 관련64passed/33.18초. **불충분한
  가설로 판정**: 5dbc는682개누락0/최대0.01930168이지만571은435개누락0/0.04321401.
  후자의 carry raw true/owner false도 확인했다. be485는 정적10초 미달 및 owner wall-age
  fault로 계속 FAIL. `capture-and-owner-postmortem.json`의 hash는 그 시점 검증기에
  해당하며 새 엔진 인수가 아니다. 뒤의 원본 소스 조사로 odometry는 평균, IMU는
  순간 component임을 확인했고 odometry를 IMU 정답으로 허용하는 분기는 철회했다.
- `task8-gazebo-instant-reference-red.log`2fail7pass/11.88초는 순간 기준 미지원 및
  평균 기준의 잘못된 허용을 각각 검출했다. native C++ 첫 RED는 헤더 위치 오류였고,
  confirmed RED는 `read_gazebo_body_reference` 미선언 컴파일 실패다. runtime assertion
  RED라고 부르지 않는다. 새 구현·실제 재측정 전에는 해결됐다고 선언하지 않는다.
- `task8-gazebo-observer-stop-red.log` API부재6실패 → GREEN17passed/8.59초.
  기존 stop service로 관찰기 송신부터 막고 pause/server stop을 수행한다. ACK는 종료
  증거가 아니며 실제 native PID exit0/회수/강제없음/잔여없음을 계속 별도 요구한다.

## Gazebo 시간 예산 후속 판별 — checkpoint abcc057 이후

- description 직접 PID 빌드44.1초/확장8패키지 source-install 감사 통과 후
  `5dbc1a36-6153-4fc8-83c6-3cea70449459` 실제GZ 실행:
  launch1141 → **직접 native child1144**, 실제3library 매핑도PID1144이며 같은PID의
  launch 종료 로그0을 수집했다. launch0·runtime exit true·강제 없음·회수·잔여[]이다.
  `/bin/sh` 종료나 stop ACK를 native 정상 종료로 대신 세지 않았다. 전체 G1은 여전히
  **FAIL**(10wall 교정 시간; IMU 비동기 cache 대조 오차0.02350rad/s도 남음)이다.
  native 기록 helper의 기존 `no_runtime_or_model_changes`는 helper가 코드를 편집하지
  않는다는 뜻이었다. 이 실행은 직전과 달리 description/script source가 바뀐 직접PID
  회귀이며, 실제source manifest가 이를 기록한다. 이후 helper metadata는 `purpose`와
  `driver_does_not_edit_runtime_or_model`로 명확히 구분한다. 원본 FAIL/ledger는 수정하지 않는다.
- 원생 library 검증 TDD `task8-gazebo-library-attest-red.log`: API 누락9실패8.42초.
  파일 경로·device/inode·실제 bytes SHA와 동일 PID/PPID/PGID/start tick·명령을 결합하고
  전후 identity/파일 변경을 거절한다. inode/device 교체 사례를 추가한 관련 회귀
  `task8-gazebo-library-attest-green.log`: **27통과10.85초**. 이는 fixture 산술 검증이며
  실제 mapper 성공으로 대체하지 않는다. 다음 실제 실행에서는 초기 READY 직후와 최종
  성공 구간의 매핑을 별도로 수집한다. source/설치8감사를 재확인했다.
- CPU 가설 격리 domain219 진단: 최초 도구는 Jazzy에 없는 qos_profile_clock import로
  시작 전 실패했다(엔진/자식 없음). 공개 QoSProfile로 교정했다.
  `clock-cost-diagnostic-2e76ac26-...json`의53.1%/17.5%는 **프로파일러 포함** 값으로
  운영 비용으로 인용하지 않는다. 오버헤드를 분리한
  `clock-cost-diagnostic-956e5e3d-085d-4fc1-9f3e-816d4c3c38bc.json`은 무계측3초에서
  500Hz idle ROS 수신19.2515%,50Hz6.50234%(one-core process CPU)다.
  계측 구간의 callback1500/150회로 주기 차이를 확인했지만 이는 합성 clock fixture이며
  실제 엔진 입력 빈도·전체 실패 근인을 증명하지 않는다. 프로파일 함수 시간은 계측
  오버헤드/코루틴 집계 영향을 포함하므로 절대 CPU 귀속으로 사용하지 않는다.
- 추가 Python 고주파 수신기로 실제 엔진을 더 부하 주지 않도록 읽기 전용 C++ clock
  계측기를 별도 사용자 build 영역에 만들었다(로봇 runtime 패키지/underlay 수정 아님).
  `clock-rate-fixture-6993765f-d4af-4eaa-9309-ae142404218f` domain219에서2458메시지/
  499.990Hz·publisher1·rollback0을 확인했다. 이것도 native 엔진 증거가 아니다.
  다음 실제GZ의 정적 구간에서만5초 계측하고 원본stamp 간격/GID·실행 binary/source SHA·
  진단 프로세스 CPU/종료를 기록한다. 시계 relay·속도/가속도/시간 상한 변경은 아직 없다.

- native 기록 비교 `571bdbe2-1fad-47fa-b209-fab9f96afe49` **FAIL**: SHIFT에서
  실제 carry arm2속도0.023103694rad/s>기존0.02. 동일 owner 선택joint stamp/판정ROS
  22.328초, arm3속도0.01841648 등 다른 팔은 기준 안이었다. 감쇠/게인/시간/힘 기준
  변경 없이 재발했으므로 저장 위치만의 해결이 아니다. 정적 관측9.98ROS/13.214146wall,
  RTF0.75525는 직전0.67148보다 높았지만 새 효과를 확정할 반복 인수는 아니다.
  calibration은0.78ROS만 관측돼10wall 완료 예산 비교는 중도 실패로 검열됐다.
  원본 native evidence20파일을 저장소로 byte/SHA 일치 복사했고 원본도 유지했다.
  runtime/launch0·강제 없음·회수·잔여[]·probe join 확인.
- `carry-excitation-analysis.json`: 실패 전후46 native snapshot 모두 비포화이며
  P법칙으로 **추정한** 팔 목표의 carry 목표 대비 오차 최대3.4e-21rad다.
  명령 토픽을 실제 native 명령으로 위장하지 않았으며 직접 command 관측은 아니다.
  다리 추정 목표 최대20ms차0.00200065rad, 회전 basis를 WORLD로 맞춘 몸체 속도
  차분 최대0.180245m/s²를 관측했다. 이는 실제 IMU 가속도나 모든 물리 스텝의 추적이
  아니므로 그 자체로 근인 확정/인수 판정에 사용하지 않는다. 단순 팔 목표 상실 가설은
  뒷받침되지 않았다. 무조건 gain 증대/속도 상한 완화는 하지 않는다.
- Task8 종료 출처 보강 TDD: `task8-direct-gazebo-child-red.log` 직접 child 없음으로
 1실패11.34초; `task8-description-runtime-audit-red.log` source/install 감사 누락4실패
 8.27초. navigation opt-in만 shell=False argv 실행으로 바꿨고 공식 설치 helper를
 import해 plugin/resource 환경을 보존했다. 첫GREEN은 테스트가 잘못된 공개 API 위치
 Executable.shell을 읽어1실패21통과17.69초였다. 올바른 ExecuteLocal.shell로 고친
 관련 회귀 `task8-direct-gazebo-child-fixed.log`는 **23통과15.80초**.
 기존13.4 경로 보존, 공백 포함 world 단일 argv, 변경/누락/소스 symlink 설치 거절을
 함께 검사했다. 실제 PID 매핑+exit 수집은 아직 실행 전이며 description 재빌드/감사 중이다.

- 로컬 `abcc057b8a2317d6034092abf15b969a270a2383`은 WIP 체크포인트이며 push하지
  않았다. 기존 Task8 source/tests와 MuJoCo3연속 G1 PASS 요약·69source 바이트 보존본을
  포함한다. 최종 Task8/G2/Nav2 완료로 표시하지 않았다. 사용자13.4교육 문서는
  stage/수정하지 않았고 원본 실패 raw도 로컬에 모두 유지한다.
- 설치8패키지 감사를 재확인한 뒤 `2e09eeac-7f06-4ff8-ae72-49b66f980472` 실제GZ를
  LP_NUM_THREADS=2 프로세스 한정으로 실행했다. native PID1131/start6676의 실제
  환경과3library 매핑을 수집했으며 root 최대59threads였다. **FAIL**: 원래10wall초
  교정 제한에 도달했다. 이 실행에서는 carry READY/first_fault=null이지만 이를
  과거 간헐 팔 속도 결함의 해결로 단정하지 않는다. 관측 정적 구간9.98ROS/14.862648wall,
  교정 구간6.478ROS/10.135101wall로 RTF0.67148/0.63916이다. 이전default 약0.69보다
  개선을 입증하지 못했으므로 LP2를 기본으로 채택하지 않는다.
- 최초 제한 도달 보고서: ROS24.008초, CALIBRATING/SHIFT/FL unload, unload시작19.650초,
  경과4.358초·명령 높이8.684mm 증가·FL 하중2.33117N으로 기존2N 미만 조건 미충족.
  지지·속도 조건 없이 시각만으로 발을 들지 않았고 기존 max10mm/2mm/s도 유지했다.
  all process0·강제 없음·회수·잔여[]·probe join 확인. STOPPED 미확정으로 runtime
  정상 인수는 실패다. wrapper exit와 service ACK를 실제 native PID 정상 exit 증명으로
  대체하지 않으며 direct native exit 증거 보강은 여전히 미완료다.
- Ruling: `_validate_limits`의 unload_speed_mps 상한0.002를 올리거나10wall 기준을
  늘리지 않는다. 다음 판별은 같은 LP2/소스/설치/모델에서 **실행 기록 위치만**
  `/home/jinho/ch13_5_completion_.../evidence`로 바꾼다. 준비 장면은 기존처럼 저장소
  evidence에 두고 실제 운전 중 raw/system/process/driver 기록만 native 영역에 쓴다.
  종료 후 원본 native 파일을 그대로 보존하고 새 저장소 UUID로 byte/SHA 일치 복사한다.
  `storage-copy-ledger.json`은 실제 command root와 복사 출처를 명시한다. 위치 효과의
  실험이며 runtime 수정·driver 변경·자료 제외·제어 한계 완화가 아니다.

## 최신 판별: 검사기 수신 소유권과 IMU 촬영 대조

- 최신 navigation 전체 회귀 `task8-imu-capture-navigation-full.log`:
  **283 passed/303.63초**, 직전 원생 센서27건도0error/0failure/0skip이다.
  이전294건의 stale 기대값 실패를 소급 수정하지 않고 새 전체 실행으로 확인했다.
  이 합계310건은 navigation+센서 범위이며 Ch13 전8패키지/기존13.3·13.4 전체 행렬
  재실행을 완료했다는 뜻이 아니다. runtime 수정 없이 문서 REUSE의 CRLF 혼입만
  LF로 정리한 뒤 diff whitespace 검사도 통과했다.

- **MuJoCo G1 수정 후 3회 연속 PASS 확정**:
  `6f390aa7-0b81-4f3b-9711-18de43e2b9dc` →
  `296cc582-b465-42a7-bda5-c941cc5d4f64` →
  `5fab26df-0a01-486e-9f25-83f7d3ccfbe7`, 각각23/23 required checks true.
  추가 두 실행 IMU720/764고유 촬영·누락0·최대오차0.00369906/0.00300633rad/s,
  lift56/54고유 촬영이다. 세 실행 모두 source_manifest와install_manifest 전체 및
  실제 원본 source bytes SHA가 동일했다. 모든 engine/runtime0·join·회수·강제 없음·
  잔여 없음 확인 뒤에만 다음 엔진을 시작했다. 첫 실패 시 중단하는 드라이버의
  `task8-imu-reliable-g1-confirmations.json` passed=true이며 원본FAIL들은 그대로다.
  69개 정확한 source bytes를 검증해 `task8-imu-reliable-frozen-source.zip`
  (188698bytes/SHA256 f25102c7d7202b21de3dac5fc0271b5c944c5c663569163fd4ed23d46e2bf578)
  으로 보존했다. **이는 MuJoCo G1만 통과한 것으로 G2/Gazebo/Nav2/Task8 완료가 아니다.**

- 신뢰 전송 후 원생S rebuild1분56초·27건/0error/0failure/0skip·8패키지 설치 감사
  통과. 실제 MuJoCo **`6f390aa7-0b81-4f3b-9711-18de43e2b9dc` G1 23/23 PASS**.
  IMU760고유 capture/기준 누락0/최대오차0.0029212526rad/s<기존0.02,
  실제 단일 발 lift51고유 capture, 수납·typed terminal·native provenance·TF 소유권·
  정상 runtime/engine 종료 모두 통과. worker와receiver join true, launch와engine0,
  forced_cleanup=false·parent_reaped=true·residual=[]를 별도 teardown에서 확인했다.
  기존 실패(d0/7c3/6a 등)는 제외하지 않고 보존한다. 이 PASS는 G1 MuJoCo 1회이며
  G2·Gazebo·Nav2·최종 전체 회귀의 대체 증거가 아니다.
- 추가2회는 source_manifest 전체·설치 manifest·실제 source bytes SHA를 앞선PASS와
  대조하며 순차 실행한다. 첫 FAIL/불일치/정리 미확정에서 중단하고 자동 재시도하지
  않는 `confirm-mj-g1.py`를 사용한다. 최종 판정은 새 confirmation JSON에 보존한다.

- 진단 신뢰 전송 TDD: `task8-imu-reliable-native-red.log` 실제 pluginlib/ROS에서
  RELIABILITY 비호환 경고와 controls.empty로1실패3.554초. 수신기 endpoint 회귀
  `task8-imu-reliable-probe-red.log`도 BEST_EFFORT로1실패11.12초다.
  양단 진단만 RELIABLE/KeepLast100으로 변경했다. 첫 관련GREEN은1실패33통과28.39초:
  Jazzy RMW graph가 history depth를0(미제공)으로 보고해 테스트 가정이 잘못됐다.
  해당 관측 불가 assertion만 제거한 `task8-imu-reliable-probe-fixed.log`는
  **34통과23.96초**다. source 계약의 bounded KeepLast100은 유지하며 센서/제어 QoS는
  변경하지 않는다. 원생 rebuild/27회귀/8설치 감사 후 새 실제 장면을 실행한다.

- 원생 동일 snapshot 구현 후 S빌드1분45초·**원생27건/0error/0failure/0skip**,
  선택8패키지 설치 감사 통과. 실제 `d0f25980-f841-4e5b-871a-ebc214d77cab`는
  다시 **IMU 하나만 FAIL**, 물리 lift/수납/typed terminal/정상종료 등 나머지 전부 true다.
  worker와receiver join true, engine/runtime0·강제 없음·회수·잔여 없음.
  `imu-reference-coverage.json`:757고유 IMU 중751은 정확히 같은 native capture와
  대조됐고 최대오차0.00729323rad/s/한계 초과0개다. 나머지6capture의 큰 진단 메시지가
  수신 기록에 없다. 센서 plugin은 같은 lease에서 IMU와 JSON을 함께 발행하지만
  진단 토픽도 best-effort였으므로 두 토픽의 동시 도착은 보장되지 않았다.
  누락6개를 삭제하지 않고 FAIL을 유지했다. 다음은 진단만 RELIABLE/유한 queue로
  바꾸는 실제 ROS 계약 회귀다. 센서·제어 QoS/시각/기준은 그대로 유지한다.

- fastFK 관련43통과50.05초, live 보고서5통과20.87초 후 설치 감사8패키지 통과.
  실제 Gazebo `82895c1e-f8b2-4587-ac52-5b22b8bcf961`은 정적10.002ROS/14.477wall초,
  SHIFT에서 팔2속도0.0281001/팔3속도0.0241314rad/s로 FAIL했다. owner 선택 관절
  stamp22.190/판정ROS22.194초이며0.02한계를 유지했다. 추가 gain 변경은 없다.
  전 프로세스0·강제 없음·회수·잔여 없음이나 STOPPED 미확정으로 정상 인수는 실패다.
- 실제 MuJoCo `6a94dda3-8179-4046-ac39-be556a090dab`은 단일 발 검증을
  9.932ROS/9.901917wall초에 마쳤고 실제 terminal/native 출처/정상 종료도 통과했지만
  frame1112의 여러 스트림 wall age약228–242ms 한 건으로 전체 FAIL이다.
  제어 소유자 fault는 없었다. 수신기와 부모 IO/프로세스 조회를 같은 executor에 묶은
  구조를 분리했다. 실제 ROS 관련20통과18.98초; 예외 고착·blocked callback join 실패
  자원 보존도 검사했다. 임계치 완화·outlier 삭제·자동 재시작은 없다.
- 다음 실제 MuJoCo `7c3d8a5e-0479-4b75-be72-b4ead8a6461e`: **IMU 하나만 FAIL**,
  나머지 required checks는 true다. 수납868고유 관측 최대오차0.019082rad,
  속도0.018871rad/s/그리퍼0.003115m/s, 단일 발 물리검증·freshness·typed terminal·
  native 관측/TF·정상 runtime/engine 종료 통과. receiver join true·exit0·강제 없음·
  회수·잔여 없음. 전체 FAIL 원본을 바꾸거나 성공 반복에 포함하지 않는다.
- `imu-alignment-analysis.json`: 독립 최신 cache의 IMU/body 시차34–54ms에서
  gyro오차0.02 초과4건. 최악31.412/31.446초,0.040626rad/s다.
  `imu-history-analysis.json`은 **인수 아닌 사후 가설**이며20ms내 선형BODY보간은
  752중314누락으로 채택하지 않았다. 모든752개는 원본 body history 안에 존재했다.
- Ruling: 같은 immutable snapshot의 free-root qvel 각속도를 gyro와 독립적으로 읽어
  기존 native_controls 진단에 넣고 exact capture로 대조한다. 촬영 header/epoch,
  .02rad/s 기준과 누락 실패를 유지한다. body 좌표를 WORLD로 중복 회전하거나
  sensordata를 정답으로 재사용하지 않는다. 신규 명령 소유자·engine 쓰기는 없다.
- `task8-imu-capture-red.log`: async positive case1실패/6통과13.04초.
  최소 검사기 수정 후 `task8-imu-capture-green.log`: 관련41통과22.69초.
  원생 회귀 `task8-imu-qvel-native-red.log`는 미구현 body_angular_velocity 멤버의
  컴파일 실패를 확인했다(실행 assertion 실패와 구분). 이어 원생 구현·빌드·전체 sensor
  회귀·설치 감사 중이며 실제 엔진 성공으로 아직 집계하지 않는다.

## 효율 개선 적용 후 단일 원인별 판별

- 실제최적화c948d056-0759-4224-a987-d74a1c23b10d: 새ELF3개의 실제mappedSHA·기본LP환경
  확인. 정적10.004ROS/14.6583wall(이전21.38wall), calibration6.694ROS/10.0618wall에서
  원래10wall초제한 실패. 그 시점CALIBRATING/SHIFT/FL하중해제 중이었고 최초fault/stop 없음.
  carry804고유관측 최대오차.0218639/속도.0103384rad/s, 그리퍼.000904m/s로 해당 구간의
  수납은 기준 안이었다. 전체G1은 실패다. process모두0·강제 없음·회수·잔여 없음.
  정적RTF.68491/crawl79.96%/guard61.00%/native143.31%onecore. 기준 변경 없이 남은
  실행 예산·하중 해제 단계를 분석한다. 최적화만으로 전체 완료라고 하지 않는다.
- c948운전 프레임 신선도를 전부 조사한 `frame-freshness-analysis.json`: scanwall_age1회,
  frame658/ROS16.412/ROSage112ms/wallage301.578094ms. 이 표본을 삭제하거나300ms한계를
  바꾸지 않는다. probe는 이미미래COM/일반sensor후보를 보류하므로 추정만으로 고치지 않는다.
- hotFK계산량 RED1실패2통과7.88초(일반4x4solve4회) → 관련43통과50.05초.
  검증된Rx/Ry/Ry URDF에만 해석적식을 사용하며 일반axis fallback·관절 한계·비유한값검사
  유지. 독립MuJoCo32자세·일반axis·기존물리/보행시험 통과이며 실제엔진 대체 증거는 아니다.
  오류가 아닌 제한시간 실패에서도 현재unload명령·floor를 볼 수 있도록 읽기전용 live보고서
  회귀를 추가했다(RED1실패10.49초). 현재 관련GREEN검사 후 새 실제 시험으로 진행한다.

- RelWithDebInfo 실제 빌드S3분29초/N18.5초/전체3분48초, 설치8감사 통과.
  고정gz1.2.20의 legacy hardware export API deprecation 경고는 빌드 로그에 보존했다.
  전체 회귀는 **294건/0error/1failure/0skip**: 유일한 실패는
  `test_nav_gazebo_position_system_binds_gains_without_changing_legacy_hardware`의
  옛calf500/arm3kv20 기대값이다. 현재calf750/arm3kv40 후보 literal로 교정한
  장면·정적 하중 관련9건은15.45초에 통과했다. 전체294 실행을 소급해 성공으로 바꾸지 않는다.
  frozen 최종 전체 인수에서 다시 실행할 예정이다. runtime 코드 변경은 없다.
- `native-optimized-build-provenance.json`에 실제 old/new CMake cache·target flags·ELF SHA,
  GCC13.3.0을 기록했다. 원래3개GZ target flags에는-O가 없었고 새flags는-O2 -g -DNDEBUG다.
  fast-math는 없다. byte가 달라졌으므로 새 actual mapping 및 실제 구동 결과가 필요하다.

- 실제82ffc55f-858a-44cb-b519-c9a06cf48956: mappedPID1183 환경LP_NUM_THREADS=2 확인,
  최대스레드59(이전71). bootstrapRTF.463/정적 일부2.528ROS/4.889wall이라 명확한
  속도 개선을 입증하지 못했으며 기본 설정으로 채택하지 않는다. 정적 구간guard:ros_age 실패,
  모든process0·강제 없음·회수·잔여 없음. 실제 guardstamp11.578초 > 로컬ROS11.576초로,
  과거250ms지연과 달리 미래2ms의 callback/clock 도착 순서였다. 임계치 완화로 숨기지 않는다.
- guard 회귀: 시험노드 참조 오기1실패11.38초 보존(원인 재현으로 세지 않음), 교정 후
  실제node callback/clock 분리RED1실패12.13초. 최대10후보 중 로컬ROS 이하 최신만 선택,
  header/최초receipt 유지·중복 갱신 금지·원래200ms 만료·inactive 준비 guard 검사 적용.
  첫관련6통과1실패27.02초는 옛 시험의120ms 즉시 만료 가정이었다. 마지막 유효 capture의
  실제200ms 만료를 기다리게 교정한 뒤 관련10통과36.76초. 실제 반복 인수는 아직 미완료.
- 빌드 병목 판별: 기존S CMakeCache의CMAKE_BUILD_TYPE/CXX_FLAGS 모두 비어 최적화 없음.
  Ch13 일반 사용자 native prefix에서만 RelWithDebInfo(-O2 -g -DNDEBUG)/빌드병렬2를 선택해
  S+N 전체빌드·8패키지 감사·전체 두패키지 회귀를 진행한다. 외부 underlay 변경이나
  fast-math/물리/힘/안전/카메라 설정 변경은 없다. 새 ELF hash로 실제 성능·결과를 다시 검증한다.

- 실제950a56ec-f016-4e0f-b6ed-f0deb9962eef: 분할 탐색 관련36통과66.75초,
  기준 고정 후5통과18.02초, N빌드22.1초/설치8감사. 오프라인20회 최대slice9.49ms,
  전체 중앙31.57ms/최대44.66ms; 목표·곡선 시간은 baseline과 동일하다.
  실제실패 직전16tick5.81–13.64ms, age위반이 아닌 팔1/2/4 속도 위반으로 실패했다.
  선택joint19.310초에서qd=-.02078356/-.03890714/+.03085482rad/s, 팔3=-.00131890.
  READYeterminal/위치 오차는 허용 범위였으나 이를 전체 수납 성공으로 집계하지 않는다.
  모든process0·강제 없음·회수·잔여 없음, 정상/전체G1 성공은 아니다.
- 원인 범위 갱신: arm3만 증대하는 접근은 전체 하중 이동 안정성을 해결하지 못했다.
  실제 몸체 속도차분31고유 관측 최대.1598m/s²(몸체basis 회전 보정 없는 범위 명시),
  내부 목표 곡선 .10m/s²와 실제 가속은 같지 않다. 다음 팔 게인 증대를 반복하지 않는다.
  950정적 구간은9.974ROS/21.323wall, engine143.27%onecore/71threads,
  crawl80.86%/guard54.10%였다. 이에 동결runtime/model의 다음82ffc55f는
  프로세스 한정LP_NUM_THREADS=2만 비교한다. 모든 안전 기준·카메라320×240/15Hz 불변,
  드라이버/시스템 설정 불변이며 실제 mapped PID의 선택 환경 키를 별도 증거로 수집한다.

- 실제149959a0-4fb0-44cc-ac36-3d8d11dcedb7: arm3감쇠 후보 관련8통과17.78초,
  N빌드21.9초/설치8감사 통과 후 실행. 첫SHIFT에 contacts:wall_age로 실패해 감쇠 효과는
  판정 불가다. 최초fault ROS18.354초, 접촉stamp18.284초/receipt424022331995,
  판정wall424228131181: ROS70ms/wall205.80ms. 직전tick173.879ms 이후 queued callbacks.
  모든process0·강제 없음·회수·잔여 없음. 성공으로 집계하지 않는다.
- 오프라인 계산 재생: 첫shift-cost-before는 설정 파일 로드를 포함했으므로 실제loop 비용으로
  쓰지 않는다. cached-config-before 중앙28.00/max34.33ms, profile의FK741회/CoM22ms/IK17ms.
  CoM 공통경로 캐시 RED1실패1통과10.31초 → 관련38통과68.31초. 변환은 한 측정 안에서만
  재사용하며 다음 측정에는 폐기한다. after 중앙28.95/max39.45ms, FK312회/CoM14ms/IK26ms.
  계산 횟수는 줄었지만 전체 wall 비용 개선을 입증하지 못했으므로 수정만으로 해결이라 하지 않는다.
- Ruling: coarse9점/binary8회 동일 탐색을 후보1개/안전 주기로 나눈다. 기존 센서·지지·owner·
  STOP 검사를 매 주기 우선하고 계획 중 기존 명령을 유지한다. 완성 후 곡선 시계를 시작하며
  STOP/FAULT는 탐색을 버린다. 새스레드/두번째명령소유자/age완화 없음. 추가 명목계획시간은
  기존10wall초calibration 예산 안에 포함한다. 계산량RED1실패2통과10.51초(한tickCoM14회)
  → 기존물리/보행포함36통과66.75초. 기준자세를 불변 복사한 최종 관련 회귀를 이어 실행한다.

- 실제626473a5-e032-4979-94c3-e6b59eb4fe75: 최초carry보고서 확보. READY 실패 판정
  ROS17.590초, 선택joint17.578초(12ms), 수신후19.3ms. arm3 q=-2.018997141870555,
  qd=.02803877186796927. 오차.018997rad<.03, 속도>.02이며 다른팔/그리퍼는 해당 한계 이내다.
  guard/crawl 모두 같은generation0/modelhash, 선택상태CALIBRATING. age/terminal실패가 아니다.
  정지3초 제한 내 STOPPED는 미확정, wrapper/runtime0·강제 없음·잔여 없음이어도G1FAIL.
  source21.4초 재빌드/설치8감사 및 nativePID라이브러리 수집 통과. 원본실패 보존.
- Ruling: 실제 실패626(원생 전체 시험 RED)를 기준으로 팔3 kv20→40만 비교한다.
  kp105/힘 한계·모델 질량·제어율·모든 인수 기준은 불변이다. 위치 강성은 오차 기준 이내이고
  하중 이동의 상대 속도 억제가 목적이다. 감쇠와 응답은 전체 연성 동역학에 의존하므로
  단순히2배면 무조건 성공한다고 주장하지 않는다. 새 양 엔진 physics/profile 해시로 재검증한다.

- 실제8fcaed13-3026-49ac-8550-b2339085192e: calf750 후보 N빌드28.6초/설치8감사 통과.
  시동·수납 READY·정적10초 후 contact_calibration에서 carry:measured carry posture lost.
  주변18.404초 native prephysics arm3 q=-2.0189842553,qd=.0219094796으로 기존.02초과지만
  CarryManager 동일 선택 입력은 아직 없으므로 원인 확정/재조정으로 뛰어넘지 않는다.
  wrapper/runtime0·강제 없음·회수·잔여 없음. filtered carry 평가 true를 전체 성공으로 쓰지 않는다.
- 최초 팔 실패 입력 보존: 실제ROS /report 회귀 RED1실패27.43초(KeyError:first_fault) →
  관련2통과25.37초. lock 안의 최초 selected cache를 깊은 복사하고 이후 입력으로 덮어쓰지 않는다.
  정지 실측이 실패해도 carry_failure_report.json을 먼저 확보한다. 임계치/제어/lease 변경 없음.
  다음 실제 Gazebo 1회에서 소유자 입력과 주변 native 관측을 연결한다.

- 고정 일반 사용자 Linux 영역 `ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b`를
  만들고 설치607파일 해시를 대조했다. source는 원래 저장소에 두며 외부 원본은 불변이다.
  navigation만 재빌드23.0초/후속21.4초와 실제 선택8패키지 감사를 확인했다.
  기존 audit wrapper가 Windows prefix를 다시 선택한다는 점을 발견해 native 전용
  감사 wrapper를 분리했다. 수정 중 첫 native 감사의 `gait.py` 불일치 실패도 보존했다.
- 활성화 명령 인계: 커널RED4실패 → 기존 상태기계 포함35통과68.23초,
  실제ROS 첫 명령RED1실패11.77초(1.035 vs1.0), 초기값 출처RED3실패 →
  인계8통과15.18초. 관련 lifecycle/안전/Python 물리10통과40.57초.
  명령 FK 목표만 기존 명령으로 인계하고 실측 앵커·floor·안전 판정은 바꾸지 않았다.
- Git 감사 범위: 실 임시 저장소RED2실패 → 프로세스·증거 회귀 포함12통과9.93초.
  HEAD와 모든 해시 대상 runtime 수정/미추적 파일은 기록하되 과거 evidence 트리는
  순회하지 않는다. manifest에 `dirty_scope=hashed_runtime_files_only`를 명시한다.
- 실제5091c217: 활성화 구간 네 발 하중은 유지됐지만 guard ROS age로 실패했다.
  이후STOPPED를 실측했어도 GazeboSIGTERM/SIGKILL 승격·forced=true·launch-15를
  보존했다. 부모 회수·잔여 없음만으로 정상 종료라고 하지 않는다. 실제라이브러리
  소유권 자동수집은 성공했다. 새 실행의 성공률에 이 실패를 제외하지 않는다.
- kernel first_fault만으로 STOPPING 원인을 설명할 수 없어 첫stop의 선택 guard/header,
  수신 시각/노드ROS시각/직전16callback소요를 보존했다. 실제DDS250ms지연RED1실패
  16.56초 → 기존 최초fault·명령 인계 포함3통과17.10초. 200ms 기준은 그대로다.
- 실제64989f80: guard age 재발 없음·STAND 지지 유지, kernel first_fault/first_stop 없음.
  그러나 STAND ready 미확정으로 startup45초 제한 실패다. wrapper/runtime0·강제 없음·
  부모 회수·잔여 없음이 확인돼도 G1을 통과했다고 하지 않는다.
  `static-preload-budget.json`은 마지막5ROS초251고유 관측을 모두 사용했다.
  앞 calf 비포화 위치력17.74983371Nm/최대속도4.03e-7rad/s,
  P법칙 유도 오차0.035499667rad가 기존0.03rad 준비 기준을 넘는다.
  이는 직접 적용 actuator force나 내부 선택 목표 측정으로 부르지 않는다.
- 설정 후보: calf만kp500→750/kv8.944272→10.954451(sqrt1.5비), 기존30Nm 한계는 유지.
  반올림 상향18Nm 설계 부하의 오차0.024rad를 기대하되 실제 인수는 별도다.
  예산RED1실패12.07초 → 예산/물리/장면9통과32.78초. 새 양 엔진 physics/profilehash와
  실제 재검증이 필요하다. 다른 게인·안전 기준은 바꾸지 않았다. 다음 실제 실행은 고유UUID다.

## 재개 후 관측 경계와 시동 시간 판별

- `task8-gz-native-damping-package.log`: 두 패키지 빌드 후 전체276건 중275통과/1실패.
  실패는 수납 READY 이후 이상 입력을 설정하고80ms만 기다려 수신 상태를 단정한 시험이었다.
  실제 이상 감지·선택된 관절 입력·클라이언트의 fault 수신을 각각 기다리도록 시험만 교정했다.
  첫 후속 실행은 새 검증 코드의 저장 위치 오기(`selected`는 guard/crawl 전용)로13통과/1실패,
  이를 실제 `inbox.samples['joints']`로 바로잡은 `task8-carry-observation-storage.log`는
  **14통과149.31초**다. 원래1초 정착·200ms watchdog·고착 실패 조건은 변경하지 않았다.
  설치8패키지의 현재 소스 일치 감사도 `task8-native-damping-resume-audit.json`에 통과했다.
  전체276건 실행을 소급해 성공으로 바꾸지 않는다.
- 새 원생 감쇠 실행 `4d5bf634-812b-4b17-b9f5-a061824a471b`
  (run_id `25628fd6-511b-4078-9ddf-d7d20f8c7767`)는 **시동55초 제한 실패**다.
  관절 상태 broadcaster를 얻지 못했고 실측 프레임0개여서 정적/보행 비교 결과가 아니다.
  native 구동91개는 관측됐으나 운전 중 연속 수납·지지 판정을 대체하지 못한다.
  실제 서버PID1202/start33913/PPID1192/PGID1189의 라이브러리3개 경로·해시를 확보했다.
  엔진 wrapper는 SIGTERM(-15)로 종료됐다. parent 회수/잔여 없음이 확인돼도
  `forced_cleanup=true`, 정상 종료 false를 유지한다. 다음 실행과 섞지 않는다.
- 프로세스 start tick 대조에서 첫 자식 생성까지4d5는33.69초,
  이전547은20.20초,384는22.65초였다. 처음부터 순수 물리 계산이55초 걸렸다고 하지 않는다.
  모든 관측 단계가 시작되지 않은 `phase-timing-analysis.json={}`도 그대로 보존한다.
- NumPy 자체의 불필요한 BLAS 스레드 가설을 별도 일반 사용자 프로세스로 확인했으나,
  기본/프로세스 한정 OPENBLAS·OMP=1 양쪽 모두 import 후1스레드였다.
  따라서 관측된 ROS 노드15스레드를 BLAS라고 단정하거나 관련 설정을 수정하지 않았다.
- 다음 판별은 설치 파일을 모두 해시 대조해 Linux 소유 임시 영역에 복제하고,
  소스·바이너리·안전 기준은 그대로 두는 저장 위치 비교다. 복제 manifest·새 설치 감사·
  실제 실행을 각각 기록한다. 캐시 온도도 달라질 수 있으므로 단일 실행의 성패만으로
  저장 장치를 유일 원인이라고 결론 내리지 않는다. 아직G1/G2 통과나13.5 게시가 아니다.

## 2026-10-24 원생 구동과 계측 경계 판별

- 명령 관측 단계를 고친 센서 패키지21건과 설치8패키지 감사 통과 후,
  `54776df9-c003-44b1-af38-a554c8135e41`에서 실제20관절/1,040구동 진단을 얻었다.
  SHIFT에서 두 점 하중 지지가 재현됐으며 일부 전달 토크가20/30Nm 축 한계에 닿았다.
  직접 적용 구동력은 제공되지 않았으므로 무제한 토크라고 해석하지 않았다.
- 위치 명령을 유지한 제한 힘 PD 후보·모델 결합의 전체270건/설치8패키지 감사는 통과했다.
  그러나 첫 실제 비교 `31bc111a-cf0c-42f1-b7b0-962fdb76ed9c`는 시동 중 계측기 오류
  `CPU sample ownership changed`로 중단됐다. 물리 PD 실패로 집계하지 않는다.
  종료의 SIGTERM 승격·정상 종료 false는 그대로 보존했다.
- `proc-exit-characterization-6c6f4a26-01a8-414c-bf65-c2f7ca59c82d.json`에서
  일반 사용자 자식의 UID1000은 그대로인데 zombie의 `/proc/PID/stat` 파일 소유자만0이
  됨을 실제 확인했다. 관련 회귀2실패/3통과 → 수정 후27통과16.07초.
  동일 PID/start tick/PGID의 확인된 종료만 표본에서 제외하며 살아 있는 외부 소유자와
  PID 재사용은 계속 fatal이다. 권한·보안 정책을 바꾼 것이 아니다.
- 그 뒤 `38499c57-595c-4c11-8651-8f84c9f787ae`에서는 계측 오류가 재발하지 않았고,
  실제 서버PID1222에서 PD/관측 라이브러리3개의 경로·해시를 `native-owned-tree.json`에
  확보했다. 그러나 시동 대기 입력477개가 **실제 관절 속도 한계**로 거절됐다.
  팔 속도가 약±2/3rad/s로 진동하고 그리퍼는 약0.474m/s였다. 신선한 관측이며
  제어기 first_fault는 없었다(비활성 대기). 외부 probe 해석을 내부 선택 입력이라고 하지 않는다.
  종료0·강제 없음·잔여 없음이어도 측정 STOPPED 미확정 때문에 정상 종료 check는 false다.
- 원인 판별용 `dart-damping-study-fe875293-b545-44ae-bcd0-7442a7785cb3.json`은
  설치된 DART6.13.2의 독립1DoF 두 모델을 순차 실행했다. dt2ms/힘 한계12Nm/같은
  kp60·kd10에서 명시적 미분 힘은 속도3rad/s 진동·오차0.1rad가 남았고,
  원생 암시적 감쇠는 마지막200ms 오차1.93e-6rad·속도1.17e-5rad/s로 정착했다.
  **Gazebo 전체 로봇 G1 인수 성공이 아니라 적분 방식 판별 실험**이다.
- 새 후보는 원래 수동 감쇠+가상 감쇠를 모델에 명시하고 외부 힘에는 제한된 위치력만
  적용한다. 원생 감쇠·접촉 wrench를 actuator force로 위장하지 않는다. 새 물리 해시와
  실제 G1/G2 재검증이 필요하다. 장면 회귀8건 통과했고 하드웨어 감쇠 중복/모델 불일치와
  native damping 관측 누락을 각각 RED로 재현했다. 새 실제 엔진 성공은 아직 없다.
- 실패한 명시적 후보의 runtime4파일을 기존 source manifest SHA와 대조해
  `native-g1-gazebo-38499c57-595c-4c11-8651-8f84c9f787ae/failed-explicit-runtime-source.zip`
  에 보존했다(SHA256 `93e31b0b7dde237cd2a530de547e4161aa346359cfaf3547343fe59174d4a1b5`).
  원본 결과·로그·source/install manifest는 덮어쓰지 않았다.

## 최초 실패 입력에 근거한 Gazebo 지지력 분석

- `task8-gz-fault-exit-package.log`: **259 tests, 0 errors/0 failures/0 skipped**.
  `task8-gz-fault-exit-install-audit.json`:8패키지 설치본·출처 감사 통과.
- 후속 실제 실행 `native-g1-gazebo-81da9758-805b-4052-8f44-057e4995ff66`은
  **FAIL**이다. 정적10초·수납 typed terminal/원본 위치·속도 검사는 통과했지만,
  SHIFT 시작22.354s 뒤23.030s에 `current measured support lost`가 발생했다.
  `controller_report.json`은 제어기가 그 tick에 실제 선택한 불변 입력을 보존한다.
  접촉 촬영23.024s에서 FR76.9202/FL0/RR0/RL72.0329N이었다. unload는 아직 시작되지
  않았고 swing_foot도 없다. 관절/몸체 촬영은23.028/23.020s, ROS age2~12ms,
  wall age7ms 미만이다. 오래된 입력/발 들기 명령/TF 부재를 원인으로 추정하지 않는다.
- 원본에서 계산한 `controller-support-analysis.json`:실제 하중 지지점2개,
  몸체 속도 약(-0.03728,-0.02100,0.000148)m/s, 높이0.46046m다.
  발의 FK 높이가 약0.02m이고 몸체 기울기가 작아도 하중 지지점3개를 보장하지 않는다.
  이론적 지지 다각형과 실제 힘에 의한 지지를 구분한다.
- 접촉 어댑터 PID1167은 이번 실제 실행에서 SIGINT 종료0으로 바뀌었다.
  기록된 runtime 자식 모두 종료0이고 엔진 wrapper0·부모 회수·강제 정리 없음·잔여 없음을
  확인했다. 그러나 sticky FAULT 뒤 측정 STOPPED가 확정되지 않았으므로 전체 정상 종료
  check는 여전히 false다. 종료 코드0만으로 정지 실패를 숨기지 않는다.
- 다음 가설은 Gazebo 위치→속도 구동과 MuJoCo 감쇠 위치 PD의 동역학 차이다.
  아직 확정하지 않는다. 실제 ECM 관절 상태·명령·전달 wrench의 읽기 전용 계측을 추가한다.
  전달 wrench와 실제 actuator force는 다른 값이며 제공되지 않은 후자는 null로 남긴다.
  코어 회귀 `task8-gz-controls-red.log`의 API 부재 →
  `task8-gz-controls-first.log` 실제 ECS 2건 통과. 수신 회귀는
  `task8-gz-controls-probe-red.log`2실패/9통과 →
  `task8-gz-controls-probe-first.log`11통과9.47초다.
- 공식 Physics 구현의 명령 초기화 단계도 검토했다. 물리 계산 이후의 0값을 적용 명령으로
  오해하지 않도록 소비 전 관측 단계 계약을 추가 검증한 뒤 다음 엔진을 실행한다.
  외부 소스·드라이버·시스템 권한·힘/시간/3점 지지 기준은 변경하지 않는다.

## Gazebo 교정 실패와 종료 처리

- 실행 `d5460fa1-f944-4b79-ab83-54ee8536743b`(run_id `d8224db6-d6b9-4ebc-9d60-9a534c2553e0`)은 시동 경쟁 수정 후 실제 FJT terminal·수납·정적10초를 통과했다. 교정 SHIFT에서 `current measured support lost`로 실패했고 발 들기까지 도달하지 않았다. 외부 probe의7개 frame check가 true여도 제어기가 선택한 정확한 실패 입력이 같다고 단정하지 않는다. 팔 최대 위치 오차1.93×10⁻⁷rad/속도2.15×10⁻⁶rad/s, 센서 힘·IMU·scan·충돌 판정은 기준 이내였다.
- STOPPED는 확인하지 못했다. 엔진 프로세스는 종료0·강제 없음·잔여 없음·부모 회수를 확인했지만, 접촉 어댑터의 SIGINT가 처리되지 않은 KeyboardInterrupt로 종료-2를 냈다. runtime 정상 종료 미확정이므로 전체 normal check는 false다. GZ 실제 제어값/라이브러리 출처도 아직 미구현이며 성공으로 세지 않는다.
- `task8-gz-fault-exit-red.log`:2실패17.23초. 실제 ready 어댑터의 SIGINT 종료-2와 제어기의 첫 실패 입력 조회 기능 부재를 각각 재현했다. 예외 처리·join.stop 및 읽기 전용 첫 실패 snapshot을 추가한 `task8-gz-fault-exit-first.log`:관련17건 통과29.25초. snapshot은 제어기 첫 fault 관측 tick의 선택된 촬영·수신 시각·phase·목표를 보존하고 후속 건강한 입력으로 덮어쓰지 않는다. 실제 fault가 advance 중 발생했는지도 구분한다. 물리 원인 수정이 아니라 원인을 판별할 계측이며 다음 실제 실행으로 분석을 계속한다.

구현 시작: `a077ff2b15145e58fca8319595215d0db41cf905`, 브랜치 `feat/ch13-section-13-5`.
작업 범위: 사용자 승인 상세 설계·구현 계획. 네이티브 단일 작업자.
아래 기록은 초기 구현 시험이며 G1~G5 실제 엔진 인수 완료가 아니다.

## G0

- 기존 설치 감사: `python Ch13/scripts/verify_all_13_4.py --audit-install-prefix Ch13/ros2_ws/install13_4_completion_f8c0bed5-cdac-43d8-81ff-84ab88360cdb`.
- 결과: 기존 6패키지 소스/설치 byte 감사 성공. 원본 JSON: `g0-install-audit.json`, stderr: `g0-install-audit.stderr`.
- 기존 소스 시험: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test -q`.
- 결과: **374 passed, 224.38초**, `g0-pytest.log`.
- 원격 조회: 일반 sandbox의 네트워크 연결 실패 뒤 허용된 네트워크 조회로 재확인했다. 동명 13.5 원격 브랜치 없음. main은 `e83fe949553d9a2217c274c0bab23bf8f0713241`. 원격 변경은 하지 않았다.

## Task 1

- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test -q`.
- 최초 `task1-red.log`: 3 failed/9 fixture errors. 누락 샘플 모듈과 신규 IDL 때문에 실패했다. 모델 계약 시험을 더하고 fixture 부재를 시험 본문에서 드러내도록 고쳤다.
- 재확인 `task1-red-confirmed.log`: **15 failed**, 새 샘플/모델/IDL 부재. 무관한 의존성 실패를 의도한 RED로 세지 않았다.
- 순수 코어 GREEN: 같은 명령에서 `test_samples.py test_model.py` 선택, **12 passed, 3.23초**, `task1-core-green.log`.
- 빌드 명령: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`.
- 기존 ROS/외부 MuJoCo underlay와 지정 venv만 source한다. 이전 장·기존 13.4 overlay를 새 빌드의 의존성으로 사용하지 않는다.
- 전용 build/install/log 접미사는 이 실행 UUID와 같다. `task1-build.log`에 실제 결과를 보존한다. 신규 센서 패키지는 아직 작성 전이므로 이 단계는 7패키지 빌드다.
- 빌드 결과: **7 packages finished, 6분52초**. 기존 제어기 deprecation 경고 외 빌드 실패 없음.
- 전체 소스 회귀: 기존 세 시험 경로+신규 navigation/test, **389 passed, 202.34초**, `task1-all-source.log`.
- colcon 시험: `--packages-select integrated_robot_navigation integrated_robot_interfaces`, test-result **15 tests / 0 errors / 0 failures / 0 skipped**, `task1-package.log`.
- 새 설치본 감사: 기존 6패키지 감사+신규 모듈이 실제 새 prefix에서 로드되는지 및 Python byte 일치를 검사해 통과했다. `task1-install-audit.json`에 모듈·기존 .so 경로와 소스 SHA256를 보존한다.
- 이 시점에는 엔진을 기동하지 않았다. 실제 crawl/Nav2 성공을 주장하지 않는다.

## 환경·결정

- WSL은 일반 사용자 jinho/uid1000로 실행한다. sandbox WSL 접근 거절에만 도구 실행 허용을 사용했으며 sudo/관리자 권한을 사용하지 않았다.
- 기존 `/etc/wsl.conf`의 알 수 없는 키 경고를 관측했다. 범위 밖 설정을 수정하지 않았다.
- Windows→WSL 중첩 인용 명령에서 증거 경로 변수가 사라진 실행은 permission denied로 중단됐다. 같은 환경을 별도 shell 파일에서 읽으면 올바른 경로임을 확인해 이후 plan-local 실행 파일을 사용한다. 이 실행 오류를 제품 시험 FAIL/PASS로 계산하지 않는다.
- 기존 제어기 빌드의 deprecated API 경고는 원본 로그에 남기고 새 기능 때문에 관련 없는 소스를 변경하지 않는다.
- 커밋 시 `.git/index.lock` 때문에 실패했다. Windows/WSL의 Git 프로세스·열린 핸들이 없고, 0바이트 잠금의 시각이 16분 넘게 변하지 않았음을 확인했다. 삭제하지 않고 `.git/index.lock.stale-85670137-e73c-4c72-bcb2-0c73e755088b`로 보존해 정상 Git 동작을 복구했다. 실패한 커밋 뒤 자동 완료 원장에 같은 BASE/HEAD가 들어간 항목은 미완료로 정정하고 실제 커밋 뒤 재시험한다.
- pytest 원본 실패 로그에는 프레임워크가 출력한 줄 끝 공백이 있다. 원본 증거를 정리해 바꾸지 않고 보존한다. 소스·문서의 whitespace 검사는 raw evidence를 제외한 별도 검사로 적용한다.

## Task 2

- 시작 기준/Task 1 완료 커밋: `01ad4986cf740673dd8452c111b589dde4805a97`.
- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_leg_kinematics.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_support.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_center_of_mass.py -q`, **15 failed**, `task2-red.log`.
- 최초 GREEN: navigation/test 전체 **30 passed**, `task2-green.log`. 전진 기구학은 별도 MuJoCo native 모델의 8자세×4발과 대조했다. 이는 물리 step/ROS/보행 시험이 아닌 오프라인 FK 교차검사다.
- 자체 검토에서 실제 thigh 상한 4rad와 atan2 주값 범위 차이를 발견했다. q=(0,3.8,0.4)의 유효 자세가 IK에서 거절되는 것을 `task2-angle-wrap-red.log`로 재현했다.
- 최소 수정: 원래 관절 한계 안의 2π 동등 해를 열거하고 직전 자세에 가까운 해를 선택한다. 작업 공간·관절 한계를 clipping해 통과시키지 않는다.
- 수정 GREEN: 전체 navigation/test **31 passed, 3.96초**, `task2-angle-wrap-green.log`.
- 수정 전 패키지 결과 `task2-package.log`와 소스 실행 `task2-all-source.log`는 최종 수정본 증거로 재사용하지 않는다. 수정 후 고정 소스로 `task2-fixed-*`에 재빌드·시험·감사를 수행한다.
- 수정 후 전체 소스 회귀: **405 passed, 202.55초**, `task2-fixed-all-source.log`.
- 수정 후 패키지 시험: **31 tests / 0 errors / 0 failures / 0 skipped**, `task2-fixed-package.log`. 새 설치본 byte 감사도 통과했으며 `task2-fixed-install-audit.json`에 해시를 보존한다.

## Task 3

- 시작 기준: `ba05b4896922e66f2c5abff06e133e5b26cdb7e8`. profile/footprint 최초 RED **9 failed**, `task3-red.log`.
- 독립 오프라인 검사 `task3-native-geometry-probe.json`: 원래 URDF와 MJCF 각각에서 base_link/네 thigh_link 침투 약0.020m. 렌더링·물리 step·ROS 실행은 하지 않았다.
- 교정 판단: 기존 기본값을 유지하는 Xacro 선택 인수 `hip_mount_y=0.13`을 추가한다. navigation 전용 발 y는±0.18m이며 이전 기본 발 y=±0.15m다. 새 MJCF도 같은 hip origin에서 생성한다. 비인접 충돌 쌍을 제외하거나 collision 크기를 줄이지 않는다.
- 선택 인수 시험: `task3-mount-red.log`에서 실제 미반영 실패→`task3-mount-green.log`의 기본 모델 보존/선택 모델 및 기구학 **8 passed**.
- profile은 오프라인 상태로만 생성한다. G1 검증 기록은 엔진/모델/물리/config hash, 필수 검사와 관측·액션·소스·설치·종료 artifact 해시가 모두 필요하다. 별도 ready 플래그만으로 통과하지 않는다.
- footprint는 허용 gait/arm 오차/roll·pitch 구간 전체의 삼각함수 극값과 보수적 행렬 구간을 사용한다. 몇 자세만 샘플링한 크기가 아니다. 원래 URDF collision과 더 큰 MJCF capsule 경계를 함께 포함한다.
- `task3-green.log`: 42 passed/1 failed. cos(π/2)의 부동소수 잔여가 경계0을 제외하는 문제를 확인해 trig 구간에 반올림 여유와 바깥 방향 반올림을 추가했다.
- `task3-roundoff-green.log`: **43 passed, 14.37초**. 준비 CLI 부재 RED는 `task3-cli-red.log`에 보존한다. 새 출력 생성·기존 출력 덮어쓰기 거절을 실제 명령으로 시험한다.
- 최초 구간 경계의 앞쪽 0.720643m는 접근 후보 상한0.65m와 맞지 않아 `task3-interval-refinement-red.log`로 과대 추정을 재현했다. 연속 구간을 최대0.10rad로 나눈 전체 합집합을 배치 계산하고, 실제 native 형상24자세의 독립 투영과5cm 여유 포함을 대조했다. `task3-interval-refinement-green.log` **5 passed**. 몇 점만 샘플링해 경계를 줄인 것이 아니다.
- 안전 설정 약화(여유·age·기울기·속도)를 허용하던 준비 API는 `task3-safety-limits-red.log`의 **4 failed**로 재현했다. 설정 상·하한 검사를 추가한 뒤 `task3-refined-green.log` **49 passed, 18.16초**.
- 수정 후 전체 소스 회귀: `task3-refined-all-source.log` **423 passed, 198.97초**. 패키지 시험: `task3-refined-package.log` **49 tests / 0 errors / 0 failures / 0 skipped**.
- `task3-refined-install-audit.json`에서 실제 설치 모듈·기존6패키지·신규 config/share bytes 일치를 확인했다. 준비 CLI는 설치본에서 실행했다.
- 새 `task3-refined-offline-profile`은 앞쪽0.579451m/뒤쪽-0.572826m/좌우±0.427560m, inflation_radius0.770118m다. 원래의 더 큰 `offline-profile`도 보존한다. 두 출력 모두 **offline**, G1 증거 없음, 이동 허용 불가다.
- 명목 수납 자세에서 URDF와 MJCF 각각401개 비인접 형상 쌍을 검사했다. 허용 gait 구간의 모든 자세가 자기 충돌 없이 동작한다는 실제 보행 보증은 아니며, G1/G2 실측이 남아 있다.

## Task 4 — navigation 센서·장면·선택 launch

- 시작 기준: `e1331bf5ff363037b7c371a7837b2a3c0049d8fa`. 소유한 중단 프로세스가 없음을 확인하고 재개했다. 기존 13.4 교육 문서40723바이트는 수정·stage하지 않았다.
- RED: `task4-core-red.log`에서 snapshot/normalization 헤더 부재, `task4-contact-wire-red.log`에서 예상 밖 접촉 필드 부재를 재현했다. 별도 미빌드 prefix의 의존성 오류는 feature RED로 세지 않는다.
- 구현: 독립 모델 clone·전체 `mj_copyData` 2슬롯·단일 consumer lease·최신 대기 프레임 덮어쓰기·stop 발행 경계·worker join. 카메라/EGL worker 또는 물리 live 데이터에 쓰지 않는다. reset/clock rollback은 재시작 전까지 차단한다.
- 버전 진단: Python 오프라인 MuJoCo는3.3.7, 실제 ROS C++ vendor는 **3.12.0/header3012000**이었다. `mj_ray` 추가 normal 인수에서 컴파일 실패한 원본은 `task4-core-first-build.log`에 보존한다. underlay/driver는 바꾸지 않았고 정확한 버전의 공개 API로 컴파일했다. 실제 플러그인 시험에서 header/library 모두3012000을 확인했다.
- 실행기 오류: `task4-core-vendor-test.log`는 colcon 탐색 범위 누락으로 Ch01의 기존 인코딩 진단이 나왔다. 소유한 시험기 PID1266에만 SIGINT를 보내고 `--base-paths Ch13/ros2_ws/src`로 교정했다. 시뮬레이터 종료 성공으로 세지 않는다. ROS 시험 콜백의 명시 타입 누락과 C++ Time 변환 오류도 원본 build log에 보존했다.
- 실제 ROS plugin class 부재 RED는 `task4-plugin-load-red-test.log`, 이후 GREEN은 `task4-plugin-time-test.log`다. fixture의 물리 kernel에서 발 하중 합/중력 IMU/원래 world 벽 ray·source 상태 불변, 실제 ROS header·발행·reset 차단·worker stop을 검사했다.
- Gazebo 관측기는 모든 로봇 collision에 `ContactSensorData`를 요청하고 실제 ECM 관성/세계 pose로 CoM을 계산한다. 빈 접촉 tick도 발행한다. fixed joint 결합 후의 실제 SDF collision 이름으로 매핑한다. 센서 core 부재 RED→ECM GREEN은 `task4-gz-observer-*`에 있다. 이는 Gazebo 전체 로봇 실행 정확도 인수는 아니다.
- Gazebo 힘은 세계 좌표의 알려진 평지 지지 하중만 정규화한다. pair 미러링의 collision 순서와 원래 힘 방향을 동일시하지 않으며, 발/ground 명시 매핑·힘 쌍 검증·중복 거절을 사용한다. 경사면/일반 접촉 힘 추정을 주장하지 않는다. native G1 정적 체중 검사는 여전히 필요하다.
- 장면 RED→GREEN: `task4-scene-red.log`, `task4-contact-map-red.log`, `task4-scenes-contacts-green.log`. 실제 MuJoCo parser와 Gazebo SDF 변환으로 검사했다. 평지·pedestal/컵·벽/우회 장애물과 같은 점유 지도를 생성하며 root 강제 이동/외력 plugin을 추가하지 않는다. RGB-D는320×240/15Hz 그대로다.
- exact scene launch·변조 hash RED→GREEN: `task4-launch-red.log` / `task4-scene-launch-first.log` **16 passed**. 실제 생성 URDF/SDF를 선택하며 navigation=false의 기존 경로를 유지한다. Gazebo controller 파일은 기존 긴 경로 문제 때문에 내용 hash 기반의 짧은 `/tmp` 복사본을 사용하고 bundle과 bytes 일치를 검사한다.
- 결합 시험: `task4-gz-join-red.log`의 신규4실패→`task4-gz-join-green.log` **11 passed**. 같은 native 촬영의 접촉/발 위치를 결합하고, 중복 수신으로 원래 wall 나이를 갱신하지 않는다. ROS/wall 각각200ms 및 clock reset 영구 차단을 확인했다.
- 최종 build: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --packages-select integrated_robot_description integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`; `task4-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential`, 이후 `colcon test-result --test-result-base <build13_5_UUID> --verbose`. **85 tests / 0 errors / 0 failures / 0 skipped**, `task4-fixed-package.log`. 구성은 Python70 + C++ 실제10 + CTest wrapper5이며85개 실제 물리 시험이라는 뜻이 아니다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`, **444 passed /257.47초**, `task4-all-source.log`.
- 설치 감사: `task4-fixed-install-audit.json`. 기존6패키지 + navigation + navigation_sensors의 실제 경로/bytes/빌드 소스 manifest를 확인했다. `.so` SHA와 실제 pluginlib probe의 header/runtime 버전, `gz plugin --info --plugin <실제 설치 .so>`의4개 System 인터페이스 등록을 기록했다.
- **미검증:** 전체 ROS 엔진 G1/G2, 실제 Gazebo 접촉·scan 정확도/자기 충돌 활성화, crawl 이동, Nav2, 정상 전체 엔진 종료는 아직 실행하지 않았다. 위 kernel/ROS/ECM/등록 시험을 종단 인수 통과로 세지 않는다.

## Task 5 — 평면 투영·이동 게이트

- 시작 기준: Task4 완료 커밋 `5d3c137a08776516642b9c4e1de27df4d90e47b2`. 커밋 후 CTest5 target/실제10 gtest 및 navigation70 시험 재확인 기록은 `task4-commit-gate.log`다.
- RED 명령: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_projection.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_motion_guard.py -q`, 누락 기능 **13 failed**, `task5-core-red.log`.
- 첫 구현의 ModelContract 필드명 오류 `.foot_links`는 `task5-core-first.log`의3실패로 확인하고 기존 계약 `.feet`만 사용하도록 수정했다. `task5-core-green.log` **13 passed**.
- 투영은 원본6D pose/twist/촬영·수신 시각을 바꾸지 않는다. 별도 `nav_base` z/roll/pitch0과 그 프레임의 실제 planar twist를 계산한다. `/odom`은 구독만 하고 `/navigation/odom` 및 `odom→nav_base`만 발행한다.
- 실제 DDS wrapper 부재는 `task5-ros-red.log`, offline profile 실제 서비스 거절을 포함한 부재는 `task5-ros-admission-red.log`에서 확인했다. 새 구현은 짧은 수신 실행기와 독립 monotonic watchdog으로 원본 raw 및 각 관측의 나이를 검사한다. 미래 센서는 clock이 따라올 때까지 최초 receipt를 보존해 대기시킨다.
- 헤더 없는 Twist의 RESET 이전 패킷은 동일 host DDS SYSTEM source timestamp cutoff로 거절한다. 엔진 epoch와 명령 generation은 별도이며, RESET은 관측·명령 cache를 비우고 HOLD로 돌아갈 뿐 CRAWL을 자동 허용하지 않는다.
- `task5-ros-first.log` **6 passed**: 실제 DDS·ROS clock pause에서 smoother 계속 발행/raw 중단, 중복 publisher, carry 이탈, scan 만료, 이전 generation, 실제 offline profile 거절. **양성 통신 시험은 외부 native-evidence admission만 stub**한다. controller·물리 보행이나 native G1 통과를 주장하지 않는다. 별도 unstubbed 서비스 시험은 실제 profile validator를 호출해 거절을 확인한다.
- 추가 RED3는 `task5-boundaries-red.log`: 실제 DDS용 투영 Node 미노출, dict 명령의 KeyError, 최종0 발행 후에도 ready=true 상태가 남는 문제. Node 경계를 노출하고 형식을 검사하며 종료 시 STOP/not-ready를 설정해 `task5-boundaries-green.log` **22 passed**로 확인했다. STOPPED는 guard가 증명하지 않는다.
- 실제 소유자 교체 RED: `task5-owner-replacement-red.log`. raw publisher를 파괴·재생성해 수가1로 돌아오면 출력이 계속(.006,.01)이었다. CRAWL 동안10개 입력/명령 stream의 실제 DDS endpoint GID도 고정해 교체 시 fault·0·명시적 재무장을 요구하도록 교정했다. `task5-owner-identity-green.log` **23 passed /26.03초**.
- 최종 build: 같은 전용 prefix에서 `colcon build --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation`; `task5-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation --executor sequential`, `test-result --test-result-base <build13_5_UUID> --verbose`. `task5-fixed-package.log`: **108 tests/0 errors/0 failures/0 skipped**. Python93 및 이전 고정 C++10+CTest wrapper5 집계이며108개 실제 엔진 인수가 아니다.
- `task5-fixed-install-audit.json`의8패키지 소스/설치 bytes·센서 build manifest/library hash·실제 등록 감사 통과. fixed-topic DDS 시험 프로세스가 서로 다른 producer로 보이지 않도록 package 시험과 전체 source 시험을 같은 domain159에서 **순차** 실행했다.
- 최종 전체 source 명령은 Task4와 같은4개 pytest 경로다. `task5-fixed-all-source.log`: **467 passed /260.61초**.
- **미검증:** 실측 접촉 기반 crawl 및 G1/G2, 실제 Nav2 접근·취소, 전체 엔진 정상 종료와 최종13.3/13.4 실제 엔진 회귀는 후속 작업이다. 이 단계는 native 배포 완료가 아니다.

## Task 6 — 관측 기반 crawl kernel·lifecycle 다리 소유자

- 시작 기준 `25ba8531f16bb020e5d664df79710b38638c62b4`. Task5 commit gate93 통과는 `task5-commit-gate.log`에 보존했다.
- `test_gait.py`/실제 DDS lifecycle 시험을 먼저 작성했다. 부재·초기 경계 실패는 `task6-gait-red.log`, `task6-gait-boundaries-red.log`, `task6-lifecycle-red.log`다. 첫 kernel11, 공유 수신기/기존 DDS22, lifecycle6 통과는 각각 `task6-gait-first.log`, `task6-shared-receiver-first.log`, `task6-lifecycle-first.log`에 기록했다.
- 확대 시험 `task6-gait-envelope-red.log`: **4 failed/15 passed**. 0명령인데 다음 swing 진행, 현재 지지 밖에서 몸체 목표 발행, 최대 전·후진 중 CoM 여유 부족을 재현했다. 0명령은 현재 발 착지·정지 대기로 바꾸고 현재 지지 검사를 선행했다. `task6-pause-support-green.log` 관련6 통과.
- `task6-com-unit-probe.json`은 수정 전 코드 SHA가 포함된 **ideal-unit-only** 진단이다. 전진 첫 swing 여유0.01530→0.009970m, 후진 RR에서0.02204→0.009922m로 감소했다. 몸통 이동=전체 CoM 이동이라는 근사가 고정 지지 발의 관절·질량 변화를 누락했다. 전체 IK/URDF 질량으로 후보 CoM을 계산하고 제한 구간 내 유계 탐색을 사용했다. 측정 여유0.01m를 완화하지 않았다. `task6-kinematic-com-first.log`: **19 passed/20.19초**.
- 시계 정지/양쪽 시계 역행, 명시적 STOP 후 비영 명령 재개 금지와 inactive 진단 보존도 추가했다. `task6-final-boundaries-red.log`: **1 failed/26 passed**. deactivate가 직전 `clock paused`를 지우는 결함을 실제 DDS에서 확인하고 inactive 상태에도 fault를 보존하도록 수정했다.
- 최초 촬영/수신 나이·미래 inbox를 복제하지 않기 위해 Task5 수신기를 `observations.py`로 추출했다. 기존 motion_guard 실제 DDS도 같은 설치본/전체 source 회귀 대상이다.
- `task6-fixed-build.log` 성공. `task6-fixed-package.log`: **141 tests/0 errors/0 failures/0 skipped** (navigation126+기존 C++10/CTest wrapper5). `task6-fixed-install-audit.json`: 8패키지 설치 bytes·센서 plugin 출처/실제 등록 감사 통과. 전체 source 회귀 결과는 실행 종료 후 별도 기록한다.
- ideal-feedback fixture는 목표에 정확히 반응하는 수학/상태 전이 시험이며 native 물리 성공 증거가 아니다. 별도 무응답 시험은 계획 CoM만으로 발을 들지 못하게 한다. **G1/G2·실제 보행/전체 종료는 아직 미검증**이다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`. `task6-fixed-all-source.log`: **500 passed/337.63초**. 검증 뒤 runtime 변경 없이 문서만 보완하고 Task6를 커밋한다.

## Task 7 — 실제 ROS 수납 액션·시동 순서·배타 launch

- 시작 기준 `b6b976c2481d729c3d2170c61ef56da2a0782f31`. Task6 지정 commit gate **30 passed/32.26초**, `task6-commit-gate.log`.
- 실제 ROS FJT peer 경계 RED: `task7-carry-red.log` **1 failed/6 errors** (기능 부재). `task7-startup-launch-red.log` **4 failed**, 누락 시동/launch와 validation_mode에서도 CRAWL을 허용하던 문제. 서버·클라이언트·terminal·cancel ACK는 실제 ROS 전송이지만 peer는 물리 엔진/실제 JTC가 아니다.
- carry는 기존13.4 `ArmActionOwner`/독립 `ArmActionTransport`를 import한다. 서비스 success=예약이며 실제 result+실측 정착1초 전에는 ready가 아니다. 미확정 terminal 중 destroy 거절·receiver 보존, 이전 세대·팔 고착·외부 active goal·중복 그리퍼 명령자를 검사한다. 빈 그리퍼0.015m 유지가 물리 파지 증거라는 주장은 하지 않는다.
- `task7-carry-first.log` **5 failed/2 passed**. 후속 계측에서 action status endpoint가 실제2개임을 확인했다(`task7-core-second.log`). 시험의 native ActionServer waitable에 명시적 destroy를 추가했다. count 제한을2로 늘리거나 중복 발행자를 무시하지 않았다.
- `task7-explicit-server-lifetime.log` **3 failed/5 passed**: 중복 endpoint 오류는 사라졌지만 실제 시험 송신 공백 **303.573768ms**가200ms 안전 제한을 넘었다. production과 다른 하나의 MultiThreaded pool에 긴 peer와 짧은 parent를 묶었던 시험을 분리했다. 실제 배포와 같은 SingleThreaded parent + 별도 blocking peer 실행기에서 `task7-production-executor-comparison.log` **13 passed/33.41초**. 제품 age·취소 제한은 완화하지 않았다. 이전 실패는 모두 보존한다.
- launch 검사의 Jazzy public executable/location 표현을 바로잡은 뒤 실제 `scene_directory`/`scene_dir` 불일치를 `task7-launch-binding-red.log`의 Gazebo1실패로 재현·교정했다. 엔진 include는 하나이며 legacy locomotion/manipulation/tracking requester를 기동하지 않는다.
- 초기 설치 검증 `task7-fixed-package.log` **155 tests/0 error/0 failure/0 skip**,8패키지 감사 통과. 하지만 native 관절 broadcaster가 뜨기 전 activate할 수 있는 빈틈을 추가 검토에서 발견했다. `task7-premature-activation-red.log` **2 failed** → inactive 비명령 관측 준비 phase를 대기하도록 수정 → `task7-bootstrap-first.log` **13 passed/26.88초**.
- 수정 뒤 `task7-bootstrap-fixed-package.log` **156 tests/0 error/0 failure/0 skip**,8패키지 감사 통과. 이후 직선 그리퍼에 rad/rad-s 허용 오차를 쓰는 단위 결함을 `task7-gripper-units-red.log` **2 failed**로 재현했다. 팔0.03rad/0.02rad-s는 유지하고, 그리퍼는 목표0.015m에 대해 **0.002m/0.005m-s**를 별도 적용했다. 양성 peer도 명시적으로0.015m 실제 메시지 피드백을 공급하도록 교정했다. 기존 footprint는 그리퍼 전체 허용 구간을 포함하므로 축소하지 않는다.
- 위155/156건은 후속 runtime 변경 이전의 결과다. 마지막 소스의 package·설치 감사 결과는 실행 종료 후 별도 기록한다. 변경 없는13.3/13.4 전체 matrix는 이 디버깅 단계마다 재실행하지 않고 Task13 최종 동결 회귀에서 수행한다.
- **미검증:** G1 실제 controller·native 센서·carry·발 lift, G2 실제 보행, 실제 Nav2와 전체 정상 엔진 종료. unit/peer 통신 성공으로 이 항목을 PASS로 세지 않는다.
- 마지막 소스 검증 `task7-si-fixed-build.log` 성공. `task7-si-fixed-package.log`: **158 tests/0 errors/0 failures/0 skipped** (navigation143+기존 C++10/CTest wrapper5). `task7-si-fixed-install-audit.json`: **8패키지 설치 bytes·센서 library/실제 등록 감사 통과**. 이후 runtime 수정 없이 Task7를 커밋한다. 실제 엔진 결과는 아직 없다.

## Task 8 — 실제 엔진 G1/G2 인수 (진행 중)

### 새 서보 설정의 실제 MuJoCo와 SHIFT 연속성

- 시동 초기 상태 수정 `task8-empty-bootstrap-build.log`27.0초 빌드 성공, `task8-empty-bootstrap-package.log`**257 tests/0 errors/0 failures/0 skipped**(Python238+native13+wrapper6), 두 패키지 시험3분48초·8패키지 설치 감사 통과를 확인했다. 소스·설치를 다시 고정하고 새 UUID Gazebo 진단을 시작한다. 이전 강제 종료를 정상으로 바꾸지 않고, 기존 MuJoCo PASS도 수정 전 역사적 결과로 구분한다. 최신 소스의 양 엔진 인수·최종 연속 성공/전체 회귀는 여전히 남아 있다.

- 최초 Gazebo `87854340-d0e6-4e20-a246-a0681ecec04c`(run_id `7fdfaf56-6b8b-4e2e-9571-099c5ca24440`)는 시동 중 `crawl:startup scene model mismatch`로 FAIL이었다. 원본에는 구성 전 `INACTIVE/BOOTSTRAP_WAIT_FEEDBACK/빈 hash/not-ready`가 실제 발행됐고, 구성 완료 서비스 ACK보다 기존 status 수신이 늦게 반영되는 순서 경쟁이었다. 이후 정상 hash는 일치하지만 이전 fault를 자동 복구하지 않는다. STOPPED 확인 실패 후 Gazebo pause/stop ACK는 받았으나 wrapper1149/start7379,parent1144가 SIGTERM(-15)까지 escalated됐다. **forced_cleanup=true, 정상 runtime/engine=false**, 잔여 없음·부모 회수만 확인했다. 이를 정상 종료로 세지 않는다.
- `task8-empty-bootstrap-red.log`:1실패/실제 잘못된 hash 거절1통과8.83초. 최소 수정은 WAIT_FEEDBACK 중 명시적 구성 전 빈 상태만 준비 부재로 기다리는 것이다. 잘못된 nonempty hash·ready/stopped를 주장한 빈 상태는 허용하지 않고200ms·45초·claim 검사는 유지한다. `task8-empty-bootstrap-first.log`:관련10건 통과19.72초. 전체 빌드·회귀·설치 감사 후 새 Gazebo 진단으로 진행하며, 종료 정지의 별도 원인은 아직 확정하지 않았다.

- **최초 MuJoCo 전체 G1 PASS:** `9bd81e84-4a85-4d91-8082-d54a318fd3d1`, run_id `cb913220-9080-4a5a-bc8d-2e1b22272e1a`.23개 required check 모두 true/errors 빈 배열, 실제 실행기 exit0이다. 정적 ROS10.038초/wall10.0366초, 교정 ROS9.84초/wall9.81075초였다. 팔 최대 오차0.0191749rad/속도0.00736246rad/s, 그리퍼0.00013943m/0.00136038m/s, 실제 FL lift41개 고유 촬영을 확인했다. 체중 상대 오차6.58×10⁻⁶·최대 거리 오차1.26×10⁻⁶m, 전체 gyro/body 차이최대0.015624rad/s도 새 판정 경계 이내였다.
- Native1216/start9523,parent1210, TF관측기와 runtime/engine 정상 종료0·회수·강제 없음·잔여 없음을 확인했다. 기존 실패는 원본 FAIL로 보존한다. 이는 **첫 G1 PASS 한 회**이며 G2 보행·Gazebo·Nav2·최종 동결 회귀/3회 연속이나13.5 완료를 의미하지 않는다. 다음은 순차 Gazebo 진단이다. Gazebo의 실제 제어값/라이브러리 출처 판정이 아직 미구현이므로 해당 required check는 false를 유지하고, 실제 물리 시동·수납·교정을 먼저 조사한다.

- G1 sensor 의미12건 RED10.14초→GREEN8.96초 뒤, 수납 raw 판정 부재8건 RED8.71초와 구간 경계3건 RED8.31초를 추가 재현했다. `task8-g1-semantics-related.log`:기존 인수·제어값·관측·TF 회귀와 함께 **61 passed/17.42초**. 실제 정적 시간은 ROS/wall 각각10초를 유지하고 원본 coverage와 구분한다. 알 수 없는 stage나 운용 중 실패를 거르지 않는다.
- controller/N/S runtime은232건 검증 이후 바꾸지 않았다. 새 검증용 script/test 변경만 관련 회귀와 문법 검사·`task8-g1-semantics-install-audit.json`8패키지 byte 감사를 통과했다. 현재 새 실행은 `9bd81e84-4a85-4d91-8082-d54a318fd3d1`이며 이전 FAIL을 재판정/수정하지 않고 완성된 검증기로 처음부터 실행한다. G1 전체 인수는 결과 완료 전 선언하지 않는다.

- 실제 `67ccb0eb-d0b8-4f8f-8ea3-2edc6d6b8f4c`(run_id `b5f9cadb-6c29-4774-834f-cdc18d7486ee`)는 시동·실제 FJT terminal·수납 정착·정적10초·단일 발 교정 후 STAND 복귀와 정상 정리를 마쳤다. runtime fault/error_traceback은 없었다. Native1148/start75222,parent1142, 관측기와 런타임 모두 종료0·부모 회수·강제 없음·잔여 없음이다. 구현된18개 check는 모두 true이며 실제 loaded producer/ctrl/TF·명령 단일 소유권도 확인했다. 다만 접촉 힘·IMU·거리·충돌·실제 발 들기5개 필수 의미 판정이 아직 없어 **원본 전체 결과는 FAIL을 유지한다**. 이 실행을 G1 전체 PASS나3회 연속 성공으로 세지 않는다.
- 누락 판정 RED `task8-g1-sensor-semantics-red.log`:12실패10.14초로 API 부재를 확인했다. 합성 unit fixture는 native 출처 증거가 아니라고 명시했고, 힘 배율/발 이름/IMU 축/자체거리 hit/발 들기 누락·오매핑/비예상 접촉/겹침/중복 촬영/합성 odometry를 거절하도록 정의했다. 종료 구간은 명시적으로 구분하되 운용 중 실패 프레임·원본 로그는 보존하는 계약이다.

- 속도 예산 후보 `task8-foot-speed-bound-horizon.log`:관련53건 통과80.73초. 그 뒤 `task8-foot-speed-build.log`34.0초 빌드, `task8-foot-speed-package.log`**232 tests/0 errors/0 failures/0 skipped**(Python213/199.32초+native13+wrapper6),8패키지 설치 감사 통과를 확인했다. 소스·설치본을 고정하고 새 UUID 장면/프로파일의 실제 MuJoCo로만 원인 가설을 판별한다. 기존 d11/046 실패는 보존하며 G1 인수와 최종 전체 회귀는 아직 미완료다.

- 속도 후보 첫 회귀 `task8-foot-speed-first.log`:48통과/3실패75.88초. 새 속도/프로파일 상한·착지 연속성·실제 물리2건은 통과했지만 최대 전진/후진 네 발 순서 시험이40초 안에 세 발만 관측했고, ideal 교정이 기존5초 관측창을 넘었다. controller fault나 실제 물리 실패와 구분한다. 최대80mm 궤적은 도출한 속도 상한에서 약10초가 필요하므로 단위 순서 관측창만 bounded60초로 명시 정정했다. 교정 단위 시험은 실제 G1과 같은10초를 적용한다. 실제 G1 교정10초·G2/과제 기준·네 발 모두 확인 조건은 유지하며, 새 회귀 `task8-foot-speed-bound-horizon.log`로 확인 중이다.

- 착지 수정 후 실제 `046c4a16-410f-4be7-97dc-70f1feef287e`(run_id `e597de84-814d-43a9-9434-337a87d64088`)도 FAIL이었다. 첫 READY16.408초, 교정26.708초, SWING32.864초, fault33.526초로 **TOUCHDOWN 전** 수납 이탈이다. 팔2 속도0.06134rad/s·그리퍼0.01510m/s였고 실제 ctrl 목표는 유지됐다. 따라서 접촉 이후 연속성만으로 전체 원인을 설명할 수 없으며 이전 수정의 효과를 과장하지 않는다. frame7항목과 정상 runtime/engine/observer 종료0·부모 회수·강제 없음·잔여 없음은 확인했다. 생산자/graph 수집 이전의 실패 check는 원본 그대로다.
- 기존 `.8s` SWING에 별도 발 속도 상한이 없다는 구조를 분리했다. `task8-foot-speed-red.log`:정지 교정·전진·회전3실패12.98초. `task8-foot-speed-profile-red.log`:0.021m/s 설정을 허용해1실패14.02초였다. 현재는 전체3D 궤적의 미분 상계로 실행 시간을 정해 발 목표 속도≤0.02m/s를 보장하는 후보를 구현했다. 새 설정은 config/profile hash에 포함되고 기존 모델/프로파일로 허가를 재사용하지 않는다. PD·힘·수납 기준은 변경하지 않는다. 관련 회귀 및 새 실제 엔진 판별 전 G1 PASS를 선언하지 않는다.

- 착지 수정의 관련36건 통과 후 `task8-measured-landing-build.log`34.1초 빌드 성공, `task8-measured-landing-package.log`**228 tests/0 errors/0 failures/0 skipped**(Python209/198.82초 + native13 + wrapper6), 두 패키지 시험3분41초·8패키지 설치 bytes/센서 출처 감사 통과. runtime을 고정하고 새 장면·프로파일·UUID의 실제 MuJoCo 진단으로 진행한다. 단위/물리 component 통과를 G1 인수로 세지 않는다.

- 후속 새 실행 `d11db78d-df47-4450-82ca-9ef113b990f9`(run_id `a6defb62-dca5-44c5-8b49-b31e2aac817f`)에서 시동 게이트와 실제 FJT typed terminal/수신·수납 정착은 통과했다. 첫 READY18.416초, 교정 SHIFT28.622초→SWING34.834초→TOUCHDOWN35.622초에 수납 이탈로 실패했다. `carry-failure-analysis.json`: 팔 최대 속도0.019385rad/s는 기준 이내였고, 그리퍼 실제 ctrl0.015m 유지 중 속도 약±0.005404m/s(직전0.5초 최대0.006271)가0.005를 넘었다. 수납 이탈을 완화하거나 성공만 골라 세지 않는다.
- `calibration-failure-analysis.json`: 착지 때 FL 하중25N, 몸체 수평 속도약0.045m/s·각속도 반동과 함께 내려가는 다리 ctrl 변화가 지속됐다. 실제 관측은 정상이며 오류 출력이 아니다. Native1149/start75825, observer1158/start75828, parent1143 모두 정상 종료0·회수·강제 없음·잔여 없음이다. 이번 정적486프레임7항목과 전체 frame7항목은 true지만 실제 생산자/graph 수집 전에 실패했으므로 native ctrl/TF check를 소급 PASS로 바꾸지 않는다.
- 착지 계약 RED `task8-landing-continuity-red.log`:3실패 중1개 시험 IK 인자 오류를 보존하고 바로잡았다. `task8-landing-continuity-red-confirmed.log`:**3실패/8.44초**로 실제 접촉을 무시한 timer-only SWING, 접촉 반동 시 과거 floor로 약13.45mm 목표 점프, 측정 compliance를 새 목표로 복사하는 착지 불연속을 각각 재현했다. 최소 수정은 접촉 시 하강 선점, command anchor 연속 유지, 접촉 상실 때 기존2mm/s의 유계 탐색이다. 그리퍼 PD·힘/위치·속도 기준은 변경하지 않으며 물리 및 native 후속 검증 전 해결 선언하지 않는다.

- 시동 순서 RED `task8-startup-claims-red.log`:6실패/2통과18.06초. 비활성 제어기 응답에서도 activate가 나간 실제 DDS4건과 장면 모델 매개변수 누락2건을 재현했다. 최소 게이트 후 `task8-startup-claims-first.log`8통과21.40초. `task8-startup-claims-build.log`35.5초 빌드, `task8-startup-claims-package.log`**225 tests/0 errors/0 failures/0 skipped**(Python206/native13/wrapper6),8패키지 설치 감사 통과. 새 UUID 실제 엔진으로만 후속 검증하며 G1 완료로 세지 않는다.

- 새 실행3ba3fa92는 교정 전에 `startup service rejected: CARRY_REQUESTED`로 실패했다. joint_state_broadcaster만 먼저 활성화되고 팔·다리·그리퍼 spawner가 기동 중인 시점에 prepare가 호출됐다. 서비스 존재/자연 정지 피드백은 실제 controller 활성/command interface 소유권의 증거가 아니다. 원래 Trigger.message가 버려져 정확한 거절 사유는 아직 미확정이다. engine/runtime/observer 종료0, STOP·측정 정지·비활성·결과 drain·worker join·부모 회수·강제 없음·잔여 없음은 확인했지만 G1 PASS는 아니다. 이전 승인 검토 사용량 제한은 재개 후 해소되어 일반 WSL uid1000으로 설치된 ListControllers/ControllerState 정의를 읽었다. 다음은 활성/소유권 지연을 실제 DDS로 재현하는 RED이며 기존 실패 원본을 보존한다.

- `task8-damped-profile-build.log`: 두 패키지 빌드34.6초 성공. `task8-damped-profile-package.log`: **222 tests/0 errors/0 failures/0 skipped**(Python203 + 실제 native13 + wrapper6). `task8-damped-profile-install-audit.json`:8패키지 설치 bytes·sensor 출처 일치. 그 뒤 runtime을 바꾸지 않고 새 장면/프로파일 `native-g1-mujoco-3ba3fa92-2ab2-4f6a-bafb-2f22682dbba7`으로 실제 G1 진단을1회 실행 중이다. 이전 prepared535a나 그 source/physics hash를 새 허가로 재사용하지 않는다.

- `task8-unload-owned-first.log`:32통과/물리1실패42.08초. 교정 자체는7.62초에 완료됐지만 팔 최대 오차0.0312446rad·속도0.050753rad/s, 그리퍼 속도0.012067m/s가 남았다. `calibration-trace-e99cea13-8a78-4e2e-bf7b-ce1080348338/trace.json`으로 SHIFT의 팔 속도0.00579와 달리 SWING 말기/TOUCHDOWN에서 반동 응답이 크다는 것을 확인했다. 단위 시험 완료만으로 수납 안정 성공이라 하지 않는다.
- `carry-gain-probe-6ee635d8-509c-4d4a-a052-a89fb70a0156/comparison.json`: 팔 강성1/1.5/2 후보 모두 교정 완료, 그러나 속도 기준 실패로 채택하지 않았다. 강성1.5를 고정한 `carry-damping-probe-89795b9b-dbd1-408b-91e8-4694117f7e90/comparison.json`의 감쇠2/3/5 비교에서 **5만** 모든 기존 기준을 충족했다. 팔 오차0.019399rad·속도0.016485rad/s, 그리퍼 오차0.000304m·속도0.004840m/s였다. force/ctrl/관절·질량은 그대로다.
- 이 후보를 navigation 전용 생성 MJCF 설정에만 적용한 `task8-damped-carry-first.log`: **53 passed/44.05초**(커널31·물리2·profile11·native 제어 의미9). 기존 description/13.4 모델은 바꾸지 않았다. 감쇠 증가는 실제 FJT settle과 ROS C++3.12.0에서 다시 확인해야 한다. `task8-damped-profile` 전체 설치/회귀/감사가 현재 실행 중이며 완료 전 다음 엔진을 시작하지 않는다.
- 원본535a의 `g1-static-analysis.json`은 정적488프레임의 독립 센서 기하 계산이다. 기대 체중149.211081N 대비 실제149.210100~149.210188N, 중력 벡터 오차최대1.54×10⁻⁵m/s²·gyro/body오차1.91×10⁻⁷rad/s·world 벽 ray 거리오차1.48×10⁻⁶m였다. 외부 센서 값을 주입하거나 기존 FAIL/required_checks를 바꾸지 않았다.

- `task8-shift-continuity-first.log`: 28통과/물리1실패35.33초. 기울기 소실은 실제 결함이지만 교정 물리 실패의 전부는 아니었다. `calibration-trace-1c10d81c-d5f1-4a9c-b1fb-cee5d9c9cf6d/trace.json`에서 내부 몸체 이동 peak≈0.17m/s,0.7초 후 반동 중 SWING 시작, 최종 FR/RL 두 발만 약73N씩 지지하는 과정을 확인했다. 센서 기준을 낮추지 않는다.
- `task8-dynamic-shift-red.log` 2실패: 내부 기준 가속도0.59625m/s², 잔여 실측 속도0.004m/s에서도 lift가 발생했다. 내부 quintic 가속도≤0.10m/s² 및 100ms 실측 안정 게이트를 추가했으나 `task8-dynamic-shift-first.log`는27통과/4실패30.57초였다. 부하 전달·진행 시계 구조가 여전히 부족하므로 이것만으로 해결됐다고 쓰지 않는다.
- 원인은 **기하학적 여유와 발 부하 해제의 혼동**으로 더 좁혔다. FL에 약25N이 남은 채 빠른 swing을 시작했다. `task8-measured-unload-red.log`는 ideal peer에서도 실제 하중30N을 확인하지 않고 전이함을 재현했다. SHIFT 안에서2mm/s로 부하를 천천히 해제하고 실제 force<2N·다른 세 발 지지·실측 안정100ms 후 SWING하는 후보로 바꿨다. 안전 대기 시간은 더 이상 몸체 진행에 추가 적분하지 않는다.
- 최초 후보 `task8-measured-unload-first.log`:30통과/2실패44.98초. carry 속도0.005794rad/s·오차0.029026rad·그리퍼 속도0.000359m/s는 원래 기준 이내였으나,5mm 해제 경계에서 여전히 FL13.75N이 남아 안전 중단했다. `calibration-trace-178939ca-584f-465a-a437-050c8eba03a2/trace.json`에 목표 높이·실제 힘/CoM/몸체를 보존했다. 이를 contact 해제로 세지 않는다.
- 같은 compliance 관측에 따라 해제 상한을 총 swing20mm 안의10mm로 설정하고, 시간 한계는 높이/2mm/s+1초로 유도했다. 실제 force<2N 조건과 부모 교정10초·팔·접촉·지지·센서 한계는 유지한다. 이전 scene/profile을 재사용하지 않는다. `task8-unload-stop-red.log`의1실패로 해제 중 STOP에서 발 소유 식별이 빠진 결함도 재현했고, 해제 시작부터 같은 발을 소유해 기존 착지≤1초/STOPPED1초 검사를 적용했다. `task8-unload-owned-first.log`가 현재 관련 회귀다.
- **시기 계약 정정/미완료:** `cycle_s=8`은 이제 발 목표·몸체 진행의 명목 phase-time이다. 실제 하중/안정 게이트 때문에 물리 주기는 더 길 수 있고 **고정8초 보행을 달성했다고 주장하지 않는다**. 이는 Nav2 진행률·기존 deadline의 실제 검증 비용을 늘린다. 순서/최대 명령 시험은 임의450/550tick 대신 bounded40초 내 네 발 모두의 실제 SWING을 요구해 범위를 강화했다. 실제 G1/G2·실습 완료·게시를 아직 선언하지 않는다.

- 새 실행 `535a37d0-bd38-43af-8438-b0bcbb0d8f66`(내부 run_id `da8a2300-9c48-470f-9932-b7491083f90f`): 기립과 실제 FJT 성공/수신·측정 settle·미검증 CRAWL 거절은 확인했다. 첫 READY ROS10.726초, 정적 유지 후 한 발 교정 `SHIFT` ROS20.906초 진입, ROS20.968초에 `measured carry posture lost`로 실패했다. **G1 전체 PASS가 아니다.**
- `carry-failure-analysis.json`: 팔2의 실측 속도0.0319435rad/s가0.02 기준을 넘었다. 실제 native ctrl은1.2, 팔3 ctrl은-2.0으로 목표를 계속 유지했다. 힘 포화가 아니라 몸체 이동 중 팔 응답을 조사해야 한다. 실패 전 stand488프레임의 freshness/자세/지지/CoM/관절/slip7항목은 모두 true였다. posthoc native 제어값·TF 의미도 true지만 실행 중 provenance/graph 수집까지 완료하지 못한 check를 소급 PASS로 바꾸지 않는다.
- **정상 정리 개선 확인:** parent2202/start55375, native2208/start55793·TF관측기2217/start55796. STOP/측정 정지/비활성/실제 결과 drain/native worker join 후 런타임·엔진 각각 종료0, 부모 회수·강제 정리 없음·잔여 없음. 이번 실행의 정상 종료 check는 true다. 반면 전체 frame의 freshness false에는 의도적으로 센서를 끈 종료 구간이 섞여 있으므로 측정 구간 분리도 후속 판별한다. 원본 FAIL은 보존한다.
- 작은 물리 `task8-carry-calibration-physics-red.log`에서도 교정 완료 실패를 재현했다. 통제 비교 `carry-gain-probe-49f87f69-f4a5-4d7f-8719-c06f7870054b/comparison.json`의 팔 gain1/3/5는 모두 `current measured support lost`였다. 팔 오차는 줄었지만 속도와 그리퍼 응답/지지 실패가 남았으므로 **어느 gain도 채택하지 않았다**. 원본 팔/그리퍼/힘 한계는 그대로다.
- 구조 판별 `task8-shift-continuity-red.log`: 기립 pitch0.04rad에서 경과0초·zero command의 교정과 첫 이동 두 경로 모두, 기존 회전이 yaw-only 항등행렬로 바뀌는 결함을 재현했다. 수정은 world-z yaw 증분만 기존 회전에 곱해 기존 기울기를 연속 보존하는 것이다. 자세 기준·8초 cycle·힘/속도/센서 기준을 완화하지 않는다. 전체 커널/실제 물리 회귀 `task8-shift-continuity-first.log` 실행 중이다.

### 수납 시험 경계 후속 진단

- 고정 소스 `task8-engine-clock-build.log` 두 패키지 빌드37.0초 성공. `task8-engine-clock-package.log`: **215 tests/0 errors/0 failures/0 skipped**(Python196 + native gtest13 + wrapper6). `task8-engine-clock-install-audit.json`: **8패키지 설치 bytes·sensor plugin 출처 일치**. 이어 `native-g1-mujoco-535a37d0-bd38-43af-8438-b0bcbb0d8f66` 새 장면/프로파일로 actual G1 진단을1회 시작했다. 이 시점 G1 PASS는 아니다.
- **시계 가설 판별 증거:** `carry-wire-trace-a171ee1c-c0e5-45c1-bedd-cc29b4f73acf.json` 연속 span의 `Δsource_system_ns − Δend_ns` 최대가 **2,936.113704ms**다. 즉 이번에는 실제 SYSTEM 대비 monotonic의 약2.936초 step을 직접 기록했다. 같은 시험은 의도한 `carry measured settle timeout`으로 끝나고 자식 exit0이었다. OS/NTP/호스트 중 누가 보정했는지는 이 자료만으로 확정하지 않으며 시스템 설정은 바꾸지 않았다. 테스트 ROS를 엔진과 같은 독립 `/clock`으로 구성한 이유를 뒷받침하지만, 이전 native body 공백을 같은 원인으로 단정하지 않는다.

- `task8-peer-owned-package.log`: 전체215건 중 고착 팔1실패로 다음 엔진/설치 감사를 보류했다. **독립 발행만으로 완전 해결되지 않았다.** 원본 `carry-wire-trace-9de378fb-220d-4466-9d8f-dcf35c5f47e2.json` 최초 fault에는 ROS age2960.115632ms/수신 후 wall age10.208276ms가 함께 있고, 별도 발행기 span은20ms 간격으로 계속됐다. graph 조회도 약0.25ms였다. 단순200ms publisher 공백과 다른 시계 경계이며 SYSTEM 시계 보정 가설을 세웠지만 이 원본만으로 운영체제 원인을 확정하지 않는다.
- 실제 엔진과 조건을 맞춰 시험용 `/clock`을 monotonic 경과로 생성하고 manager/peer에 `use_sim_time=true`를 적용했다. 기존 촬영 header 재기록, 호스트 시계 설정, 오래된 목표 재사용은 하지 않는다. 새 캡처/clock/SYSTEM/첫 MONOTONIC 수신을 별도로 남긴다. 시험 원본·clock을 함께 끊을 때도 **wall_age**가 취소를 일으켜야 하며, typed result 전 lease 유지와 sticky fault를 그대로 요구한다. 이 변경은 통신 fixture에만 적용되며 실제 MuJoCo body342ms 문제의 해결 증거로 쓰지 않는다.

- 후속 `task8-feedback-lifetime-fixed.log`: **14 passed/105.46초**. 원래 수납·취소·세대·11초 고착 팔 timeout과 새 독립 발행/실제 입력 손실을 모두 검사했고, 자식의 정상 종료0·join을 확인했다. `carry-wire-trace-*.json`에 각 시험의 실제 수신 상태, 최초 fault 경계, 발행 시각/스레드CPU, 자식 시작 단계/PID/종료를 보존했다. 시작 단계 계측의 대부분은4.19~4.79초로 기존5초 경계가 빠듯했음을 보이나 이전 두 지연의 정확한 원인을 소급 단정하지 않는다.
- `task8-native-control-verdict-red.log` 9건 API 부재 실패 → `task8-native-control-verdict-first.log` **25 passed/9.25초**(제어값 의미9 + 기존 인수 경계16). 새로운 판정은30개 고유 촬영/단조 sequence,20개 관절의 실제 scalar 주소/단위/position 제어/gain/한계/힘/유한값을 exact MJCF·URDF와 대조한다. fixture JSON의 통과만으로 native 출처를 증명하지 않으며 runner는 별도 loaded producer 감사와 결합한다. 나머지 G1 누락 항목은 여전히 false다.

- `task8-generation-timing-characterize.log`: 관련3건 통과25.46초. wall 대기157ms/발행0.28ms/스레드 CPU2.36ms로 관측되어 호스트 스케줄링과 클라이언트 본문에 묶인 발행 구조를 구분해야 한다. `task8-load-observed-package.log`는 전체204건 중 고착 팔 시험1건이 `guard:ros_age`로 실패했다. 통과할 때까지 동일 실행을 반복해 성공만 취하지 않는다.
- `task8-feedback-isolation-red.log`: 클라이언트가250ms 대기하면 pump 기반 원본도 멈춰 `guard:ros_age`가 발생하는 구조를 최소 재현했다. 실제 시스템처럼 **시험용** 상태 발행기를 별도 프로세스50Hz로 분리했다. 실제 엔진 센서 또는 물리 G1 증거로 부르지 않는다. 의도적인 실제 입력 손실에서는200ms 차단·sticky fault·typed terminal 전 lease 유지도 검사한다.
- 첫 분리 실행 `task8-feedback-isolation-first.log`는 **12통과/2 setup error,105.30초**였다. 입력 안전 검사는 바꾸지 않았지만 시험 자식이5초 내 시작되지 않은2건이 있었고, 부모가 이미 생성한 action receiver가 생성 실패 경로에 남았다. 프로세스 시작 실패와 제어기 실패를 혼동하지 않는다. 테스트 부모PID1099/PPID752/PGID752·실제 명령을 확인한 뒤 일반 사용자 SIGINT로 정리했다. 그 뒤 abort(-6)와 KeyboardInterrupt를 원본 로그에 보존했으며 이를 정상 종료 성공으로 세지 않는다. PID1099/1120 잔여 없음도 확인했다.
- 후속 수정은 시험 자식을 **부모 ROS 자원보다 먼저** 취득하고, interpreter import/rclpy init/Node/publisher 준비 단계를 계측한다. 자식 시작은15초의 별도 wall deadline이고 실행 중200ms 센서 기준과 무관하다. 정확한 ready 조건 후에만 시험을 시작하며 취소 결과 전 부모 자원을 파괴하지 않는다. `task8-feedback-lifetime-fixed.log`로 전체 수납 경계를 재검증 중이다. 새 native 엔진은 아직 시작하지 않았다.

- 시작 커밋 `b26bcfb03e72753140be41e5fa089621f417bd55`. G1이 통과하기 전 G2 실행과 Nav2 성공 기능 추가는 차단한다. 현재 **G1/G2 통과 기록은 없다**.
- 판정기는 명령 적분 odometry·필수 관측 누락·강제 정리·미회수 부모·cancel ACK/status만으로 PASS하지 않는다. `task8-verdict-red.log` 부재14실패 → `task8-verdict-first.log` 14통과. 수학 fixture는 실제 물리 증거가 아니다.
- G1용 한 발 제자리 교정은 validation_mode·실측 STAND·완료된 carry를 요구하며 기존 단일 다리 소유자만 명령한다. CRAWL 권한을 부여하거나 비영 이동 속도를 허용하지 않는다. kernel/실제 ROS 보고 경계 RED → `task8-contact-report-first.log` **28 passed/38.27초**. 실제 FJT 결과 보고는 UUID·typed result·future 완료·잔여 소유권을 구별한다.
- `prepare_navigation_model_13_5.py --scene-engine mujoco|gazebo`가 exact scene URDF에 결합된 offline profile을 만든다. `task8-prepare-scene-red.log` → `task8-prepare-scene-first.log` **2 passed/21.34초**. offline 상태는 native 허가가 아니다.
- 첫 MuJoCo 실행: `native-g1-mujoco-584c83b0-af5c-4d62-851f-b75154aa833f`, 내부 run_id `9dcf00ed-9073-4990-9c94-5ffceca95769`, 부모 PID1236/start17927·native PID1242. probe가 Jazzy의 dict 형식 MessageInfo를 객체로 가정하여 실패했다. native frame은0건이고 물리 인수로 세지 않는다. 종료 중 SIGINT **후** native controller 생성에서 context-invalid 예외가 발생했다. 주 원인을 MuJoCo ABI 오류로 단정하지 않는다. 부모 회수·잔여 없음이어도 native -6 종료는 정상 종료 FAIL이다.
- 이 경계의 실패 회귀는 `task8-first-native-regression-red.log`, `task8-child-exit-red.log`에 있다. dict/object metadata를 지원하고 잘못된 metadata도 executor를 파괴하지 않게 하며, 실제 소유 native PID의 부모 로그 종료 코드를 검사했다. `task8-native-boundary-green.log`: **19 passed/8.34초**.
- 두 번째 호출 `native-g1-mujoco-9e34cf5a-8376-41ee-8150-6287714a0fbf`는 **엔진 시작 전** 실패했다. `task8-scene-cache-load-probe.log`로 `/tmp/ch13_5_controllers_1927b0a9a09dae57.yaml` 소실을 확인했다. persistent bundle은 온전하며 OS 소실 원인은 단정하지 않는다. 이를 두 번째 물리 실행 실패로 집계하지 않는다.
- 수정 원리: persistent 파일들의 hash를 먼저 확인하고, 내용 hash로 도출한 정확한 소유 cache만 exclusive-create로 복원한다. 손상 cache·symlink·임의 대상·변조 원본은 거절하고 덮어쓰지 않는다. `task8-cache-lifetime-red.log`에서 소실/임의 대상 실패를 확인했다. 재개 후 첫 회귀는 JSON list/원본 tuple 비교라는 시험 표현 오류1건으로 실패했으며 원본 기록 `task8-cache-lifetime-first.log`를 보존했다. controller binding/실제 복원 bytes로 시험을 교정한 `task8-cache-lifetime-green.log`: **8 passed/30.05초**.
- **남은 인수:** 실제 native 센서 연속성·carry/발 lift·ctrl 실측·frame/힘/CoM/scan 의미 검증·정상 종료, 이후 양 엔진 G2. 누락된 check는 false로 유지하고 profile을 승격하지 않는다.
- 2026-10-23 설치 갱신: `task8-cache-fixed-build.log` 26.5초 성공, `task8-cache-fixed-install-audit.json` 8패키지 일치. 새 실제 실행 `native-g1-mujoco-ac9bc025-63bd-4ae0-a66f-c163edf2c5d6` (run_id `015c3bc8-36e7-44db-9400-716ad60d1be3`)은 TF 수신 metadata의 `publisher_gid` 누락으로 실패했다. 부모 PID1216/native1222/start43945, 수집 frame0. 잔여 없음·강제 정리 없음·부모 회수는 확인했지만 native -6이므로 정상 종료 FAIL이다.
- **가설 교정:** 앞선 dict 양성 fixture가 실제 API에 없는 키를 공급했다. 엔진 없는 실제 DDS characterization `task8-actual-tf-metadata.json`에서 Python callback 필드가 source/received timestamp와 두 sequence뿐임을 확인했다. graph에는 GID가 있으나 그것을 개별 TF 메시지의 출처로 추정하지 않는다.
- **최소 구조 보완:** Ch13 신규 C++ `tf_provenance`가 실제 `rclcpp::MessageInfo`의 GID를 읽는다. TF·모터·상태 명령을 발행하지 않고, 동일 topic/parent/child/GID만 중복 제거한다. 소유자나 부모가 바뀌면 반드시 별도 줄을 기록한다. 새 파일만 독점 생성하며 기존 evidence를 덮어쓰지 않는다. runner는 소스/설치 bytes·실행 파일 hash·소유 PID/start tick·실제 종료 코드를 함께 요구한다. Python의 API 기능 부재 자체를 로봇 fault로 해석하지 않되, C++ 증거가 없으면 TF 소유권 check는 FAIL이다.
- 회귀: `task8-tf-provenance-red.log` C++ header 부재 → `task8-tf-native-test.log` 실제 DDS **1 gtest passed/2.00초** (실제 publisher GID 대조·반복 제거·서로 다른 소유자/부모/static topic 보존). `task8-tf-boundary-red.log` 7실패와 `task8-tf-launch-red.log` 2실패 → `task8-tf-boundary-green.log` **12 passed/10.38초**.
- 별도 실행 파일 시험은 설치 전 binary 부재, 이어 peer의 explicit context/default executor 혼용으로 실패했다. 두 원본 로그를 보존하고 fixture executor만 동일 context로 맞췄다. `task8-tf-process-context-fixed.log` **1 passed/5.43초**: 실제 GID·기존 파일 거절/bytes 불변·소유 프로세스 SIGINT 종료0을 확인했다. 이 엔진 없는 성공을 전체 엔진 정상 종료나 G1 통과로 세지 않는다.
- TF 보완 후 고정 소스 `task8-tf-fixed-build.log` 두 패키지 build 성공111초. `task8-tf-fixed-package.log`: **196 tests/0 errors/0 failures/0 skipped** (Python179/116.50초 + 실제 native gtest11 + CTest wrapper6). `task8-tf-fixed-install-audit.json`: **8패키지 소스/설치 감사 통과**. 이 뒤 runtime을 변경하지 않고 새 UUID의 실제 MuJoCo 진단으로 진행한다. 최종 동결 전체13.3/13.4 엔진 회귀는 아직 아니다.
- 다음 실행 `native-g1-mujoco-407340de-1b07-4865-9ed6-e7693003ca82`, run_id `25c12e1f-0dfd-4525-a345-9fd5c85ad932`: 실제 native 관측과 TF 소유 관측기가 동작하여 bootstrap frame201건을 수집했지만, startup은 `crawl:body:wall_age`로 실패했다. 수납/정적10초/발 lift 단계까지 도달하지 않았으므로 G1 PASS가 아니다.
- 원본 시각 분석 `timing-analysis.json`: 최초 fault ROS12.564초에서 body 마지막 촬영12.384초, probe 수신 후 나이206.309ms. 같은 시점 IMU/접촉54.9ms·관절37.4ms였다. body의 최대 수신 공백342.539ms 동안 촬영 시각 증가는30ms였다. **전체 엔진 정지나 renderer 하나로 단정하지 않는다.** 원본 FreeJoint 발행과 Python 변환/전달 중 어느 경계의 지연인지 추가 계측해야 한다.
- 종료 증거: native PID1172/start95648·부모1166, TF 관측기1181은 모두 실제 종료0, 강제 정리 없음·잔여 없음·부모 회수 확인. 하지만 fault 이후 STOPPED를 확인하지 못해 서비스 기반 자원 정리 순서는 완료하지 못했다. 따라서 정상 runtime/engine 종료 인수 check는 FAIL을 유지한다. 종료 코드0만으로 성공을 덮어쓰지 않는다.
- 외부 고정 FreeJoint 소스를 **읽기만** 했다: SystemDefaultsQoS, RealtimePublisher `try_publish`,50Hz, 원본 ROS header 보존. 외부 원본 변경은 없다. 다음 계측은 `/native/free_joint_states` 원본과 `/odom` 변환 출력의 DDS source/received SYSTEM 시각·callback SYSTEM/첫 MONOTONIC 수신, 소유 PID/start tick의1Hz CPU/thread sample을 수집한다. ROS 시간과 wall 시간은 빼지 않으며 age200ms를 완화하지 않는다.
- 계측 부재 RED `task8-body-boundary-red.log` 3실패 → `task8-body-boundary-first.log` **29 passed/17.75초**. 관측기 자체가 두 번째 모터/TF 발행자가 되지 않도록 원본은 구독·로그만 한다. 실제 ROS 콜백 형식도 별도 시험 후 다음 엔진을 시작한다.
- 실제 콜백/시각 시험 `task8-body-transport-wire-first.log` **1 passed/10.80초**, `task8-body-trace-install-audit.json` 8패키지 감사 통과 후 새 실행 `native-g1-mujoco-60663048-a98c-4242-a536-abed2c9d4c41`을 수행했다. 이번에는 body-age가 아니라 STAND의 `stance slip`으로 실패했다. engine/runtime 코드와200ms·20mm 기준은 바꾸지 않고 실패를 보존했다.
- `body-transport-analysis.json`: 같은 촬영638개를 연결했다. 원본 발행→변환 출력 발행 최대18.381ms/p95 9.653ms, 원본 RMW 전달 최대14.653ms였다. 이 실행의 양호한 변환 시간이 앞선342ms 공백의 원인을 소급 증명하지는 않는다. probe dispatch 통계에는 종료 정리 구간이 섞여 있어 그 최대값을 변환기 계산 비용으로 해석하지 않는다. `process_metrics.jsonl`은 소유 PID/start tick·1Hz CPU/thread 기록이다. renderer 원인 단정이나 CPU 설정 변경은 하지 않았다.
- `stand-geometry-analysis.json`: 앞발 실제 접촉점 XY 이동20.039mm, URDF-FK 중심 이동20.043mm로 일치했다. FK/접촉 XY 차이≤2.617mm, URDF/native CoM 차이≤2.581mm였다. 따라서 이번 실패는 좌표 계산 착시가 아닌 실제 물리 미끄러짐이다. native/관측기는 종료0, 부모 회수·잔여 없음·강제 없음이지만 측정 정지 확인 실패로 전체 정상 종료 인수는 FAIL이다.
- 최소 재현 `test_gait_physics.py`는 **Python MuJoCo3.3.7의 실제 물리 component 시험**이며 ROS C++3.12.0 인수가 아니다. 정상 keyframe 초기화와 actuator ctrl만 쓰고 root pose/속도/외력을 쓰지 않는다. 첫 fixture의 contact.id API 오류는 `task8-physical-stand-red.log`에 보존했다. 접촉 인덱스만 교정한 `task8-physical-stand-red-confirmed.log`에서 같은 미끄러짐을 **3.08초**에 재현했다.
- 통제 실험 `stand-gain-probe-ec500876-eac4-4996-bbe3-ca58b041df67/comparison.json`: 동일 원본 모델의 메모리 복사본에서만 다리 kp 배율1/5/10, kv 배율1/√5/√10을 순차 비교했다. 힘·관절·ctrl 한계는 모두 유지했다. 원본은20.063mm 이동/0.07715rad 오차로3.08초에 실패,5배는5초 유지·3.581mm/0.01067rad,10배는5초 유지·1.648mm/0.00515rad였다. 성공만 추려 집계하지 않았다.
- 낮은 검증 배율5를 navigation 전용 `mujoco_navigation_actuators.yaml`에 채택했다. 기존 모델·팔·그리퍼·힘 한계는 수정하지 않았다. physics hash가 바뀌므로 이전 scene/profile로 재실행하거나 허가를 상속하면 안 된다. `task8-physical-stand-first.log`: 실제 물리 STAND·힘 제한·profile/장면/footprint **23 passed/23.44초**. **실제 ROS G1/G2와 Gazebo 동역학은 여전히 별도 검증이 필요하다.**
- G1의 누락 항목인 실제 native ctrl도 보완 중이다. `task8-native-controls-red.log`는 원본 상태 읽기 기능 부재, `task8-native-controls-probe-red.log`는 수신기 부재를 확인했다. probe 수신/실제 DDS 회귀 `task8-native-controls-probe-first.log` **9 passed/10.90초**. native source는 같은 소유 snapshot에서 ctrl/qpos/qvel/actuator_force/qfrc_actuator·단위·gain·명시 주소를 읽으며 명령 토픽을 실제 제어값으로 대체하지 않는다. C++ 첫 빌드의 `mjNGEAR` 오류를 고정3.12.0 헤더의 실제6열 gear 및 nactuator/nu/nout 주소 계약에 맞춰 교정했다. **native_ctrl_observed check는 의미·출처 검증 완료 전 false를 유지한다.**
- 이후 `task8-load-fixed-build.log` 두 패키지 빌드는 성공했다. `task8-load-fixed-package.log`는 **204건 중 1실패**(실제 native gtest13 + wrapper6 통과, Python185 중 generation 변경 시험 실패)로 종료되어 설치 감사와 다음 엔진 실행을 보류했다. 세대0/MOVING의 마지막 발행만 확인됐으며 입력 콜백 부재라고 단정할 증거는 없다.
- 재개 후 진단 정보를 추가한 단독 `task8-generation-characterize.log`는 1통과/9.47초였다. 파일 단위 `task8-generation-full-characterize.log`에서는 세대 변경 시험은 통과했으나 실제 속도 settle/고착 팔 timeout 시험이 `guard:ros_age`로 2실패/10통과(52.51초)했다. 시험용 원본 발행 공백 **213.6852ms**가 관측되어 200ms 차단 자체는 옳다. 다른 실패를 같은 결함으로 합치거나 통과 실행만 추려 세지 않는다. 다음 판별은 시험 발행 전후 MONOTONIC/스레드 CPU와 실제 상태 이력이며 엔진을 시작하지 않았다.
