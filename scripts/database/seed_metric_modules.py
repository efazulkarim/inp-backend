"""
Seed metric modules and their questions into the database.

Modules are optional add-on validation dimensions that users can enable per-idea
on top of the core 11-step questionnaire.
"""
import json
import sys
from pathlib import Path

# Ensure app imports resolve when this script is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from datetime import datetime


from app.database import SessionLocal
from app.models import MetricModule, Questionnaire

MODULES = [
    {
        "slug": "unit_economics",
        "title": "Unit Economics",
        "description": "Evaluate the financial health signals of your SaaS: CAC, LTV, churn, and payback period.",
        "max_score": 9,
        "sort_order": 1,
    },
    {
        "slug": "go_to_market",
        "title": "Go-to-Market Readiness",
        "description": "Assess your launch strategy, distribution channels, and early traction plan.",
        "max_score": 9,
        "sort_order": 2,
    },
    {
        "slug": "technical_feasibility",
        "title": "Technical Feasibility",
        "description": "Gauge your ability to build, scale, and secure the product.",
        "max_score": 9,
        "sort_order": 3,
    },
    {
        "slug": "network_effects",
        "title": "Network Effects & Moat",
        "description": "Determine the defensibility of your product through switching costs, data advantages, and platform effects.",
        "max_score": 9,
        "sort_order": 4,
    },
    {
        "slug": "regulatory_risk",
        "title": "Regulatory & Compliance Risk",
        "description": "Identify legal, privacy, and industry-specific regulatory hurdles.",
        "max_score": 9,
        "sort_order": 5,
    },
]

MODULE_QUESTIONS = {
    "unit_economics": [
        {
            "q_uuid": "mod_ue_cac_estimate",
            "text": "What is your estimated Customer Acquisition Cost (CAC)?",
            "input_type": "single_choice",
            "range": json.dumps(["<$50", "$50-$200", "$200-$500", "$500-$1000", ">$1000", "Not sure yet"]),
        },
        {
            "q_uuid": "mod_ue_ltv_estimate",
            "text": "What is your estimated Customer Lifetime Value (LTV)?",
            "input_type": "single_choice",
            "range": json.dumps(["<$100", "$100-$500", "$500-$2000", "$2000-$10000", ">$10000", "Not sure yet"]),
        },
        {
            "q_uuid": "mod_ue_ltv_cac_ratio",
            "text": "What LTV:CAC ratio are you targeting?",
            "body": "A healthy SaaS benchmark is 3:1 or higher.",
            "input_type": "single_choice",
            "range": json.dumps(["<2:1", "2:1 - 3:1", "3:1 - 5:1", ">5:1", "Not sure yet"]),
        },
        {
            "q_uuid": "mod_ue_churn_target",
            "text": "What monthly churn rate are you targeting?",
            "input_type": "single_choice",
            "range": json.dumps(["<2%", "2-5%", "5-10%", ">10%", "Not sure yet"]),
        },
        {
            "q_uuid": "mod_ue_payback_period",
            "text": "How long do you expect it to take to recover CAC from a single customer?",
            "input_type": "single_choice",
            "range": json.dumps(["<3 months", "3-6 months", "6-12 months", "12-18 months", ">18 months", "Not sure yet"]),
        },
    ],
    "go_to_market": [
        {
            "q_uuid": "mod_gtm_primary_channel",
            "text": "What is your primary customer acquisition channel?",
            "input_type": "multiple_choice",
            "range": json.dumps([
                "Content Marketing / SEO", "Paid Ads (Google, Meta)", "Social Media (organic)",
                "Sales / Outbound", "Partnerships / Affiliates", "Product-Led Growth",
                "Community / Word of Mouth", "Other",
            ]),
        },
        {
            "q_uuid": "mod_gtm_launch_timeline",
            "text": "When do you plan to launch your MVP or beta?",
            "input_type": "single_choice",
            "range": json.dumps(["Already launched", "<1 month", "1-3 months", "3-6 months", "6-12 months", ">12 months"]),
        },
        {
            "q_uuid": "mod_gtm_beta_pipeline",
            "text": "How many beta users or waitlist sign-ups do you currently have?",
            "input_type": "single_choice",
            "range": json.dumps(["0", "1-50", "51-200", "201-1000", ">1000"]),
        },
        {
            "q_uuid": "mod_gtm_partnerships",
            "text": "Do you have any strategic partnerships or distribution agreements in place?",
            "input_type": "single_choice",
            "range": json.dumps(["Yes, signed", "In negotiation", "Identified targets", "None yet"]),
        },
        {
            "q_uuid": "mod_gtm_content_strategy",
            "text": "Describe your content or inbound marketing strategy.",
            "input_type": "textarea",
        },
    ],
    "technical_feasibility": [
        {
            "q_uuid": "mod_tf_tech_stack",
            "text": "What technology stack are you using or planning to use?",
            "input_type": "textarea",
        },
        {
            "q_uuid": "mod_tf_mvp_scope",
            "text": "How would you describe the scope of your MVP?",
            "input_type": "single_choice",
            "range": json.dumps([
                "Very lean (1-2 core features)", "Moderate (3-5 features)",
                "Feature-rich (6+ features)", "Not yet defined",
            ]),
        },
        {
            "q_uuid": "mod_tf_scalability",
            "text": "What is your scalability approach?",
            "input_type": "multiple_choice",
            "range": json.dumps([
                "Cloud-native (auto-scaling)", "Serverless", "Containerized (Kubernetes)",
                "Traditional server-based", "Not considered yet",
            ]),
        },
        {
            "q_uuid": "mod_tf_security",
            "text": "What security and compliance measures are you planning?",
            "input_type": "multiple_choice",
            "range": json.dumps([
                "SOC 2", "GDPR compliance", "HIPAA", "Encryption at rest & in transit",
                "Penetration testing", "None planned yet", "Other",
            ]),
        },
        {
            "q_uuid": "mod_tf_build_timeline",
            "text": "How long do you estimate it will take to build and ship the MVP?",
            "input_type": "single_choice",
            "range": json.dumps(["<1 month", "1-3 months", "3-6 months", "6-12 months", ">12 months"]),
        },
    ],
    "network_effects": [
        {
            "q_uuid": "mod_ne_switching_costs",
            "text": "How high are the switching costs for your customers once they adopt your product?",
            "input_type": "single_choice",
            "range": json.dumps(["Very high (data lock-in, integrations)", "Moderate", "Low", "None"]),
        },
        {
            "q_uuid": "mod_ne_data_advantage",
            "text": "Does your product generate a data advantage that improves with more users?",
            "input_type": "single_choice",
            "range": json.dumps(["Yes, strongly", "Somewhat", "No"]),
        },
        {
            "q_uuid": "mod_ne_platform_effects",
            "text": "Does your product have marketplace or platform dynamics (two-sided network)?",
            "input_type": "single_choice",
            "range": json.dumps(["Yes", "Planning to build", "No"]),
        },
        {
            "q_uuid": "mod_ne_brand_moat",
            "text": "What brand or community moat are you building?",
            "input_type": "multiple_choice",
            "range": json.dumps([
                "Strong community", "Thought leadership / content", "First-mover advantage",
                "Proprietary technology / patents", "None yet", "Other",
            ]),
        },
        {
            "q_uuid": "mod_ne_defensibility_summary",
            "text": "Summarize why a well-funded competitor could NOT easily replicate your product.",
            "input_type": "textarea",
        },
    ],
    "regulatory_risk": [
        {
            "q_uuid": "mod_rr_data_privacy",
            "text": "Which data privacy regulations apply to your product?",
            "input_type": "multiple_choice",
            "range": json.dumps(["GDPR", "CCPA / CPRA", "HIPAA", "PCI-DSS", "None", "Not sure", "Other"]),
        },
        {
            "q_uuid": "mod_rr_industry_regulations",
            "text": "Are there industry-specific regulations you need to comply with?",
            "input_type": "single_choice",
            "range": json.dumps(["Yes, well-understood", "Yes, still researching", "No", "Not sure"]),
        },
        {
            "q_uuid": "mod_rr_certifications",
            "text": "What certifications or audits will you need?",
            "input_type": "multiple_choice",
            "range": json.dumps(["SOC 2", "ISO 27001", "HITRUST", "FedRAMP", "None required", "Not sure"]),
        },
        {
            "q_uuid": "mod_rr_legal_counsel",
            "text": "Do you have access to legal counsel experienced in your industry?",
            "input_type": "single_choice",
            "range": json.dumps(["Yes, retained", "Yes, on-demand", "No, but planned", "No"]),
        },
        {
            "q_uuid": "mod_rr_risk_summary",
            "text": "Describe the biggest regulatory or legal risk to your product launch.",
            "input_type": "textarea",
        },
    ],
}


