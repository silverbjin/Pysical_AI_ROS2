# 실행 보존본

이 파일들은 승인 계획의 ignored 작업공간에 있던 실제 helper의 바이트 복사본이다.
일반 실습 진입점은 Ch13/docs/LAB_13_4_GUIDE_KO.md와 Ch13/scripts의 도구다.
helper는 당시 절대 설치 경로·고정 UUID·`.superpowers/sdd/2026-10-20-egl-camera-latency-plan`
상대 경로를 포함한다. 원본 실행의 재현/감사용이며 다른 환경에서 그대로 실행하지 않는다.
native-matrix는 기존 출력과 잔여 엔진을 거부하고, 제품 FAIL과 다음 trial의 정리 허용을 구분한다.
legacy는 기존 fail-closed 검증을 사용하며 첫 검증 실패 뒤 추가 엔진을 시작하지 않는다.
verify-final의`--remote`는 아직 성공하지 않은 게시 게이트용이며 실행 완료로 세지 않는다.
원본 소스/결과를 다시 쓰지 않는 분석과 테스트 완료·설치·해시 감사를 함께 보존했다.
