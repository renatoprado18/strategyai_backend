# IMENSIAH Intelligent Form - User Guide

## Welcome to IMENSIAH

IMENSIAH (Intelligent Multi-layered Enrichment Network System for Intelligent Application Handling) is an AI-powered form system that automatically fills in company information as you type. Just enter your company website, and watch as the form intelligently populates with accurate business data.

---

## How It Works

### 1. Enter Your Company Website

Simply type your company's website URL into the form. You can enter it with or without `https://`:

```
Examples:
- google.com
- www.techstart.io
- https://company.com
```

The system automatically normalizes and validates the URL for you.

### 2. Watch the Magic Happen

IMENSIAH uses a **3-layer progressive enrichment system** that gathers data in real-time:

#### Layer 1: Instant Data (< 2 seconds)
- Company name from website metadata
- Business description
- Geographic location from IP
- Detected technologies
- Basic company information

#### Layer 2: Detailed Data (3-6 seconds)
- Employee count and company size
- Annual revenue estimates
- Industry classification
- Legal company name
- Brazilian CNPJ data (if applicable)
- Google Places verification
- Contact information

#### Layer 3: AI Insights (6-10 seconds)
- Industry categorization
- Company size classification
- Digital maturity assessment
- Target audience analysis
- Key differentiators
- LinkedIn company data

### 3. Review and Confirm

All auto-filled fields are:
- **Editable** - Change any field as needed
- **Verified** - Data comes from trusted sources
- **Scored** - Confidence indicators show data quality

**Confidence Indicators:**
- High Confidence (85-100%): Government registries, verified APIs
- Medium Confidence (70-84%): Structured business data
- Lower Confidence (50-69%): AI inference, metadata

---

## Data Sources

We collect information from **public sources only**:

### Free Sources (Layer 1 - < 2s)
- **Website Metadata**: Your public website content
- **IP Geolocation**: Approximate location from domain

### Paid APIs (Layer 2 - 3-6s)
- **Clearbit**: Company details, employee count, revenue
- **ReceitaWS**: Brazilian CNPJ government registry
- **Google Places**: Location verification, ratings

### AI + Professional Data (Layer 3 - 6-10s)
- **OpenRouter GPT-4o-mini**: Strategic insights
- **Proxycurl**: LinkedIn company information

---

## Understanding Confidence Scores

Each field has an associated confidence score:

| Score Range | Meaning | Source Examples |
|-------------|---------|-----------------|
| **95-100%** | Verified government data | CNPJ registry, legal registrations |
| **85-94%** | High-quality business data | Clearbit, Google Places verified |
| **70-84%** | Reliable structured data | Clearbit estimates, website metadata |
| **60-69%** | Approximate/inferred data | IP location, AI classification |
| **50-59%** | Lower confidence | AI inference, unverified sources |

---

## Privacy and Data Usage

### What We Collect
- Your email address (required for contact)
- Company website URL (required for enrichment)
- Public business data from your website and databases
- Publicly available business registry information

### What We DON'T Collect
- Personal browsing history
- Private company documents
- Employee personal information
- Financial records (only public estimates)
- Customer data

### Your Privacy Rights
- **Transparency**: All data sources are disclosed
- **Control**: Edit any auto-filled field
- **Access**: Request your data anytime
- **Deletion**: Request data removal within 30 days
- **LGPD Compliant**: Brazilian data protection laws
- **GDPR Ready**: European privacy standards

### Data Retention
- **Enrichment sessions**: 30 days (for form reuse)
- **Submitted forms**: Until you request deletion
- **Analytics**: Anonymized, 90 days

---

## Editing Auto-Filled Data

### How to Edit Fields

1. **Click any field** - All fields are editable
2. **Type your correction** - Override AI suggestions
3. **Save your changes** - Data is tracked for improvement
4. **Submit the form** - Your edits are preserved

### Why Edits Matter

When you edit an auto-filled field, you help IMENSIAH learn:
- Which data sources are most accurate
- Common errors in AI inference
- Industry-specific nuances
- Regional data patterns

**Your edits improve the system for everyone!**

---

## What Happens After Submission

### Phase 1: Form Auto-Fill (What You See)
1. Enter website URL + email
2. System enriches data in 5-10 seconds
3. Form fields populate progressively
4. Review and edit as needed
5. Click "Submit"

### Phase 2: Strategic Analysis (Behind the Scenes)
1. System receives your submission
2. Loads cached enrichment data (saves time!)
3. Runs comprehensive strategic analysis:
   - Data extraction and validation
   - Gap analysis and research
   - Strategic recommendations
   - Competitive positioning
   - Risk assessment and prioritization
   - Final report polishing
4. Generates complete strategic report
5. Emails report to you (2-5 minutes)

**Total Time:**
- Form filling: 5-10 seconds (instant feedback)
- Strategic analysis: 2-5 minutes (email delivery)
- **You don't wait!** Continue working while analysis completes.

---

## Frequently Asked Questions

### General Questions

**Q: How accurate is the auto-filled data?**
A: Accuracy varies by source:
- Government registries: 95-100% accurate
- Verified APIs (Clearbit, Google): 85-95% accurate
- AI inference: 70-85% accurate
- Always review and edit as needed!

**Q: Can I use this for any company?**
A: Yes! Works best for:
- Companies with public websites
- Brazilian companies (CNPJ data)
- Companies on LinkedIn
- Established businesses (vs. stealth startups)

**Q: What if my company is very new?**
A: We'll gather what's available:
- Website metadata (always available)
- AI inference (based on industry patterns)
- Manual entry (you can fill remaining fields)

