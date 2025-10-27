"""
Industry-Specific Deep Dive Configuration
Specialized prompts, frameworks, KPIs, and research queries per industry
"""

from typing import Dict, List, Any

# Industry-specific configurations
INDUSTRY_DEEP_DIVE = {
    "Tecnologia": {
        "extra_research_queries": [
            "Latest VC funding trends in Brazilian tech startups 2024-2025 with specific numbers",
            "Developer salaries and talent availability in São Paulo and Brazil tech market 2025",
            "SaaS metrics benchmarks for B2B software in Brazil (CAC, LTV, churn, NRR)",
            "API integration trends and developer ecosystem growth in {specific_segment}",
            "Tech stack preferences for Brazilian startups: frameworks, cloud providers, tools"
        ],

        "specialized_frameworks": [
            "Platform Strategy Analysis (Network Effects, Multi-sided Marketplace)",
            "Developer Experience (DX) Assessment (API design, documentation, SDKs)",
            "API-First Architecture Review (RESTful, GraphQL, gRPC considerations)",
            "Unit Economics Deep Dive (CAC, LTV, Payback Period, Gross Margin)",
            "Product-Led Growth (PLG) Readiness Assessment"
        ],

        "critical_kpis": [
            "MRR / ARR (Monthly/Annual Recurring Revenue)",
            "Net Revenue Retention (NRR) - target: >110%",
            "CAC Payback Period - target: <12 months",
            "LTV:CAC Ratio - target: >3:1",
            "Gross Margin - target: >70%",
            "Churn Rate (Logo vs Revenue) - target: <5% monthly",
            "Activation Rate - target: >40%",
            "Time to Value (TTV) - target: <7 days",
            "API Calls per Customer - growth indicator",
            "Developer Adoption Rate - for platform/API products",
            "Weekly Active Users (WAU) / Monthly Active Users (MAU)",
            "Product Qualified Leads (PQLs) - for PLG motion"
        ],

        "competitive_intelligence_queries": [
            "Track competitor GitHub activity and open-source contributions",
            "Monitor competitor API documentation quality and developer experience",
            "Analyze developer community engagement (Discord, Slack, forums)",
            "Compare pricing models, packaging tiers, and feature gating",
            "Identify technology partnerships and integration ecosystem",
            "Monitor competitor hiring patterns (eng, product, sales headcount)"
        ],

        "success_metrics": {
            "early_stage": {
                "mrr": "R$ 50k-200k",
                "customers": "20-100",
                "team": "5-15 people",
                "burn_rate": "R$ 100k-300k/month",
                "runway": ">12 months"
            },
            "growth_stage": {
                "mrr": "R$ 200k-1M",
                "customers": "100-500",
                "team": "15-50 people",
                "nrr": ">100%",
                "gross_margin": ">70%"
            },
            "scale_stage": {
                "arr": ">R$ 12M",
                "customers": ">500",
                "team": ">50 people",
                "nrr": ">120%",
                "rule_of_40": ">40"
            }
        }
    },

    "Saúde": {
        "extra_research_queries": [
            "Healthcare regulatory changes in Brazil (ANVISA, ANS) 2024-2025 with compliance requirements",
            "Digital health adoption rates and telemedicine trends in Brazil post-pandemic",
            "Patient satisfaction benchmarks for {specific_service} in Brazilian healthcare",
            "Healthcare reimbursement landscape and insurance coverage for digital health",
            "Clinical outcomes data and evidence-based medicine trends in {specific_area}"
        ],

        "specialized_frameworks": [
            "Healthcare Value Chain Analysis (Providers, Payers, Patients, Suppliers)",
            "Clinical Efficacy Assessment (Evidence-based outcomes, RCT data)",
            "Regulatory Compliance Review (ANVISA, ANS, LGPD Health Data)",
            "Patient Journey Mapping (Awareness → Care → Recovery)",
            "Health Economics and Outcomes Research (HEOR)",
            "Telehealth Readiness Assessment"
        ],

        "critical_kpis": [
            "Patient Satisfaction (NPS, HCAHPS, Net Promoter Score)",
            "Clinical Outcomes (Readmission rates, Complication rates, Mortality)",
            "Patient Acquisition Cost (PAC)",
            "Average Revenue per Patient (ARPP)",
            "Bed/Resource Utilization Rate - target: >85%",
            "Length of Stay (LOS) - benchmark vs industry",
            "No-Show Rate - target: <10%",
            "Wait Time (Appointment scheduling to visit) - target: <7 days",
            "Regulatory Compliance Score - target: 100%",
            "Reimbursement Rate - % of services covered by insurance",
            "Staff-to-Patient Ratio",
            "Revenue Cycle Metrics (Days in A/R, Collection Rate)"
        ],

        "competitive_intelligence_queries": [
            "Track competitors' clinical partnerships and hospital affiliations",
            "Monitor regulatory approvals and certifications obtained",
            "Analyze patient review sentiment across Google, Doctoralia, iClinic",
            "Compare service offerings, specializations, and treatment modalities",
            "Identify technology stack (EMR systems, telemedicine platforms)",
            "Monitor insurance network participation and reimbursement rates"
        ],

        "success_metrics": {
            "clinic_practice": {
                "monthly_patients": "200-500",
                "revenue_per_patient": "R$ 200-500",
                "nps": ">50",
                "utilization": ">80%"
            },
            "digital_health": {
                "active_users": "5k-50k",
                "engagement_rate": ">30%",
                "clinical_outcomes": "Measurable improvement",
                "regulatory_compliance": "100%"
            },
            "healthtech_saas": {
                "arr": ">R$ 1M",
                "hospitals_clinics": ">50",
                "churn": "<10% annually",
                "nrr": ">100%"
            }
        }
    },

    "Varejo": {
        "extra_research_queries": [
            "E-commerce growth trends in Brazil 2024-2025 with conversion rate benchmarks",
            "Consumer spending patterns and retail foot traffic recovery data",
            "Inventory management and supply chain innovations for Brazilian retail",
            "Omnichannel retail strategies and buy-online-pickup-in-store (BOPIS) adoption",
            "Payment methods and installment preferences in Brazilian e-commerce"
        ],

        "specialized_frameworks": [
            "Retail Diamond Framework (Merchandise, Location, Service, Communication)",
            "Customer Lifetime Value (CLV) Analysis for Retail",
            "Omnichannel Strategy Assessment (Online, Mobile, In-Store Integration)",
            "Supply Chain Resilience Evaluation (Inventory, Logistics, Vendor Management)",
            "Visual Merchandising and Store Layout Optimization"
        ],

        "critical_kpis": [
            "Same-Store Sales Growth (SSS) - target: >5% YoY",
            "Conversion Rate (Online: >2%, In-Store: >20%)",
            "Average Transaction Value (ATV) / Average Order Value (AOV)",
            "Inventory Turnover Ratio - target: >4x per year",
            "Gross Margin Return on Investment (GMROI) - target: >3",
            "Customer Retention Rate - target: >60%",
            "Net Promoter Score (NPS) - target: >50",
            "Foot Traffic (In-Store Visits) - trend vs benchmark",
            "Online Traffic (Website Visitors, App Downloads)",
            "Cart Abandonment Rate - target: <70%",
            "Return Rate - target: <15%",
            "Revenue per Square Meter (Physical Stores)"
        ],

        "competitive_intelligence_queries": [
            "Track competitor pricing strategies and promotional campaigns",
            "Monitor new store openings, closures, and expansion plans",
            "Analyze customer reviews and sentiment across Google, Reclame Aqui",
            "Compare loyalty program effectiveness and benefits",
            "Identify omnichannel capabilities (click-and-collect, same-day delivery)",
            "Monitor social media engagement and influencer partnerships"
        ],

        "success_metrics": {
            "small_retail": {
                "monthly_revenue": "R$ 50k-200k",
                "gross_margin": "30-40%",
                "inventory_turnover": ">4x",
                "customer_retention": ">50%"
            },
            "ecommerce": {
                "monthly_revenue": "R$ 200k-1M",
                "conversion_rate": ">2%",
                "aov": "R$ 150-300",
                "cac": "<15% of LTV"
            },
            "omnichannel": {
                "monthly_revenue": ">R$ 1M",
                "online_share": "20-40%",
                "nps": ">50",
                "same_store_sales": "+5% YoY"
            }
        }
    },

    "Educação": {
        "extra_research_queries": [
            "EdTech adoption rates in Brazilian schools and universities 2024-2025",
            "Student engagement metrics and learning outcomes data for online education",
            "Education policy changes and government funding in Brazil (MEC programs)",
            "Remote learning trends and hybrid education models post-pandemic",
            "Skill development priorities and corporate training market in Brazil"
        ],

        "specialized_frameworks": [
            "Learning Experience (LX) Framework (Content, Delivery, Assessment, Support)",
            "Student Success Analytics (Retention, Completion, Outcomes)",
            "Curriculum Design Assessment (Backwards Design, Learning Objectives)",
            "Instructional Technology Review (LMS, Video, Interactive Tools)",
            "Adult Learning Theory Application (Andragogy for Professional Training)"
        ],

        "critical_kpis": [
            "Student Enrollment / Retention Rate - target: >80%",
            "Course Completion Rate - target: >70%",
            "Student Satisfaction (NPS, CSAT) - target: >60",
            "Learning Outcomes (Test scores, Certifications earned)",
            "Student-to-Teacher Ratio - benchmark: <25:1",
            "Revenue per Student (RPS)",
            "Customer Acquisition Cost (CAC) - for students",
            "Lifetime Value (LTV) of Student - multi-course enrollment",
            "Engagement Metrics (Logins, Video Completion, Forum Activity)",
            "Time to Completion (vs planned duration)",
            "Job Placement Rate (for vocational/professional training) - target: >70%",
            "Net Revenue Retention (if subscription model)"
        ],

        "competitive_intelligence_queries": [
            "Track competitor course offerings, curriculum, and pricing",
            "Monitor pricing models (pay-per-course, subscription, cohort-based)",
            "Analyze student review sentiment across Google, Trustpilot, Course Report",
            "Compare learning platform features (LMS, video quality, certifications)",
            "Identify partnerships (universities, corporations, government programs)",
            "Monitor instructor quality and teaching methodologies"
        ],

        "success_metrics": {
            "online_courses": {
                "active_students": "500-5k",
                "completion_rate": ">70%",
                "nps": ">60",
                "revenue_per_student": "R$ 200-1k"
            },
            "corporate_training": {
                "corporate_clients": "10-50",
                "arr": ">R$ 500k",
                "retention_rate": ">85%",
                "job_placement": ">70%"
            },
            "edtech_platform": {
                "schools_universities": ">100",
                "students_reached": ">50k",
                "arr": ">R$ 2M",
                "nps": ">70"
            }
        }
    },

    "Serviços Financeiros": {
        "extra_research_queries": [
            "Fintech regulation and Banco Central do Brasil (BACEN) updates 2024-2025",
            "Open Banking adoption and Pix transaction volume trends in Brazil",
            "Digital payment methods and e-wallet market share data",
            "Loan default rates and credit risk trends in Brazilian fintech",
            "Buy-Now-Pay-Later (BNPL) and embedded finance growth in Brazil"
        ],

        "specialized_frameworks": [
            "Financial Services Value Chain (Acquisition, Underwriting, Servicing, Collection)",
            "Credit Risk Assessment Framework (Default rates, Loss rates, Collections)",
            "Regulatory Compliance Review (BACEN, CVM, LGPD Financial Data)",
            "Unit Economics for Lending (Origination cost, Servicing cost, Net Interest Margin)",
            "Open Banking Strategy Assessment (API integration, Data sharing)"
        ],

        "critical_kpis": [
            "Monthly Active Users (MAU) / Daily Active Users (DAU)",
            "Transaction Volume (GMV - Gross Merchandise Value)",
            "Take Rate - % of transaction volume captured as revenue",
            "Customer Acquisition Cost (CAC)",
            "Lifetime Value (LTV) - based on fees, interest, cross-sell",
            "Default Rate / Non-Performing Loans (NPL) - target: <5%",
            "Net Interest Margin (NIM) - for lending products",
            "Cost-to-Income Ratio - target: <40%",
            "Regulatory Compliance Score - target: 100%",
            "Fraud Rate - target: <0.5%",
            "Payment Success Rate - target: >95%",
            "NPS (Net Promoter Score) - target: >50"
        ],

        "competitive_intelligence_queries": [
            "Track competitor product launches (cards, loans, investments)",
            "Monitor pricing strategies (fees, interest rates, FX spreads)",
            "Analyze customer review sentiment across Google, Reclame Aqui, Trustpilot",
            "Compare technology stack and app experience (UX, speed, features)",
            "Identify partnerships (banks, merchants, payment processors)",
            "Monitor regulatory approvals and licenses obtained"
        ],

        "success_metrics": {
            "neobank_digital_wallet": {
                "active_users": "50k-500k",
                "transaction_volume": "R$ 10M-100M/month",
                "cac": "<R$ 50",
                "ltv_cac": ">3"
            },
            "lending_platform": {
                "loan_originations": "R$ 5M-50M/month",
                "default_rate": "<5%",
                "nim": ">8%",
                "cac": "<10% of loan size"
            },
            "payments_fintech": {
                "gmv": ">R$ 100M/month",
                "take_rate": "1-3%",
                "merchants": ">1000",
                "payment_success": ">95%"
            }
        }
    }
}


