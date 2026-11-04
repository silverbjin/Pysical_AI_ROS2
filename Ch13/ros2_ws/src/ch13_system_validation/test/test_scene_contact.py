from moveit_msgs.msg import AllowedCollisionMatrix,AllowedCollisionEntry
from ch13_system_validation.scene_contact import permit_pair


def test_only_target_support_pair_changes_and_existing_robot_rules_remain():
    matrix=AllowedCollisionMatrix(entry_names=['robot','pick_target'],
        entry_values=[AllowedCollisionEntry(enabled=[False,False]),AllowedCollisionEntry(enabled=[False,False])])
    result=permit_pair(matrix,'pick_target','reuse_receiving_support',True)
    assert matrix.entry_names==['robot','pick_target']
    assert result.entry_names==['robot','pick_target','reuse_receiving_support']
    assert [list(row.enabled) for row in result.entry_values]==[[False,False,False],[False,False,True],[False,True,False]]
    restored=permit_pair(result,'pick_target','reuse_receiving_support',False)
    assert not any(any(row.enabled) for row in restored.entry_values)
