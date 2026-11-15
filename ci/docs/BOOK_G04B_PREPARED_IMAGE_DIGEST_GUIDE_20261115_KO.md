# G04B 준비형 이미지 생성 및 digest 고정 (P1)
_2026-11-15; Draft, 기존 Gazebo/WSL2 런타임 미전환_

현재 #202의 가용 digest는 `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`이다. 실제 CI 매번 `apt-get update/install`이 발생하므로, **기존 이미지를 변경하지 않고** ROS Jazzy MoveIt + Gazebo Sim8 C++ 개발 헤더와 컨트롤러를 포함한 파생 이미지를 한 번 만든다.

- 빌드 명령 (Docker 설치·GHCR 권한이 있는 격리된 CI/빌더): `bash ci/docker/build_book_g04b_prepared_runtime.sh`
- 이 명령의 기본 동작은 **빌드+무목표 의존성 검수만 수행**, 업로드하지 않음.
- 배포 승인 후 `G04B_PUBLISH_PREPARED_IMAGE=YES bash ci/docker/build_book_g04b_prepared_runtime.sh`로 올리고 출력된 **immutable image@sha256 digest**를 증거로 기록한다. 사용자 승인 전 임의 배포 금지.
- Docker build 시점에 ROS/Gazebo apt 저장소에서 설치한 모든 의존성은 최종 게시한 digest로 고정된다. 태그는 재현성의 근거가 아니다.
- 새 digest를 CI G04B와 WSL2에 반영하려면 **same source SHA + prepared digest + native FJT/pose/contact/ROI** 비교 결과가 필요하다. 이미 성공한 G00–G04A를 재시험하거나 G04B FAIL을 PASS로 바꾸는 이유가 될 수 없다.
- 현 대화 환경에는 Docker CLI가 없어 **이미지를 빌드·게시하거나 새로운 digest를 확정하지 못했다**. 준비 단계의 L0 bash 구문과 소스 정적 계약은 별도로 점검할 수 있다. 지금의 물리 CI는 기존 digest를 유지한다.
