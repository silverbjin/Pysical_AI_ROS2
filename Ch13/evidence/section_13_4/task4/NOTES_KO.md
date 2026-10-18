# 13.4 탐지·자산 중간 검증

이 단계는 고정 이미지 실제 YOLO 추론과 ROS 탐지 노드 계약 검증이다.
실제 엔진 영상의 YOLO 의미 인식·3D 오차·팔 추적을 통과했다고 해석하지 않는다.

## 환경

전용 venv: /home/jinho/ch13_vision_13_4_venv (--system-site-packages).
NumPy1.26.4, pytest8.4.2, ultralytics8.3.221, opencv-python4.10.0.84,
Pillow10.4.0, torch2.5.1+cpu, torchvision0.20.1+cpu, mujoco3.3.7.
CPU torch/torchvision은 공식 https://download.pytorch.org/whl/cpu 에서 설치했다.
cv_bridge의 uint8 BGR 왕복 변환을 실제로 확인했다.

`pip-check-system.txt`와 `pip-check-venv.txt`의 오류 목록은 동일했다.
상속된 Flask/Arrow/위젯/type stub 및 matplotlib 요구 충돌과 pybind11 metadata 경고가 있다.
이는 해결되지 않은 시스템 기준 환경 경고이며 pip check PASS로 기록하지 않는다.
무관한 웹 앱 스택을 추가하거나 전역 패키지를 변경하지 않았다.

네 패키지를 이 venv의 `python /usr/bin/colcon`으로 빌드했다.
object_detector shebang과 설치된 detector 모듈 경로는 `installed-prefix.txt`에 확인했다.
설치된 share/config 메타데이터를 사용하며 실행 시 저장소 CWD가 필요하지 않다.

## 자산

출처·버전·크기·SHA256·배포 라이선스 표기는 Ch13/config/vision_assets.json을 따른다.
최초에는 승인된 고정 공식 URL에서 명시적으로 내려받아 해시를 기록했다.
그 뒤 fetch 유틸리티는 동일 해시·크기를 검사하며 손상된 기존 캐시를 덮어쓰지 않는다.
ROS 노드는 모델이 없거나 해시가 다르면 실패하고 다운로드나 fixture로 자동 전환하지 않는다.
SDK의 자동 의존성 설치도 import 전에 비활성화한다. 이미 활성 상태로 import된 SDK는 거부한다.

모델·bus 원본 사진·그 사진의 annotation은 외부 캐시에만 둔다.
개별 사진 권리나 전체 배포의 법적 적합성을 확인했다고 주장하지 않는다.
신규 Ch13 코드의 Apache 표기와 외부 Ultralytics의 AGPL/별도 상용 조건을 구분한다.
원본·annotation 경로와 해시는 JSON에 남겼으므로 동일 자산으로 재생성할 수 있다.

## 결과

- backend 테스트 7개, 실제 ROS 지연·만료 노드 테스트 2개,
  자산/실패 verifier 테스트 3개를 포함한 전체 111개 통과 (`full.txt`).
- 30Hz ROS 입력에서 150ms 처리 지연은 촬영 시각을 보존해 발행하고,
  350ms 처리 지연은 최대 age 300ms를 초과하므로 발행하지 않았다.
- 단위 fixture는 빨간 픽셀 기하 검출이며 YOLO 결과로 집계하지 않는다.
- yolo-autoinstall-red: 실제 bus 검출 자체는 성공했으나 SDK autoinstall 차단 검사가 실패했다.
  해당 설정을 교정한 뒤 같은 실제 가중치·이미지로 GREEN을 확인했다.
- 최종 근거는 `yolo-final-installed/result.json`: 설치된 실제 backend,
  공식 yolov8n.pt, 고정 bus.jpg, bus 클래스5/신뢰도 약0.825 검출,
  모델·이미지 해시 확인 및 SDK 자동 설치 비활성화 통과.
- 첫 추론은 약0.45–0.80초였다. 10Hz는 최대 시작률 제한일 뿐 달성률 보장이 아니다.
  ROS 노드는 cold-start 등으로 만료된 추론을 버린다. 실제 엔진 처리율은 후속 시험에서 측정한다.
- 첫 설정 디렉터리 부재로 /tmp fallback 경고가 있었고, 전용 설정 디렉터리를 만든 뒤
  `YOLO_CONFIG_DIR=/home/jinho/ch13_vision_13_4_venv/yolo_config`로 재실행했다.

검증 code SHA/dirty 목록과 전체 13.4 판정은 최종 통합 evidence에서 별도로 고정한다.
