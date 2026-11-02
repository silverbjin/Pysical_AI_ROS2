# 13.5 공개 통합 플랫폼 재현·선정 보고

> **최신 R2 결과:** 최소 ROS2 연결과 첫 실제 이동·정지·팔 hold·입력 손실·정상 회수가 통과했다. [R2 진입 보고](SECTION_13_5_REUSE_R2_REPORT_KO.md)를 먼저 읽는다. R2 전체 fault matrix와 R3는 아직 완료하지 않았다.

> **후속 R1 결과:** A 제한 조사와 교재용 게이트 개정을 마쳤다. 최소 배포 보완 후 실제 이동·세 정착 창을 확인했다. [최신 정착 검토](SECTION_13_5_REUSE_SETTLING_REVIEW_KO.md)를 먼저 읽는다. 아래 최초 조사와 실패는 이력으로 보존한다.

개정 ID: `section_13_5_reuse_v1`. 2026-11-02 한국 시각. 단일 작업자로 `superpowers:executing-plans` 적용.

**최초 조사 시점의 판정: 채택 플랫폼 없음.** 후보 A는 실제 원본 MuJoCo 이동을 재현했으나 0명령 뒤 정착에 실패했다. 후보 B는 두 공개 정책이 팔까지 제어하므로 독립 팔 소유권 사전 검사에서 채택하지 않았다. R2–R5는 착수하지 않았다. 기존 Task8 실패와 인수 기준은 보존했다.

## 결과와 증거

| 후보/실험 | 실행 범위 | 실제 결과 | 판정 |
|---|---|---|---|
| A 원본 `41f6d798` | 원본 PlayMujoco 클래스/제어 루프, rough 장면, 초기 home, 5초 0→5초 vx0.2→5초 0→4초 wz0.2→6초 0 | 25.002sim초/42.457wall초, 전진 x약0.83m, 회전약0.733rad, exit0. 마지막 0구간 끝1wall초에서 최대 몸체 각속도0.532459rad/s·팔 관절속도6.047884rad/s | 이동 재현, 정착 FAIL |
| A 최소 보완 `28b63c42` | 같은 명령·물리·정책·게인. 팔 목표 배열의 독립 복사만 적용 | 25.002sim초/40.130wall초, exit0. 마지막 끝1wall초 최대 몸체 각속도0.449874rad/s·팔 관절속도6.937535rad/s | 목표 drift 보완, 정착 FAIL |
| B 사전 검사 `7ad9856c` | 공개 Flat/WBC TorchScript CPU inference 및 배포 코드·설정 감사. 물리 실행 없음 | 두 actor 모두 입력[1,210], 실제 유한 출력[1,18]. 마지막6출력이 팔 PD 목표로 적용됨 | 현재 독립 팔 소유권 계약 미충족 |

A의 수치는 마지막 관측을 기준으로 직전1wall초 안의 실제 표본 최대값이다. 표본은 10물리 step마다 수집했다. 두 A 실행 모두 선언한 낙하/tilt 경계를 넘지 않았지만, 이것만으로 충돌 부재·수납 적합성·모든 관절 한계를 증명하지 않는다. actuator_force가 모델 cap 이내인 것은 확인했으나 원래 요청 ctrl과 실제 전달력을 동일시하지 않는다. 최종 인수 PASS는 없다.

정착 판별용 수치는 실행 전에 `probe_spec.json`에 고정했다: 선속도≤0.03m/s, 몸체 각속도≤0.05rad/s, 팔 관절속도≤0.1rad/s, 연속1wall초. 이는 R1 적합성 판별 기준이며 R2 최종 안전 사양 동결을 대신하지 않는다. 20ms simulation 간격 표본에서 이 기준을 만족하는 연속 구간은 두 실행 모두 0초였다. 표본 사이의 안전 보장은 수행하지 않았다. 실패 후 기준을 바꾸지 않았다.

증거:

- [원본 설정](../evidence/section_13_5_reuse/41f6d798-60a6-46b4-ad07-978435d030e3/probe_spec.json), [실행 요약](../evidence/section_13_5_reuse/41f6d798-60a6-46b4-ad07-978435d030e3/summary.json), [정착 메트릭](../evidence/section_13_5_reuse/41f6d798-60a6-46b4-ad07-978435d030e3/settling_metrics.json)
- [팔 목표 보완 요약](../evidence/section_13_5_reuse/28b63c42-e94a-47ee-bf22-451bd6d4ac91/summary.json), [정착 메트릭](../evidence/section_13_5_reuse/28b63c42-e94a-47ee-bf22-451bd6d4ac91/settling_metrics.json)
- [실제 MuJoCo 배열 공유 입증](../evidence/section_13_5_reuse/r0-20261102/arm_alias_proof.json)
- [B 실제 정책 출력·소유권 감사](../evidence/section_13_5_reuse/7ad9856c-cdfa-47c3-9cee-2884f68c79fb/ownership_audit.json)
- [양 후보 자산 해시 lock](../dependencies/section_13_5_reuse.lock.json)

## A: 재현된 것과 남은 문제

