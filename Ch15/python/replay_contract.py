"""Only explicit observation topics can be played. Never replay recorded clock."""
SAFE=('/ch15/mission_event','/ch15/mission_state')
def validate(domain,source_domain,topics):
    if type(domain) is not int or type(source_domain) is not int or not 1<=domain<=232 or not 0<=source_domain<=232 or domain==source_domain or tuple(topics)!=SAFE:
        raise ValueError('replay isolation rejected')
    return list(SAFE)
