"""Ch12.8 deployment contract adapted to standalone Ch13 (optional policy only)."""
import numpy as np
from .contract import load_contract
from .locomotion_core import PolicyContract,ControllerCore

def validate_manifest(manifest):
    if (manifest.get('task') not in ('locomotion','robust') or manifest.get('observation_schema')!='locomotion-v1-48'
        or manifest.get('observation_size')!=48 or manifest.get('action_size')!=12 or manifest.get('normalization')!='none'):
        raise ValueError('requires unnormalized 48-D locomotion / 12-D action bundle')

def create_policy_core():
    c=load_contract();g=c.groups['legs']
    contract=PolicyContract(g.names,np.array(g.nominal),np.column_stack([g.lower,g.upper]),np.full(12,.35),.02)
    return ControllerCore(contract)