고정 원본은 [IIT-DLSLab d010212](https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab/tree/d010212c3f5c9e6e5542ada61cfdacc19b00f775)이다. profile은 `tested_policies/arm_moving_clock`, actor ONNX 293,655bytes, SHA256 `4ad160d24357827db896d1106f643cd89b9657e1ab97c013504e3e3e5af71a48`이다. 관련94파일/97,439,027bytes를 해시로 기록했다. 외부 checkout은 수정하지 않았고 실행 전후94파일 해시가 모두 일치했다.

선택 env.yaml은 concurrent estimator/RMA/IMU를 비활성화한다. 따라서 config.py가 가리키는 estimator/RMA 파일이 없는 것은 이 profile의 필수 자산 누락이 아니다. TorchScript 내보내기 코드를 zip으로 읽은 결과 normalizer는 Identity, actor는300→128→128→128→12 ELU다. ONNX runtime은 obs[1,300]→actions[1,12]를 확인했다. ONNX와 TorchScript의 수치 동등성은 확인하지 않았다.

모델 런타임은 nq27/nv26/nu19, physics2ms, policy50Hz다. 관측60차원×history5, action_scale0.5, clip6, filter alpha0.8이며 원본 관절 재배열을 사용했다. 팔 모델은 `piper_l`이고 정확한 하드웨어 변형·도달 범위·수납 형상은 미확정이다. 원본 home 자세를 검증된 수납 자세로 부르지 않는다.

원본 play_mujoco.py 82행의 팔 목표 대입은 live `mjData.qpos[19:25]` view였다. 실제 원본 AST 대입문과 실제 MuJoCo 데이터에서 관측을0→0.125로 바꾸면 목표도 바뀌었다. 새 helper `freeze_arm_reference()`는 `.copy()` 한 줄로 목표만 분리한다. 작은 시험에서 관측 변경에 목표가 바뀌는 RED를 본 뒤 두 검사 GREEN을 확인했다. 이는 drift 원인의 입증이며 고속 진동의 단독 원인을 입증한 것은 아니다. 보완 후 실제 정착 실패가 남았다.

원본은 policy tick에서 walking gains20/1.5를, 나머지 physics tick에서는 stand gains50/5를 선택한다. 원본 기본 MuJoCo 적분 설정과 명시 PD의 조합도 추가 조사 대상이다. 이번에는 gain·dt·integrator·질량·접촉을 바꾸지 않았고 원인을 단정하지 않았다. 같은 실패에 무제한 조정을 이어가지 않는다.

실제 XML cap은 hip/thigh±23.7, calf±45.43, 팔 앞3축±32/뒤3축±8, gripper±0.5다. 기존 자체 로봇20/30Nm를 이식하지 않았다. 이것을 새 플랫폼의 최종 안전 사양 확정으로 표시하지 않는다.

원본 ROS2 controller에는 /joy 입력이 있고 직접 cmd_vel 구독은 보이지 않는다. 자체 float64 timestamp/sequence_id 의미를 확인해야 한다. import 시 renice·autogroup 쓰기를 호출하므로 해당 ROS2 파일은 실행하지 않았다. R2를 선택할 경우 부작용을 제외한 실행 경계와 provenance가 필요하다.

## B: 사전 검사에서 멈춘 이유

