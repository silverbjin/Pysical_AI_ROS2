# 13.7 단일 작업자 자체 검토

2026-11-04 KST. 사용자 지시에 따라 별도 에이전트를 쓰지 않고 구현과 분리된 검토 관점으로 설계·공식 upstream·diff·시험을 대조했다. 독립 검토보다 약하다. 실제 선택4사례 PASS와 최종243개 부품 시험·설치 감사를 대조했다.

## 확인한 경계

- BT update/terminate는 직접 ROS 결과를 기다리지 않는다. robot node의 spin 소유자는 한 worker다.
- Nav goal 수락, cancel ACK, 실제 terminal, 실제 정착, 자식 회수는 다른 증거다.
- Blackboard는 원본 관측과 session을 보관하고 Pick에서 live lease를 재확인한다.
- 정상/abort terminal은 latch이며 다음 tick에 새 mission을 시작하지 않는다.
- 기본 py_trees_ros snapshot=false를 명시 활성화하고 tree.tick()의 방문자·후처리를 유지한다.
- 기존6패키지와 새패키지를 별도 build에 설치하고 기존94자산·모델 정책을 감사한다.
- mock 운반/기립/충전은 실제 엔드포인트와 연결하지 않는다.

## 검토에서 드러난 보완 대상

실제 정상 인수 중 소스 변경은 하지 않고 아래를 검토 기록에 남겼다. 인수 종료 후 다음 수정을 RED→GREEN과 영향 범위에 맞춰 확인했다.

1. 파지 중 BT 취소의 HOLD/POST_SETTLE과 실제 취소 marker를 파지 증거에 함께 남겨야 기존 held-cancel 판정기를 정확히 재사용할 수 있다.
2. pending send/result가 있는 action client는 caller의 finally에서 먼저 파괴하지 않고 소유 추적기가 취소·terminal 회수를 마친 뒤 파괴해야 한다.
3. 전체 mission node의 예외 경로에서도 worker cancel/join을 먼저 처리하고 ROS context를 회수해야 한다.
4. Blackboard 관측에 소유 Nav goal ID도 보관하고 동일 session·goal 연계 확인을 명시한다.

1~3은 실패 재현 시험으로 확인한 뒤 보완했다. DeferredClients는 늦은 수락→취소→실제 terminal 이후에만 client를 파괴하며 미회수 시 실패로 남긴다. worker 예외 회수 시험과 HOLD/POST_SETTLE 기록 시험을 추가했고 실제 파지 후 BT 취소1회로 힘 유지·낙하0mm·2.18sim초·접촉100%·정상 join을 확인했다.4는 실제 소유 Nav goal handle의 UUID를 전달해 원본 관측과 함께 보관한다.

최종 자료 검토에서는 verdict 덮어쓰기와 archive manifest의 복원 도구 계약을 추가로 점검했다. 각각 기존 PASS가 FAIL로 덮이는 재현, archive 이름 필드 누락으로 복원이 실패하는 재현을 확인한 뒤 수정했다. 새 출력 이름/독점 생성과 실제 hash 복원 시험이 통과했고 전체243개 시험이 GREEN이다. 이는 제어 변경이 없어 저장 증거를 새 파일명으로 재판정했으며 engine matrix는 반복하지 않았다.

미해결 Critical/Important 항목은 없다. 검증한 것은 각 선택 사례1회와 명시한 모의/부품 범위다. 독립 검토·반복 강건성·실기는 주장하지 않는다. 최종 diff에서 기존 장·13.6 freeze/FAIL·사용자 파일 변경은 없음을 확인한다.

## 범위 판단

실제 운반·기립·충전, 일반6D/YOLO 인식·실기·새 WBC/학습은 사용자가 선택한 실제 범위 밖이다. 모의 성공을 물리 성공으로 합산하지 않는다. 기존13.6 전체16 matrix 반복은 요청하지 않으며 공통 hook과 취소 경계 영향 사례만 고른다. 정상/실패 증거와 과거 freeze는 삭제하지 않는다.
