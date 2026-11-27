# R08 — 장기 Clock Drift 재분석
- R07 archive SHA 4/4, manifest 163/163. 9101 host samples 원본 로컬 분석; raw 자료 공개하지 않음.
- 10초 bracket endpoint rate, offset 변화, coverage gap/step 구분, ROS sim 제외, 보정 사이의 실제 RAW offset 차이와 step 크기 비교. 원인 판정 UNKNOWN.
- 후반 3개 RAW/Monotonic median ppm 90962.055487, 90962.060406, 90962.060421. F03 transient 첫 약 70초 거의 0, 70~80초 전환, 이후 +9.0962%. 전체 평균 2.824558%는 전환을 숨김.
- F06 local accumulated drift vs observed (s): 2.933529/2.932368, 2.933524/2.929128, 2.956272/2.964421, 2.933520/2.931182. F03 transient 전환 구간 2.241281/2.222662. 연관성 강하지만 누가 보정하는지 미확정.
- RED 설계 리뷰: 긴 sampling gap에서 RAW offset 누적을 step으로 오인할 수 있고, 전환 실행 전체 median으로 step 규모를 예측하면 오판. FIX gap 우선 분리, step별 RAW 변화 직접 비교. GREEN 로컬 12/12 (실제 F06 상대값 2쌍 포함) 및 4 원본 재분석. 코드 Git blob 764c77c71b57743a21e29ed75b6533b6c97b85f5, test 1ed209a6989513f5fa360e955449f8a0962fef64, 로컬/원격 일치. CI 별도.
- 9% 진행률 자체는 정상 NTP slew로 단정할 수 없음. R09 Windows QPC·timex·Docker cross RPC 근거 필요. 기존 R02/R03/안전 코드 무변경.
