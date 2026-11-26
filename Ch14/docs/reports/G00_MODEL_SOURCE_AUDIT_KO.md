# G00 YOLO 공식 모델 출처 및 fail-fast 확보 경계

공식 GitHub release v8.3.0에 n/s 파일은 있으나 API digest가 null. 동일성이 입증되지 않은 GitHub 파일과 HF 파일을 혼용하지 않는다. 대신 Ultralytics 공식 HF repo revision a335eb8d58ded1464e0ff09b3994fc8ae0e6f8fe의 model pointer가 두 SHA256을 제공함을 직접 확인했다. [n](https://huggingface.co/Ultralytics/YOLOv8/blob/a335eb8d58ded1464e0ff09b3994fc8ae0e6f8fe/yolov8n.pt), [s](https://huggingface.co/Ultralytics/YOLOv8/blob/a335eb8d58ded1464e0ff09b3994fc8ae0e6f8fe/yolov8s.pt). manifest는 publisher expected digest이며 실제 다운로드/파일 해시/역직렬화/추론은 NOT_RUN. HF pickle imports 표기도 확인; 승인된 원본만 hash 검사 후 이후 backend에서 로드.

라이선스: publisher AGPL-3.0 선언. https://www.ultralytics.com/license 의 공식 라이선스 안내에 따라 배포 방식 검토가 필요하다. 이 저장소 root LICENSE 부재 및 일부 기존 package.xml TODO가 있으므로 repository owner가 출판 코드의 권리를 확정해야 한다. 모델과 이미지는 Git에 vendor하지 않는다. 다운로드 acknowledgement는 법적 승인으로 간주하지 않는다.

실행기: bash Ch14/scripts/fetch_models.sh yolov8n --cache /absolute/cache (오프라인 해시 검사). 실제 다운로드는 권리 검토 이후 --fetch --acknowledge-agpl을 명시적으로 사용. 임시 파일에 다운로드 후 SHA 검증, exclusive link로 원자적 게시. 손상된 기존 파일 덮어쓰기 금지. 모델 로드/실제 YOLO 검수는 별도 Gate. 합성 byte fixture로 정상 hash, missing/ack, corruption, symlink, manifest reject 5/5 unittest PASS(0.004s, exit0). 합성 payload는 모델이 아니다. 이미지 20개와 label/license 및 실제 PPO ZIP 확보는 미완료.
