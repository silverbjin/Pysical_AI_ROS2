"""Process-local CPU inference scheduling; original actor graph/inputs unchanged."""
import onnxruntime as ort
def cpu_session(path):
 options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
 options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
 options.add_session_config_entry('session.intra_op.allow_spinning','0')
 options.add_session_config_entry('session.inter_op.allow_spinning','0')
 return ort.InferenceSession(path,sess_options=options,providers=['CPUExecutionProvider'])
