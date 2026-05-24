from core.executive_decision_board import build_decision_board, parse_pipeline_steps


def test_decision_board_blocks_when_foundation_data_is_missing():
    board = build_decision_board({"1": "done"})

    assert board.status == "データ不足"
    assert board.readiness_score < 40
    assert "決算書" not in board.next_decision
    assert any("財務" in q for q in board.blocking_questions)


def test_decision_board_surfaces_financial_validation_before_approval():
    steps = {str(i): "done" for i in range(1, 15)}
    board = build_decision_board(steps)

    assert board.status == "数値検証待ち"
    assert board.next_decision == "戦略をPL/CFで検証する"
    assert any("キャッシュフロー" in q for q in board.blocking_questions)


def test_decision_board_becomes_executable_after_all_steps():
    steps = {str(i): "done" for i in range(1, 19)}
    board = build_decision_board(steps)

    assert board.status == "実行判断可能"
    assert board.readiness_score == 100
    assert board.next_decision == "実行判断"
    assert any("責任者" in gate for gate in board.quality_gates)


def test_parse_pipeline_steps_handles_client_notes_json():
    project = {"notes": '{"pipeline_steps": {"1": "done", "2": "in_progress"}}'}

    assert parse_pipeline_steps(project) == {"1": "done", "2": "in_progress"}