def get_industry_config(industry: str) -> Dict[str, Any]:
    """
    Get industry-specific configuration

    Args:
        industry: Industry name (e.g., "Tecnologia", "Saúde")

    Returns:
        Industry-specific config or default
    """
    return INDUSTRY_DEEP_DIVE.get(industry, {
        "extra_research_queries": [],
        "specialized_frameworks": [],
        "critical_kpis": [],
        "competitive_intelligence_queries": [],
        "success_metrics": {}
    })


def format_industry_queries_for_perplexity(
    industry: str,
    company: str,
    specific_segment: str = None
) -> List[str]:
    """
    Format industry-specific research queries for Perplexity

    Args:
        industry: Industry name
        company: Company name
        specific_segment: Specific segment/niche within industry

    Returns:
        List of formatted queries ready for Perplexity
    """
    config = get_industry_config(industry)
    queries = config.get("extra_research_queries", [])

    # Replace placeholders
    formatted = []
    for query in queries:
        formatted_query = query.replace("{specific_segment}", specific_segment or industry)
        formatted_query = formatted_query.replace("{company}", company)
        formatted_query = formatted_query.replace("{specific_service}", specific_segment or "healthcare services")
        formatted_query = formatted_query.replace("{specific_area}", specific_segment or "general healthcare")
        formatted.append(formatted_query)

    return formatted


