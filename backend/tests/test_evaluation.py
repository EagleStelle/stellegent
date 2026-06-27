from stellegent.evaluation import evaluate_lecture, score_summary, score_transcript


def test_transcript_exact_match_has_full_recognition():
    scores = score_transcript(
        hypothesis="Hello   world",
        reference="hello world",
    )

    assert scores is not None
    assert scores["wer"]["error_rate"] == 0
    assert scores["wer"]["recognition_rate"] == 1
    assert scores["cer"]["error_rate"] == 0
    assert scores["cer"]["recognition_rate"] == 1


def test_transcript_edit_operations_are_counted():
    substitution = score_transcript(
        hypothesis="hello wurld",
        reference="hello world",
    )
    insertion = score_transcript(
        hypothesis="hello big world",
        reference="hello world",
    )
    deletion = score_transcript(
        hypothesis="hello",
        reference="hello world",
    )

    assert substitution is not None
    assert insertion is not None
    assert deletion is not None
    assert substitution["wer"]["substitutions"] == 1
    assert substitution["wer"]["error_rate"] == 0.5
    assert insertion["wer"]["insertions"] == 1
    assert insertion["wer"]["error_rate"] == 0.5
    assert deletion["wer"]["deletions"] == 1
    assert deletion["wer"]["error_rate"] == 0.5


def test_missing_reference_returns_no_metrics():
    assert score_transcript(hypothesis="hello", reference="") is None
    assert score_summary(hypothesis="hello", reference="") is None
    assert evaluate_lecture(
        raw_ocr_text="hello",
        corrected_text="hello",
        summary="hello",
        reference_transcript=None,
        reference_summary=None,
    ) == {"raw_ocr": None, "corrected": None, "summary": None}


def test_rouge_exact_match_and_no_overlap():
    exact = score_summary(
        hypothesis="alpha beta gamma",
        reference="alpha beta gamma",
    )
    no_overlap = score_summary(
        hypothesis="delta epsilon",
        reference="alpha beta gamma",
    )

    assert exact is not None
    assert no_overlap is not None
    assert exact["rouge1"]["fmeasure"] == 1
    assert exact["rouge2"]["fmeasure"] == 1
    assert exact["rougeL"]["fmeasure"] == 1
    assert no_overlap["rouge1"]["fmeasure"] == 0
    assert no_overlap["rouge2"]["fmeasure"] == 0
    assert no_overlap["rougeL"]["fmeasure"] == 0
