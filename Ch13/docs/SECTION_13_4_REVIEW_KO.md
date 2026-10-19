# 13.4 네이티브 자체 리뷰

> 2026-10-20 최종 상태: 사용자 선택에 따라 **현재 실험 브랜치와 증거만 보존**한다.
> snapshot 렌더 worker의 `glfwInit/CreateWindow/DestroyWindow` 호출은 설치된 GLFW의
> main-thread-only 계약을 위반한다(P1/Important, 미해결). GL 시험·기하 측정의 일부 PASS는
> 이 API 계약 준수나 배포 안전성을 입증하지 않는다. EGL 변경·추가 실측은 진행하지 않았다.
> 전체 인수 FAIL이며 snapshot 사용을 권장하지 않는다. 아래 명령은 역사적 재현 절차이지
> 인수 완료 권고가 아니다. main 병합과 13.5 재개는 보류한다.
> [최종 보존 판정·근거](../evidence/section_13_4/cam-66d636a0/RETENTION_KO.md)

## 2026-10-19 후속 리뷰 보충

후속 timer 재진입, complete RGB-D 후보 덮어쓰기, 처리 중 중복 detection 결함은
실패 회귀를 먼저 재현한 뒤 수정했다. 15Hz 선택은 사용자 승인된 기본값 불변 옵션이다.
의미 인식 미달은 자체 형상 컵으로 두 엔진에서 별도 PASS를 얻었으나, 아래 기존
최종 실행의 결과는 그대로 보존한다. 연속 추적·취소 terminal 응답의 간헐 미확인·
Gazebo 종료 정지는 아직 해결됐다고 판단하지 않는다. 10/15Hz 비교 네 실행이 모두
미달이므로 다음 수정 전에 종단 시간 예산/실행 구조 검토가 필요하다. 상세 원본은
`SECTION_13_4_DEBUG_KO.md`에서 추적한다. 이번 보충도 독립 리뷰가 아닌 네이티브
작성자 자체 리뷰이며 서브에이전트를 사용하지 않았다.

검토 기준은 승인 설계·구현 계획과 `df993e86d9b6ad446c058bc3b5a61c59c15495db..1b173e3b5dc7d996ad2a77b5bca5a57d07329cd0`의 소스, 실제 실행 증거다. 사용자의 네이티브 모드 지시에 따라 **작성자가 분리된 읽기 검토를 직접 수행했으며 서브에이전트/독립 리뷰어를 호출하지 않았다.** 작성자 자체 리뷰는 새로운 시각의 독립 검토보다 약하다.

## 결론

실습용 패키지·검증기를 실행/재현할 수 있고 실패를 은폐하지 않는다는 점은 확인했다. **전체 인수 기준을 만족한 브랜치 또는 실로봇 배포 준비 상태로 판단하지 않는다.** 필수 native 지연·일부 안전 시험과 지속 추적/인식에 미달이 남는다. main 병합이나 13.5 자동 접근의 성공 근거로 사용하면 안 된다.

## 다섯 검토 초점

| 초점 | 확인한 코드와 시험 | 판단 |
|---|---|---|
| 보정/epoch/역순 결과 | `cache.py`, `freshness.py`, `vision_processor.py:190`의 원본 header·중복/오래된 결과·유계 대기, `tracker.py`의 대상별 상태 | epoch/보정 변경 후 이전 작업 폐기. 촬영 timestamp를 현재 시각으로 바꾸지 않음 |
| depth·ROI·정합 | `geometry.py`, `parse_intrinsics`, `test_rgbd_cache.py`·깊이 byte fixture | mm/m, big endian, 행 패딩, 비정합/비유한 값/왜곡/ROI 실패를 유효 거리로 바꾸지 않음 |
| 만료/disable/결과 경합 | `tracking_support.py:290`, `arm_action_owner.py:30`·`:54`·`:69`·`:103`, 실제 ROS 액션 경계와 .31초 계산 지연 시험 | 계산 후 재검사, UUID 선등록, 한 outstanding, terminal 결과까지 예약. 늦은 결과가 재활성화하지 않음 |
| 누락 모델/검출 실패 | 명시적 backend·로컬 SHA, launch 사전 검사, saved-image/두 엔진 YOLO·fixture 별도 결과 | fallback 없음. GZ 159개 결과 메시지와 의미 검출 0건을 구분. MJ 낮은 신선 출력 수도 그대로 FAIL |
| 예외/오래된 PASS/종료 | `verify_vision_13_4.py:150`·`:177`, `verify_all_13_4.py:30`, `execution.py:10`, `common.py:11` | fresh UUID/기한/필수 검사/원본 artifact 해시, 생성자·작업 중 신호·실제 자식 사망·무관 PGID 보존 시험. 런처0이라도 내부 SIGTERM/SIGKILL은 정상 종료로 간주하지 않음 |

