# G09 출판용 교차 QA 및 §14.9 교체 체크리스트
원본 명세 v1.0 §8~12와 원본 S1 §14.9.3 (68–69쪽) 확인. S2는 G00에서 19 코드 직접 대조된 기록 사용; 이번에 S2/S3 전문 직접 확보/대조하지 못했다. 원고 원본/개정 파일 자체를 공개 Git에 커밋하지 않는다. 이 문서는 출판 수정 제안이며 원고 실제 개정/승인 아님.

| 기존 체크 항목 | CPU simulation-only 개정 문구 | 근거/판정 |
|---|---|---|
| PT → TensorRT | PT→ONNX, ORT CPU checker/parity; optional OV | G01 conversion scoped; absolute required n14/16 s15/16 FAIL. G02 OV CPU actual PASS |
| FP16/trtexec 20ms | CPU FP32의 P50/P95/max와 target period를 구분; GPU 선택 | TRT/FP16 NOT_RUN; INT8 theory; G08 RL 20ms budget separate, YOLO 20ms hard RT claim 없음 |
| Threaded AI / latest queue | latest slot 1, pending overwrite / DDS loss / heartbeat separately | G03 123 overwrite; G05 heartbeat misses 16/7/0 scoped |
| Header/time sync | source capture stamp preserved, depth aligned, valid TF + skew/freshness | G03 actual 13 semantic+3D frames; local clock age caveat |
| QoS | publisher/subscriber compatibility 실제 DDS; reliable fault injection separately | G03 phases not all one execution |
| Runtime parameters | atomic setting and model swap terminal request generation, rollback | G04 17 requests; 7 success/10 rejections |
| CPU headroom 20%, thermal30min | 60s scoped measurement CPU/RSS/RTF, no universal 20% headroom or 30min claim | G05 60s each A/B/C only, 30min NOT_RUN |
| One container whole system | source-free CPU image and 3-service compose DDS + replay, same image ID | G06 T14~16 actual replay scope, not physical Gazebo or full product |
| Jetson power mode | N/A actual board excluded | NOT_RUN / not required |
| E-stop torque0 | simulated joint command guard, last valid hold, overrun no new command; torque zero is not proven | G08 MuJoCo 5 guards; hardware safety NOT_ACCEPTED, Gazebo negative NOT_RUN |

## Traceability and remaining differences
18 canonical code paths present, 14-5 optional implementation absent. Nine guide paths present incl 14.9. Path audit does not certify every manual example. T01~19 receipt statuses and scope in MANUSCRIPT_TRACEABILITY; missing or untested selected option must be marked. New common runner explicitly supports automated headless checks for 14.4,14.8 enabled,14.9; 14.1/2/3/5/6/7 existing manual guides only; 14.8 shadow manual guide and GPU/GUI unautomated, no automatic fallback. No all-section L3 acceptance. Review historical wording in older guide sections against appended actual results; new summary supersedes provisional status, not erase historical evidence.

## Release decision
Do not present source-level PASS, one selected build, or single simulation as entire G09/full publication PASS. Full release BLOCKED/HOLD: G01 absolute semantic, G00 rights/profile, G04 general simultaneous Ctrl+C, legacy preflight, original source full manuscript QA, automatic entrypoint/GUI gaps. No main merge until approvals and required conditions resolved. No blanket runtime regression justified by doc-only work.

2026-11-26: G09 WSL2 CPU headless Docker selected four-path L3 accepted; other publication conditions above unchanged. See G09_MVP_RELEASE_DECISION_KO.md. No automatic all-section L3 promotion.

## 2026-11-26 후속 정적 검토
원본 S1 75쪽 전체 텍스트, S2 교체 원고 26쪽 전체 텍스트와 개발 명세 v1.0의 파일 읽기 완료. 코드 19 번호 및 18 경로/9 가이드 확인; T05 optional absent. 교체 원고는 실제 HW 제외와 CPU 기본, 기존 정책의 SMOKE_ONLY 범위를 이미 명시. 원본의 성능 보장/보드 명령/토크0/열30분은 합성 원고에서 잔존 여부를 출판 편집 후 확인. S3 원본 및 편집 완료본 미확보; 그림·문서 레이아웃 QA 미수행. 최종 원고 승인과 권리 조건 미해결. 상세 [후속 QA](reports/G09_RELEASE_CLOSEOUT_QA_20261126_KO.md). 공용 CI 수정 #207 독립 GREEN 및 main merge 완료, Ch14 PR 동기화 검사 별도.
