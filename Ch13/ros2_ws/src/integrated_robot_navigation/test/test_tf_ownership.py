"""Break: endpoint count alone hides duplicate authority for the same TF child."""
import copy
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import verify_navigation_13_5 as verify


def observations(model):
    rows = []
    for joint in ET.fromstring(model.urdf).findall('joint'):
        rows.append(dict(parent=joint.find('parent').get('link'),
            child=joint.find('child').get('link'), gid='01'*16, stamp_ns=0,
            source_timestamp=123, topic='/tf_static' if joint.get('type') == 'fixed' else '/tf'))
    rows.extend(dict(parent='odom', child=child, gid='02'*16, stamp_ns=123,
                     source_timestamp=124, topic='/tf')
                for child in ('base_footprint', 'nav_base'))
    return rows


def test_tf_requires_complete_single_authority_tree(nav_robot_model):
    rows = observations(nav_robot_model)
    assert verify.assess_tf_ownership(rows, nav_robot_model)
    assert not verify.assess_tf_ownership(rows[:-1], nav_robot_model)
    assert not verify.assess_tf_ownership([], nav_robot_model)


@pytest.mark.parametrize('change', ['owner', 'parent', 'topic', 'zero_gid', 'missing_source'])
def test_tf_records_reject_owner_parent_or_unattributed_replacement(nav_robot_model, change):
    rows = observations(nav_robot_model)
    extra = copy.deepcopy(rows[-1])
    if change == 'owner':
        extra['gid'] = '03'*16
    elif change == 'parent':
        extra['parent'] = 'map'
    elif change == 'topic':
        extra['topic'] = '/tf_static'
    elif change == 'zero_gid':
        extra['gid'] = '00'*16
    else:
        del extra['source_timestamp']
    rows.append(extra)
    assert not verify.assess_tf_ownership(rows, nav_robot_model)
