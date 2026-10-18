# 13.4 변경·검증 보고서

## 2026-10-19 후속 진단 상태

아래 기존 일괄 인수 기록은 역사적 결과로 보존한다. 최신 후속 진단은
`SECTION_13_4_DEBUG_KO.md`와 `evidence/section_13_4/debug-20261018`에 있다.
자체 형상 컵의 실제 YOLO 탐지는 두 엔진에서 성공했고, MuJoCo 지연 기하와 일부
고장 주입도 별도 실행에서 통과했다. 다만 동일 설치본의 10/15Hz 추적 비교 4건은
모두 FAIL이며 Gazebo 15Hz는 종료 정지도 재현했다. 따라서 전체 판정은 여전히
미달이다. 서로 다른 소스 단계의 성공을 합쳐 새 최종 일괄 PASS로 만들지 않는다.
기본 10Hz, 사용자 선택 상한 15Hz, 촬영/receipt 안전 기준300ms, 팔 상한5Hz를
유지했다. 관리자 권한과 시스템 ptrace 정책 변경은 사용하지 않았다.

추가 일반 권한 부모 GDB 진단으로 실제 Gazebo 스택을 수집했고, 두 엔진의 llvmpipe
CPU 렌더러를 확인했다. 후속 exec/렌더 스레드2 조건에서 Gazebo 추적 단일 실행은
5.2초·15명령·전체 필수 검사 PASS였으나 같은 렌더 제한의 MuJoCo는 FAIL이었다.
exec 단독 실행에는 clock bridge -11 종료도 남았다. 따라서 전체 판정은 변하지 않는다.
최종 소스 회귀254건과 패키지101건은 통과했다. 카메라 소유권 수정은 별도 승인된
설계서 작성 단계이며 실제 새 플러그인은 아직 구현하지 않았다.

## 판정의 범위

13.4의 실행 가능한 RGB-D/YOLO/TF/추적 패키지와 실패를 숨기지 않는 검증기를 구현했다. **전체 인수 판정은 FAIL이며, 13.4 전체 완성·13.5 자동 접근 준비 완료를 선언하지 않는다.** 최종 일괄 실행 `evidence/section_13_4/final-validation-20261018-a`는 종료 코드1로 끝났다. 20개 실행 그룹 중 11개 PASS / 9개 FAIL이며 미달 그룹을 이전 성공으로 채우지 않았다. 아래 확정 표와 해당 `summary.json`을 함께 읽는다.

- 기준: 13.3 `df993e86d9b6ad446c058bc3b5a61c59c15495db`.
- 절 브랜치: `feat/ch13-section-13-4`.
- 런타임/검증 소스 고정 커밋: `1b173e3b5dc7d996ad2a77b5bca5a57d07329cd0`.
- 최종 일괄 실행은 이 커밋을 만들기 전에 시작했으므로 top-level HEAD는 `adb74f2…`와 당시 dirty 경로를 기록한다. HEAD만으로 검증 코드를 주장하지 않는다. 정확한 실행 소스 바이트는 각 `source_snapshot.json`, 설치 일치 검사는 `installed_paths`에 있다. 최종 문서/evidence 커밋과 원격 SHA는 별도로 확인한다.
- 이전 장과 synced `sources/`는 수정하지 않았다. 실행 코드는 Ch13 네 패키지와 고정 외부 MuJoCo 의존성만 사용한다.

## 기존 사실·이번 구현·미구현 제안

| 구분 | 사실 |
|---|---|
| 기존 13.2 | 4족 12 + 팔 6 + 그리퍼 2의 20 가동 관절, 독립 모델·엔진 launch·position controllers |
| 기존 13.3 | 측정 stow/기립 lifecycle, 별도 프로세스, PickObject dry-run·취소·실패 전파; PPO/MoveIt/파지는 없음 |
| 이번 구현 | 실제 eye-in-hand RGB-D, 광학 프레임·native odom, 로컬 검증 가중치 YOLO, 촬영 시각 3D 투영/TF·대상별 필터·TTL |
| 이번 제어 확장 | 명시적 선택의 기립 소각도 q1/q5 추적, stow와 공유하는 단일 팔 소유권, 취소 결과 확인·fault·명령 감사 |
| 검증 도구 | 새 실행 UUID/해시/시각/필수 검사, 순차 실제 엔진·기하·YOLO·추적·입력 상실·기존 기능 시험 |
| 미구현 | Nav2 접근, 실제 PPO 보행/보행 전환·적재 안정성, MoveIt/IK/충돌 회피 계획, 물리 파지·운반, 일반 hand-eye 보정·SLAM·실로봇 |

