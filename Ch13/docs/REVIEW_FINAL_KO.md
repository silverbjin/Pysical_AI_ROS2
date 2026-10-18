# 13.1 최종 독립 리뷰와 수정 결과

리뷰 범위: 승인 계획 `71b3c44` 이후 `3c3b1d7`까지. 구현은 원 세션에서 직접 수행했고, 전체 브랜치에 대한 fresh-context 읽기 전용 리뷰를 한 번 수행했다. 리뷰어는 checkout/index/HEAD를 변경하지 않았다. 초기 판정은 Critical 없음, Important 2개, Minor 2개, With fixes였다. 리뷰어 환경에서는 WSL 접근이 거부돼 엔진을 독립 재실행하지 못했고, 저장 증거와 실제 순수 코어 재현으로 판단했다. 엔진 실행 증거는 구현 세션이 직접 생성했다.

## 수정한 항목

1. **Important — clock 검증 우회**: 초기 resolve 전의 임의 future 명령이 safe target/owner를 오염시키거나, 정지한 clock에서 다른 목표가 적용될 수 있었다. 미초기화 clock 명령은 거부하고, 유효 입력도 pending에 보관한 뒤 strictly advancing resolve에서만 적용한다. 만료된 pending은 폐기하고, 역행 epoch는 재시작을 요구한다. startup 미래·오래된 명령, 소유자 오염 방지, clock 정지/재개, pending 만료의 RED→GREEN을 기록했다. 기존 테스트도 실제 clock 전진을 명시하도록 수정했다.
2. **Important — 예외 후 false PASS**: finish 예외가 error 필드만 추가해도 일부 true 검사만으로 PASS가 될 수 있었다. probe_completed, error 부재, backend별 필수 검사 집합 전체를 요구하도록 수정했다. 예외·미완료·검사 누락 회귀가 RED→GREEN이다. 이전에 저장된 정상 실행이 이 경로를 탔다고 주장하는 지적은 아니다.
3. **Minor 제안 → Important로 재분류 — 출처 해시 정확성**: Ch11/Ch08 3개 해시는 CRLF checkout 바이트인데 기준 Git blob 해시로 표시되어 있었다. 실제 `git show 1451f54:<path> | sha256sum`의 해시로 바로잡았다. Ch12 2개는 원래부터 blob과 일치했다. 사람용 출처 문서 수정이므로 의미 없는 텍스트 존재 테스트를 추가하지 않았다.
4. **Minor 제안 → Important로 재분류 — 재현 가능한 렌더 설치**: 실제 이미지 검증에 필요한 Pillow가 선언되지 않았다. 설치 metadata에 Pillow가 없음을 먼저 실패시킨 뒤 의존성을 추가하고 재설치 metadata와 실제 이미지 생성을 검사했다. 환경에 우연히 설치되어 있다는 가정은 제거했다.

수정 직후 전체 pytest는 63개 통과했다. 최종 native 엔진 재실행 결과와 이후 코드 SHA는 evidence/verification_summary.json을 기준으로 한다. 두 번째 리뷰는 요청하지 않고, 재현 테스트와 전체·실제 엔진 재검증으로 수정 효과를 판정한다. 보류한 Minor는 없다.

## 리뷰에서 판단을 유보한 범위에 대한 결정

- MoveIt/통합 ros2_control/안정 PPO/운반/실제 로봇 준비성: 승인 설계의 제외 범위를 유지한다. 이 기능이 필요하면 별도 구현·검증이 필요하며 현재 코드를 그 대체로 사용하면 안 된다.
- Gazebo 파지 성공·실제 PPO 추론: 실패/미검증 상태를 유지한다. overall PARTIAL을 전체 성공으로 바꾸지 않는다. 학생이 Gazebo에서 성공 파지나 학습 보행을 기대할 경우 아직 그 요구를 충족하지 못한다.
- 독립 엔진 재현: 리뷰어의 WSL 제약을 명시한다. 구현 세션의 원시 로그·종료·물리 수치에 의존하므로 별도 환경의 제3자 재현까지 입증한 것은 아니다.

## 구현 중 내린 판단과 비용

| 판단 | 근거 | 잘못됐을 때의 비용/검증 한계 |
|---|---|---|
| 잘못된 하한 시험 값을 0→4로 수정 | 하한 0은 유효하므로 원래 fixture가 오류 | 실행 동작 변화 없음; 실제 invalid-limit 검증은 유지 |
| 이전 leg origin의 1.2/-2.4 회전 제거 | 명시적 nominal과 중복 적용 방지 | 기존 정책의 물리 동등성을 보장하지 않음 |
| 초기 z=.468m 및 몸통–허벅지 구조 4쌍 제외 | 실제 초기 관통·충격 재현 | 해당 4쌍의 충돌 검사는 제외됨; 다른 self-contact는 유지 |
| sole graph endpoint로 command owner 확인 | 설치 Jazzy callback에 GID 없음 | discovery race 시 보수적 거부; TF 패킷별 source attribution 불가 |
| build13_1/install13_1/log13_1 별도 사용 | 다른 절의 ignored 산출물을 보존 | 디스크 사용 증가 |
| yaw와 roll/pitch tilt 분리 | heading 회전은 전도가 아님 | XY 위치 유지/방향 유지 성능은 별도 미검증 |
| source hash에서 venv·생성물 제외 | 소스 증거에 의존성/빌드 산출물 혼입 방지 | 설치 의존 파일 자체 hash는 없고 버전/wheel 검증으로 보완 |
| Git 비교에 명령별 CRLF 정규화 사용 | Windows/WSL checkout 해석 차이 | 줄바꿈만 바뀐 변경은 의도적으로 무시; 내용 변경은 테스트로 검출 |

Ch08/Ch11의 라이선스 TODO, KDL 루트 관성 경고, Gazebo 파지 실패는 남아 있으며 기능 성공 주장으로 덮지 않는다.
