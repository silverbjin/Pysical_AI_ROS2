# Native Nav2 1.3.13 geometry comparison

Development-only reconstruction from v50 case990fa443-b46e-4790-9dce-a2f9515a8dec. No ROS initialization, action, physics or command is executed. Build against the installed nav2_regulated_pure_pursuit_controller library using CMake/ament; invoke rpp_geometry_probe input.txt.

The protected native getLookAheadPoint is exposed by subclassing, as in upstream component tests. The curvature expression is the upstream free function formula reproduced locally; it is not an exposed native member. The initial failed build tried to expose that free function as a member; the corrected probe only exposes getLookAheadPoint. Output columns: label, lookahead metres, interpolate-after-goal flag, carrot x/y, reconstructed curvature /metre.

input_metadata.json identifies saved poses. The saved final path is pruned at the nearest pose and transformed into that pose's base frame; the last two points are retained. This is NOT an exact timestamp-associated live transformed plan or a controller-command replay. Tests support geometry/parameter selection only, not physical success or deadline compliance. The .25m fixed curvature length reuses the current configured minimum lookahead; ordinary lookahead .45m and the original goal/collision checks remain unchanged.
