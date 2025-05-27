import json
from datetime import datetime
import os
import sys

# Add project root to sys.path to allow imports from app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(project_root)

from app.database import SessionLocal
from app.models import CustomerPersonaQuestionnaire

def seed_customerboard_questions():
    db = SessionLocal()

    questions_data = [
        # Example questions for each section (replace/add as needed)
        # 1. Personal Information
        {"q_uuid": "persona_1_age_range", "text": "Age Range", "input_type": "checkbox-group", "range": json.dumps(["Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say"]), "category": "Personal Information", "status": 1},
        {"q_uuid": "persona_1_gender_identity", "text": "Gender Identity", "input_type": "checkbox-group", "range": json.dumps(["Female", "Male", "Non-binary", "Genderfluid", "Prefer not to say", "Other"]), "category": "Personal Information", "status": 1},
        {"q_uuid": "persona_1_education_level", "text": "Education Level", "input_type": "checkbox-group", "range": json.dumps(["No formal education", "High School or equivalent", "Associate Degree", "Bachelor's Degree", "Master's Degree", "PhD", "Certification/Vocational Training", "Prefer not to say", "Other"]), "category": "Personal Information", "status": 1},
        {"q_uuid": "persona_1_location_region", "text": "Location/Region", "input_type": "checkbox-group", "range": json.dumps(["North America", "Europe", "Asia-Pacific", "Middle East & Africa", "Latin America", "Oceania", "Other"]), "category": "Personal Information", "status": 1},

        # 2. Professional Information
        {"q_uuid": "persona_2_role_occupation", "text": "Role/Occupation", "input_type": "text", "category": "Professional Information", "status": 1},
        {"q_uuid": "persona_2_company_size", "text": "Company Size", "input_type": "checkbox-group", "range": json.dumps(["Solopreneur", "1-10 Employees", "11-50 Employees", "51-200 Employees", "201-500 Employees", "500+ Employees", "Not applicable"]), "category": "Professional Information", "status": 1},
        {"q_uuid": "persona_2_industry_types", "text": "Industry or Business Type", "input_type": "checkbox-group", "range": json.dumps(["Technology", "Healthcare", "Education", "Finance", "E-commerce", "Consumer Goods", "Government", "Freelancing/Contract Work", "Hospitality", "Manufacturing", "Other"]), "category": "Professional Information", "status": 1},
        {"q_uuid": "persona_2_annual_income", "text": "Annual Income/Revenue", "input_type": "checkbox-group", "range": json.dumps(["<$50K", "$50K-$100K", "$100K-$500K", "$500K-$1M", "$1M-$10M", "$10M+", "Prefer not to say"]), "category": "Professional Information", "status": 1},
        {"q_uuid": "persona_2_work_styles", "text": "Work Style", "input_type": "checkbox-group", "range": json.dumps(["Fully Remote", "Hybrid", "In-Person", "Flexible", "Freelance/Contract", "Not applicable"]), "category": "Professional Information", "status": 1},
        {"q_uuid": "persona_2_tech_proficiency", "text": "Tech Proficiency (1-10)", "input_type": "slider", "range": json.dumps({"min": 0, "max": 10, "default": 5}), "category": "Professional Information", "status": 1},
        
         # 3. Goals & Challenges
    {"q_uuid": "persona_3_goals", "text": "Goals (Select up to 4)", "input_type": "checkbox-group", "range": json.dumps([
        "Increase revenue", "Optimize business operations", "Generate creative ideas", "Automate repetitive tasks",
        "Grow customer base", "Improve product quality", "Scale globally", "Improve customer satisfaction",
        "Achieve work-life balance", "Innovate in their industry", "Expand into new markets", "Other"
    ]), "category": "Goals & Challenges", "status": 1},
    {"q_uuid": "persona_3_challenges", "text": "Challenges (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Tight deadlines", "Lack of skilled employees", "Budget constraints", "Market competition",
        "Rapid technological change", "Customer retention issues", "Creative blocks", "Supply chain issues",
        "Regulatory/legal concerns", "Time management", "Remote work coordination", "Limited resources", "Other"
    ]), "category": "Goals & Challenges", "status": 1},

    # 4. Behavior and Decision-Making
    {"q_uuid": "persona_4_tools_used", "text": "What tools or platforms does this persona use daily to manage their business or tasks? (Check all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Google Workspace", "Microsoft Office", "Slack", "Zoom", "Trello", "Notion", "HubSpot", "Shopify",
        "Salesforce", "Monday.com", "Airtable", "Asana", "Other"
    ]), "category": "Behavior and Decision-Making", "status": 1},
    {"q_uuid": "persona_4_info_sources", "text": "How does this persona stay updated or informed about industry trends? (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Online communities (e.g., Reddit, LinkedIn Groups)", "Professional networks", "Tech blogs and publications",
        "Podcasts or YouTube", "Industry events/conferences", "Webinars and workshops", "Social media influencers", "Other"
    ]), "category": "Behavior and Decision-Making", "status": 1},
    {"q_uuid": "persona_4_decision_factors", "text": "What factors influence this persona's decision-making when choosing tools or services for their business? (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Cost-effectiveness", "Ease of use", "Proven results", "Scalability", "Customer support", "Peer recommendations",
        "Product features and flexibility", "Data security and privacy", "Brand reputation", "Integrations with existing systems", "Other"
    ]), "category": "Behavior and Decision-Making", "status": 1},

    # 5. Emotional Triggers and Motivations
    {"q_uuid": "persona_5_emotions", "text": "What emotions or triggers drive this persona's need for your product or service? (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Stress from high demands and workload", "Fear of falling behind competition", "Desire for efficiency and innovation",
        "Pressure to meet revenue targets", "Relief when operations are streamlined", "Excitement about new technologies",
        "Desire to improve work-life balance", "Frustration with outdated systems", "Other"
    ]), "category": "Emotional Triggers and Motivations", "status": 1},
    {"q_uuid": "persona_5_motivations", "text": "What emotions or triggers drive this persona's need for your product or service? (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Stress from high demands and workload", "Fear of falling behind competition", "Desire for efficiency and innovation",
        "Pressure to meet revenue targets", "Relief when operations are streamlined", "Excitement about new technologies",
        "Desire to improve work-life balance", "Frustration with outdated systems", "Other"
    ]), "category": "Emotional Triggers and Motivations", "status": 1},

    # 6. User Journey
    {"q_uuid": "persona_6_user_journey_stage", "text": "What stage is this persona in their journey with your product? (Multiple Choice)", "input_type": "checkbox-group", "range": json.dumps([
        "Just exploring options", "Actively comparing solutions", "Ready to make a purchase", "Long-term user, seeking improvement", "Other"
    ]), "category": "User Journey", "status": 1},

    # 7. Pain Points
    {"q_uuid": "persona_7_pain_points", "text": "Pain Points (Select up to 4)", "input_type": "checkbox-group", "range": json.dumps([
        "Time management", "High workload", "Difficulty keeping up with market trends", "Lack of reliable tools",
        "Employee or team coordination issues", "Difficulty managing customer satisfaction", "Data security or privacy concerns",
        "Difficulty in accessing the right technology", "Other"
    ]), "category": "Pain Points", "status": 1},

    # 8. Preferred Features in Tools/Services
    {"q_uuid": "persona_8_preferred_features", "text": "Preferred Features (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "Automation capabilities", "Scalability for growing businesses", "Advanced analytics", "AI-generated insights",
        "Ease of integration with existing tools", "Customization options", "Security and compliance", "Support and training",
        "Low-code or no-code tools", "Sustainability and eco-friendly practices", "Other"
    ]), "category": "Preferred Features in Tools/Services", "status": 1},

    # 9. Preferred Communication Channels
    {"q_uuid": "persona_9_preferred_communication_channels", "text": "Preferred Communication Channels (Select all that apply)", "input_type": "checkbox-group", "range": json.dumps([
        "LinkedIn", "Twitter/X", "Facebook", "Instagram", "YouTube", "TikTok", "Tech Blogs (e.g., TechCrunch)",
        "Industry-specific forums", "Podcasts", "Email newsletters", "Other"
    ]), "category": "Preferred Communication Channels", "status": 1},

        # ...continue for all 8 sections, using your Figma as a guide...
    ]

    try:
        existing_q_uuids = {q.q_uuid for q in db.query(CustomerPersonaQuestionnaire.q_uuid).all()}
        new_questions_added = 0
        for q_data in questions_data:
            if q_data["q_uuid"] not in existing_q_uuids:
                question = CustomerPersonaQuestionnaire(
                    q_uuid=q_data["q_uuid"],
                    text=q_data["text"],
                    body=q_data.get("body"),
                    remarks=q_data.get("remarks"),
                    input_type=q_data["input_type"],
                    range=q_data.get("range"),
                    category=q_data.get("category"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status=q_data.get("status", 1)
                )
                db.add(question)
                new_questions_added += 1
            else:
                print(f"Question with q_uuid '{q_data['q_uuid']}' already exists. Skipping.")

        if new_questions_added > 0:
            db.commit()
            print(f"Successfully added {new_questions_added} new customerboard questions.")
        else:
            print("No new questions were added. They may already exist in the database.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding customerboard questions: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Seeding customerboard questionnaire data...")
    seed_customerboard_questions()
    print("Customerboard questionnaire seeding process finished.")