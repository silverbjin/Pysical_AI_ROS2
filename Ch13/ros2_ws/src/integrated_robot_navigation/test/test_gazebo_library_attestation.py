"""Filesystem fixtures are not native evidence; verify the attestation rules."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner

NAMES = ('libnavigation_gazebo_observer.so', 'libnavigation_gazebo_observation.so',
         'libnavigation_position_system.so')


@pytest.mark.parametrize('fault', ['', 'missing', 'wrong_library', 'wrong_hash', 'wrong_pid',
                                   'reused_pid', 'wrong_group', 'wrapper', 'ambiguous',
                                   'wrong_inode', 'wrong_device'])
def test_only_the_live_owned_native_child_can_attest_all_libraries(tmp_path, fault):
    proc = tmp_path/'proc'
    child = proc/'43'
    child.mkdir(parents=True)
    fields = ['S', '42', '42']+['0']*17
    fields[19] = '123'
    (child/'stat').write_text('43 (gz sim fixture) '+' '.join(fields))
    (child/'cmdline').write_bytes(b'/usr/bin/ruby\0/usr/bin/gz\0sim\0-r\0-s\0')
    expected = []
    for index,name in enumerate(NAMES):
        path = tmp_path/'selected/lib'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(('fixture library '+str(index)).encode())
        expected.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    maps = []
    for item in expected:
        stat = Path(item['path']).stat()
        maps.append(f'000-fff r-xp 00000000 {os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} '
                    f'{stat.st_ino} '+item['path'])
    members = [dict(pid=43,ppid=42,pgid=42,start_ticks=123)]
    if fault == 'missing': maps.pop()
    elif fault == 'wrong_library': maps[0] = maps[0].replace('selected/lib','other/lib')
    elif fault == 'wrong_hash': expected[0]['sha256'] = '0'*64
    elif fault == 'wrong_pid': members[0]['pid'] = 44
    elif fault == 'reused_pid': members[0]['start_ticks'] = 124
    elif fault == 'wrong_group': fields[2] = '99'
    elif fault == 'wrapper': (child/'cmdline').write_bytes(b'/bin/sh\0-c\0ruby /usr/bin/gz sim\0')
    elif fault == 'ambiguous': maps.append(maps[0].replace('selected/lib','other/lib'))
    elif fault in ('wrong_inode','wrong_device'):
        fields_map = maps[0].split(maxsplit=5)
        if fault == 'wrong_inode': fields_map[4] = str(int(fields_map[4])+1)
        else: fields_map[3] = 'ff:ff'
        maps[0] = ' '.join(fields_map)
    (child/'stat').write_text('43 (gz sim fixture) '+' '.join(fields))
    (child/'maps').write_text('\n'.join(maps))
    assert hasattr(runner,'attest_gazebo_libraries'), 'native Gazebo library attestation missing'
    if fault:
        with pytest.raises(RuntimeError,match='Gazebo'):
            runner.attest_gazebo_libraries(SimpleNamespace(pid=42),members,expected,proc_root=proc)
    else:
        value = runner.attest_gazebo_libraries(SimpleNamespace(pid=42),members,expected,proc_root=proc)
        assert value['pid'] == 43 and value['ppid'] == 42 and value['start_ticks'] == 123
        assert value['libraries'] == expected


@pytest.mark.parametrize('fault',['','missing_provider','wrong_provider_hash','wrong_version','wrong_provider_inode'])
def test_contact_experiment_requires_its_actual_dart_provider_in_the_same_native_pid(tmp_path,fault):
    proc=tmp_path/'proc';child=proc/'43';child.mkdir(parents=True)
    fields=['S','42','42']+['0']*17;fields[19]='123'
    (child/'stat').write_text('43 (gz fixture) '+' '.join(fields))
    (child/'cmdline').write_bytes(b'/usr/bin/ruby\0/usr/bin/gz\0sim\0-r\0-s\0')
    libraries=[];maps=[]
    for name in (*NAMES,'libdart.so.6.13.2'):
        file=tmp_path/name;file.write_bytes(('explicit fixture '+name).encode())
        libraries.append(dict(path=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        stat=file.stat()
        maps.append(f'000-fff r-xp 00000000 {os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} {stat.st_ino} {file}')
    provider=dict(library_path=libraries[-1]['path'],library_sha256=libraries[-1]['sha256'],header_version='6.13.2')
    if fault=='missing_provider':maps.pop()
    elif fault=='wrong_provider_hash':provider['library_sha256']='0'*64
    elif fault=='wrong_version':provider['header_version']='6.19.0'
    elif fault=='wrong_provider_inode':
        pieces=maps[-1].split(maxsplit=5);pieces[4]=str(int(pieces[4])+1);maps[-1]=' '.join(pieces)
    (child/'maps').write_text('\n'.join(maps))
    members=[dict(pid=43,ppid=42,pgid=42,start_ticks=123)]
    if fault:
        with pytest.raises(RuntimeError,match='Gazebo'):
            runner.attest_gazebo_libraries(SimpleNamespace(pid=42),members,libraries[:3],
                dart_provider=provider,proc_root=proc)
    else:
        result=runner.attest_gazebo_libraries(SimpleNamespace(pid=42),members,libraries[:3],
            dart_provider=provider,proc_root=proc)
        assert len(result['libraries'])==4 and result['pid']==43
