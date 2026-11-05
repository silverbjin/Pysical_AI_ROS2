# 13.8 바닥 관측 실패 원인과 수정

작성일: 2026-11-05 KST. 단일 작업자. 이 문서는 Level1의 실제 완료나 10회 평가 완료 증거가 아니다.

현재는 반복된 관측 실패의 서로 다른 원인 두 가지를 분리해 수정했다. 실제 내려놓기 전체 성공은 아직 확인하지 않았다.

| 사례 | 확인한 원인 | 수정과 현재 근거 |
|---|---|---|
| v16 | 붉은 팔 끝 좌표 표시가 센서 영상에 섞임 | 공식 MuJoCo 표시 그룹 API로 제외. v17 실제 접근·파지·귀환에서 관측 거부0회 |
| v17 | 관절 목표 완료 뒤에도 캔이 바닥보다1.79mm 높음 | 실제 저속·정착·지지를 확인하는 별도 gate. 실제 해당 단계 재검증 필요 |
| v18 | 하부13픽셀 조각을 모델 결합 전에 폐기 | 큰 조각에 기하적으로 맞는 작은 조각만 보존. 양성/음성3개 및 실제234자세 재현 통과 |

기존 검출 높이·표면 합의·관측 수명과 힘 제한을 낮추지 않았다. 바닥 정착 대기 상한은5wall초에 의존하던 경계에 명시적인20wall초 정착 단계를 추가한 것으로, 아래에 변경 이유와 제한을 공개한다.

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

## v17 실제 결과와 다음 정착 경계

v17은 전체접근/실제파지/귀환에서관측6134회수락·거부0·vision fault없음을확인했다. 최소103.9716mm lift/2.2sim초유지/양finger접촉100%/slip0.027672mm로pickPASS다. 다만LOWER뒤support를5wall초내확인하지못해전체FAIL. trial200.394sim초/478.197393wall초,귀환오차43.3379mm,CPU44.46431%,tilt0.045418rad. workerjoin/12child정상종료/공유lock해제PASS. 원고3cm/120초목표도미달이다.

정확한실행소스351개는source_v17/runtime_source.tar.gz에hash일치로보존했다(SHA f15af2529444c14593113ae3049b76ee21b3fb927551cedde62fd34d3c4d08c7). 원본raw51,384,145byte(SHA39aac6e2683db89d6aa08d1702907f3766e3f95a97aeb638a79c872667a874ef)와실패판정을유지한다.

[실제설치 control_msgs5.10.0의 FollowJointTrajectory.action](https://github.com/ros-controls/control_msgs/blob/5.10.0/control_msgs/action/FollowJointTrajectory.action)은성공을관절goal tolerance와시간으로정의한다. 처음비교한4.8.0외에설치package.xml의5.10.0을다시확인하고같은ref원문을읽었다. 프로젝트nativebridge도관절오차0.05rad/속도0.05rad/s의유지로완료하며그리퍼물체의바닥지지를보증하지않는다.

실제LOWER terminal시각에는물체가바닥보다1.7886mm높았고팔최대속도는0.001856rad/s였다. 최초지지0.01492N은5.124567wall초뒤,기존5초한계직후다. 이미정리중발생한늦은접촉을성공으로바꾸지않는다. FK잔차4.159mm는전체3D수치이므로수직간격과혼동하지않는다.

v18후보는기존pick의정착확인패턴을참고해floor LOWER뒤저속(각팔<=0.003rad/s)/base실측정착/원본fresh관측·유효lease/실측support>0.01N을0.5sim초연속요구한다. 정착단계의최대wall대기는기존pick정착과같은20초로명시적으로늘린다. 이추가단계뒤기존접촉확인/유지도유지한다. 기본development는변경하지않는다. 새로운관측수명이나개방권한을부여하지않으며,실제지지없이시간만지나서개방하지않는다. global action120sim/240wall·mission600sim은유지한다.

## v18의 다른 관측 실패와 구조 재검토

v18 UUIDcb260b36-8fae-46e9-97c8-927376588f46은GRASP_APPROACH에서높이가시성거부70회/OBSERVATION_EXPIRED로FAIL했다. accepted3748,130.392sim초/296.650778wall초,CPU43.8524%,tilt0.063353rad. 실제지지정착단계에미도달했으므로정착수정의실제성공이나실패로쓰지않는다. 물체tilt0/양finger접촉0/전체side합의100%/RMS0.0405mm였고붉은site는더이상검출되지않았다.

원본영상의상부245pixel은높이37.18~79.86mm,하부13pixel은2.96~17.37mm다. centroid간격13.53mm로기존반경20mm결합조건에맞고,합치면기존높이76.306mm와표면기준을통과한다. 그러나기존코드는각연결조각에20pixel최소조건을먼저적용하여하부를버렸다. 2D영상연결조각과물체전체를동일시한earlyfilter결함이다. 실제부족한높이를허용하는문제와구분한다.

[PCL1.15.1 cylinder_segmentation.cpp](https://github.com/PointCloudLibrary/pcl/blob/pcl-1.15.1/doc/tutorials/content/sources/cylinder_segmentation/cylinder_segmentation.cpp)의입력cloud→모델→inlier선별패턴을다시읽었다. 예제는각image patch에독립적인물체크기조건을요구하지않는다. 이프로젝트의고정축/반경/이미지성분구조는PCL예제와다르며,자유축RANSAC나예제5cm허용오차를이식하지않는다.

v19후보는robust mode에서작은연결조각을3D결합까지보존한다. 최소20pixel이상anchor가하나있어야하며작은조각단독후보는금지한다. 기존centroid거리/높이span/95%합의/2mm/RMS/폭/합쳐진side최소20점조건을모두유지한다. 전체mask를무조건합치는방식이아니다. 기본legacy의20pixel사전필터는그대로둔다. 새로운판정metadata auxiliary_fragment_points로사용한작은조각의점수를기록한다.

최초음성시험의마스크가회색까지포함한오류는수정하고원래실패로그를보존했다. 올바른마스크의2 FAIL/1 PASS를확인한뒤3 PASS/2.01초. 아래조각을지우거나작은조각만남기면거부하며,무관한작은붉은영역을추가해도원통에합치지않는다. 두실제접근궤적234자세를고정해같은camera/원본검출조건으로재렌더링한시험1 PASS/7.71초(347 deselected),중심정답은추정후평가에만사용했다. 정적재현과새물리실행은별도이며고정10회평가를대신하지않는다.
