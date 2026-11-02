
## 2026-11-02 explicit discrete equilibrium and book policy

Own Apache-2.0 modules `native_equilibrium.py`, the optional bindings in
`native_xyz.py`/`native_complete_xyz.py`, and the gait/process identity checks
use existing NumPy, Eigen and JSON dependencies. No external source was copied.
The full energy/Jacobian oracle is independent diagnostic code under
`Ch13/diagnostics/position_force`. New fixed failure tests retain original
failures and verify all20 predicted commands in an independent joint order.
The optional Gazebo same-cycle path identifies the linked equilibrium library
SHA before accepting work. Its owner releases the plan with the optimizer.
The recorded raw preclip P value is a tracking diagnostic in this explicit
mode; actual actuator limits and measured contact release are unchanged.
The default calibration lease is20s; legacy10s and bounded profile validation
remain. See `Ch13/docs/SECTION_13_5_BOOK_ACCEPTANCE_POLICY_KO.md` for the user's
book-example gate policy and limits of the local quasistatic predictor.

## 2026-11-02 crawl geometry reuse and explicit measured fault stop

Same-cycle crawl now shares its already owned NativeReferenceEnvelope plan
with nominal IK and both shift-search routes. The original28-sample clearance
and joint residuals are retained; repeated Python clearance work is removed
only when the identical native result is available. Default routes remain.
No new geometry algorithm, worker, handle, stale result or fallback was added.
The contact joiner retains256 input/pair/expiry metadata events using existing
capture/receipt clocks; its200ms dual-age and exact matching are unchanged.
A held pre-unload SHIFT contacts:wall_age fault can begin one fresh read-only
measurement window after explicit stop, with no motion or fault clearing.
The first fresh stop sample must pass current support/freshness/clock checks;
any invalid observation permanently closes that window, without automatic retry.
Existing1s dual-clock settle and unique-capture requirements remain.

The same-cycle support LP now injects the existing NativeMassEvaluator contact
terms instead of repeating URDF gravity/Jacobian work in Python. Optional
injection is selected before evaluation, never as an error fallback. The LP,
friction, physical20/30Nm checks and independent residual validation remain
unchanged; current model binding/dimensions/finiteness are checked. Other
routes retain their original default terms. A support-stage timing boundary
distinguishes LP cost from the preceding geometry calculation.

Explicit Gazebo support planning also constrains and minimizes the original20
actuator command caps using the same validated discrete affine terms. Original
continuous physical torque rows, friction/force/wrench equilibrium and all primal
checks remain; default statics remains unchanged. The support model owns one
immutable arithmetic handle, closed with the machine, without a worker or motor
authority. Predicted actuator commands are recorded without clipping. This is
still a necessary local support model, not a full path or actual release proof.

## 2026-11-02 contact/clock capture boundary

Actual DDS delayed-Clock regression reproduces loss of both exact-capture inputs
before numerical submission, without a physics engine or control load. Future
captures now remain bounded/pending until original ROS Clock catches up; the
clock callback may release them. They are never used early or restamped, and
original200ms dual-age expiry/duplicate receipts/rollback stop remain. Existing
bounded metadata connects native generation/transport-call return, DDS original
source/receive MessageInfo, callback entry, pair selection/publication and
controller cache admission by capture/epoch/sequence. Native publish return
is explicitly not subscriber delivery. No new worker, dependency, command
authority, physics parameter, full-frame log stream or clock write was added.
