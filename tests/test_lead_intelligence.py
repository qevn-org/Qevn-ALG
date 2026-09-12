"""Unit tests for Lead Intelligence domain models, feature extraction, and ML scoring."""


from linkedin_intelligence.agents.contact_discovery import discover_contacts_for_lead
from linkedin_intelligence.models.lead import (
    Company,
    ContactInfo,
    Lead,
    LeadIntent,
    LeadSource,
    Person,
)
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.signals import Signal
from linkedin_intelligence.services.company_aggregation import aggregate_company_signals
from linkedin_intelligence.services.ml_scoring import (
    MLScoringService,
    classify_lead_temperature,
    extract_lead_features,
)


def test_lead_model_creation_and_flattening():
    lead = Lead(
        id="lead-test-123",
        status="new",
        score=92.5,
        temperature="HOT",
        person=Person(name="Priya Sharma", job_title="VP Engineering", is_decision_maker=True, decision_maker_status="confirmed"),
        company=Company(name="Acme Health", industry="Healthcare & MedTech", location="Bangalore, India", company_size="Growth (Series B)"),
        source=LeadSource(post_id="p1", post_url="https://linkedin.com/feed/update/1", post_date="2026-09-10"),
        intent=LeadIntent(detected_intent="Hiring", detected_requirement="Senior Backend Engineer", technology_need="Python, FastAPI, AWS"),
        contacts=[
            ContactInfo(type="business_email", value="priya@acmehealth.com", confidence=0.96, verification_status="verified_public")
        ],
        evidence=["p1"],
        why_detected=["Active hiring for engineering roles"],
        why_now="Founder publicly announced scaling platform.",
    )

    assert lead.id == "lead-test-123"
    assert lead.score == 92.5
    assert lead.temperature == "HOT"
    assert lead.person.is_decision_maker is True

    flat = lead.to_flat_dict()
    assert flat["Company"] == "Acme Health"
    assert flat["Person Name"] == "Priya Sharma"
    assert flat["Business Email"] == "priya@acmehealth.com"
    assert flat["Contact Status"] == "verified_public"
    assert flat["Lead Score"] == 92.5


def test_temperature_classification_tiers():
    assert classify_lead_temperature(95.0) == "HOT"
    assert classify_lead_temperature(90.0) == "HOT"
    assert classify_lead_temperature(85.0) == "WARM"
    assert classify_lead_temperature(75.0) == "WARM"
    assert classify_lead_temperature(65.0) == "COOL"
    assert classify_lead_temperature(55.0) == "COOL"
    assert classify_lead_temperature(40.0) == "COLD"
    assert classify_lead_temperature(30.0) == "COLD"
    assert classify_lead_temperature(20.0) == "UNQUALIFIED"
    assert classify_lead_temperature(0.0) == "UNQUALIFIED"


def test_feature_extraction_18_dimensions():
    lead = Lead(
        id="lead-456",
        score=88.0,
        person=Person(name="Rahul Verma", job_title="CTO", is_decision_maker=True),
        company=Company(name="FinCorp", industry="Fintech & Payments", location="Mumbai, India", company_size="100-500"),
        intent=LeadIntent(urgency=85.0),
        signals=["Looking for agency partner to scale core platform"],
        contacts=[ContactInfo(type="business_email", value="rahul@fincorp.com")],
        evidence=["post-1", "post-2"],
    )

    features = extract_lead_features(lead)
    assert len(features) == 18
    assert features["hiring_intent"] > 0
    assert features["decision_maker_probability"] == 85.0
    assert features["geographic_fit"] == 90.0
    assert features["contact_availability"] == 100.0
    assert features["explicit_vendor_search"] == 100.0


