# 1.4절 워크스페이스 진단 코드 변경·정적 테스트 보고서

- 기준: 1.4절 원고 및 `SECTION_1_4_REPORT_KO.md`
- 판정: **STATIC_PASS / COLCON_RUNTIME_NOT_RUN**
- 변경: `Ch01/scripts/check_workspace_layout.sh`, `Ch01/tests/test_ch01_workspace_checker_offline.py`

## 수정 근거

대규모 `examples` 벤더 트리 자체를 수정하지 않고, 안전한 **읽기 전용 워크스페이스 구조 진단기**를 추가했다. `src/build/install/log` 존재, `install/setup.bash` 존재, 현재 overlay 경로를 점검한다. 실습 원고의 위험한 `rm -rf build install log`를 자동 수행하지 않으며, 절대경로가 아니거나 `src`가 없는 경로를 거부한다.

## 실행한 테스트

| 항목 | 실제 결과 | 판정 |
|---|---|---|
| `bash -n Ch01/scripts/check_workspace_layout.sh` | exit 0 | **PASS** |
| 표준 라이브러리 `unittest`: 새 워크스페이스 비파괴 확인 | PASS | **PASS** |
| 상대경로 거부(exit 2) | PASS | **PASS** |
| `src` 디렉터리 누락 거부(exit 2) | PASS | **PASS** |
| `python3 -m compileall` 테스트 파일 | exit 0 | **PASS** |
| 실제 `colcon list`/빌드·DDS | 호스트에 ros2/colcon 없음 | **NOT_RUN** |

## 재현 절차

```bash
bash -n Ch01/scripts/check_workspace_layout.sh
python3 -m unittest discover -s Ch01/tests -p test_ch01_workspace_checker_offline.py -v
bash Ch01/scripts/check_workspace_layout.sh "$HOME/ch01_lab_14"
```

**주의:** 생성된 워크스페이스가 빌드되지 않은 경우 `build/install/log`은 없어도 정상이므로 보수적으로 안내한다. 이 도구는 실제 노드가 동작하는지 확인하는 테스트가 아니라 **구조와 안전한 진단 절차**에 대한 테스트다. 원고의 `source install/setup.` 오탈자는 문서에서 `setup.bash`로 교정되어 있으며 코드 변경과 구분한다.
