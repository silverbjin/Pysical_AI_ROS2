import collections, json, os, time, uuid
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
roots = [repo/'Ch13/evidence', Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')]
result = {'id': str(uuid.uuid4()), 'started_system_ns': time.time_ns(), 'roots': []}
for root in roots:
    total = 0; count = 0; top = []; groups = collections.Counter(); suffix = collections.Counter(); symlinks = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(directory)/name
            if path.is_symlink(): symlinks.append(str(path)); dirs.remove(name)
        for name in files:
            path = Path(directory)/name
            if path.is_symlink(): symlinks.append(str(path)); continue
            size = path.stat().st_size; total += size; count += 1
            relative = path.relative_to(root)
            group = '/'.join(relative.parts[:3]) if root == roots[0] else relative.parts[0]
            groups[group] += size; suffix[path.suffix] += size
            if size >= 30_000_000: top.append({'path': str(path), 'bytes': size})
    result['roots'].append({'path': str(root), 'bytes': total, 'files': count,
        'groups': groups.most_common(), 'suffixes': suffix.most_common(),
        'large_files': sorted(top, key=lambda item: -item['bytes']), 'symlinks': symlinks})
out = roots[0]/'section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/('retention-inventory-'+result['id']+'.json')
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'report': str(out), 'roots': [{k:v for k,v in item.items() if k in ('path','bytes','files','suffixes')} for item in result['roots']]}, indent=2))
