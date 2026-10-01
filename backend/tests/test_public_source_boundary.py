"""The public snapshot must remain usable without disclosing candidate answers."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_excluded_private_material_is_not_present():
    policy = json.loads((ROOT / 'docs/public-source-policy.json').read_text(encoding='utf-8-sig'))
    assert policy['public_parent'] == 'ca87754f320be5c73d05bfb1dfaf6cc7cf5e3e7a'
    assert len(policy['excluded_files']) == 78
    assert not [name for name in policy['excluded_files'] if (ROOT / name).exists()]


@pytest.mark.parametrize('number', range(1, 19))
def test_qnet_candidates_are_not_bundled_as_grading_or_wiring_answers(number):
    path = ROOT / 'problems' / f'qnet_electrician_practical_{number:03d}' / 'answer.json'
    answer = json.loads(path.read_text(encoding='utf-8-sig'))
    for field in ('socket_pin_answers', 'required_connections', 'expected_nets',
                  'allowed_alternatives', 'wiring_connections'):
        assert not answer.get(field), (number, field)
    assert answer['verification']['status'] == 'unverified'
    if number == 10:
        assert len(answer['operation_tests']) == 5
