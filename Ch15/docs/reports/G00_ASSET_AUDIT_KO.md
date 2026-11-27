# G00 자산·환경 감사 — 공개 개발 재개
2026-11-27 KST. 사용자 공개 저장소 개발 승인. 출판·원고·외부 모델 재배포 및 main 병합은 별도 승인 유지.

## 근거
기준 main 1931cac92585fc155357880b584c72c76d67257c, root 0d67e7f2bb3e83632a840fec36e54895f0a8c912, Ch01~14 tree 14개 고정. #206/#207 merged; 기존 open Draft 25개, Ch15 충돌 없음. 원고와 명세 SHA256 대조 일치, 원고 코드 블록 24개. 원고/모델/원시 bag 미게시. 독립 branch feat/ch15-mission-engineering 생성.
Ch13 원본 basic runner 및 assessor 10개, native gateway 50Hz와 300ms guard, actual observation contract, navigation terminal/settle 8 wall / 5 sim seconds, 1200 wall 초과 cancel, 600 sim budget 확인. 94개 자산 manifest를 읽어 기록. 실제 bytes 및 권리 미확인. SIGINT 및 navigation idle은 원래 소유자의 종료 경로이며 F01 scan loss hook으로 승인하지 않음. Ch13 Level2/3 역사적 basic PASS, full 0/10 FAIL 그대로. Ch14 G09 PIN 6c458e345236b124c9aa60f65788f35cfed74e62, CPU scoped PASS, 의미 탐지 FAIL, 일반 Ctrl+C HOLD, policy SMOKE_ONLY 유지. PointStamped와 Detection2DArray는 동일 stamp만으로 개별 객체 association 보장 불가. Ch14 G07 원본 archive 현재 접근 미확인.

## 교육용 개발/검수
원래 장애: 공개 게시 보류 및 실행환경 부재. 공개 소스 개발 승인이 첫 장애만 제거했다. 현재 도구 환경 Debian 13/Python 3.13, ROS/Docker 없음, 직접 git DNS 실패. 기존 Ch14 CI에서 사용된 두 immutable digest를 후보로 고정했으나 Ch15 runtime에서 pull/build한 것은 아니다. audit JSON은 완성 lock이 아니다.
preflight는 HEAD/기존 14 subtree drift, physical 자산 access acknowledgment/94 bytes, OS ABI, ROS 및 MCAP을 fail-closed 검사한다. 권리의 법적 확인을 acknowledgement로 대체하지 않는다. 설치/네트워크/물리 움직임 없음. 현재 구현 검수 NOT_RUN. 최종 G00_CPU_READY 금지.
결정: 독립 G01 정적 시나리오·자체 생성 월드만 진행 가능. G04 physical 및 실제 모델 사용은 자산/원본 runtime closure/권리 확보 전 BLOCKED. G02 이후 실제 ROS 검수는 CI에서 확인. 새 증거 없이 같은 실패 재실행 금지. 
