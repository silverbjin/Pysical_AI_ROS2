"""DDS publication order is independent of adjustable SYSTEM timestamps.

The existing source-time generation cutoff remains fail-closed. A detected
SYSTEM backstep makes a later epoch reset ambiguous, requiring a new receiver.
This does not change ROS/monotonic leases or original source metadata.
"""


def metadata_field(info,name):
    return info.get(name) if isinstance(info,dict) else getattr(info,name,None)


class CommandOrder:
    def __init__(self):
        self.last_publication_sequence=-1
        self.last_source_system_ns=-1
        self.last_rmw_received_system_ns=None
        self.system_backstep=False

    def accept(self,info,cutoff_system_ns):
        source=metadata_field(info,'source_timestamp')
        sequence=metadata_field(info,'publication_sequence_number')
        if type(source) is not int or source<=0:return False,'missing_dds_source_time'
        if type(sequence) is not int or sequence<=0:return False,'missing_dds_publication_sequence'
        if sequence<=self.last_publication_sequence:return False,'duplicate_or_reordered'
        if self.last_source_system_ns>0 and source<self.last_source_system_ns:
            self.system_backstep=True
        if source<cutoff_system_ns:return False,'source_before_epoch'
        self.last_publication_sequence=sequence
        self.last_source_system_ns=source
        received=metadata_field(info,'received_timestamp')
        self.last_rmw_received_system_ns=received if type(received) is int and received>0 else None
        return True,''

    def snapshot(self):
        return dict(publication_sequence=self.last_publication_sequence,
            source_system_ns=self.last_source_system_ns,
            rmw_received_system_ns=self.last_rmw_received_system_ns,
            system_backstep=self.system_backstep,
            epoch_reset_requires_new_receiver=self.system_backstep)
