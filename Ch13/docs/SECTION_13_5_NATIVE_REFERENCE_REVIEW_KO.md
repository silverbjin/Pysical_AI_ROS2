# 13.5 native 검증 보완 자체 리뷰·보존 안내

## 범위와 판정

기준 `abcc057` 이후의 Gazebo 직접 PID/라이브러리·힘 메타데이터·순간 IMU 기준·
carry 최초 실패 결합·관찰기 송신 차단 변경을 단일 작업자가 자체 리뷰했다.
사용자 지시에 따라 서브에이전트/독립 리뷰어를 사용하지 않았다. 독립 검토를 받은
것과 동등하다고 주장하지 않는다. **전체13.5 완료/merge/push 판정은 NO**다.

좋았던 점: 별도 latest-TF/now retag 없이 정확한 촬영으로 결합했고, body reference는
gyro가 아닌 native canonical link의 world velocity에서 독립 계산했다. 평균 odometry
가설의 반례를 발견한 뒤 원본 FAIL을 보존하고 가설을 교정했다. 엔진 stop ACK와
실제 native PID 종료를 구분했으며 강제 정리 없이 수집을 마쳤다.

리뷰 중 수정: native 기준 배열이 비었을 때 동기 body 캐시로 돌아가던 분기를
`task8-missing-instant-reference-red.log`2실패/9.21초로 재현한 뒤 제거했다.
관련62시험/23.87초 통과. 실제 f5eff9bc 입력의 엄격 재평가에서도 IMU410고유 capture/
누락0/최대0.0000342422rad/s를 유지했고 기준 삭제 음성 사례는 거부했다.
이 재평가는 **새 엔진 실행이 아니다**. 마지막 변경은 순수 판정기와 fixture뿐이며
엔진·명령·native 라이브러리는 f5eff9bc와 같다.

최신 엄격 판정기 전체 navigation pytest는 **343passed/315.05초**다.
native 센서 패키지는 colcon test-result **28건/실패0** 및8패키지 설치 감사 통과다.
28에는 CTest wrapper가 포함되며28개의 독립 물리 실험이라는 뜻은 아니다.
기존13.3/13.4 전체 회귀 또는 양 엔진G1/G2 완료와 구분한다.
원본 실패 로그의 pytest diff trailing space는 증거 보존을 위해 그대로 뒀고,
코드·문서의 diff whitespace 검사는 로그를 제외해 별도로 확인한다.

## 미해결 중요 사항

1. `gait.py`의 SHIFT 실제 구동에서 carry 팔속도 한계 초과: f5eff9bc에서
   arm2=0.0261044473,arm3=0.023647733rad/s. 허용0.02는 유지한다. 단일 발 lift/G1
   완료 전에 멈췄으므로 G2/Nav2로 승격하지 않는다.
2. 조건부 P-law 역산44개 packet의 팔 목표 오차는 약1.36e-20rad, 포화0이었다.
   따라서 샘플된 구간의 수납 목표 소유권 변경보다 몸체 운동의 동역학적 결합을
   우선 조사한다. 다리 역산 목표의20ms 차분 최대0.001508rad와 odometry 기반
   world 속도 차분 가속도0.186899m/s²를 관측했으나, **원생 모든 명령/순간 IMU
   가속도의 증명 또는 단독 근인 확정은 아니다**.
3. `carry_profile.py:validate_profile`은 기존 role dictionary를 기대하지만 실제
   EvidenceRun은 artifact list를 만든다. current source/install/실행 모드 binding도
   완료해야 한다. 임의 PASS 선언을 허용하는 임시 호환 처리로 해결하지 않는다.
4. 동결본 Gazebo G1 및 간헐 조건3회 연속 성공, G2, 실제 Nav2,13.3/13.4 최종
   전체 회귀가 남았다. 과거 MuJoCo3성공은 보존 체크포인트의 결과이며 최신 전체
   소스에서 다시3회 성공했다고 쓰지 않는다.

검토에서 제외한 전체 요구: 없음. 위 후속 과제를 이번 작은 수정의 성공으로
대체하지 않는다. PPO/MoveIt/파지/다음 절 확장은 이번 요청 범위 밖이다.

## 재시작에 필요한 정확한 보존본

`Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/`
안의 `task8-gazebo-instantaneous-f5eff9bc.zip`:

- 크기14,278,979bytes, SHA256
  `8afa141de8e1ef8a4fe0e5fc813913eaed38fa5cdc37366c3b13ebc97177c17c`.
- `sources/`는 실제 f5eff9bc 실행71소스의 정확한 bytes다. 기준 Git SHA와 dirty scope는
  원본 source_manifest에 있다. 기존 소스/사용자 파일에 바로 덮어쓰지 않는다.
- `evidence/`는 원본 FAIL·실제 명령·출처·설치 manifest·frames·native controls·종료
  로그와 prepared scene이다. `verification/`에는 해당 시점 시험 로그가 있다.
- sidecar JSON의 member별 size/SHA를 모두 재독 대조했고 원본을 지우지 않았다.
  보존 후의 strict 판정 변경은 현재 Git 소스와 별도
  `task8-strict-native-reference-f5eff9bc.json`으로 구분한다.
- 별도 빈 폴더에만 압축을 풀고 sidecar와 대조한다. source 복원은 `abcc057`
  체크아웃의 별도 복사본에 필요 bytes를 적용하는 방식으로 검토한다. 원래 result의
  절대 경로/실행 시각을 현재 실행으로 위장하거나 원본 FAIL을 PASS로 바꾸지 않는다.

기존 과거 실패 원본과 native Linux 원본은 별도로 남아 있다. 이 ZIP은 이번 한 실행의
보존본이며 과거 전체 증거의 아카이빙이 완료됐다는 주장이 아니다.
