# G00 개발·디버깅 보고서 — 감사 체크포인트

문제: 명세의 SHA 및 원고 예제가 실제 코드/모델과 일치하는지 확인해야 한다. 해결 방법: 원격 main 재조회, tree/파일 blob 비교, manifest와 실제 verifier source 및 역사적 결과 분리, 개정 원고 19개 코드 번호 직접 대조. 사용자 승인으로 쓰기 대상 확정. 원고에 제시된 예제는 전체 구현이 아니므로 공개 Git에는 계약과 추적표만 보존한다.

최초 실패 경계: 실제 PPO ZIP 및 YOLO fixture 미확보, 실행 컨테이너에서 onnx/ORT/Ultralytics 및 ROS CLI가 없음. 외부 git DNS 오류( Could not resolve host: github.com ). 같은 clone 반복 금지. GitHub API 브랜치 경로 사용, Ubuntu24.04/Python3.12 CPU preflight는 별도 CI로 진행. 외부 모델/코드 권리를 추측하여 복사하거나 랜덤 actor를 학습 모델로 간주하지 않는다.

검증: 원격 SHA 및 기존 코드/blob 확인, 개정 원고 SHA256과 19개 코드 번호 확인. 실제 모델 export, CI, L2, L3는 아직 NOT_RUN. G00 PARTIAL/BLOCKED. 기준 commit은 감사 문서 참조. 이후 preflight 결과와 원장 갱신은 별도 커밋. 기존 성공 실행을 재시험하지 않음.
