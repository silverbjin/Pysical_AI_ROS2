# G08 clock reset 영향 검수 (인계 보완 항목)

G07 replay helper와 G08 installed controller, 원본 ONNX를 이용하는 실제 DDS 좁은 시험. 정상 nominal pose synthetic sensor envelope, 5초대에서 2초로 시뮬레이션 clock 역행. 새 sensor 없이 inference count 유지, 동일 hold target만 허용, 새 sensor 이후 arming→active, reset 전 cmd 소멸 확인. 실제 물리 엔진은 실행하지 않고 물리 PASS로 승격하지 않는다. 별도 domain과 actuator 미연결, 신규 학습 없음. 다른 정상/negative suite 재실행 금지. CI 결과 전 candidate only.
