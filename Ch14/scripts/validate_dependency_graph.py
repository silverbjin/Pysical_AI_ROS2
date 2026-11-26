"""Evaluate effective target distributions before installing wheel overlay."""
import argparse
import json
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version


def wheel_rows(directory):
    rows = []
    for path in sorted(directory.glob('*.whl')):
        with ZipFile(path) as z:
            roots = [n for n in z.namelist() if n.endswith('.dist-info/METADATA') and n.count('/') == 1]
            if len(roots) != 1:
                raise ValueError(f'invalid root metadata: {path.name}')
            m = BytesParser().parsebytes(z.read(roots[0]))
        rows.append({'name': str(m['Name']), 'version': str(m['Version']),
                     'requires_dist': [str(r) for r in m.get_all('Requires-Dist', [])],
                     'requires_python': str(m['Requires-Python']) if m['Requires-Python'] else None,
                     'origin': path.name})
    return rows


def audit(system, wheels, environment):
    effective = {}
    for rows in (system, wheels):
        seen = set()
        for row in rows:
            key = canonicalize_name(row['name'])
            if key in seen:
                raise ValueError(f'ambiguous distribution: {key}')
            seen.add(key)
            Version(row['version'])
            effective[key] = row
    errors = set()
    extras = {k: {''} for k in effective}
    edges = set()
    while True:
        changed = False
        for key, row in effective.items():
            py = row.get('requires_python')
            if py and not SpecifierSet(py).contains(environment['python_full_version'], prereleases=True):
                errors.add(f'{key} {row["version"]}: Python {py}')
            for raw in row.get('requires_dist') or []:
                req = Requirement(raw)
                if req.marker and not any(req.marker.evaluate({**environment, 'extra': x}) for x in extras[key]):
                    continue
                target = canonicalize_name(req.name)
                edges.add((key, raw, target))
                actual = effective.get(target)
                if req.url or actual is None or not req.specifier.contains(actual['version'], prereleases=True):
                    errors.add(f'{key} {row["version"]} requires {raw}; found {actual["version"] if actual else "MISSING"}')
                if actual and not req.extras <= extras[target]:
                    extras[target].update(req.extras)
                    changed = True
        if not changed:
            break
    return {'status': 'FAIL' if errors else 'PASS', 'environment': environment,
            'effective': effective, 'edges': sorted(edges), 'errors': sorted(errors)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inspect', type=Path)
    p.add_argument('wheelhouse', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    data = json.loads(args.inspect.read_text())
    system = [{**item['metadata'], 'origin': item.get('metadata_location')} for item in data['installed']]
    env = default_environment()
    result = audit(system, wheel_rows(args.wheelhouse), env)
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
    print('DEPENDENCY_GRAPH', result['status'], 'distributions', len(result['effective']), 'edges', len(result['edges']))
    for error in result['errors']:
        print(error)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
