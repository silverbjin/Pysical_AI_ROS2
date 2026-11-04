# 13.8 바닥 관측 실패 원인과 수정

작성일: 2026-11-05 KST. 단일 작업자. 이 문서는 Level1의 실제 완료나 10회 평가 완료 증거가 아니다.

## 실제 실패

v16/UUID `8fb61073-d484-43d8-a2d3-3aa51c7c7572`는 원고 Level1의 바닥 원통에 접근했다. navigation/정착/find/사전 파지 계획을 통과했지만 GRASP_APPROACH에서 새 관측이 거부돼 OBSERVATION_EXPIRED로 종료했다. accepted3450/rejected59, 거부 원인은 surface consensus 부족이다. CLOSE와 파지 성공은 발생하지 않았다. 126.44sim초/274.480495wall초, CPU43.609%, 최대 tilt0.0363422rad. worker 회수와 자식12개 정상 종료, 공유 lock 해제를 확인했다. 원래 FAIL을 유지한다.

## 증상에서 원인까지

마지막 원본 RGB-D/촬영 TF와 실제 종료 전 qpos를 고정해 물리 stepping 없이 다시 렌더링했다. 영상 일치율99.9896%, 깊이 최대 차이3.10µm, 촬영 TF 최대 차이8.88e-16이었다. paired raw depth와 MuJoCo native depth의 문제 픽셀 차이는0이었다. 따라서 이 프레임의 좌표 변환이나 단일 패스 깊이 환산을 원인으로 바꾸지 않는다.

원통 후보 side190점 중41점이 기존2mm 표면 기준 밖이었다. 합의율78.42%로 요구95%에 못 미쳤다. 실제 원통 tilt는0이고, 문제점의 높이는56~70mm여서 바닥 반사라고 단정할 수 없었다. geom 투명도 강제 변경도 실패했다.

진단용 segmentation에서41점 모두 object ID1/type6이었다. 첫 채널을 geom ID로 잘못 읽은 초기 진단은 벽 이름을 출력했지만, 두 채널의 object ID/type을 함께 읽자 `mjOBJ_SITE`임을 확인했다. 원본 모델의 site1은 붉은 `attachment_site`다. 실제 물리 표면이 아닌 팔 끝 보조 표시가 센서 RGB와 depth에 함께 렌더링돼 캔의 붉은 영역에 합쳐졌다. 이 ID는 종료 후 원인 확인에만 사용했고 실제 추정·제어에 사용하지 않는다.

site 표시만 끈 동일 자세에서 기존 검출 기준으로 중심(2.0000523,-0.0000591,0.0403589)m, 합의율100%, 관측 높이78.998mm를 얻었다. 이는 저장된 실패 프레임의 수정 확인이며 새 물리 미션 성공은 아니다.

## 공식 구현과 채택 근거

- [MuJoCo 3.13.0 mjvisualize.h](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjvisualize.h)는 `geomgroup`과 `sitegroup`을 별도 표시 옵션으로 제공한다.
- [3.13.0 engine_vis_visualize.c](https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_vis_visualize.c)의 site 생성 경계는 `sitegroup` 검사 후 `mjOBJ_SITE` 시각 형상을 추가한다. 물리 geom만 필터링해도 site는 계속 보이는 이유다.
- [3.13.0 visualization 설명](https://github.com/google-deepmind/mujoco/blob/3.13.0/doc/programming/visualization.rst)은 물리 상태와 보조 시각 요소를 구분한다. 문서의 존재를 로봇 물리 성공 증거로 사용하지 않는다.

현재 설치 MuJoCo3.13.0과 같은 ref를 읽었다. 외부 로봇 XML을 수정하지 않고 sensor용 MjvOption의 sitegroup만0으로 설정한다. 기존 geom 표시 그룹은 유지하며 기존 legacy 카메라 옵션은 그대로 둔다. 적용 범위는 기존 latest/paired 센서 스트림이다. 원통 추정에 object ID나 정답 좌표를 추가하지 않는다. 95% 합의율, 2mm 기준, capture300ms/TF100ms, 원본 hash/GID, 접촉/취소 계약은 유지한다.

## 검증과 남은 일

실제 실패 qpos를 작은 고정 fixture로 보존했다. 새 API 부재로1 FAIL을 확인한 뒤, 동일 시험에서 legacy 옵션의 기존 거부와 sensor 옵션의 표면 검출·중심 오차2mm 이내를 함께 확인했다: 1 PASS/2.59초,335 deselected. 기존 정적 초기/파지/운반 카메라 시험도 실제 sensor 옵션을 사용하도록 연결했다.

전체 부품 회귀, 별도 build/설치/동결, 새 UUID의 실제 Level1 연속 실행은 각각 별도 결과로 기록한다. 이 수정만으로 중간 경로 전체, 실제 파지·운반·놓기나 Level2/3를 성공했다고 쓰지 않는다. v16 원본·실패 판정·정확한 실행 소스는 보존한다.

전체336 PASS/55.03초. v17 별도 build12.7초·설치62모듈/94자산/actual venv child 감사 PASS. source351/assets94 동결 SHA256 fadf346d87273f9efb59efcd27234cdbdc5f99bb93063097d1b86a4b540b2390. 실제 Level1 UUID65199d33-38ee-4073-a561-bb8b22b5e79c의 결과는 진행 기록에 별도로 남긴다.
