"""Check actual installed Jazzy plugin declarations without launching behavior_server."""
import json,sys
from pathlib import Path
from xml.etree import ElementTree as ET
import yaml
from ament_index_python.packages import get_package_share_directory,get_package_prefix
root=Path(__file__).resolve().parents[1]
cfg=yaml.safe_load((root/'config/nav2_behaviors_example.yaml').read_text())['behavior_server']['ros__parameters']
assert cfg['behavior_plugins']==['spin','backup','wait'] and cfg['cycle_frequency']==10.
share=Path(get_package_share_directory('nav2_behaviors'))
prefix=Path(get_package_prefix('nav2_behaviors'))
classes={}
for p in share.rglob('*.xml'):
    try:r=ET.parse(p).getroot()
    except ET.ParseError:continue
    for lib in r.iter('library'):
        for c in lib.findall('class'):
            if c.get('type'):classes[c.get('type')]=dict(xml=str(p),library=lib.get('path'),base=c.get('base_class_type'))
result={}
for n in cfg['behavior_plugins']:
    plugin=cfg[n]['plugin'];row=classes[plugin]
    assert row['base']=='nav2_core::Behavior'
    library=row['library'];matches=list((prefix/'lib').glob('lib'+Path(library).name+'.so'))+list((prefix/'lib').glob(Path(library).name+'.so'))
    assert matches,(plugin,row)
    result[n]=dict(plugin=plugin,**row,shared_object=str(matches[0]))
Path(sys.argv[1]).write_text(json.dumps(dict(result='PASS',installed_plugins=result,physical_motion='NOT_RUN'),indent=2)+'\n')
print('G08_NAV2_PLUGIN_SCHEMA_PASS',json.dumps(result))
