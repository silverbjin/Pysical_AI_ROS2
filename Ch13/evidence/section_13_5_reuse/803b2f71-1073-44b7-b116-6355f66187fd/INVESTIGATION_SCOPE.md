# Limited A settling investigation — 2026-11-02

User authorizes textbook-appropriate gate revision plus limited A settling investigation; not ROS2/Nav2 implementation this turn.
Hypotheses: H1 explicit Python PD damping + 2ms integration destabilizes low-inertia wrist modes; H2 leg gains alternate 20/1.5 vs50/5 at policy/nonpolicy ticks. First isolate H1 with actual model one-step velocity perturbations; no gain search. H2 inspect source; defer engine replay unless H1 fails to explain residual.
Budget: one local-model diagnostic, one candidate correction characterization, at most two full 25sim-second scenarios if warranted. No new policy training, contact/mass/gain retuning, driver/system changes.
Historical R1 FAIL remains FAIL. New gate gets separate revision and is frozen before fresh acceptance execution.
Gate design intent: root xy/yaw displacement and finite-window actual speed for navigation stop, bounded 3D posture/arm stow excursions for manipulation handoff; instantaneous oscillatory peaks remain diagnostics. Numerical instability and large arm motion must be corrected, not admitted by threshold relaxation.
