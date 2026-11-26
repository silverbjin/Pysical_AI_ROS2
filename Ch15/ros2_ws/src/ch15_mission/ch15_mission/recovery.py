"""G03 base contract; no automatic recovery or retry until G08."""
def reset_allowed(active,unresolved,stopped,fresh_ready,latched):
    return not active and not unresolved and stopped and fresh_ready and not latched
def outcome(root_success,normal_verified,safety_requested):
    if safety_requested:return 'ABORTED'
    return 'COMPLETED' if root_success and normal_verified else 'ERROR'
