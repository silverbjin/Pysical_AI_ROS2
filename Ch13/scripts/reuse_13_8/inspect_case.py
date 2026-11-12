"""Student result reader. No ROS, actions, replay or file writes."""
import argparse
import json
from ch13_system_validation.case_reader import read_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    print(json.dumps(read_case(args.case), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
