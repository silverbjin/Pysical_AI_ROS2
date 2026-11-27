# 15.1 실습 — 미션 계약과 독립 월드
## 목표
프로파일, 상태, 시나리오, 완료 조건을 구현 전에 명확히 한다. 물리 파지 성공과 논리 성공을 구분한다.
## 실행
저장소의 Ch15 디렉터리에서:
```bash
python3 -m unittest discover -s tests -p 'test_scenarios.py' -v
python3 -m unittest discover -s tests -p 'test_world_contract.py' -v
```
현재 Python 표준 라이브러리 정적 시험이며 ROS 설치 없이 실행할 수 있다. Gazebo 검증은 G04 실제 센서 시험과 별도로 수행한다.
## 관찰
mission_context.py에서 mark_ready 전 advance를 거절하며 terminal 이후 같은 ID를 재사용하지 않는다. B의 금지 단계와 C의 실행 거부를 확인한다. config/mission_requirements.yaml 및 scenarios/*.yaml에서 trigger, witness, retry budget을 읽는다.
월드는 고정된 탁자 상면 0.20m에 큐브 중심 z=0.225m, 관성 0.0000416667 kg m². 카메라 5Hz는 설계 설정이지 실측 주기가 아니다. 원래 Ch13 world와 섞지 않는다.
## 과제
정상 및 F01에서 테스트 PASS와 미션 결과의 차이를 설명하고, 큐브 크기 변경 시 관성·접촉 초기 조건을 계산한다. 원본 월드를 수정하여 검수를 우회하지 않는다.
## 제출
실제 unittest 출력, 프로파일 비교표, 물리 성공을 주장하지 않는 보고서. G04 T11 actual RGB-D PASS; G01 정적 시험과 구분.

## G09 공통 실행 경로
Ch15 루트, `CH15_SOURCE_SHA`를 실제 고정 HEAD로 설정하고 `bash scripts/run_lab.sh 15.1 --profile mock` 실행. 상세 선행 환경과 evidence archive는 [15.9](LAB_15_9_GUIDE_KO.md) 참조. 문서 조회와 실제 실행을 구분한다.
