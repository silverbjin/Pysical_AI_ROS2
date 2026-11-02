"""Process-local prepared evidence; no ROS parameter can supply this receipt."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .carry_profile import validate_profile


def _identity(profile,model,engine,execution_profile):
    raw=json.dumps(dict(profile=asdict(profile),model=model.model_sha256,engine=engine,
        execution_profile=execution_profile),sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()


def _stat(path):
    value=path.stat()
    return value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns


def _files(profile,engine):
    entry=profile.native_evidence[engine]
    reference=Path(entry['path']).absolute()
    result=reference.resolve(strict=True)
    data=json.loads(result.read_text());root=result.parent
    # Keep the lexical reference for later stat: resolving it away here would
    # miss an alias repointed after preparation while the old target survives.
    files={reference:_stat(reference)};resolved={result}
    for artifact in data['artifacts']:
        relative=Path(artifact['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('evidence path')
        path=root/relative;actual=path.resolve(strict=True)
        if not actual.is_relative_to(root) or actual in resolved:raise ValueError('evidence path')
        files[path]=_stat(path);resolved.add(actual)
    return files


class PreparedAdmission:
    def __init__(self,identity,files,result):
        self.identity,self.files,self.result=identity,files,result

    def check(self,profile,model,engine,*,execution_profile=None):
        if not self.result[0]:return self.result
        try:
            if self.identity!=_identity(profile,model,engine,execution_profile):
                raise ValueError('admission profile or engine changed')
            if any(_stat(path)!=expected for path,expected in self.files.items()):
                raise ValueError('evidence changed since preparation')
        except (OSError,ValueError,TypeError,KeyError):
            self.result=False,'prepared_admission_changed' # sticky: no automatic revalidation
        return self.result


def prepare_admission(profile,model,engine,*,execution_profile=None,checker=validate_profile):
    """Hash before control starts and reject changes during that heavy check."""
    identity=_identity(profile,model,engine,execution_profile)
    try:
        before=_files(profile,engine)
        result=(checker(profile,model,engine) if execution_profile is None else
            checker(profile,model,engine,execution_profile=execution_profile))
        after=_files(profile,engine)
        if before!=after:result=False,'evidence_changed_during_preparation'
        return PreparedAdmission(identity,after,result)
    except (OSError,ValueError,TypeError,KeyError):
        return PreparedAdmission(identity,{},(False,'invalid_native_evidence'))