카메라 축/FK는 URDF와 독립 MuJoCo 카메라를 영점·비영점 관절에서 비교했다. 실제 RGB/depth/전체 CameraInfo·TF·관절 기록을 읽고 native 주석 영상도 확인했다. 내부 TF는 RSP, root/odom은 adapter, 팔 목표는 manipulation_node의 한 소유자를 거친다. 센서·제어 프로세스 분리는 확인했으나 hard realtime을 보장하지 않는다.

## 중요 미달 사항 — 해결됐다고 판단하지 않음

1. **MuJoCo 지연 기하 표본 부족.** 최종 `geometry_mujoco/native/delay/result.json`에서 60초 안에 3/30개다. 낮은 RMS만 보고 통과시키면 재현성을 잘못 주장한다. 촬영·수신·추론·TF 도착 지연을 실제 시각으로 나누어 계측하고, 원래 300ms/100ms 한계 안에서 처리 경로를 개선한 뒤 새 실행으로 확인해야 한다.
2. **연속 5초 추적 미달.** GZ는 약1.98초/6개 목표 뒤 invalid/lost target로 중단, MJ는 목표 신선도 gate에서 거부했다. `tracking_support.py:166`·`:200`·`:290`의 거부는 안전 동작이지만 추적 성공이 아니다. 좌표/TF 정합·처리량의 원인을 계측할 일이며, 오래된 좌표를 valid로 유지하는 방식으로 해결하면 안 된다.
3. **의미 인식 성공 없음.** native YOLO가 단색 fixture를 찾지 못했다. `yolo_gazebo/native/result.json`, `yolo_mujoco/native/result.json`의 0 검출/0 유효 3D는 실제 결과다. 향후 적합한 권리/레이블의 물체 자산·데이터셋·학습 또는 평가 설계를 별도로 정해야 한다. fixture 결과를 YOLO 성능으로 대체할 수 없다.
4. **간헐적인 native Gazebo 종료 승격.** 최종 images 손실과 legacy 실행에서 논리 검사/런타임은 통과했으나 엔진 SIGTERM이 필요했다. 원본 vendor 소스는 수정하지 않았다. bounded cleanup 뒤 잔존이 없다는 것과 정상 종료는 다르다. 이미 세 가지 원인 분리 재현을 했으며 네 번째 추측성 조치를 시도하지 않았다.
5. **일부 fault 미주입.** 최종 MJ TF/joint 시험은 실제 fault를 주기 전에 기한이 끝났다. 이 실행으로 해당 손실 경로가 안전하다고 인증할 수 없다. 이전 별도 실행의 TF PASS는 그대로 보존하지만 최종 실패를 덮지 않는다.

위 사항은 source unit 테스트가 녹색이라는 이유로 낮은 등급으로 내리지 않았다. 이 때문에 전체 인수는 FAIL이다. 관측된 미달과 미검증을 기록한 교육용 진행 브랜치로만 인계한다.

## 마지막 수정·회귀

이 구현 과정에서 단일 소유권의 미확인 send/cancel, 입력 계산 중 만료, 생성자/worker 신호 종료, 탐지-before-RGB-D 순서와 중복 결과, lazy YOLO 스레드 재설정 등을 먼저 실패 시험으로 재현해 수정했다. 원래 물리/시각 허용치를 늘리지 않았다. 최종 일괄 pytest235/colcon96 통과는 이 런타임 상태의 결과다.

