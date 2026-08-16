from tools.validate_problem import main


def test_validation_cli_returns_success_for_sample(capsys):
    exit_code = main(["problems/practice_001"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[정상] practice_001" in output
    assert "경고 1개" in output

