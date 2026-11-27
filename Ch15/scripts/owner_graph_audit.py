"""Read-only graph audit after all owned children exited."""
import json,os,subprocess,sys,time
from pathlib import Path
if len(sys.argv)>1 and sys.argv[1]=='--one':
    import rclpy
    from rclpy.node import Node
    rclpy.init();n=Node('ch15_residual_audit')
    samples=[]
    try:
        for _ in range(10):
            rclpy.spin_once(n,timeout_sec=.1)
            samples.append([list(x) for x in n.get_node_names_and_namespaces() if x!=(n.get_name(),n.get_namespace())])
        print(json.dumps(samples))
    finally:n.destroy_node();rclpy.try_shutdown()
    sys.exit(0 if not any(samples) else 1)
out=Path(sys.argv[1]);rows=[]
for domain in sys.argv[2:]:
    env=dict(os.environ,ROS_DOMAIN_ID=domain)
    p=subprocess.run([sys.executable,__file__,'--one'],env=env,capture_output=True,text=True,timeout=15)
    try:samples=json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:samples=None
    rows.append(dict(domain=domain,exit=p.returncode,samples=samples,stderr=p.stderr))
ok=bool(rows) and all(r['exit']==0 and r['samples'] is not None and not any(r['samples']) for r in rows)
out.write_text(json.dumps(dict(result='PASS' if ok else 'FAIL',domains=rows),indent=2)+'\n')
sys.exit(0 if ok else 1)