마지막 archive 검토에서 `core.autocrlf=true`의 실제 Git checkout이 `engine.log`/JSON 바이트를 CRLF로 바꾸어 저장 해시를 깨뜨리는 결함을 추가로 재현했다(`artifact-checkout-red.txt`). evidence에만 `-text`를 설정했으며 원본 로그를 다시 쓰지 않았다. 생성된 XML/SDF 복사본의 원래 공백을 유지하면서 source XML 검사는 여전히 실패시키는 실제 Git 회귀도 추가했다. 관련 요약/checkout 회귀12개, 마지막 전체237개가 통과했다. 이 수정은 런타임·모델 변경이 아니므로 물리 실험 결과를 다른 코드의 성공으로 갈아끼우지 않는다.

종료 후 감사는 검증 소스115개가 고정 코드 커밋과 일치하고, 등록 artifact145개가 원본 해시/크기를 유지하며, 실행 후 runtime 변경 및 새 설치 prefix를 가진 live 프로세스가 0임을 확인했다. 이는 archive/출처/종료 감사의 PASS이지 기능 인수 PASS가 아니다.

## 범위 밖으로 분리한 판단과 비용

- 기존 절 전용 checkout을 계속 사용했다. 추가 worktree의 격리는 없지만 사용자 작업·과거 실패 증거를 이동/삭제하지 않는다.
- 일반 설치를 사용해 수정 후 재빌드했다. Windows 마운트에서 설치 모드를 중간에 바꾸지 않는 대신 재빌드 비용이 든다.
- ideal MuJoCo R=0 adapter는 알려진 센서 전용이다. 임의의 실제 렌즈/미등록 depth 보정에는 사용할 수 없다.
- vision의 짧은 ROS 콜백은 single-threaded, 작업/TF 대기는 별도 worker다. callback 수신은 직렬이며 realtime 우선순위는 없다. 기존 제어 실행기의 Jazzy private-pool 보완은 버전 변경 시 다시 시험해야 한다.
- 팔 소유권은 terminal 결과까지 유지한다. 통신 상태를 모르면 자동 해제하지 않아 작업이 멈출 수 있다. 복구는 fault 해제일 뿐 자동 stow/자동 재개가 아니며 필요 시 새 명시적 stow가 필요하다.
- TF 소유권은 그래프·전체 간선·소스 계약의 추론이다. GID 없는 Jazzy에서 패킷별 인증을 구현했다고 할 수 없다. 외부 악의적 DDS writer·같은 UUID 복제까지 방어하는 보안 계층도 아니다.
- foreign trajectory는 발견하면 own tracking을 끄지만 외부 controller client가 명령을 보내기 전부터 강제로 차단하지 않는다. 통제된 단일 실습 ROS graph를 전제로 한다.
- 기립 gate는 신선한 다리 상태/참조 모드·안전 관절 범위다. 본체 IMU/접촉력/속도 기반 안정성 인증이 아니며, 적재 보행·미끄러짐·외력 상황의 정지 보증이 아니다.
- 카메라 진동 benchmark는 target 없이도 실행할 수 있는 명시적 opt-in이며 같은 팔 소유자·관절 한계를 사용한다. 이것이 물체 추적이나 PPO 보행의 대체 증거가 되지 않는다.
- images 손실은 소비 차단이고 joints 손실은 관절 TF에도 영향을 준다. 센서 전원 장애·TF가 정상인 독립 joint 손실 전체를 검증한 것은 아니다.
- native 픽셀의 가시 표면 점은 일반 물체 pose/그립 방향/충돌 회피 계획이 아니다. 사진의 사용 권리·일반 객체 데이터·MoveIt/물리 파지·Nav2는 해결되지 않은 별도 범위다.
- 원고의 자동 접근/운반 완료를 이 코드로 선언하지 않는다. 13.5는 새로운 설계와 유효 목표·실제 보행 능력의 별도 검증이 필요하다.

기능에 영향 없는 추가 스타일/미세 최적화는 이번 리뷰에서 무리하게 확장하지 않았다. **독립 리뷰 부재와 위 중요 인수 미달은 남아 있다.**

## 2026-10-20 snapshot 소유권 구현 자체 검토

검토 범위: 승인된 camera snapshot 설계/계획의124061f 이후 변경,6828b82의 실제
엔진 체크포인트와 cc17631의 실측 기록, 후속 실행기 가드. 서브에이전트 없이 작성자가
검토했다. 독립적인 새 리뷰어보다 약한 검토이며 main 병합 준비 완료를 의미하지 않는다.

