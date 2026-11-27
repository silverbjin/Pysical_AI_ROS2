"""Only explicit observation topics can be played. Never replay recorded clock."""
SAFE=('/ch15/mission_event','/ch15/mission_state')
def validate(domain,source_domain,topics):
    if type(domain) is not int or type(source_domain) is not int or not 1<=domain<=232 or not 0<=source_domain<=232 or domain==source_domain or tuple(topics)!=SAFE:
        raise ValueError('replay isolation rejected')
    return list(SAFE)

# Strict graph-only infrastructure allowance; not additional playback topics.
GRAPH_TYPES={
    SAFE[0]:'ch15_interfaces/msg/MissionEvent',
    SAFE[1]:'ch15_interfaces/msg/MissionStatus',
    '/clock':'rosgraph_msgs/msg/Clock',
    '/rosout':'rcl_interfaces/msg/Log',
    '/parameter_events':'rcl_interfaces/msg/ParameterEvent',
    '/events/read_split':'rosbag2_interfaces/msg/ReadSplitEvent',
}
def validate_graph_topic(name,types,owners):
    if name not in GRAPH_TYPES or set(types)!={GRAPH_TYPES[name]}:
        raise ValueError('unexpected replay graph topic/type: '+name)
    if name in (*SAFE,'/clock','/events/read_split') and set(owners)!={'rosbag2_player'}:
        raise ValueError('unexpected replay publisher: '+name)
    return True
