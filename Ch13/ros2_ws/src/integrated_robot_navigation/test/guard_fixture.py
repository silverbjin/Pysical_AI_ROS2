"""Hand-defined measured state, not native engine acceptance evidence."""
from integrated_robot_navigation.samples import Sample, SensorBundle

CARRY = (0., 1.2, -2., 0., .8, 0.)
OWNERS = ('raw', 'smoothed', 'final', 'legs', 'joints', 'imu', 'contacts', 'body', 'scan', 'carry')


def bundle(model, ros=1_000_000_000, wall=10_000_000_000, generation=0):
    positions = {name: 0. for name in model.limits}
    for prefix in ('fr', 'fl', 'rr', 'rl'):
        positions[prefix+'_thigh_joint'] = -.5
        positions[prefix+'_calf_joint'] = 1.
    positions.update({f'arm_joint_{i}': q for i, q in enumerate(CARRY, 1)})
    sample = lambda data, frame: Sample(ros, wall, 0, ros, frame, data)
    return SensorBundle(
        sample(dict(position=positions, velocity={name: 0. for name in positions}), 'base_link'),
        sample(dict(acceleration=(0., 0., 9.81), angular_velocity=(0., 0., 0.)), 'base_link'),
        sample(dict(names=('fr_foot', 'fl_foot', 'rr_foot', 'rl_foot'),
                    points=((.25, -.18, 0.), (.25, .18, 0.), (-.25, -.18, 0.), (-.25, .18, 0.)),
                    forces=(30.,)*4, touching=(True,)*4, unexpected_contacts=0), 'odom'),
        sample(dict(position=(0., 0., .46), orientation=(0., 0., 0., 1.),
                    linear_velocity=(0., 0., 0.), angular_velocity=(0., 0., 0.),
                    child_frame_id='base_footprint'), 'odom'),
        sample(dict(ranges=(10.,)*360, hits=(False,)*360, range_min=.05, range_max=10.,
                    angle_min=-3.141592653589793, angle_increment=6.283185307179586/360), 'lidar_link'),
        sample(dict(ready=True, generation=generation, model_sha256=model.model_sha256), 'base_link'))


def command(ros=1_000_000_000, wall=10_000_000_000, generation=0, value=(.006, 0., .01)):
    return Sample(ros, wall, generation, wall, 'nav_base', value)
