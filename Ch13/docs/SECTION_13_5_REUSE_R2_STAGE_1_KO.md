# R2 단계 1 — 실제 DDS 고장·재무장과 시작/종료 경합

작성일: 2026-11-02 KST. 결과: 작은 검사36/36 PASS, 격리된2패키지 빌드 PASS. [전체 검사](../evidence/section_13_5_reuse/r2_stage1_20261102/tests.log).

## 추가 검증

실제 로컬 DDS에서 clock 중복발행 중 정지, base/joints 각각 관측 손실, base 미래stamp, 원publisher 제거 후 새GID 교체, relay 소멸, 고장 뒤 reset→fresh zero→명시arm을 확인했다. 모든 고장에 zero와 FAULT latch를 확인했다. publisher 교체는 단순graph추측이 아닌 실제새표본GID에 `OWNER_REPLACED:raw`가 발생했고 최초GID가 보존됐다. 기존 입력복귀 자동재개금지, raw손실, 중복publisher, clockrollback 검사도 유지한다.

## 시작/종료 경합

기준본 재검사에서 SIGTERM exit1이 발생했다. stderr수집을 추가한 제한8회 진단에서는 재현되지 않았다. 따라서 원래 간헐 실패의 유일원인을 확정하지 않는다. 별도 결정적검사는 arm service 생성 직후 실제SIGTERM을 보내 context 종료를 기다렸다. 다음reset service 생성이 `rcl context is invalid`로 실패했다. [RED](../evidence/section_13_5_reuse/r2_stage1_20261102/lifecycle_red.log).

기존main은 node생성이 try밖이라 이 시작경계를 처리하지 못했다. node생성을 try안으로 옮기고 종료된context의RCLError만 정상종료로 처리했다. 살아있는context의오류는 다시raise한다. 실제하위process 회귀 및 전체36검사가GREEN이다. 원간헐실패를같은원인으로단정하지않고 최종설치launch실행에서정상회수를추가확인한다.

## 범위와 게시 상태

MuJoCo물리는 이단계에서 실행하지 않았다. DDS부품성공을 실제엔진의각고장물리검증으로전이하지않는다. 원본함수/정책/관절힘한계는변경하지않았다. R2는계속진행중이며 다음은시간축정렬과설치launch실행이다.

단계0 push는 자동승인검토가 구체적GitHub목적지/업로드범위확인부족으로거절했다. 사용자에게기존origin과범위를명시해승인을요청했으며답변전재시도하지않는다. 이단계는보고서와검증결과를로컬commit하며승인후단계commit모두같은새브랜치로게시한다.

해시 보존 속성의 우선순위 점검에서 Ch13/.gitattributes의text=auto가root설정을덮는것을확인했다. 새재사용경로에만Ch13수준에서-text/!eol을설정하고색인을실제바이트로재등록한다. 최종Gitblob해시를workingbyte/lock과대조하며, 기존장개행계약은변경하지않는다.