**Q: Is this free to use?**
A: The form enrichment is free for users. We cover the API costs (~$0.01-0.06 per enrichment) to provide a better experience.

### Technical Questions

**Q: How long does enrichment take?**
A:
- Layer 1: < 2 seconds (instant)
- Layer 2: 3-6 seconds (detailed data)
- Layer 3: 6-10 seconds (AI insights)
- **Total: 5-10 seconds**

**Q: What if enrichment fails?**
A: No problem! You can:
- Manually fill the form (always works)
- Retry enrichment (errors are rare)
- Contact support for help

**Q: Can I skip auto-fill and enter manually?**
A: Absolutely! All fields remain editable. You can:
- Enter data manually from the start
- Use partial auto-fill and complete the rest
- Override any auto-filled fields

**Q: Does this work on mobile?**
A: Yes! IMENSIAH is fully responsive:
- Mobile-friendly interface
- Touch-optimized inputs
- Progressive enrichment works on all devices

### Privacy Questions

**Q: Who can see my data?**
A:
- **Your data**: Only you and authorized staff
- **Analytics**: Anonymized aggregate data only
- **Third parties**: Never shared or sold

**Q: Can I delete my data?**
A: Yes! Contact us to:
- Delete your submission
- Remove enrichment cache
- Export your data (portable format)

**Q: Is my email address safe?**
A: Absolutely:
- Used only for sending your report
- Never shared with third parties
- Never used for marketing (unless you opt-in)
- Stored encrypted in secure database

**Q: What about LGPD/GDPR compliance?**
A: We're compliant:
- Right to access your data
- Right to deletion (erasure)
- Right to data portability
- Transparent data processing
- Secure data storage

---

## Troubleshooting

### Common Issues

#### "Website URL is Invalid"
**Solution:** Ensure your URL:
- Is a valid domain (e.g., `company.com`)
- Doesn't have typos
- Is publicly accessible
- Has a working website

#### "Enrichment Taking Too Long"
**Possible causes:**
- Slow website response
- API rate limits hit
- Network connectivity issues

**Solution:**
- Wait up to 15 seconds
- Refresh and try again
- Fill form manually if needed

#### "Some Fields Are Empty"
**Why:** Not all data is available for every company

**Solution:**
- Fill missing fields manually
- Company size/industry may be inferred
- New companies have less public data

#### "Email Address Required"
**Why:** We need it to send your strategic report

**Solution:**
- Use your business email
- Personal email works too
- Required field (cannot skip)

---

## Tips for Best Results

### 1. Use Your Primary Domain
- Use main company website (not subdomain)
- Example: Use `company.com` not `blog.company.com`

### 2. Wait for All Layers
- Layer 1 (2s): Basic info appears
- Layer 2 (6s): Detailed data loads
- Layer 3 (10s): AI insights complete
- **Wait 10 seconds for maximum data**

### 3. Review AI Inferences
- Fields prefixed "AI:" are inferred
- Double-check for accuracy
- Edit if needed
- These improve over time!

### 4. Verify Critical Data
Always review:
- Company name and description
- Industry classification
- Contact information
- Target audience

### 5. Use Consistent Formatting
- Phone: +55 11 1234-5678
- CNPJ: XX.XXX.XXX/XXXX-XX
- Website: company.com (we add https://)

---

## Support and Feedback

### Need Help?
- **Email**: support@imensiah.com (hypothetical)
- **Documentation**: https://docs.imensiah.com
- **Response time**: < 24 hours

### Found a Bug?
Report issues with:
- Description of the problem
- Company website used
- What field(s) had issues
- Expected vs. actual result

### Feature Requests
We'd love to hear:
- What data sources would help
- What industries need better coverage
- What fields should be added
- UX improvements

---

## System Status

**Current Version:** 1.0.0 (January 2025)

**Data Sources:**
- Metadata Scraping: Operational
- Clearbit: Operational
- ReceitaWS: Operational
- Google Places: Operational
- OpenRouter AI: Operational
- Proxycurl: Operational

**Average Performance:**
- Layer 1 completion: < 2 seconds
- Layer 2 completion: 3-6 seconds
- Layer 3 completion: 6-10 seconds
- Success rate: > 95%
- Data accuracy: 70-95% (by source)

---

## Glossary

**IMENSIAH**: Intelligent Multi-layered Enrichment Network System for Intelligent Application Handling

**Progressive Enrichment**: Data gathering in multiple stages, showing results as they become available

**SSE (Server-Sent Events)**: Technology that streams data from server to browser in real-time

**Confidence Score**: Percentage indicating data reliability (0-100%)

**Session ID**: Unique identifier for caching enrichment data between phases

**Layer**: Stage of enrichment (1=fast, 2=detailed, 3=AI)

**Source Attribution**: Tracking which API provided each data field

**Auto-Fill**: Automatically populating form fields with enriched data

**CNPJ**: Brazilian national corporate tax identification number

**LGPD**: Brazilian General Data Protection Law (privacy regulation)

**GDPR**: European General Data Protection Regulation

---

## What's Next?

After submitting your form, you'll receive:

1. **Immediate Confirmation**: On-screen success message
2. **Email Notification**: Within 2 minutes, confirming receipt
3. **Strategic Report**: Within 2-5 minutes, comprehensive analysis
4. **Follow-Up**: Optional consultation scheduling (if requested)

**Thank you for using IMENSIAH!**

Your intelligent form system for faster, smarter business data collection.

---

*Last Updated: January 2025*
*Version: 1.0.0*
