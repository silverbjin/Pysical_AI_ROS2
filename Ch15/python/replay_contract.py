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

RESTRICTED=(*SAFE,'/clock','/events/read_split')
UNKNOWN_OWNERS={'','_NODE_NAME_UNKNOWN_'}
class EndpointAudit:
    """Exact endpoint identity through graph teardown, never authorize unknown new writers."""
    def __init__(self):
        self.bound={};self.metadata_loss=[]
    def observe(self,name,types,endpoints,completed=False):
        if name not in GRAPH_TYPES or set(types)!={GRAPH_TYPES[name]}:
            raise ValueError('unexpected replay graph topic/type: '+name)
        if any(e['type']!=GRAPH_TYPES[name] for e in endpoints):
            raise ValueError('endpoint type mismatch: '+name)
        owners=[e['owner'] for e in endpoints]
        if name not in RESTRICTED:return sorted(set(owners))
        if len(endpoints)!=1:raise ValueError('restricted publisher count: '+name)
        e=endpoints[0];gid=e['gid']
        if not gid or not any(c!='0' for c in gid):raise ValueError('invalid endpoint gid')
        if e['owner']=='rosbag2_player':
            if name in self.bound and self.bound[name]!=gid:raise ValueError('publisher GID changed: '+name)
            self.bound[name]=gid
        elif completed and e['owner'] in UNKNOWN_OWNERS and self.bound.get(name)==gid:
            detail=dict(topic=name,owner=e['owner'],gid=gid)
            if detail not in self.metadata_loss:self.metadata_loss.append(detail)
        else:raise ValueError('unexpected replay publisher: '+name+' '+repr(e))
        return ['rosbag2_player']
