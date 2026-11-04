"""Read a closed bag and write a new, independent recording verdict."""
import argparse,json,sys
from pathlib import Path
from ch13_system_validation.bag_inspection import inspect_bag


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bag',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output)
    if out.exists():raise ValueError('existing verdict preserved; choose a new output')
    result=inspect_bag(args.bag)
    with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result,indent=2));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
