# G01 source identity and CI preparation
- Local test source: 19 Git blobs verified equal to remote G01 commit 0f3c2acfa3f5be9e295a39a9b7af6625265ce48a; all 14 legacy chapter subtrees unchanged against base 1931cac92585fc155357880b584c72c76d67257c.
- CI separates Ubuntu 24.04 static T01/T02, G00 scoped ROS image probe (drift/missing asset negative and mock environment positive), and native Harmonic SDF validation. Existing Ch14 pinned images are reused as candidates, not claimed as newly verified.
- No simulation or external model download, no actual DDS, no Ch13/14 reruns. GitHub Actions actual run/result pending. This is infrastructure preparation, not new acceptance.
- CI paths currently cover Ch15; further installed DDS build/test and manual physical jobs are future G02–G05 scope. Existing common document preflight is untouched. 