`PickObject`의 비-dry-run은 거부한다. dry-run도 물리 성공이 아니라 NOT_IMPLEMENTED 또는 취소/실패를 반환한다. 안전 영점 stow는 운반용 folded pose가 아니다. 원고의 추후 제안을 이미 동작하는 기능으로 바꾸어 쓰지 않았다.
통합 로봇은 원시 형상과 근사 물성의 교육용 모델이며 제조사 Go1의 정확한 CAD/관성 복제품이나 실기 보정 결과가 아니다.

## 주요 변경과 근거

1. `integrated_robot_vision`을 별도 설치 패키지로 추가했다. 수학·입력 검증은 ROS 독립 모듈, 탐지와 융합은 각각 짧은 ROS 콜백과 한 작업자다. 최신 대기 프레임만 유지하고 원본 촬영 header를 보존한다.
2. `vision_enabled`로 센서와 질량 없는 추가 프레임을 선택한다. 13.2 카메라 -1.5708 pitch를 정확한 -π/2로 교정하고 URDF 고정축 RPY/MJCF Euler 차이를 quaternion과 독립 카메라 비교 시험으로 고정했다. 물리 장착 위치·질량은 유지했다.
3. MuJoCo native CameraInfo의 R=0은 고정 원본 소스로 확인했다. 알려진 무왜곡 모델만 검사해 R=identity로 정규화하고 raw는 `/native/camera_info`에 남긴다. 임의의 실제 왜곡을 교정하는 노드가 아니다. clipping의 extent 스케일도 명시했다.
4. `native_pose_adapter`만 root TF/odom을 발행한다. 내부 TF는 RSP가 소유한다. 고정 MuJoCo 플러그인의 free qvel은 선속도 world/각속도 local이므로 선속도만 child로 회전한다. 단위 회귀는 통과했으나 Nav2용 동적 상태 추정기가 검증된 것은 아니다.
5. RGB-D 정합 ≤30ms, 입력 age ≤300ms, Info ≤1s, TF 대기 ≤100ms를 유지했다. 먼저 도착한 탐지는 원래 기한 안에서 RGB-D를 기다린다. 늦은/중복 결과는 최신 상태를 무효화하거나 TTL을 갱신하지 않는다. epoch/보정 변경 시 대기 작업을 비운다.
6. mm/m·stride·endian·K/R/P/D·ROI·유효 표본/MAD·프레임을 검사한다. 필터는 odom에서 대상별로 적용하며 대상 전환·모호함·TTL/TF 상실 시 제어 입력을 무효화한다. 공분산은 휴리스틱이다.
7. 팔 전체 세션 예약과 한 outstanding 액션을 구분했다. send 전 UUID를 등록하고, 늦은 수락도 disable 이후 취소한다. cancel ACK만으로 소유권을 풀지 않는다. terminal 결과 지연은 fault이며 늦게 끝나도 자동 복구하지 않는다.
8. 실제 선택 UUID/관절 이름/소스 측정값/명령/단조 시각을 감사 토픽에 남긴다. 계산 도중 입력이 만료돼도 send하지 않도록 직전 재검사를 추가했다. 다른 팔 직접 trajectory 발행자나 unknown live UUID는 추적 중단 조건이다. ROS 네트워크의 접근 권한을 강제로 독점하는 보안 기능은 아니다.
9. 생성자/추론 중 SIGINT를 실제 프로세스로 재현했다. 신호를 처리하는 동안 생성자 반환과 worker join을 기다린 뒤 ROS context를 종료한다. 기존 다중 실행기는 Jazzy guard 종료 순서를 국소적으로 보완했다.
10. YOLO의 lazy predictor 설정이 Torch 스레드를 7개로 되돌리는 것을 실제 저장 영상으로 재현했다. 발행하지 않는 준비 추론 뒤 1개로 복원한다. 이후 Gazebo의 유효 결과 발행은 0개에서 159개로 관측됐지만, 이것이 모든 지연 원인의 독립 인과 분석이나 의미 인식 성공을 뜻하지는 않는다.
11. 통합 launch는 엔진 하나·기존 control 소유자·실제 vision만 실행한다. 모델/인자 사전 검사는 엔진 시작 전에 수행한다. MuJoCo 기본 모드는 명시적 legacy 카메라 설정으로 eye stream을 끈다. 외부 vendor 소스는 변경하지 않았다.