| Review Focus | 근거 / 판단 |
|---|---|
| overwrite/rollback | 두 슬롯과 move-only lease, 같은 metadata 교환. 실제 readback barrier와 epoch 폐기 시험. ROS/DDS에 이미 발행된 패킷까지 회수한다는 보장은 아님 |
| cleanup/init | lifecycle 직렬화·state atomic 교환·stop/wake·join 후 해제. GL 자원은 worker 소유이나 GLFW main-thread 계약 위반(P1)이 남아 API 정합성은 미달. driver 무한 정지의 강제 안전 중단도 보장하지 않음 |
| mixed policy | disabled 미렌더, polled 병합/보존·취득 후 반복 방지, index/중복/비유한 time 거부. 단일 control producer와 외부 모델 수명 계약 필요 |
| ABI/overlay | 별도 class ID, 실제 pluginlib 생성, source manifest, 실제 PID의 camera/mailbox 두 .so 경로·해시. 원본·설치 checkout은 불변 |
| delay/result loss | 촬영300ms/TF100ms/팔5Hz 유지, terminal 결과 전 소유권 해제 금지. clean10/15Hz 각3회 실패와 일부 terminal timeout은 미해결로 남김 |

중복 렌더링은 실제 로그/여섯 숨은 토픽 검사로 확인했고 snapshot 경로의 문서화된
하드웨어 인자로 차단했다. upstream/vision=false·20관절/TF·명령 소유권은 유지했다.
고유 촬영 기하·컵 YOLO 및 일부 손실 시험은 실제 엔진에서 확인했으나, 이것이 전체
추적·파지·자율 보행 성공을 뜻하지 않는다. 상세30회 결과는 변경 보고서를 따른다.

### 실행기 중요 지적과 단일 수정 패스

1. `run_vision_13_4.py`의 geometry 루프가 static 종료/잔여 PID를 확인하지 않고
   delay 엔진을 시작할 수 있었다. phase 결과를 먼저 보존하고 명시적인 empty residual
   기록이 없으면 다음 엔진을 거부하도록 했다.
2. `verify_all_13_4.py`는 native 분기만 종료 확인을 했고 legacy FAIL 뒤에도 다음
   엔진을 진행했다. legacy 형식에는 별도 cleanup 증명이 없어 실패/미확인이면 중단한다.
   이후 미실행 그룹은 UNVERIFIED이며 성공으로 채우지 않는다.
3. 같은 batch의 smoke 주석 경로가 weights 부모 폴더였다. 읽기 전용 외부 입력을
   변경하지 않도록 해당 batch의 ignored build/smoke_annotations로 옮겼다. 외부 사진을
   evidence Git에 재배포하지 않으며 원래 결과의 경로·해시는 남는다.

신규9회귀 RED를 실제 확인한 뒤 최소 수정했고 관련 runner/summary50건이 통과했다.
최종 전체 소스·패키지·설치 검사는 별도 최종 로그를 따른다. 이 가드 수정은 실제 카메라/
물리 모델이나 이전30회 결과를 바꾸지 않으며 문서만 작성한 뒤 native 성공을 주장하지 않는다.

### 판단을 분리한 범위와 최종 평가

- Gazebo driver/bridge 종료 및 액션/실행 지연의 추가 구조 변경은 승인된 snapshot 범위
  밖이다. 해결됐다고 선언하지 않고 전체13.4 FAIL/13.5 보류라는 비용을 명시한다.
- GUI/실로봇/PPO 적재 보행/MoveIt/물리 파지/Nav2는 이번 승인 계획의 대상이 아니며
  UNVERIFIED다. 임의의 외부 모델·해상도·악의적 DDS writer에 대한 인증도 아니다.
- 최신 TSAN 실행은 WSL memory mapping 제약으로 미검증이다. 초기9 core case의
  단일 실행 성공을 현재 전체 코드의 race-free 판정으로 확대하지 않는다.

**전체13.4 병합 준비: 아니오.** 데이터 소유권과 명시적 backend 선택은 시험했지만
GLFW 스레드 계약 위반과 연속 추적·일부 종료 인수 미달이 남는다. 전체 승격 또는13.5
진행 전에 API 정합성·시간 예산/액션 응답 설계와 새 실제 실행 검증이 필요하다.
사용자 선택에 따라 현재는 수정 없이 증거만 보존한다. 추가 사소한 지적의 보류 목록은 없다.
