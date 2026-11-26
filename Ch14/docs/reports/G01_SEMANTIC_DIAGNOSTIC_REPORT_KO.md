# G01 — 두 고정 실패 영상 실제 원본 모델 진단
## 근거
기존 T04 Run 45745101023 artifact 15082717992, 원본 ZIP SHA 0537cf7ba76db50b918fe8d27a12c3304b810a8aa98781861591441d98ed32e9 및 내부 18/18 재검증. 새 diagnostic [Run 45746373267](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45746373267), source 5cd0eb2e4941b90d023977e3344c9008a846e2f2, job 139663328363, artifact [15082449287](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45746373267/artifacts/15082449287), ZIP SHA 2b36b59c8d8d9cbd3455fefe4b853776d28552632524a3c8cf88555fc187954d, 내부 6/6 검증. 실제 4 forward (2 모델×2 영상)만 수행; T01/T02/T03/전체 T04 재실행 금지. 새 실행은 PyTorch raw 분석, 기존 ORT 실행 증거와 구분. 진단 job PASS는 원래 모델 품질 PASS 아님.
## 실제 원인 계측
| model/image | IoU>=.5 raw 후보 | GT 클래스 score>=.5 | GT 영역 최고 GT score | 최종 custom/upstream NMS |
|---|---:|---:|---:|---|
| n/463199 bus | 17 | 0 | .001083996 | miss/miss |
| s/463199 bus | 31 | 0 | .000668534 | miss/miss |
| n/392818 dog | 117 | 0 | .211314678 | cat/cat |
| s/392818 dog | 113 | 9 | .785237968 | dog/dog |
Bus raw 후보의 위치 GT IoU n .830625, s .732110; 전체 유효 raw 후보의 최대 Bus score n .003887245, s .001976859. NMS 이전부터 target score 미달, 위치 후보 없음이 아님. n Dog 최고 점수 후보 .211315, same candidate Cat .340661; 최종 Cat 후보 .528898, 동일 후보 Dog .149248, GT IoU .944362. s Dog .785238, Cat .011814, GT IoU .945956. Custom and independent Ultralytics class-wise NMS counts/classes/scores match for all four observations. 동일 raw 입력에서 NMS 문제 근거 없음. 전처리는 동일 canonical tensor; 독립 end-to-end Ultralytics preprocessing은 이번 시험 범위 아님. 이미지 bytes SHA 검증 성공, 원본 육안 확인은 local DNS/web 실패로 NOT_RUN; 실제 가림/촬영 특징/label visual validity 또는 학습 데이터 원인은 미확정.
## 기존 전체 fixture 재분석
기존 결과 JSON과 GT로 실제 1:1 class matching IoU>=.5, confidence descending, per-image exact GT index set 비교. n 26/26 TP, s 36/36 TP, 양쪽 모두 새 누락/새 검출 0. 필수 표적 n14/16, s15/16 기존 FAIL 유지. T04 numeric and semantic preservation PASS within scope, absolute semantics FAIL. 결과 scope docs/G01_ACCEPTANCE_SCOPE_KO.md. No threshold/model/fixture changes, no retraining. Educational engineering decision: distinguish model deployment equivalence from baseline accuracy. G02 independent CPU comparison allowed within scope; G03 actual required targets and safety unchanged. Full Gate and main merge HOLD. 
