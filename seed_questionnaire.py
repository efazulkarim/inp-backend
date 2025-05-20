import json
from datetime import datetime
import os
import sys

# Add project root to sys.path to allow imports from app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(project_root)

from app.database import SessionLocal, engine # Assuming your setup is in app.database
from app.models import Questionnaire # Assuming your model is in app.models
# If your Base is needed for table creation (usually not for seeding if tables exist)
# from app.database import Base

def seed_questions():
    db = SessionLocal()

    questions_data = [
        # Step 1: Target Audience
        {"q_uuid": "step_1_age", "text": "Age", "input_type": "multiple_choice", "range": json.dumps(["under 18", "18-25", "26-35", "36-45", "46-55", "56-65", "65+", "Other"]), "status": 1},
        {"q_uuid": "step_1_location", "text": "Location", "input_type": "multiple_choice", "range": json.dumps(["Urban", "Suburban", "Rural", "Other"]), "status": 1},
        {"q_uuid": "step_1_industry", "text": "Industry", "input_type": "multiple_choice", "range": json.dumps(["Technology", "Healthcare", "Finance", "Education", "Retail", "Other"]), "status": 1},
        {"q_uuid": "step_1_characteristics", "text": "What characteristics describe your target audience?", "input_type": "multiple_choice", "range": json.dumps(["Early Adopters", "Price Conscious", "Tech-Savvy", "Values Sustainability", "Other"]), "status": 1},
        {"q_uuid": "step_1_customer_personas_created", "text": "Have you created detailed customer personas?", "input_type": "single_choice", "range": json.dumps(["Yes", "No", "In Progress"]), "status": 1},

        # Step 2: Problem Identification
        {"q_uuid": "step_2_main_problem", "text": "What is the main problem or pain point your customers face?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_2_problem_description_type", "text": "Which best describes this problem?", "input_type": "multiple_choice", "range": json.dumps(["Unworkable", "Urgent", "Underserved"]), "status": 1},
        {"q_uuid": "step_2_current_solutions_type", "text": "How are your customers currently solving this problem?", "input_type": "multiple_choice", "range": json.dumps(["DIY Solutions", "Competitor Products", "Hiring Help", "Unresolved", "Other"]), "status": 1},
        {"q_uuid": "step_2_other_current_solution_specify", "text": "If Other, please specify", "input_type": "text", "status": 1}, # Conditional on "Other" in previous
        {"q_uuid": "step_2_problem_validated", "text": "Have you validated this problem with actual customers?", "input_type": "single_choice", "range": json.dumps(["Yes", "No", "In Progress"]), "status": 1},
        {"q_uuid": "step_2_validation_method", "text": "If yes, briefly describe how you did this.", "input_type": "textarea", "status": 1}, # Conditional on "Yes"

        # Step 3: Consequence of not solving the problem
        {"q_uuid": "step_3_consequences_of_not_solving", "text": "What are the consequences if customers don't solve this problem?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_3_problem_urgency", "text": "How urgent is this problem for your customers?", "body": "(Likert scale: 1 = Not Urgent, 5 = Extremely Urgent)", "input_type": "slider", "range": json.dumps({"min": 1, "max": 5, "default": 3}), "status": 1},
        {"q_uuid": "step_3_financial_emotional_costs", "text": "What financial or emotional costs are your customers incurring by not solving this problem?", "input_type": "textarea", "status": 1},

        # Step 4: Articulate Solution
        {"q_uuid": "step_4_product_service_offering", "text": "What product or service are you offering?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_4_how_solution_solves_problem", "text": "How does your solution solve the problem?", "input_type": "multiple_choice", "range": json.dumps(["Reduces Costs", "Increases Productivity", "Improves Experience", "Offers New Features", "Other"]), "status": 1},
        {"q_uuid": "step_4_why_solution_better", "text": "Why is your solution better than current alternatives?", "input_type": "multiple_choice", "range": json.dumps(["Lower Price", "Better Features", "Easier to Use", "Customizable", "More Scalable", "Other"]), "status": 1},

        # Step 5: Before & After
        {"q_uuid": "step_5_customer_life_before", "text": "What does your customer's life look like before using your product?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_5_customer_life_after", "text": "What does it look like after using your product?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_5_improvement_significance", "text": "How significant is the improvement?", "body": "(Likert scale: 1 = Minor Improvement, 5 = Major Transformation)", "input_type": "slider", "range": json.dumps({"min": 1, "max": 5, "default": 3}), "status": 1},

        # Step 6: Key Benefits & Differentiation
        {"q_uuid": "step_6_primary_benefits", "text": "What primary benefits will customers experience from using your product?", "input_type": "multiple_choice", "range": json.dumps(["Saves Time", "Increases Efficiency", "Boosts Revenue", "Reduces Risk", "Other"]), "status": 1},
        {"q_uuid": "step_6_other_primary_benefit_specify", "text": "If Other, please specify", "input_type": "text", "status": 1}, # Conditional
        {"q_uuid": "step_6_emotional_psychological_benefits", "text": "What emotional or psychological benefits will customers feel?", "input_type": "multiple_choice", "range": json.dumps(["Relief from Stress", "Confidence", "Empowerment", "Satisfaction", "Other"]), "status": 1},
        {"q_uuid": "step_6_other_emotional_benefit_specify", "text": "If Other, please specify", "input_type": "text", "status": 1}, # Conditional

        # Step 7: Market Opportunity
        {"q_uuid": "step_7_market_size", "text": "How large is the market for your solution?", "input_type": "single_choice", "range": json.dumps(["Small (<10,000 customers)", "Medium (10,000-100,000 customers)", "Large (>100,000 customers)"]), "status": 1},
        {"q_uuid": "step_7_driving_demand", "text": "What is driving demand in this market?", "input_type": "multiple_choice", "range": json.dumps(["Technological Advancements", "Changing Consumer Behavior", "Regulatory Changes", "Other"]), "status": 1},
        {"q_uuid": "step_7_other_driving_demand_specify", "text": "If Other, please specify", "input_type": "text", "status": 1}, # Conditional
        {"q_uuid": "step_7_market_evolution", "text": "How is this market expected to evolve in the next 5 years?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_7_timing_introduction", "text": "Why is now the right time to introduce your solution?", "input_type": "textarea", "status": 1},

        # Step 8: Competitive Advantage
        {"q_uuid": "step_8_main_competitors", "text": "Who are your main competitors?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_8_swot_competitors", "text": "SWOT Analysis for Competitors", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_8_swot_your_product", "text": "SWOT Analysis for Your Product", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_8_unfair_advantage", "text": "What is your unfair advantage that cannot easily be copied?", "input_type": "textarea", "status": 1},

        # Step 9: Customer Adoption Potential
        {"q_uuid": "step_9_adoption_barriers", "text": "What barriers might prevent customers from adopting your solution?", "input_type": "multiple_choice", "range": json.dumps(["Cost", "Complexity", "Lack of Awareness", "Switching Costs", "Other"]), "status": 1},
        {"q_uuid": "step_9_willingness_to_pay", "text": "Have customers indicated they're willing to pay for your solution? If yes, how much?", "input_type": "single_choice_with_text", "range": json.dumps(["Yes", "No", "In Progress"]), "body":"If yes, specify amount in text field.", "status": 1}, # Custom type, may need split: Yes (how much)/No/In Progress
        {"q_uuid": "step_9_willingness_to_pay_amount", "text": "Amount willing to pay", "input_type": "text", "status": 1}, # Conditional
        {"q_uuid": "step_9_early_traction", "text": "What early traction or interest have you gathered? (e.g., sign-ups, pilot users)", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_9_adoption_incentives", "text": "What incentives can you offer to encourage adoption?", "input_type": "multiple_choice", "range": json.dumps(["Free Trial", "Discounts", "Referral Program", "Other"]), "status": 1},

        # Step 10: Success Metrics & Goals
        {"q_uuid": "step_10_kpis", "text": "What are your key performance indicators (KPIs)?", "input_type": "multiple_choice", "range": json.dumps(["Customer Acquisition", "Retention Rate", "Revenue Growth", "ROI", "Customer Satisfaction", "Other"]), "status": 1},
        {"q_uuid": "step_10_measure_metrics", "text": "How will you track and measure these metrics?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_10_milestones", "text": "What milestones will indicate progress?", "input_type": "textarea", "status": 1},

        # Step 11: Feasibility
        {"q_uuid": "step_11_revenue_model", "text": "What is your revenue model?", "input_type": "multiple_choice", "range": json.dumps(["Subscription", "One-Time Fee", "Freemium", "Other"]), "status": 1},
        {"q_uuid": "step_11_pricing_feedback", "text": "Have you tested your pricing with customers? What was the feedback?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_11_key_costs", "text": "What are the key costs involved in bringing this solution to market?", "input_type": "textarea", "status": 1},
        {"q_uuid": "step_11_profitability", "text": "Can you deliver the solution profitably at your current price point?", "input_type": "single_choice", "range": json.dumps(["Yes", "No", "Not Sure"]), "status": 1},
        {"q_uuid": "step_11_profitability_explanation", "text": "If no or not sure, please explain.", "input_type": "textarea", "status": 1} # Conditional
    ]

    try:
        existing_q_uuids = {q.q_uuid for q in db.query(Questionnaire.q_uuid).all()}
        
        new_questions_added = 0
        for q_data in questions_data:
            if q_data["q_uuid"] not in existing_q_uuids:
                question = Questionnaire(
                    q_uuid=q_data["q_uuid"],
                    text=q_data["text"],
                    body=q_data.get("body"),
                    remarks=q_data.get("remarks"),
                    input_type=q_data["input_type"],
                    range=q_data.get("range"), # Will be None if not provided
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status=q_data.get("status", 1) # Default status to 1 (active)
                )
                db.add(question)
                new_questions_added +=1
            else:
                print(f"Question with q_uuid '{q_data['q_uuid']}' already exists. Skipping.")
        
        if new_questions_added > 0:
            db.commit()
            print(f"Successfully added {new_questions_added} new questions to the questionnaire table.")
        else:
            print("No new questions were added. They may already exist in the database.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding questions: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # This is to ensure tables are created if they don't exist.
    # Usually, Alembic handles table creation. If you're sure tables exist, you can omit this.
    # from app.models import Base # If you have a Base.metadata.create_all structure
    # print("Creating tables if they don't exist (idempotent operation)...")
    # Base.metadata.create_all(bind=engine) # Be cautious with this in a production setup with Alembic

    print("Seeding questionnaire data...")
    seed_questions()
    print("Questionnaire seeding process finished.") 