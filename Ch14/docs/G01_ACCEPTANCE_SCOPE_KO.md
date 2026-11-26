# G01 최종 기술 인수 범위 — SCOPED_PASS
사용자 요청에 따른 교육용 CPU 변환/배포 기술 범위의 확정. 원고 14.1~14.2는 더미 입력 속도 측정과 실제 라벨 데이터 정확도 측정 분리, 동일 입력 raw/후처리 동등성 비교를 설명한다. 개발 명세 §7.1의 절대 필수 표적 누락 0건은 별도 조건이며 기존 FAIL을 변경하거나 삭제하지 않는다.

## 기술 인수
T01 실제 2x100 benchmark PASS (45744146299); T02 actual n/s export checker/ORT/load/seed parity PASS (45745101023); T03 100 input demo PASS (45742206902); T04 raw 40/40, paired 71/71, unmatched 0, invalid-contract 10/10 PASS (45745101023). 기존 64개 GT 라벨의 실제 1:1 일치 객체 집합을 재계산: n PT/ORT 26/26, s 36/36, 새 누락 0, 새 검출 0. 동일 confidence .5, NMS .45, GT IoU .5, raw atol/rtol .001, matched IoU>=.95, score diff<=.02. 고정 20 이미지/라벨/weights/기준 변경 없음. 원래 모델의 미검출 및 오분류는 반드시 보고하고 학생 분석 사례로 사용한다. 전체 정확도 보증 아님.

## 절대 의미 검수
원본 §7.1 필수 16개 중 n14, s15; 각각 2/1 누락. 이전 run FAIL 그대로. 두 영상 한정 실제 raw+독립 NMS Run 45746373267 (artifact 15082449287), 두 bus 점수 및 n dog 점수가 threshold 미달, 별도 Ultralytics NMS 동일 결과. 원본 이미지 육안 확인 미실행; 라벨 자체의 시각적 오류 여부는 단정 금지. G01 기술 교육 범위 SCOPED_PASS, 원래 전체 Gate BLOCKED. 신규 누락 0의 상대적 인수는 배포 기능을 판단하는 범위 한정 기준이며 기존 절대 요구를 몰래 완화하는 것이 아니다. 정식 전체 PASS로 변경하려면 사용자의 명시적인 명세 변경 승인 또는 원래 요구 충족 증거 필요.

## 다음 단계 및 배포 경계
G02 CPU 엔진 비교 독립 개발 착수 가능: 같은 fixed fixture와 정확히 식별된 ONNX, 원본 의미 한계 보존, 신규 누락 0, 동일 raw/box/score 기준, 실제 timing. 이는 G01 전체 PASS나 G02 전체 완료를 의미하지 않는다. G03 실제 Gazebo 표적/TF/시간/안전 조건에서 절대 필수 표적 누락 0은 그대로 유지. 실 HW 없음. GPU optional NOT_RUN. WSL2 L3 NOT_RUN.
main 병합 HOLD: 원래 G01 전체 성공 조건 미충족, AGPL/fixture 배포 권리 미확정, 독립 기존 Book Lab Acceptance sparse checkout 실패. main 성공 조건 임의 대체 금지. Draft #206 유지. no full rerun; no model training; no threshold/fixture cherry-pick. Evidence check exact SHA, existing source/lock model hashes reuse. No upstream weights/photos/exported ONNX redistribution.
