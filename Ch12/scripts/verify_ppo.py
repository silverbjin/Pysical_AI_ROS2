"""Short, real PPO updates, serial/subprocess workers and saved inference."""
import argparse
import json
from pathlib import Path

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

from quadruped_rl.ppo import train,play


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    results = []
    for task,backend,steps in [('locomotion','dummy',2048),('goal','dummy',2048),
                               ('goal','subproc',128)]:
        run = args.output/f'{task}_{backend}'
        result = train(run,task=task,backend=backend,total_timesteps=steps,n_envs=2,
            n_steps=32 if steps == 128 else 128,batch_size=64,n_epochs=2,
            eval_every=64 if steps == 128 else 512,eval_episodes=2,
            checkpoint_every=64 if steps == 128 else 512,max_episode_steps=200)
        assert result['parameter_delta'] > 0 and result['status'] == 'PASS'
        replay = play(run,steps=200,trajectory_path=run/'trajectory.csv',
                      frame_path=run/'inference.png',expected_task=task)
        assert replay['steps'] == 200
        assert (run/'best_model/best_model.zip').is_file()
        events = next((run/'tensorboard').rglob('events.out.tfevents.*'))
        accumulator = EventAccumulator(str(events)).Reload()
        tags = accumulator.Tags()['scalars']
        assert 'train/value_loss' in tags and 'train/entropy_loss' in tags
        assert 'eval/mean_reward' in tags
        if task == 'goal':
            assert 'eval/success_rate' in tags
        results.append(dict(training=result,replay=replay,tensorboard_scalar_tags=tags))
    report = dict(status='PASS',total_training_transitions=4224,runs=results,
                  limitation='Smoke training only; walking and navigation proficiency unproven')
    (args.output/'ppo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',training_transitions=4224)))


if __name__ == '__main__':
    main()
