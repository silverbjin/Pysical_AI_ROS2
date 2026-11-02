
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
