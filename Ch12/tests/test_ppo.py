"""Real PPO integration tests; install the train extra to run these."""
from pathlib import Path
import json

import numpy as np
import pytest

pytest.importorskip('stable_baselines3')
from quadruped_rl.ppo import train, play, load_bundle


def test_real_training_save_evaluate_reload(tmp_path):
    result = train(tmp_path/'run', total_timesteps=128, n_envs=2,
                   n_steps=32, batch_size=32, n_epochs=2,
                   eval_every=64, eval_episodes=1, max_episode_steps=40,
                   checkpoint_every=64, seed=7)
    assert result['parameter_delta'] > 0
    assert result['timesteps'] == 128
    root = tmp_path/'run'
    assert (root/'final_model.zip').is_file()
    assert (root/'best_model/best_model.zip').is_file()
    assert list((root/'checkpoints').glob('*.zip'))
    assert list((root/'tensorboard').rglob('events.out.tfevents.*'))
    assert (root/'evaluation/evaluations.npz').is_file()
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['task'] == 'locomotion'
    assert manifest['observation_schema'] == 'locomotion-v1-48'
    assert manifest['eval_callback_frequency'] == 32
    report = play(root, steps=20, seed=4)
    assert report['steps'] == 20 and np.isfinite(report['reward_total'])
    with pytest.raises(ValueError, match='task'):
        load_bundle(root, expected_task='goal')
    model, env, _ = load_bundle(root)
    try:
        obs, _ = env.reset(seed=4)
        act, _ = model.predict(obs, deterministic=True)
        assert act.shape == (12,) and np.isfinite(act).all()
    finally:
        env.close()


@pytest.mark.parametrize('kwargs', [dict(n_envs=0), dict(n_steps=1),
    dict(batch_size=3), dict(total_timesteps=0), dict(eval_every=0),
    dict(device='mystery'), dict(backend='mystery')])
def test_invalid_config_has_no_output(tmp_path, kwargs):
    with pytest.raises(ValueError):
        train(tmp_path/'invalid', **kwargs)
    assert not (tmp_path/'invalid').exists()


def test_refuse_overwrite(tmp_path):
    (tmp_path/'existing').mkdir()
    with pytest.raises(FileExistsError):
        train(tmp_path/'existing', total_timesteps=64)


def test_goal_train_and_reject_same_size_wrong_weights(tmp_path):
    from stable_baselines3 import PPO
    result = train(tmp_path/'goal',task='goal',total_timesteps=64,n_envs=1,
        n_steps=32,batch_size=32,n_epochs=1,eval_every=32,eval_episodes=1,
        checkpoint_every=32,max_episode_steps=20)
    assert result['parameter_delta'] > 0
    manifest = json.loads((tmp_path/'goal/manifest.json').read_text())
    assert manifest['evaluation_env_kwargs']['goal_mode'] == 'terminate'
    assert play(tmp_path/'goal',steps=5,expected_task='goal')['steps'] == 5
    model = PPO.load(tmp_path/'goal/final_model.zip')
    model.chapter12_schema = 'locomotion-v1-48'
    model.save(tmp_path/'goal/wrong_task.zip')
    with pytest.raises(ValueError,match='task/schema'):
        load_bundle(tmp_path/'goal',model_name='wrong_task.zip',expected_task='goal')
    model.chapter12_schema = manifest['observation_schema']
    model.chapter12_env_kwargs = {'max_episode_steps':500}
    model.save(tmp_path/'goal/wrong_env.zip')
    with pytest.raises(ValueError,match='environment'):
        load_bundle(tmp_path/'goal',model_name='wrong_env.zip')
