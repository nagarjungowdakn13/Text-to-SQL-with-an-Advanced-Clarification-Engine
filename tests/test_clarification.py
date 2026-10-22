import pytest
from app.services.llm.mock import MockLLMProvider
from app.services.clarification.detector import AmbiguityDetector
from app.services.clarification.manager import ClarificationManager
from app.services.schema.extractor import SchemaExtractor
from app.core.config import settings

def test_ambiguity_detection():
    """Verify that ambiguous questions trigger scoring above threshold."""
    llm = MockLLMProvider()
    detector = AmbiguityDetector(llm)
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    
    # Straightforward question
    res_clear = detector.analyze_question("Show products with price greater than 100", schema)
    assert not res_clear.is_ambiguous
    assert res_clear.ambiguity_score < settings.AMBIGUITY_THRESHOLD
    
    # Ambiguous question
    res_amb = detector.analyze_question("Who is our best customer?", schema)
    assert res_amb.is_ambiguous
    assert res_amb.ambiguity_score >= settings.AMBIGUITY_THRESHOLD
    assert len(res_amb.options) >= 2

def test_clarification_loop_prevention(db_session):
    """Verify that loop prevention halts clarification rounds and makes safe assumptions."""
    llm = MockLLMProvider()
    manager = ClarificationManager(llm)
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    
    session = manager.get_or_create_session(
        db=db_session,
        session_id="test-loop-session",
        question="Who is our stubborn best customer?"
    )
    
    # First turn - should flag ambiguity
    session, analysis = manager.process_turn(db_session, session.session_id, None, schema)
    assert session.rounds == 0
    assert session.status == "active"
    assert analysis.is_ambiguous
    
    # Submit answer round 1
    session, analysis = manager.process_turn(db_session, session.session_id, "Highest total revenue", schema)
    assert session.rounds == 1
    
    # Submit answer round 2 (exceeding MAX_CLARIFICATION_ROUNDS which is default 2)
    # The Mock LLM keeps returning ambiguity, but manager must override it to force resolve
    session, analysis = manager.process_turn(db_session, session.session_id, "Another answer", schema)
    assert session.rounds == 2
    assert session.status == "max_rounds_reached"
    # Even if LLM claimed ambiguity, is_ambiguous must be overridden to False to break the loop
    assert not analysis.is_ambiguous
    assert "Assuming" in session.current_question
