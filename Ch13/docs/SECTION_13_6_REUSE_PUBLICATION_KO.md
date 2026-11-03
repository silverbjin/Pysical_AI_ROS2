# 13.6 v13 게시·다운로드 검증

2026-11-04 KST. 소스·보고서·모델 제외 증거의 게시 payload commit은157c1b28af60d3cef533e12a2fcc19b19800fd6c이며 로컬/실제 원격 SHA 일치를 확인했다. 이후 변경은 이 문서·가이드 다운로드 범위 수정·검증 증거·완료 표기뿐이다. runtime v13의248파일/외부94자산과 동결 SHA67da28691991d81152526919e5a4c65fec91ba3d75e1d84a5fc2681901d39101은 유지된다. 최종 문서 commit의 실제 원격 일치는 게시 직후 별도로 확인한다.

- 원격: https://github.com/silverbjin/Pysical_AI_ROS2.git, branch feat/ch13-section-13-6-manipulation. non-force push만 사용했고 main merge/PR은 하지 않았다.
- 새 clone: `C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_13_6_final_validation_20261104_v13`.
- 별도 build: `/home/jinho/ch13_reuse_13_6_guide_validation_v13_20261104`. R2/R5 및 개발용13.6 install을 덮지 않았다.
- 기존 venv·OS/ROS/MoveIt 의존성·외부94자산을 재사용했다. 새 OS나 apt/pip 설치의 검증이 아니다. clone에서 새 engine/renderer를 실행하지 않았다.

## 실제 결과

첫 sparse 다운로드에서는 기존 integrated_robot_vision 설치 데이터인 Ch13/config/vision_assets.json이 없어 build가 실패했다. 파일은 이미 저장소에 있었고 가이드 sparse 범위 누락이었다. 초기 실패 로그를 보존하고 `Ch13/config`를 다운로드 범위에 추가했다. 같은 별도 build에서 이어서6개 패키지를62초에 build하고 설치 감사34개+13.6감사23개·원본94자산 hash 일치를 확인했다. stderr의 byte-compiling disabled 경고는 PYTHONDONTWRITEBYTECODE 정책에 따른 것이며 빌드 실패가 아니었다.

추가 설치 데이터 vision_assets.json SHA256은9c82545c489718e1b96a6942d542802a18594bc3d56915ee30656f9fd21c7172다. 실행248파일 manifest 밖의 기존 package data이며 이번 sparse 다운로드·build 검증에 명시했다.

원본248파일 동결은 새 clone에서 PASS였다. 다음4개 사례는 engine.json이 없는 빈 복원 대상임을 먼저 확인한 뒤 archive/각 파일 hash를 검사하고 복원했다.

| 사례 | 복원 파일 수 | 저장 결과 재판독 |
|---|---:|---|
| pick20662d06 | 39 | 실제 상승/유지/접촉과 RGB-D 재계산 PASS |
| held_cancel4448d833 | 39 | 실제 취소 뒤 유지/낙하/접촉 PASS |
| MoveIt70837980 | 38 | 실제 pose·직선·취소 PASS |
| raw_lossa854efd7 | 25 | 원판정 FAIL 보존, 좁은 오프라인 검토 PASS |

판정기 실제 fixture+11개 반례12개는 다운로드본에서0.19초에 PASS였다. 통과한 전체 unit199개나16개 engine을 다시 돌리지 않았다. 최종 감사는16개 사례·원래15 PASS/1 FAIL·별도 검토1 PASS·판정 소스/입력 해시·runtime 동결·다운로드 검증·잔여 없음을 재대조해 PASS였다.

새로 만든 이전/최종 증거 archive101개(합계367,064,848bytes)는 원본을 남긴 채 모든 게시 파일 hash를 대조했다. 기존15개 archive도 보존했다. 여기에 이번 다운로드 검증 증거를 별도 묶음으로 추가한다. 모델/가중치·생성 URDF/SRDF·그것을 내장한 planner.yaml은 게시하지 않는다. 각 archive의 raw_manifest.json에 제외 항목과 로컬 경로를 남겼다.

[최종 인수 보고서](SECTION_13_6_REUSE_REPORT_KO.md), [게이트 검토](SECTION_13_6_REUSE_GATE_REVIEW_KO.md), [자체 검토](SECTION_13_6_REUSE_FINAL_REVIEW_KO.md), [실습 가이드](LAB_13_6_REUSE_GUIDE_KO.md), [다운로드 검증 증거](../evidence/section_13_6_reuse/download_validation_v13/raw_manifest.json)를 함께 제공한다. 작성자 자체 검토는 독립 검토보다 약하며, scenario 각1회·교육 profile 범위의 제한은 유지한다.