# Ch14 출고 마감 교차 QA — 2026-11-26
상태: PARTIAL_STATIC_QA / G09 OWNER_L3_SCOPED_PASS / PUBLIC_RELEASE_HOLD.

## 근거와 범위
원본 S1 템플릿_ch14_260719_raw_review_code.docx (75쪽, 추출 텍스트 3338줄), S2 Ch14_수정원고_교체부분_20261126(1).docx (26쪽, 추출 텍스트 1713줄), CH14_DEVELOPMENT_SPEC_KO(1).md v1.0 (419줄)을 Library에서 전 범위 읽음. S3 BOOK_CODE_REVIEW_6_HANDOVER_20261126_KO.md는 정확한 제목 검색에서 미확보; 현 저장소 증거로 대체할 수 있는 기술 범위만 참조. 원고 원문은 공개 Git에 넣지 않음. S1+S2의 최종 편집 합성본/레이아웃/그림 QA는 미검증. 검토 대상 branch HEAD f4c548b92cd95faca1e16cb45036ffb1246dd833, 고정 실행 PIN 6c458e345236b124c9aa60f65788f35cfed74e62. 실제 18 canonical entry paths 확인(14 Python paths + 1 launch + 3 Docker, 14-5 제외), 9 guides 존재 확인, 기존 G09 source audit 및 CI/owner 증거 재사용. 전수 수동 명령 재실행 아님.

| 절 | 정적 교차 QA | 출판 경계 |
|---|---|---|
| 14.1 | 14-1 CPU benchmark, S2 seed/warmup/forward 및 latency/throughput 구분 | GPU 및 보드 실측 아님; guide historical candidate wording에 최신 증거 안내 |
| 14.2 | 14-2/3/4 실제 export/parity, UNTRAINED_DEMO 분리 | fixed absolute misses n14/16 s15/16 유지, zero new GT miss만 승인 제안 |
| 14.3 | 14-6 ORT/OV 실제 CPU 800 samples; 14-5 absent | S2 선택 TensorRT 예제의 구현/시험 없음 명시; GPU N/A와 NOT_RUN 구분 |
| 14.4 | 14-7/8 latest slot, RGB-D+TF, QoS actual selected evidence | ROS OV 경로 미검증; alignment != timestamp sync; G09 headless selected path만 L3 |
| 14.5 | 14-9/10/11/12 parameters/swap/launch | ordered shutdown 성공만; 일반 동시 Ctrl+C 및 arbitrary launch not proven |
| 14.6 | 14-13 profiler, A/B/C 60s actual; D optional | local ROS age caveat, 예시표 실제값 구분; 30min/thermal/20% headroom 주장 제외 |
| 14.7 | 14-14/15/16 CPU Dockerfile/run/compose, same image, actual DDS replay | native Gazebo whole-system 아님; WSL2 G06 compose 자체 미검수 |
| 14.8 | 14-17/18/19 48→12, exact original smoke bundle; shadow0 command, two actual engines | 보행 품질 NOT_ACCEPTED; Gazebo negative cases 미검증; 20ms 정책 기한은 hard RT 보증 아님 |
| 14.9 | four-path owner actual L3 scoped PASS, 82/82, exit0 | 자동화 14.4/14.8 enabled/14.9 한정, 수동 가이드 6절; actual hardware excluded |

S2는 원본의 필수 GPU/실물 보드/발열/토크0·고정 성능 주장을 교체 대상으로 명시한다. 최종 합성본에서 실제 교체 적용 확인 필요. A 인지와 B 정책 제어는 독립 실습. 인지-보행-조작 통합 제품 보장 금지. guide에 남은 역사적 시점의 NOT_RUN/candidate 표기는 아래 current index 우선(기존 증거 삭제 금지). 14.8 exact artifact 보관 확인 후 신규 독자에게 안내; 30일 보존 만료시 BLOCKED. 신규 실행/학습/코드 변경 없음.

## 공유 CI
RED run45825072895 job139927013907; missing vision_basics caused by sparse path omitted. GREEN independent PR #207 run45828900636 job139940138580 14/14 incl 6 Ch07 tests, guide inventory and matrix success; two manual-only pilots skipped. Merge 4255f810524c177db724548bb74d16b20fda64e5; only two sparse paths plus educational CI report, no Ch07 code change. Ch07 7.7 BLOCKED and existing failures retained. Ch14 head check to be verified after branch synchronization.

## Final approval gates
1. G01 spec §7.1 absolute failure remains; authorize limited educational parity scope without retroactive PASS, or require actual absolute acceptance.
2. Author/publisher rights decision required: official upstream license sources and outstanding attribution/license approvals in G09_ASSET_RELEASE_REGISTER_KO.md. No permission inferred from education or download-only. Original binary/image files not republished.
3. Author/publisher confirm ordered-only shutdown, no GUI/native/GPU/real hardware required, SMOKE_ONLY, manual vs automated paths. No approval for hardware safety/locomotion/general exit.
4. Recover S3 and final composed manuscript; confirm 19 code labels, 14-5 optional absent, actual metric tables and checklist, figures and exercise mapping. User retains unpublished document; no original text in Git.
5. Verify Ch14 PR document-preflight green and exact head; then only when above approvals satisfied merge PR #206. Existing owner acceptance independent, no rerun.
