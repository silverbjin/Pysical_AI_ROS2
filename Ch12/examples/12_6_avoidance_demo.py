import sys
from quadruped_rl.goal_demo import main

if __name__=='__main__':
    raise SystemExit(main(['--task','avoidance',*sys.argv[1:]]))
