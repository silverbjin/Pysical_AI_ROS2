import numpy as np
import pytest
from ch14_ai_common.benchmark import measure, seeded_input, summarize
from ch14_ai_common.yolo import preprocess, postprocess
from ch14_ai_common.export import demo_inputs, demo_model


def test_t01_measure_excludes_warmup_and_counts_sync():
    events = []
    clock = iter([0, 1_000_000, 2_000_000, 5_000_000])
    values, stats = measure(lambda: events.append('forward'), iterations=2,
                            synchronize=lambda: events.append('sync'), clock=lambda: next(clock))
    assert values == [1., 3.] and stats['samples'] == 2 and stats['mean_ms'] == 2.
    assert events.count('forward') == 12 and events.count('sync') == 5
    assert seeded_input().shape == (1, 3, 640, 640)
    np.testing.assert_array_equal(seeded_input(), seeded_input())


@pytest.mark.parametrize('values', [[], [-1], [np.nan], [np.inf]])
def test_t01_invalid_timing(values):
    with pytest.raises(ValueError):
        summarize(values)


def test_t03_actual_untrained_torch_forward():
    import torch
    x = demo_inputs()
    assert x.shape == (100, 9) and x.dtype == np.float32
    state = torch.random.get_rng_state().clone()
    a, b = demo_model(), demo_model()
    assert torch.equal(state, torch.random.get_rng_state())
    with torch.inference_mode():
        y, z = a(torch.from_numpy(x)), b(torch.from_numpy(x))
    assert y.shape == (100, 6) and torch.isfinite(y).all()
    torch.testing.assert_close(y, z, atol=0, rtol=0)


def test_t04_letterbox_nms_non_square_and_classwise():
    img = np.zeros((480, 640, 3), np.uint8)
    img[:, :, 2] = 255
    tensor, meta = preprocess(img)
    assert tensor.shape == (1, 3, 640, 640) and tensor.dtype == np.float32 and tensor.flags.c_contiguous
    assert tensor[0, 0, 80, 0] == 1 and tensor[0, 2, 80, 0] == 0
    assert tensor[0, 0, 0, 0] == np.float32(114 / 255)
    assert (meta.left, meta.top, meta.sx, meta.sy) == (0, 80, 1., 1.)
    output = np.zeros((1, 84, 8400), np.float32)
    for i, cls, score in ((0, 0, .9), (1, 0, .8), (2, 1, .7)):
        output[0, :4, i] = [120, 180, 40, 40]
        output[0, 4 + cls, i] = score
    result = postprocess(output, meta)
    assert [x.class_id for x in result] == [0, 1]
    assert all(x.xyxy == (100., 80., 140., 120.) for x in result)
    assert postprocess(np.zeros_like(output), meta) == []


@pytest.mark.parametrize('image', [None, np.zeros((0, 2, 3), np.uint8), np.zeros((2, 2), np.uint8), np.zeros((2, 2, 3), np.float32)])
def test_t04_invalid_image(image):
    with pytest.raises(ValueError):
        preprocess(image)


def test_t04_nonfinite_and_wrong_shape():
    _, meta = preprocess(np.zeros((40, 80, 3), np.uint8))
    a = np.zeros((1, 84, 8400), np.float32)
    a[0, 0, 0] = np.nan
    for bad in (a, a[:, :, :1], a.astype(np.float64)):
        with pytest.raises(ValueError):
            postprocess(bad, meta)