## 검증 이력과 읽는 방법

최종 일괄 실행의 새 빌드는 앞 장/이전 Ch13 overlay 없이 네 패키지를 설치했다. 설치된 Python 모듈·launch·URDF·MJCF·설정 바이트가 소스와 일치하며 패키지 prefix가 새 install 아래인지 검사했다. 전체 pytest **235개 통과**, colcon 결과 **96 tests / 0 errors / 0 failures / 0 skipped**가 기록됐다. 버스 저장 이미지의 실제 YOLO/hash/autoinstall 검사도 통과했다. 이것들은 엔진 전체 인수 통과와 별개다.

| 확정된 일괄 실행 그룹 | 결과 / 수치 |
|---|---|
| Gazebo 정적 기하 | PASS, 30개 독립 촬영, RMS .002294469206m |
| Gazebo 150ms 추가 지연 + 실제 카메라 진동 | PASS, 30개, RMS .001871643196m; 최신 TF 진단 RMS .007825485966m |
| Gazebo native YOLO | 실제 유효 메시지 159개, 물체 의미 검출/유효 3D 0개 → FAIL |
| Gazebo 5초 추적 | 약1.98초/6개 명령 후 invalid/lost target로 OFF → FAIL. 측정 최대 속도 .05334rad/s, 각도 .02072rad, 최소 명령 간격 .2847s는 제한 안 |
| Gazebo images 손실 | 개별 로직/종료 판정은 원본 파일 참고. native 강제 종료가 있어 전체 FAIL, 잔존 PID 0 |
| Gazebo TF 손실 | PASS, 새 엔진·실제 목표 뒤 의도한 자체 RSP 종료·명령 중단·미완료 해소·정상 종료 |
| Gazebo joint 손실 | PASS, broadcaster 비활성화·명령 중단·취소 확인·정상 종료 |
| Gazebo 기존 13.3 회귀 | 기능 및 5개 runtime 종료 PASS, native Gazebo SIGTERM 승격/exit -15로 전체 FAIL |
| MuJoCo 정적 기하 | PASS, 30개, RMS .003131535163m, 수집 약37.75초 |
| MuJoCo 150ms 추가 지연 | 60초 안에 3/30개, 해당 3개의 RMS .002417955214m이나 표본 부족 → FAIL |
| MuJoCo native YOLO | 신선한 결과 메시지 4개로 요구 10개 미달, 의미 검출/유효 3D 0개 → FAIL |
| MuJoCo 5초 추적 | target_valid/target_fresh gate에서 활성화 거부 → FAIL. 5초·위치/속도 성능은 미검증이지 실제 제한 위반을 관측한 것이 아님 |
| MuJoCo images 손실 | PASS, 실제 목표 뒤 소비 입력 차단·기한 내 명령 중단·취소 확인·정상 종료 |
| MuJoCo TF/joint 손실 | 각각 fault 주입 전 기한 초과 → FAIL, 해당 중단 경로는 이 실행에서 미검증 |
| MuJoCo 기존 13.3 회귀 | 기능 및 runtime/native 정상 종료 PASS |

일괄 실행 ID는 `30b8e523-d190-4e22-929e-f11cb14a1826`이다. 기하의 static/delay는 각각 새 엔진에서 실행했으며 top-level 두 geometry 그룹에 포함된다. 표의 단위는 모두 m/rad/초이며 mm 표기는 가독성을 위한 환산이다. 종료 승격 후에도 잔존 PID가 0임을 확인했으나 이를 정상 종료로 바꾸지 않았다. 별도 종료 후 프로세스/등록 artifact/소스 감사는 `task7/archive-source-audit.json`이다.

이전 실행도 보존했다. MuJoCo 정적 기하 30개/RMS .003024m PASS, 이전 지연 시험은 60초 안에 3개만 유효하여 FAIL이었다. Gazebo 지연 기하는 통과했어도 종료 승격으로 전체 FAIL이었던 실행이 있다. 최초 센서 smoke의 PASS 중에도 후속 잔존 프로세스 감사에서 문제가 드러난 파일이 있어 `task2/NOTES_KO.md`에 한계를 명시했다. 과거 파일을 새 판정으로 고치지 않았다.

## 판정·증거의 한계

