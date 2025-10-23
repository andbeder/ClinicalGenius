# HIPAA Business Associate Agreement (BAA) Status

**Last Updated:** October 22, 2025
**Reviewed By:** Clinical Genius Development Team
**Next Review Date:** January 22, 2026 (Quarterly)

---

## Overview

This document tracks the status of Business Associate Agreements (BAAs) with all third-party vendors that process, store, or transmit Protected Health Information (PHI) on behalf of Clinical Genius.

Per HIPAA §164.308(b)(1) and §164.314(a)(1), covered entities and business associates must have written BAAs in place with any third party that handles PHI.

---

## Current BAA Status

| Vendor | Service | BAA Required? | BAA Status | Date Signed | Renewal/Review Date | Contact | Notes |
|--------|---------|---------------|------------|-------------|---------------------|---------|-------|
| **Salesforce** | CRM Analytics | ✅ Yes | ✅ **ACTIVE** | [To Be Documented] | [To Be Documented] | [SF Contact] | Health Cloud includes BAA |
| **Microsoft** | Copilot API | ✅ Yes | ✅ **ACTIVE** | [To Be Documented] | [To Be Documented] | [MS Contact] | Azure OpenAI Service BAA verified |
| **OpenAI** | ChatGPT API | ✅ Yes | ❌ **NOT SIGNED** | N/A | N/A | N/A | **PROVIDER DISABLED** |
| **LM Studio** | Local LLM | ❌ No | ⚪ **N/A** | N/A | N/A | N/A | Self-hosted, no PHI leaves premises |

---

## Vendor Details

### ✅ Salesforce - CRM Analytics
- **Service Used:** CRM Analytics datasets, SAQL queries, data storage
- **PHI Exposure:** High (stores source patient/claims data)
- **BAA Status:** Active (assumed - requires verification)
- **Action Required:**
  - ⚠️ Obtain copy of signed BAA
  - ⚠️ Document BAA signing date and renewal terms
  - ⚠️ Verify coverage includes CRM Analytics specifically

### ✅ Microsoft - Copilot API
- **Service Used:** AI-powered data enrichment via Azure OpenAI Service
- **PHI Exposure:** High (receives patient data in prompts)
- **BAA Status:** Active (customer confirmed)
- **Action Required:**
  - ⚠️ Obtain copy of signed BAA
  - ⚠️ Document BAA signing date and renewal terms
  - ⚠️ Verify API endpoint is Azure (not standard OpenAI)
  - ⚠️ Confirm data residency requirements

### ❌ OpenAI - ChatGPT API (DISABLED)
- **Service Used:** AI-powered data enrichment (DISABLED)
- **PHI Exposure:** Would be High if enabled
- **BAA Status:** NOT SIGNED
- **Mitigation:** Provider completely disabled in application code
- **Code Protection:**
  - `lm_studio_client.py` lines 49-51, 67-69: Blocks OpenAI in `generate()` and `generate_chat()`
  - `templates/main.html` line 644: Removed from UI provider dropdown
- **Action Required:**
  - ✅ Provider disabled - no immediate action
  - Future: Contact OpenAI Enterprise sales if BAA needed

### ⚪ LM Studio - Local LLM (Self-Hosted)
- **Service Used:** AI-powered data enrichment via local models
- **PHI Exposure:** None (data processed locally only)
- **BAA Status:** Not applicable (self-hosted solution)
- **Security Notes:**
  - PHI never leaves localhost
  - No cloud APIs involved
  - Recommended for highest security use cases
- **Action Required:** None

---

## Compliance Actions Taken

### Phase 1: Immediate Risk Mitigation (Completed Oct 22, 2025)

✅ **OpenAI Provider Disabled**
- Code-level blocking in `lm_studio_client.py`
- Error message: "OpenAI provider is disabled: No Business Associate Agreement (BAA) in place"
- UI dropdown option removed
- Documentation updated

✅ **BAA Status Documentation Created**
- This document created to track all vendor relationships
- Quarterly review schedule established

### Phase 2: BAA Documentation (In Progress)

⚠️ **Salesforce BAA Verification**
- Action: Request copy of signed BAA from Salesforce account team
- Deadline: Within 30 days
- Owner: [To Be Assigned]

