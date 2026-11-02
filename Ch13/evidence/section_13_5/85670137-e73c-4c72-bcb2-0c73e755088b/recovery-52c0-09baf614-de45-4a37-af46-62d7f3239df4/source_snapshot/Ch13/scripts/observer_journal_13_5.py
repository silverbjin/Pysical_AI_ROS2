"""Immutable primitive capture records; full JSON export waits for engine/ROS join.

Only Ch13-created, owner/hash-verified files enter the post-join reader. Only
the builtin float scalar constructor is permitted; other class resolution
and persistent references are forbidden. No external
or uploaded pickle is a supported input. The permanent interchange is JSON.
"""
import io
import json
import math
import pickle
import struct

MAGIC=b'CH13OBS1'
MAX_RECORD_BYTES=8*1024*1024


def _primitive(value):
    ancestors=set()
    def visit(item):
        kind=type(item)
        if kind in (str,int,bool,type(None)):return item
        # ROS fixed float64 arrays expose numpy.float64, which the original
        # JSON encoder accepts as a float subclass. Store the identical native
        # float, without adding numpy class resolution to the capture reader.
        if isinstance(item,float):
            result=float(item)
            if not math.isfinite(result):raise ValueError('non-finite capture value')
            return item if kind is float else result
        if kind not in (list,tuple,dict):raise ValueError('non-primitive capture value: '+str(kind))
        identity=id(item)
        if identity in ancestors:raise ValueError('cyclic capture value')
        ancestors.add(identity)
        try:
            if kind is dict:
                if any(type(key) is not str for key in item):raise ValueError('capture keys must be strings')
                normalized={key:visit(value) for key,value in item.items()}
                return item if all(normalized[key] is value for key,value in item.items()) else normalized
            normalized=[visit(value) for value in item]
            return item if all(a is b for a,b in zip(normalized,item)) else kind(normalized)
        finally:ancestors.remove(identity)
    return visit(value)


def encode_record(row):
    # The witness's complete finite/schema walk is post-join work, like its
    # physical assessment. Motor/sensor admission checks are unchanged. Exact
    # builtin containers/scalars stay inside the C pickler; numeric subclasses
    # are normalized only when encountered, without a second Python graph walk.
    output=io.BytesIO();_CaptureWriter(output,protocol=5).dump(row);payload=output.getvalue()
    if not 0<len(payload)<=MAX_RECORD_BYTES:raise ValueError('capture record size')
    return struct.pack('>Q',len(payload))+payload


class _CaptureWriter(pickle.Pickler):
    def reducer_override(self,value):
        if value is float:return NotImplemented
        if isinstance(value,float):return (float,(float(value),))
        raise ValueError('non-primitive capture value: '+str(type(value)))


class _PrimitiveReader(pickle.Unpickler):
    def find_class(self,module,name):
        if (module,name)==('builtins','float'):return float
        raise ValueError('capture class resolution forbidden')
    def persistent_load(self,pid):raise ValueError('capture persistent reference forbidden')


def read_records(source):
    if source.read(len(MAGIC))!=MAGIC:raise ValueError('capture journal magic/version')
    while True:
        header=source.read(8)
        if header==b'':return
        if len(header)!=8:raise ValueError('truncated capture length')
        length=struct.unpack('>Q',header)[0]
        if not 0<length<=MAX_RECORD_BYTES:raise ValueError('capture record size')
        payload=source.read(length)
        if len(payload)!=length:raise ValueError('truncated capture record')
        buffer=io.BytesIO(payload);row=_PrimitiveReader(buffer).load()
        if buffer.tell()!=length:raise ValueError('capture trailing payload')
        _primitive(row)
        if type(row) is not dict or set(row)!={'kind','value'} or type(row['kind']) is not str:
            raise ValueError('capture record schema')
        yield row