def test_ml_scoring_cold_start_and_training(tmp_path):
    ml_service = MLScoringService(model_dir=tmp_path)
    meta = ml_service.get_metrics()
    assert meta.mode == "Cold Start"
    assert "insufficient" in meta.status_message.lower()

    # Inference in cold start returns hybrid heuristic
    feat = {"hiring_intent": 85.0, "decision_maker_probability": 80.0, "urgency": 75.0}
    score, temp, mode = ml_service.predict_lead(feat)
    assert 0.0 <= score <= 100.0
    assert temp in ["HOT", "WARM", "COOL", "COLD", "UNQUALIFIED"]
    assert "Cold-start" in mode

    # Build mock outcome dataset with at least 20 samples
    dataset = []
    for i in range(25):
        is_pos = (i % 2 == 0)
        dataset.append({
            "lead_id": f"lead-{i}",
            "action": "won" if is_pos else "disqualified",
            "label": 1 if is_pos else 0,
            "features": {
                "hiring_intent": 90.0 if is_pos else 30.0,
                "buying_intent": 85.0 if is_pos else 25.0,
                "technology_intent": 80.0 if is_pos else 20.0,
                "decision_maker_probability": 90.0 if is_pos else 20.0,
                "post_freshness": 80.0,
                "urgency": 85.0 if is_pos else 20.0,
                "company_fit": 80.0 if is_pos else 30.0,
                "company_size_score": 80.0,
                "industry_fit": 85.0,
                "geographic_fit": 90.0,
                "role_relevance": 80.0,
                "explicit_vendor_search": 100.0 if is_pos else 0.0,
                "recommendation_request": 0.0,
                "technology_problem_detected": 0.0,
                "related_posts_count": 60.0 if is_pos else 10.0,
                "hiring_velocity": 70.0 if is_pos else 20.0,
                "contact_availability": 100.0 if is_pos else 0.0,
                "evidence_confidence": 85.0 if is_pos else 40.0,
            },
        })

    new_meta = ml_service.train_from_dataset(dataset)
    assert new_meta.mode == "Trained"
    assert new_meta.training_samples == 25
    assert new_meta.accuracy is not None
    assert new_meta.accuracy > 0.60

    # Inference after training uses trained ML model
    score_ml, temp_ml, mode_ml = ml_service.predict_lead(dataset[0]["features"])
    assert "Supervised ML" in mode_ml
    assert score_ml > 50.0


def test_contact_discovery_parsing_and_confidence():
    post = LinkedInPost(
        id="post-test-1",
        author_name="Ananya Roy",
        author_headline="Head of Talent Acquisition at HealthStack",
        author_profile_url="https://linkedin.com/in/ananyaroy",
        content="We are hiring 3 Senior Backend Engineers! Please email ananya@healthstack.in or call 9876543210.",
        published_at="2026-09-11",
    )

    lead = Lead(
        id="lead-contact-test",
        person=Person(name="Ananya Roy", job_title="Head of Talent Acquisition", profile_url="https://linkedin.com/in/ananyaroy"),
        company=Company(name="HealthStack", website="https://www.healthstack.in"),
        evidence=["post-test-1"],
    )

    contacts = discover_contacts_for_lead(lead, [post])
    assert len(contacts) >= 2

    # Check verified email
    emails = [c for c in contacts if c.type == "business_email"]
    assert any(e.value == "ananya@healthstack.in" and e.verification_status == "verified_public" for e in emails)

    # Check verified phone
    phones = [c for c in contacts if c.type == "phone"]
    assert any("9876543210" in p.value and p.verification_status == "verified_public" for p in phones)


def test_multi_post_company_aggregation():
    p1 = LinkedInPost(id="p1", company_name="Zeta Cloud", content="Hiring distributed systems architects!")
    p2 = LinkedInPost(id="p2", company_name="Zeta Cloud", content="Looking for technology partner to build our platform.")
    p3 = LinkedInPost(id="p3", company_name="Zeta Cloud", content="Digital transformation project kick-off hiring engineers.")

    s1 = Signal(
        signal_type="HIRING",
        company_name="Zeta Cloud",
        confidence=0.9,
        explanation="hiring architects",
        evidence_post_ids=["p1"],
    )

    profiles = aggregate_company_signals([p1, p2, p3], [s1])
    assert "zeta cloud" in profiles
    profile = profiles["zeta cloud"]
    assert profile.post_count == 3
    assert profile.hiring_velocity == "High"
    assert profile.vendor_search is True
    assert profile.digital_transformation is True
    assert profile.aggregated_score_boost > 5.0
