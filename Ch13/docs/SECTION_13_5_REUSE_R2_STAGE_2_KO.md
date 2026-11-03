# R2 단계 2 — 명령 램프 시간축 확정

작성일: 2026-11-02 KST. 결과:39개 검사 PASS/11.201s, 격리2패키지 빌드 PASS, 설치10항목·원본94파일hash PASS. [검사](../evidence/section_13_5_reuse/r2_stage2_20261102/tests.log), [설치 감사](../evidence/section_13_5_reuse/r2_stage2_20261102/install_audit.json).

## 변경과 근거

기존 램프는wall시간기준이었다. 느린simulation에서는같은sim1초당명령변화가커져사양해석이불명확했다. 새검사는wall0.20초에sim0.02초가진행된경우vx변화0.006m/s·wz변화0.010rad/s, sim진행없는반복출력에는증가0을요구했다. 기존코드에서두검사가RED였다. [RED](../evidence/section_13_5_reuse/r2_stage2_20261102/slew_red.log).

Guard는arm시simclock을기록하고각출력의sim시간차로slew를계산한다. vx0.30(m/s)/sim초·wz0.50(rad/s)/sim초이며clock이멈추면증가하지않는다. 한출력의dt는최대0.10sim초로제한한다. wall0.30초입력/시계만료와고장시즉시zero는그대로다. 이는명령램프규약으로실제몸체가속도상한을증명하지않는다. 플랫폼설정에도시간축과의미를명시했다.

## 검사 중 발견한 fixture 문제

첫전체39검사에서미래base주입이joints도미래로바꿔검사1개가실패했다. 원인은Python ROS메시지의공유Time객체참조다. 미래base에별도Time객체를생성하도록고쳐정확히한입력만고장나게했다. [실패보존](../evidence/section_13_5_reuse/r2_stage2_20261102/future_fixture_failure.log). 생산guard기준이나허용치를늘리지않았다. 이후전체39개GREEN이며설치byte감사도완료했다.

## 다음 경계

원본물리/모델/정책/힘한계는변경하지않았다. 다음단계는설치된launch경로의실제전진·회전·정지·팔독립성·입력손실latch·정상회수다. R2전체완료는그결과뒤판정한다. GitHubpush는구체적목적지승인질문이대기중이므로이단계도먼저로컬commit한다.
