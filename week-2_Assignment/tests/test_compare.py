from clibot.compare import _calc_tokens_per_second


def test_calc_tokens_per_second():
    latency_s = 2.0
    ttft_s = 0.5
    completion_tokens = 150
    # Generation time = 2.0 - 0.5 = 1.5
    # tok/s = 150 / 1.5 = 100.0

    result = _calc_tokens_per_second(latency_s, ttft_s, completion_tokens)
    assert result == 100.0


def test_calc_tokens_per_second_no_ttft():
    latency_s = 2.0
    ttft_s = None
    completion_tokens = 100
    # Generation time = 2.0 - 0.0 = 2.0
    # tok/s = 100 / 2.0 = 50.0

    result = _calc_tokens_per_second(latency_s, ttft_s, completion_tokens)
    assert result == 50.0


def test_calc_tokens_per_second_zero_tokens():
    result = _calc_tokens_per_second(2.0, 0.5, 0)
    assert result is None


def test_calc_tokens_per_second_zero_generation_time():
    result = _calc_tokens_per_second(1.0, 1.0, 100)
    assert result is None