def get_industry_frameworks(industry: str) -> List[str]:
    """Get specialized frameworks for industry"""
    config = get_industry_config(industry)
    return config.get("specialized_frameworks", [])


def get_industry_kpis(industry: str) -> List[str]:
    """Get critical KPIs for industry"""
    config = get_industry_config(industry)
    return config.get("critical_kpis", [])


def get_industry_success_metrics(industry: str, stage: str = None) -> Dict[str, Any]:
    """
    Get success metrics for industry and company stage

    Args:
        industry: Industry name
        stage: Company stage (early_stage, growth_stage, scale_stage, etc.)

    Returns:
        Success metrics for benchmarking
    """
    config = get_industry_config(industry)
    success_metrics = config.get("success_metrics", {})

    if stage and stage in success_metrics:
        return success_metrics[stage]

    return success_metrics


# Example usage
if __name__ == "__main__":
    # Test industry config retrieval
    tech_config = get_industry_config("Tecnologia")
    print("Tecnologia KPIs:", tech_config["critical_kpis"][:5])

    # Test query formatting
    queries = format_industry_queries_for_perplexity(
        industry="Saúde",
        company="Telemedicina Brasil",
        specific_segment="telemedicine for mental health"
    )
    print("\nSaúde Research Queries:")
    for q in queries:
        print(f"- {q}")

    # Test success metrics
    tech_metrics = get_industry_success_metrics("Tecnologia", "growth_stage")
    print("\nTecnologia Growth Stage Metrics:", tech_metrics)