def seed_metric_modules():
    db = SessionLocal()
    try:
        existing_slugs = {m.slug for m in db.query(MetricModule.slug).all()}
        modules_added = 0

        for mod_data in MODULES:
            if mod_data["slug"] not in existing_slugs:
                module = MetricModule(
                    slug=mod_data["slug"],
                    title=mod_data["title"],
                    description=mod_data["description"],
                    max_score=mod_data["max_score"],
                    sort_order=mod_data["sort_order"],
                    created_at=datetime.utcnow(),
                )
                db.add(module)
                modules_added += 1
            else:
                print(f"Module '{mod_data['slug']}' already exists. Skipping.")

        if modules_added > 0:
            db.commit()
            print(f"Added {modules_added} metric module(s).")
        else:
            print("No new modules added.")

        existing_q_uuids = {q.q_uuid for q in db.query(Questionnaire.q_uuid).all()}
        questions_added = 0

        for module_slug, questions in MODULE_QUESTIONS.items():
            for q_data in questions:
                if q_data["q_uuid"] in existing_q_uuids:
                    print(f"Question '{q_data['q_uuid']}' already exists. Skipping.")
                    continue
                question = Questionnaire(
                    q_uuid=q_data["q_uuid"],
                    text=q_data["text"],
                    body=q_data.get("body"),
                    remarks=q_data.get("remarks"),
                    input_type=q_data["input_type"],
                    range=q_data.get("range"),
                    module_slug=module_slug,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status=1,
                )
                db.add(question)
                questions_added += 1

        if questions_added > 0:
            db.commit()
            print(f"Added {questions_added} module question(s).")
        else:
            print("No new module questions added.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding metric modules: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding metric modules and questions...")
    seed_metric_modules()
    print("Done.")
