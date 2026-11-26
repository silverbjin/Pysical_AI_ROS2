"""Actual wrong IO ONNX and invalid class manifest, no inference result accepted."""
import argparse,json
from pathlib import Path
from dataclasses import replace
import onnx
from onnx import helper,TensorProto
from ch14_ai_common.backends import digest
from ch14_ai_perception.model_slot import registry,load_candidate
def main():
    p=argparse.ArgumentParser();p.add_argument("registry",type=Path);p.add_argument("out",type=Path);a=p.parse_args()
    entries=registry(a.registry);entry=entries["yolov8s"];bad=a.registry.parent/"incompatible.onnx"
    # Small valid ONNX graph, intentionally incompatible input/output names and shapes.
    x=helper.make_tensor_value_info("wrong",TensorProto.FLOAT,[1,9]);y=helper.make_tensor_value_info("wrong_out",TensorProto.FLOAT,[1,9])
    graph=helper.make_graph([helper.make_node("Identity",["wrong"],["wrong_out"])],"fault",[x],[y])
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid("",13)],ir_version=8)
    onnx.checker.check_model(model);onnx.save(model,str(bad))
    rows=[]
    for name,e in [("incompatible_io",replace(entry,path=bad,sha256=digest(bad))),("wrong_reference_sha",replace(entry,reference_sha256="0"*64))]:
        try:load_candidate(e,"ort",2)
        except Exception as exc:rows.append(dict(case=name,status="PASS_REJECTED",reason=str(exc)))
        else:raise AssertionError("candidate accepted "+name)
    d=json.loads(a.registry.read_text());d["models"][1]["class_map_sha256"]="0"*64
    wrong=a.registry.parent/"wrong_registry.json";wrong.write_text(json.dumps(d))
    try:registry(wrong)
    except ValueError as exc:rows.append(dict(case="class_map",status="PASS_REJECTED",reason=str(exc)))
    else:raise AssertionError("wrong class map accepted")
    a.out.write_text(json.dumps(rows,indent=2)+"\n")
if __name__=="__main__":main()