⚠️ **Microsoft Copilot BAA Verification**
- Action: Request copy of signed BAA from Microsoft account team
- Deadline: Within 30 days
- Owner: [To Be Assigned]
- Verify endpoint: Ensure using Azure OpenAI (not public OpenAI API)

---

## BAA Requirements Checklist

All Business Associate Agreements must include:

- ✅ Permitted uses and disclosures of PHI
- ✅ Business Associate must implement safeguards
- ✅ Business Associate must report security incidents and breaches
- ✅ Return or destruction of PHI upon contract termination
- ✅ Business Associate must obtain satisfactory assurances from subcontractors
- ✅ Allow covered entity and DHHS access to information for compliance reviews
- ✅ Specify data retention and disposal requirements
- ✅ Define liability and indemnification terms

---

## Audit and Review Schedule

| Review Type | Frequency | Last Review | Next Review | Status |
|-------------|-----------|-------------|-------------|--------|
| **BAA Status Review** | Quarterly | Oct 22, 2025 | Jan 22, 2026 | ✅ Current |
| **Vendor Risk Assessment** | Annually | [Pending] | [TBD] | ⚠️ Overdue |
| **SOC 2 Report Review** | Annually | [Pending] | [TBD] | ⚠️ Overdue |
| **Breach Notification Test** | Semi-Annually | [Pending] | [TBD] | ⚠️ Overdue |

---

## Contact Information

### Internal Contacts
- **HIPAA Privacy Officer:** [To Be Assigned]
- **HIPAA Security Officer:** [To Be Assigned]
- **Application Owner:** Andrew Beder
- **Legal Counsel:** [To Be Assigned]

### Vendor Contacts
- **Salesforce:** [To Be Documented]
- **Microsoft:** [To Be Documented]

---

## Incident Response

### In Case of Vendor Breach Notification

1. **Document receipt:** Log date/time of breach notification
2. **Notify privacy officer:** Within 1 hour
3. **Assess scope:** Determine if our PHI was affected
4. **Notify affected individuals:** Within 60 days (if required)
5. **File HHS report:** Within 60 days (if ≥500 individuals) or annually (if <500)
6. **Review BAA:** Ensure vendor followed contract terms
7. **Evaluate relationship:** Consider termination if non-compliant

### Vendor Breach Notification Contacts
- **Salesforce Security:** trust.salesforce.com
- **Microsoft Security:** [To Be Documented]

---

## Document Control

- **Version:** 1.0
- **Created:** October 22, 2025
- **Last Updated:** October 22, 2025
- **Classification:** Internal - Confidential
- **Retention:** 7 years minimum per HIPAA requirements

---

## Appendices

### Appendix A: OpenAI Disablement Evidence

**Code Location:** `lm_studio_client.py`

```python
# Line 49-51: generate() method
if provider == 'openai':
    raise Exception("OpenAI provider is disabled: No Business Associate Agreement (BAA) in place. Use LM Studio or Microsoft Copilot only.")

# Line 67-69: generate_chat() method
if provider == 'openai':
    raise Exception("OpenAI provider is disabled: No Business Associate Agreement (BAA) in place. Use LM Studio or Microsoft Copilot only.")
```

**UI Location:** `templates/main.html` line 642-646
- OpenAI option removed from provider dropdown
- Help text updated: "Choose your LLM provider (OpenAI disabled - no BAA)"

### Appendix B: Recommended BAA Language for LLM Providers

When obtaining BAAs from LLM providers, ensure the following specific provisions:

1. **Data Use Limitations:**
   - Vendor may not use PHI to train or improve AI models
   - Vendor may not retain PHI after session completion
   - Vendor may not share PHI with third parties

2. **Data Residency:**
   - Specify geographic location of data processing
   - Ensure compliance with state privacy laws

3. **Audit Rights:**
   - Right to audit vendor's security controls annually
   - Right to review vendor's SOC 2 Type II reports

4. **Breach Notification:**
   - Notification within 24 hours of discovery
   - Detailed root cause analysis required
   - Vendor pays for breach notification costs

---

**Document Status:** ✅ Active and Current