- `geometry`는 bbox 광선과 알려진 전면 x=.98m의 깊이 일관성이다. 물체 COM x=1m와 비교하지 않는다. 같은 촬영 TF를 사용하므로 모든 TF 자유도의 독립 ground truth는 아니다.
- YOLO 추론 시도, 신선한 결과 발행, 의미 검출, 유효 3D 수를 구분한다. 빨간 fixture를 강제로 캔으로 분류하거나 color backend를 대체 투입하지 않았다.
- images 손실은 탐지 소비 입력 차단이며 native 센서 전원 차단이 아니다. joints 손실은 joint_state_broadcaster 비활성화이며 관절 TF도 함께 오래된다. fault 전 tracking 시작 자체가 거부되면 그 음성 경로는 미검증이다.
- TF 단일 소유권은 실제 발행자 집합·전체 모델 간선·소스 계약의 추론이다. 설치 Jazzy metadata에 GID가 없어 패킷별 발행자 인증은 할 수 없었다.
- Python/WSL/렌더러 환경의 10/15/50Hz는 상한/목표다. hard realtime·PPO 안정성·실로봇 안전을 주장하지 않는다.
- shutdown stop ACK·런처 종료·자식 정상 종료·잔존 PID를 구분한다. 취소 확인 실패를 Torque Off나 물리 정지로 바꾸어 쓰지 않는다. 강제 종료는 실패로 남긴다.
- 시스템과 venv의 `pip check`에는 기존 Flask/Arrow/widget/type stub/matplotlib 관련 동일 경고가 있었다. 실습으로 전부 해결했다고 보고하지 않는다.
- MuJoCo C++ pal_statistics의 shutdown context 관련 메시지, root KDL 및 Gazebo 확장 태그 경고는 원본 로그에 남는다. 정상 반환값이 해당 경고의 부재를 뜻하지 않는다.

## 리뷰·후속 조치

새 큐 처리와 스레드 예산 수정은 실제 RED→GREEN 이후 재빌드/엔진 재현했다. 마지막 archive 감사에서는 `core.autocrlf=true` checkout이 로그/JSON을 CRLF로 바꿔 기록된 SHA를 깨뜨리는 것을 실제 Git 왕복으로 재현했다. evidence에만 `-text`를 적용했다. 생성된 native XML/SDF의 원래 공백도 해시 후 잘라내지 않도록 evidence에만 검사 예외를 두고, 실제 source XML 검사는 유지하는 Git 회귀를 추가했다. 관련 회귀 **12개**, 최종 전체 pytest **237개**가 통과했다(`task7/final-source-suite.txt`, `final-source-tests.xml`). 이는 저장 정책/시험 추가이며 런타임·모델·실행기의 동작 변경이 아니다. 일괄 실행 당시의 235개/colcon96 결과를 새 개수로 덮어쓰지 않았다.

문서·archive 점검 후에도 이전 장 무변경과 source/document `git diff --check`를 다시 확인했다. 원격 push는 절 브랜치만 대상으로 하고 force/main 병합/PR 생성은 하지 않는다. 마지막 commit 자체의 SHA를 그 commit에 포함할 수는 없으므로 최종 원격 SHA 일치는 응답 및 Git 명령 결과로 별도 인계한다.

남은 주요 인수 미달은 MuJoCo 지연 경로의 처리량, 두 엔진의 연속 5초 추적, native 물체의 YOLO 인식, 일부 손실 시험의 활성화 기한 및 간헐적 Gazebo 종료다. 입력 age/TF 기한을 늘리거나 invalid 목표를 유효로 유지해 통과시키지 않았다. 후속 개선은 촬영→수신→작업→TF 도착 지연을 먼저 계측하고 실제 새 실행으로 재검증해야 한다. 고정 외부 렌더러 소스를 수정하거나 범위를 바꾸는 선택은 별도 판단이 필요하다. 13.5는 이 상태를 자동 보행 준비 완료로 간주해 시작하지 않았다.

단계별 재현은 [가이드](LAB_13_4_GUIDE_KO.md), 출처·커밋·Git blob 해시와 권리 미확정 사항은 [REUSE_MANIFEST](REUSE_MANIFEST.md), 소유권/실패 모드 검토는 [자체 리뷰](SECTION_13_4_REVIEW_KO.md)를 따른다. 13.5의 자동 보행 접근 구현은 이 보고서에서 완료했다고 주장하지 않는다.
