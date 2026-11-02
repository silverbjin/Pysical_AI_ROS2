# 오프라인 재현 기록 — 2026-10-26

범위: 기존 MuJoCo G1 `61422188` 원본과 readonly 외부 소스를 분석했다.
새 엔진 실행·controller 변경·물리 성공·절 완료 기록이 아니다.
WSL `Ubuntu-24.04`, 일반 사용자 `jinho` UID1000. 관리자 권한·드라이버·시스템 설정 변경 없음.

repository 루트에서 실제 수행한 계산은 다음과 같다. 각 Python 명령의 종료 코드는 0이었다.
이미 결과가 존재하는 곳에서 재현하려면 새로운 출력 경로를 사용한다. 코드는 기존 결과를
덮어쓰지 않으며 verify.py도 기존 verification.json을 덮어쓰지 않는다.

```bash
task_analysis=Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/analysis-a1ee6678-35ab-484c-9fba-aa861f1af230
/usr/bin/python3 "$task_analysis/analyze.py" "$task_analysis/result.json"
/usr/bin/python3 "$task_analysis/arm_hold.py" "$task_analysis/arm-hold.json"
/usr/bin/python3 "$task_analysis/analyze.py" "$task_analysis/result-repeat.json"
/usr/bin/python3 "$task_analysis/verify.py"
```

두 result의 SHA256은 모두 `aebcd0ea1188d6a0184427b824529f2820756552b39b445713828b735f61af9b`다.
결과 재현을 실제 엔진의 연속 성공 횟수로 세지 않는다. 결과 JSON에 입력 SHA·소스 해시·가정·한계와
외부 소스 구간이 있다. verification.json은 script/result 해시, 119개 런타임 파일 불변, 원본FAIL,
문서 링크4개, Mermaid fence, 당시 프로세스 잔여 없음과 새 엔진0회를 구분한다.
Mermaid 실제 렌더링은 시험하지 않았다. runtime 전체 재시험·설치 재빌드는 수행하지 않았다.

추가 읽기 전용 조사 명령은 `git -C /home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control rev-parse HEAD`,
`status --porcelain`, 해당 소스의 `sed`/`rg`였다. HEAD는
`c261f5552edf124d1000a23fb25b6c07cadeb807`, 작업트리는 깨끗했다.
Git diff 공백 검사는 `git diff --check` 종료0이었다(기존 LF/CRLF 알림만 존재).

분석 직후 로컬 HEAD는 `4e87f6f6031d0ac5e73b2575bcee261e92a0e59e`,
브랜치는 `feat/ch13-section-13-5`다. 이 재개에서 commit/push는 수행하지 않았다.
사용자 13.4 교육 문서는40723bytes/원래 수정시각 그대로 보존했다.
