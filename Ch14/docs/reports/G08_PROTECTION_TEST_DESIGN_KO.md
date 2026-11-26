# G08 보호 계약 실제 시험 설계

실제 MuJoCo bridge → DDS relay → 설치된 G08 controller. 정상 8초 benchmark 재실행이 아니라 음성 검수만 수행한다. 정상 IMU 원본을 전달하다 프레임만 의도적으로 잘못 주입; hold target의 독립 DDS 대조. 별도 publisher는 제어 메시지를 발행하지 않고 graph conflict 검증에만 사용. conflict 중 명령 증가 0, rearm 거절, 제거 후 복구. 실제 rearm 후 arming → active. 실제 ORT 추론 호출 뒤 단 한 번 35ms 추가하는 시험 전용 harness; production controller/정책 수정 없음. 20ms 초과 판정에서 새 명령 0, 다음 정상 회복 확인. disabled mode는 graph publisher 0. 모두 candidate, 실제 CI 결과 및 원본 증거 검토 전 PASS 금지. 물리 로봇 및 범용 safety claim 금지. Gazebo fault coverage 별도 표기.
