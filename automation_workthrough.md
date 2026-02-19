# Candidate Screening Workflow — Walkthrough

## High-Level Overview

This workflow automates the initial stages of candidate screening for Seismic Consulting Group.

When a new application email arrives at the designated careers inbox, the workflow:
1. Extracts the candidate's name and email from the message
2. Scans the email body for three specific keywords: `Mid-level`, `Python`, and `GenAI`
3. Routes the candidate based on whether **at least 2 keywords** are present
4. Logs the candidate to the appropriate Google Sheet tab ("Candidates" or "Rejected")
5. Sends a personalized email — either an interview invite or a polite rejection

The workflow is built in **n8n** using Gmail (trigger + send), a Code node for logic, 
an IF node for branching, and Google Sheets for data logging.

---

## Prerequisites

To run this workflow, you will need:

- An **n8n** instance (cloud or self-hosted)
- A **Gmail account** for receiving applications (IMAP enabled)
- A **Google account** with access to Google Sheets
- OAuth2 credentials configured in n8n for both Gmail and Google Sheets
- A **Google Sheet** titled "Seismic Consulting - Candidate Tracker" with two tabs:
  - `Candidates` — columns: Name, Email, Application Date, Status
  - `Rejected` — columns: Name, Email, Application Date
- A valid **Calendly link** (or any scheduling tool) to replace the placeholder in the interview email

---

## Assumptions Made

- The candidate's **name** is available in the "From" field of the email (display name)
- The **email body (plain text)** is used for keyword scanning, not the attachment
- Resume attachments are expected but **not parsed** — only stored as metadata
- The resume file is assumed to be a **PDF**
- Keywords are matched **case-insensitively**
- The workflow uses a **single Gmail account** for both receiving and sending emails
- Emails arrive in the **primary inbox** (not spam or promotions tab)

---

## Potential Improvements & Edge Cases Not Handled

| Edge Case | Current Behavior | Suggested Improvement |
|---|---|---|
| No attachment | Workflow proceeds without a resume | Add validation and send a follow-up email requesting the resume |
| Duplicate applications | Both rows are added to the sheet | Check for existing email before inserting |
| Name not in "From" field | `candidateName` may be empty | Fall back to parsing the email signature |
| HTML-only email body | Plain text may be empty | Extract text from HTML body as fallback |
| Large volume of emails | May hit Gmail API rate limits | Add error handling / retry logic |
| Resume parsing | Resume content is not analyzed | Integrate a PDF parser (e.g., with n8n's HTTP Request + a parsing API) |
| Scheduling link | Hardcoded placeholder | Dynamically generate Calendly links per candidate using the Calendly API |