# G00 CPU preflight — Header 직렬화 및 기존 lock 재사용

원본 CI [45739405822](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739405822), source 3b3b636efeaceeb54166e663a4cf0f742230166f, job 139640445572, [artifact 15080307846](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739405822/artifacts/15080307846). FAIL: TypeError: Object of type Header is not JSON serializable. 최초 오류의 nested metadata 원인은 실제 setuptools 내부 12개 목록으로 확인 완료. 새로운 오류는 email.parser.BytesParser 기본 정책에서 non-ASCII header가 Header 객체로 반환되는 경우다. 로컬 fixture로 실제 Header 타입 재현. 문자열로 정규화하고 JSON 직렬화 완료 전 lock 출력을 기록하지 않는다. 4/4 regression PASS (0.012s, exit0), 설치/ABI/ONNX 미실행.

원본 ZIP 실제 다운로드 후 SHA256 787f474c70d7cfdf1efaeb4c85fdbd07677dc365aae6159f8f0d8d815fa3bb6c 및 내부 7/7 SHA 확인. 기존 run의 46개 wheel lock은 JSON manifest 직렬화 이전에 기록되어 있음. 원본 lock SHA256 cbec2ab0a357702ae1f03277e8b40fd8cf754259755af1e4f2426a144e7f7b2d, blob e8adc08739f57f8b84679b72303c58755eac752c. 이를 cpu.probe.lock.txt로 그대로 고정. 다음 CI는 버전 재해석 없이 --require-hashes 다운로드 및 regenerated lock cmp를 적용한다. 배포용 lock 승격은 아직 금지. 동일 이미지 digest ros@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6, Ubuntu24.04.5 확인. apt 패키지 버전은 다시 기록. 설치/ABI 실제 검증 후에만 CPU preflight PASS 판정.

동일 원인 반복이 아닌 두 번째 경계의 신규 오류이며 고정 증거를 재사용하여 한 번만 재검증한다. G00 전체/WSL2/YOLO 미인수.
