# G04 T10 교육용 중간 인수 보고서 — 실제 곡선·직선 GREEN
## 1. 실제 인수 증거
Run 45934040387 / Job 140293013216 / source 1cd16b1a66ce94fb3ef4a474c01b043a00e43112, Artifact 15169973234, 2,031,645 bytes ZIP SHA256 173434b89edd903e73ed1d9021867d696b6dbf1266bf005c5c839d2fe2805c82, 내부 54/54 독립 검증. V3 실제 MuJoCo PASS_SCOPED_ARC_STRAIGHT. 동일 compiled model, 원본 94 assets/source freeze, ARM 연속성 PASS. Curve 730 samples, settled XY19.898mm/yaw .010083rad, straight 231 samples settled XY12.266mm/yaw .051915rad. 원본 엔진 표본 nearest timestamp 차이 <1ns, 독립 자세 재계산 일치. 9/9 scoped checks, original cap ratio1.0, engine COMPLETED/no active fault, 3/3 exit0, residual/lock PASS. Native gateway fault INPUT_OR_CLOCK_TIMEOUT은 stationary shutdown ACK 이후278.660ms에 실제 발생; 정상 종료 이후 source loss이며 숨기거나 reset하지 않음. 최종 yaw margin .008085rad (~0.46deg), XY margin2.734mm; 넓은 여유나 일반화 보장 아님.
## 2. 디버깅 사이클 비교
- ARC RED1 45927863442: ARM startup source timeout, zero motion.
- ARC RED2 45931318335: DISARMED FUTURE_SOURCE:base, zero motion.
- ARC RED3 45932381041: CPU isolation/trace + original guard; actual arc39.440mm >30mm; straight not run.
- ARC RED4 45933266376: V2 cross feedback actual arc20.150mm PASS; straight17.089mm after settle >15mm.
- ARC GREEN 45934040387: V3 straight slip/taper and measured stop cross compensation. Actual curve19.898mm, straight12.266mm; final .051915rad. Original 15mm/.06rad unchanged.
## 3. 교육용 교훈
실행 실패의 첫 경계는 매번 다를 수 있다. startup gate, native time ordering, curvature error, actual settle are separate contracts. 단순히 tolerance를 완화하면 failure mode를 숨긴다. 실제 trace에 근거한 선형 민감도 모델은 변경 후보 선정용이며 GREEN은 실제 엔진에서만 선언한다. 다음은 real table area with fresh vision target, fixed world coordinates, one original CommandGateway owner and bounded approach. Existing original CH13_NATIVE L2 RED4 remains FAIL; no BT, bag or owner L3 claim. No re-run of accepted isolated candidate without integration requirement. Main merge HOLD.
