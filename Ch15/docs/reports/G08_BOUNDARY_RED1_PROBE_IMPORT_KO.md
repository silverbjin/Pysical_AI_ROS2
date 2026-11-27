# G08 boundary RED1 — 검수기 시작 경계 오류
- [Run 45955557284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45955557284), job140361103523, artifact15178880859, source f58fca72c4e1d64fe3f4034c8496298401945cdc.
- SHA256 73a187cdb662a0e6e47271f46d49e9ca93928d7e100382a7d01cc7c2848c3688, ZIP 내부5/5 독립 검증. 실제 빌드3/3 11.6s, 8/8 단위시험 PASS. F01_receipt probe launch에서 NameError('subprocess' is not defined). trace=[], injection_observed=false, processes=[]; 실제 DDS 장애 주입 NOT_RUN. F01_source/F07 NOT_RUN.
- 원인: 검수기 import 목록에 subprocess 누락. 런타임 안전 노드가 실행되지 않았으므로 watchdog/arbiter 장애로 해석하지 않는다. import 추가 및 무의미한 local 제거; 원본 안전 코드, 시간 기준, FMEA, retry 정책 불변. 다음 V2 actual boundary. G04~G07 재실행 금지. G08 HOLD.
