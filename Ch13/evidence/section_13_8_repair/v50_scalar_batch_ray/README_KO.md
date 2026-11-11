# v50 ray 비교 자료

comparison.json은 v49 scalar source에서 구현 전 실행한 결과다. probe_original_v49.py가 당시 도구이며 v49 소스에만 사용한다. 이후 ray_scan이 batch를 고를 수 있으므로 재현용 probe.py는 scalar 기준을 직접 고정해 비교가 자기 자신을 검증하지 않도록 했다. 새 출력 디렉터리를 인자로 주거나 기본 v50_scalar_batch_reproduction을 사용하며 기존 출력을 거절한다.

로컬 v49 UUID0e7456d4-adcd-4ffc-873b-4ab4a054afa4의 raw archive와 동결된 외부 자산이 필요하다. 이 도구는 설치된 native MuJoCo3.13.0/env.sh에서 실행하는 개발자용 부품 조사이며 학생 기본 실습이나 실제 임무 성공 판정이 아니다. eligibility.json은 실제 Level2 모델의 world 및 centred cylinder 조건을 확인한 자료다. 회전된 offset 몸체의 알려진 이슈3731은 runtime eligibility guard와 scalar fallback으로 배제한다.