고정 원본은 [LeggedManip Lab 4e12109](https://github.com/zzzJie-Robot/LeggedManip_Lab/tree/4e12109d1eccb1d9da2e4a35f189fabea3f13677)다. Flat policy는1,111,382bytes/SHA256 `72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8`, WBC policy는1,111,510bytes/SHA256 `c5f57c79bc01d8b8f2c0846163b149e3f53de39291770a1ccb230ef3be6b800e`다. 배포 관련53파일을 별도 해시로 기록했다.

`go2_piper.py`는 action[:,12:]를 팔 목표로 합쳐 전18축에 적용한다(286–289행). config/config_wbc 모두 num_actions18이다. 배포 경로에서 독립 팔 소유자로 전환하는 검증된 모드를 찾지 못했다. 공개 actor의 마지막6축을 버리거나 Ch13 명령으로 대체하면 검증 단위의 제어권·닫힌루프가 달라진다. 이를 단순 adapter로 간주하지 않았다. 이것은 모든 가능한 분리가 수학적으로 불가능하다는 주장이 아니다.

B는 A의 격리 환경에서 binary inference만 수행했다. README의 MuJoCo3.2.7 원본 환경 재현이나 기립·이동·정지·종료 PASS가 아니다. 학습 환경·드라이버를 설치하지 않았다. clone 직후 LFS checkout에서 source/assets의 USD10개가 modified로 표시됐다. 이 파일들은 MuJoCo 배포 해시 목록 밖이며 작업자가 수정·복구하지 않았다.

## 환경·보존·시간

작업 브랜치는 `feat/ch13-section-13-5-reuse`, 별도 경로는 `work/Pysical_AI_ROS2_reuse`다. base는 `bc31d370501bde5653dd6254ae6c18766d45aacc`다. 원래 브랜치의 실제 remote SHA와 일치함을 조회했고 새 원격 브랜치 이름은 비어 있었다. 앱 worktree 도구는 하위 저장소 sourceRoot를 허용하지 않아 sibling Git worktree로 격리했다.

원래 checkout의32개 dirty/untracked 항목은 그대로 보존했다. 기존 evidence·사용자13.4 교훈 문서·Ch01–12·sources를 수정하거나 stage하지 않았다. 기존 Task8은 재실행하지 않았다. 새 결과를 기존 PASS로 반영하지 않았다. commit/push는 수행하지 않았으며 R5 게시 단계도 아니다.

Ubuntu-24.04 WSL2/Python3.12.3/Jazzy, RAM약15GiB, 초기 available약14GiB/C:여유약85GiB를 확인했다. GPU RTX2060 Max-Q6GiB가 있으나 CPU inference만 사용했다. 새 전용 venv는 `/home/jinho/ch13_reuse_iit_d010212_venv`다. MuJoCo3.13.0/torch2.9.0+cpu/mink1.4.0 등 실제 버전은 [pip-freeze](../evidence/section_13_5_reuse/r0-20261102/pip-freeze.txt)에 기록했다. Isaac Lab/rsl-rl 전체 설치 없이 A 배포 import·실제 추론을 수행했다. 기존 vendor3.12.0/underlay는 변경하지 않았다.

설치 대기와 엔진 실행은 분리했다. A 실제 루프 실행시간은 원본42.457wall초, 보완40.130wall초다. 다운로드/설치/활성 분석시간의 전체 누계는 정확히 계측하지 않아 공수로 산출하지 않는다. /tmp 환경은 WSL 재시작 사이에 유지되지 않았고 Windows 공유 경로 설치는 파일I/O로 지연됐다. 자신의 정확한 설치 PID만 확인해 중단하고 새 Linux 전용 경로로 옮겼다. 실패·설치 로그를 보존했다. 기존 /etc/wsl.conf 경고는 관측만 했으며 수정하지 않았다.

시작 때 WSL 배포판은 모두 Stopped였다. A 실행 parent/worker(770/771,736/737), B 감사(750/751)는 후속 조회에서 없었다. 각 A 루프는0명령 구간을 마친 뒤 viewer.close를 호출하고 exit0이었다. close 직후 viewer daemon thread가 남은 관측은 보존했다. 명시 join 검증·장기 잔여 감시는 하지 않았으므로 U6 전체 PASS가 아니다. 원본 init-only 시험은 성공 출력을 남겼으나 exit1이어서 정상 종료 성공으로 계산하지 않는다.

root 라이선스는 A BSD-3-Clause/B Apache-2.0다. 모델·mesh·가중치의 제3자 provenance/재배포 범위는 미해결이다. root 라이선스만으로 모든 자산 권리 검토가 끝났다고 표시하지 않는다. 로봇 자산·가중치를 새 저장소 변경으로 복사하지 않았다.

## 최초 조사 당시 판단과 후속 선택

인계안의 “두 후보가 모두 탈락하면 … 증거·대안·필요한 결정을 제시한다”에 따라 R2를 열지 않는다. 현재 다음 두 경로 중 범위 결정이 필요하다.

1. **A의 정착 원인을 별도 제한 조사한다.** 원본 gain 선택·PD와 적분의 관계를 작은 물리/수치 시험으로 분리하고 근거 있는 최소 배포 보완 가능성을 판단한다. 새 보행기·재학습·무제한 gain 탐색은 제외한다. 성공은 보장되지 않는다.
2. **B의 전신정책 팔 소유권을 허용하도록 명세를 바꾼다.** EE 목표 interface와 별도 팔 단계 인계 방식을 다시 설계하고, 그 변경을 승인받은 뒤 B 원본 물리를 재현한다. 기존의 독립 Piper/MoveIt 연결을 그대로 약속할 수 없다.

새 후보를 더 늘리거나 자체 crawl 개발로 돌아가려면 별도 범위 결정이 필요하다. 현재 플랫폼 확정·ROS2 어댑터·Nav2·비전 접근·최종 인수는 모두 미완료다.

## 최종 기록 검증

팔 목표 보완의 독립2검사는 최종 실행에서2/2 통과했다. A94+B53=147개 자산의 bytes/SHA256 재대조에서 불일치0개였다. 실제 표본2500개·두 실행의 단조 증가 시각·마지막0명령·실패 메트릭 보존을 확인했다. 대표 실패/소유권 감사 증거24파일 약5.36MB를 manifest로 pin했다. 기존 ROS 패키지 코드는 변경하지 않아 기존 Ch13 전체 엔진 회귀는 실행하지 않았다.

사용자 지정 단일 작업자 원칙에 따라 자체 검토했다. 별도 검토자의 검토는 없다. 실행 종료와 실측 정착을 분리했고, B의 inference를 물리 재현으로 표시하지 않았으며, 신규 R1 probe 기준을 최종 인수 조건으로 표시하지 않았다. 전체 계획 완료나 R5 게시를 선언하지 않는다.
