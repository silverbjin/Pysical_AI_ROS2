"""Code 12-5: finite/reproducible random motion; add --render to show the robot."""
import sys

from quadruped_rl.demo import main


if __name__ == "__main__":
    raise SystemExit(main(["--section", "12.2", *sys.argv[1:]]))
