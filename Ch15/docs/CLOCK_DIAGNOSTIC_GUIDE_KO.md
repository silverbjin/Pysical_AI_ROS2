# G09 R09 읽기 전용 교차 진단
Windows PowerShell에서 일반 사용자로 실행한다. 실제 사용한 WSL 배포판 이름은 wsl -l -v 로 확인한다. Docker는 기존과 동일한 실행 상태를 유지하며 미션은 실행하지 않는다. 종료/재시작/절전 및 시간 설정 변경 금지.
릴리스 안내에 제공된 immutable bootstrap SHA와 SHA256을 대조한 뒤 clock_diag_bootstrap.ps1 -Distro <배포판> 을 호출한다. 소스 7개를 bd07d22da44e725e36ff2099b64f76f7b5e688c2에서 다운로드하고 각 SHA256 검증 후에만 실행한다. VerifyOnly는 다운로드 검증만 한다.
기본 620초 idle, 620초 Docker 및 CPU 부하 계측. Windows UTC/QPC, WSL MONOTONIC/RAW/BOOTTIME/REALTIME, timex modes=0, Docker 및 가능시 ROS Clock, 서비스와 이벤트 조회. 외부 NTP stripchart는 조회만 하며 실패 시 외부 기준 불충분으로 기록한다.
ZIP, ZIP.sha256, source-receipt.json을 비공개 전달한다. 개인정보/원본 로그를 공개 Git에 올리지 않는다. 계측 결측과 지원되지 않는 명령은 NOT_AVAILABLE 또는 실패로 구별한다. 후보 gate는 최종 환경 PASS가 아니다. 정책상 PowerShell 실행이 막히면 설정 변경하지 말고 오류를 전달한다.
