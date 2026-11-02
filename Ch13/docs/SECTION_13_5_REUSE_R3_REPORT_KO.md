# R3 Nav2 연결 완료 보고서

작성일: 2026-11-02 KST. **R3 개발 검증 완료. R4 비전/R5 동결 인수는 다음 단계다.**

설치된Nav2 1.3.13을 실제MuJoCo에 연결했다. Navfn→RegulatedPurePursuit→Nav2 velocity_smoother→원본stamp/receipt/GID를보존하는navigation boundary→기존gateway→upstream정책 경로다. side-step/reverse/Spin/BackUp recovery를기본활성화하지않는다. localization은명시적engine-ground-truth profile이며AMCL/SLAM성공주장이아니다.

## 실제 결과

terminal4=SUCCEEDED,5=CANCELED,6=ABORTED다. blocked와cancel의목표오차는도착판정대상이아니다.

| 시나리오 | terminal | 실제 위치 오차 m | terminal→정착 wall초 | 증거 UUID |
|---|---:|---:|---:|---|
| free | 4 | 0.0385 | 1.464 | 048b8e4e-8efa-4414-aa43-82f4c69db1eb |
| obstacle | 4 | 0.0426 | 1.608 | 05c9c5ca-1b7d-47a2-a380-cdc390a092e5 |
| blocked | 6 | 1.1989 | 0.000 | 535013f5-7288-4b71-afe7-b29aaed0a164 |
| cancel | 5 | 2.1837 | 1.866 | 3824b7f0-cda8-46ea-b37f-907fb82bc461 |

각실행에서NavigateToPose 실제terminal과500Hz원본의edu_stop_v2 정착을독립판별했고정상엔진종료·RX/upstreamjoin·10개자식clean exit·부모회수·flock해제를확인했다. 장애물case는실제root의측면우회가0.45m를넘는것도검사했다. cancelACK와terminalCANCELED를분리했다. 원본94자산hash 및설치20항목을실행전대조했다.

## RED→GREEN 보완

- 실제58검사에서적분후qpos를수정하고FK를갱신하지않으면ray원점이전시각에남는것을RED확인했다. ray마다mj_kinematics를호출해header와같은실제상태를썼다.
- 외부graph조회가physics상태잠금을막는경합을별도RED검사로확인했다. query/publish/log를잠금밖으로분리했다. 이후자유공간실행은목표오차0.0385m/0.0221rad로통과했다. 계측은시작전DISARMED시일부ROS publish>0.3wall초를기록했으며허용age를늘리지않았다.
- idle생성zero→controller원본stamp가잠시역전되는경계를RED확인했다. 원본명령을now로바꾸지않고high-water stamp에서0을유지하며양쪽원본시각이따라온뒤전달한다.
- 초기취소case는TF/clock의서로다른DDS도착순서로시작전future fault였다. 최대50wallms의유계보류만추가했다. 원본stamp·최초receipt는바꾸지않고실제clock이기존25simms범위까지따라온후에만admit한다. 미도달/중복receipt갱신/복수edge소유자는거절한다. 기존R2 guard의future/expiry규칙은바꾸지않았다.
- 현재전체 **62/62 PASS,19.608초**. 실제DDS의TF미래만료도포함한다. [최종 부품 로그](../evidence/section_13_5_reuse/r3_preflight/tests_62.log).

## 보존과 다음 단계

이개발시험들은수정별source/설치hash가다르다. **R5는최종source/config를동결한뒤필수case를새UUID에서전수실행한다.** 이번개발PASS를자동으로최종고정본PASS로전이하지않는다. 이전실패3d4656a4/0552b293/772c95f5/b129a641와관련RED로그를보존했다.

R3초기wrapper가tests_57.log를58/59재검사로덮었으므로그경로를원래57검사의fresh증명으로사용하지않는다.56전체원본tests.log와59사본tests_59.log,실패별고유로그,현재62전체로그를분리보존했다. 이제wrapper는매실행고유로그경로를받는다.

카메라기능코드는opt-in으로추가됐으나이번R3물리검증은scan/Nav2만이다. RGB-D/과거TF/관측/작업영역은R4에서별도검증한다. footprint는R2실측70개collision AABB+0.04m여유로산출했고임의팔동작envelope로표현하지않는다.

단일작업자자체검토. 기존파일/실패보존,upstream원본무수정,새보행기·학습·main병합·PR없음. [계획](SECTION_13_5_REUSE_R3_R5_PLAN_KO.md).
