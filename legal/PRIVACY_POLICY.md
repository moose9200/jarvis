# Privacy Policy

**Effective date:** 2026-05-20
**Last updated:** 2026-05-20
**Controller:** Braivex (operated by WBJ Team Private Limited, Bengaluru, Karnataka, India)
**Contact:** hemant@wbj.team

---

## 1. Introduction

This Privacy Policy explains how Braivex ("we", "us", "JARVIS") collects, uses, stores, and shares your personal data when you use the JARVIS AI assistant service ("the Service"). We aim for plain English; legal terms only where they matter.

By using JARVIS you agree to this policy. If you do not agree, do not use the Service.

We comply with the EU General Data Protection Regulation (GDPR), the UK GDPR, and the California Consumer Privacy Act (CCPA / CPRA). Indian users are protected under the Digital Personal Data Protection Act, 2023.

---

## 2. What We Collect

### 2.1 Account data
- Email address (required for sign-in)
- Password (stored only as a bcrypt hash — we cannot recover the plaintext)
- Industry (a short text label you provide at signup — drives default Intel Briefs)
- Account preferences (tier, personality mode, response length, daily token budget)

### 2.2 Content from connected services
When you connect an external account (Gmail, Outlook Mail, Google Calendar, Outlook Calendar, Slack, Microsoft Teams, GitHub, Linear, Jira, Notion, WhatsApp, Shopify, Freshdesk) we receive an OAuth access token from that provider. We use the token to read the data you explicitly request — for example, fetching your inbox when you ask JARVIS to triage email.

We do **not** continuously poll your accounts in the background unless you explicitly enable a recurring task (e.g. an Intel Brief or scheduled summary).

OAuth tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256). The encryption key is held only in our application server's environment.

### 2.3 AI conversation
- Your chat messages and JARVIS's responses
- Files you upload (PDFs, images, CSVs, text)
- Knowledge base entries you add (Retrieval-Augmented Generation chunks)
- Persona context you provide (about-me, communication style, priorities, team members)

### 2.4 Usage metrics
- Token counts per message (input, output, cache hit, thinking tokens)
- Estimated USD cost per call (so you can monitor spend)
- Timestamps + provider + model used

### 2.5 BYOAK keys
If you bring your own API key for Anthropic, OpenAI, Groq, Mistral, or Google Gemini, the key is encrypted at rest with Fernet and used only to make AI calls on your behalf.

### 2.6 Logs and security data
- Server access logs (IP address, user-agent, endpoint, status code, latency)
- Failed login attempts (for rate limiting and abuse detection)

We do **not** track you across other websites. We do **not** use Google Analytics, Facebook Pixel, or any third-party analytics SDK in the product.

---

## 3. How We Use Your Data

We process your data only for the purposes below:

1. **Run the Service** — authenticate you, fetch data from your connected accounts at your request, send your messages to the AI provider, return the response.
2. **Build context** — store conversation history, your persona, and Knowledge Base chunks so JARVIS gives personalised answers.
3. **Cost tracking** — record token usage so you can see what you've spent.
4. **Security** — rate-limit login attempts, detect abuse, investigate incidents.
5. **Service improvement** — aggregate, anonymised metrics on response time and error rates. Never your content.
6. **Legal compliance** — respond to lawful requests, enforce our Terms.

We do **NOT** train any AI model on your data. Your content is never used to improve our models or any third-party model beyond the single AI call you initiated.

---

## 4. Legal Basis (GDPR Article 6)

- **Contract performance** — running the Service you signed up for.
- **Consent** — when you connect a third-party account or upload sensitive content. You can withdraw at any time by disconnecting or deleting the data.
- **Legitimate interest** — fraud prevention, security, debugging. Balanced against your rights.
- **Legal obligation** — when law requires us to retain or disclose data.

For California residents (CCPA), we do **not** sell or share your personal information for cross-context behavioural advertising.

---

## 5. Sharing with Third Parties (Sub-processors)

We use the following sub-processors. Each receives only what's necessary to perform its function.

| Sub-processor | Purpose | Data shared |
|---|---|---|
| Anthropic | Claude AI inference (default) | Your messages + system prompts |
| OpenAI | GPT inference + embeddings (if you BYOAK or enable RAG) | Your messages, embeddings |
| Groq | Llama inference (BYOAK) | Your messages |
| Mistral | Mistral inference (BYOAK) | Your messages |
| Google AI | Gemini inference (BYOAK) | Your messages |
| Microsoft / Google / Slack / GitHub / Atlassian / Notion / Meta WhatsApp / Shopify / Freshdesk | Source data when you connect their account | Only the items you request |
| Cloudflare R2 | File-upload storage (when enabled) | Files you upload |
| Stripe | Billing (if you subscribe) | Email, plan, payment metadata. We never see your card |
| Railway / Render | Hosting | Everything we hold, transit-encrypted |
| ElevenLabs | Text-to-speech (optional, opt-in) | The text JARVIS reads aloud |

We do not share your data with marketers, advertisers, or data brokers. We do not sell your data — full stop.

---

## 6. International Transfers

We are based in India. Some sub-processors are in the US (Anthropic, OpenAI, Cloudflare, Stripe) or the EU.

For EU/UK users, transfers outside the EEA/UK are protected by Standard Contractual Clauses (SCCs) approved by the European Commission and adequacy decisions where applicable.

For California residents, transfers outside the US are made in compliance with CCPA Section 1798.140.

---

## 7. Data Retention

| Data | Retention |
|---|---|
| Account (email, password hash) | Until you delete your account |
| OAuth tokens | Until you disconnect that provider or delete account |
| Conversation history | Until you delete it. We auto-summarise old turns to save tokens |
| Knowledge Base chunks | Until you delete them or your account |
| File uploads | Until you delete them or your account |
| Token usage logs | 13 months (for billing reconciliation and cost dashboards) |
| Server access logs | 30 days |
| Failed login attempts | 30 days |
| Billing records | 7 years (Indian tax law) |

Deleted data is removed from primary storage immediately and from encrypted backups within 35 days.

---

## 8. Security

- **In transit:** TLS 1.2+ for every API call.
- **At rest:** OAuth tokens and BYOAK keys are Fernet-encrypted. Database backups are encrypted.
- **Passwords:** bcrypt with per-user salt.
- **Auth:** JWT (HS256) with 30-day expiry. Tokens never appear in URLs or server logs.
- **Rate limiting:** 5 login/register attempts per minute per IP.
- **Audit:** Health endpoint reports dependency status; all errors are logged without leaking stack traces to the client.

No system is perfectly secure. If we suffer a breach affecting your personal data, we will notify you within 72 hours per GDPR Article 33.

---

## 9. Your Rights

Wherever you live, you have the right to:

- **Access** — request a copy of all data we hold about you.
- **Rectification** — correct anything inaccurate.
- **Erasure** — delete your account and all your data ("right to be forgotten").
- **Portability** — export your data in JSON.
- **Restrict** — temporarily pause our processing.
- **Object** — refuse processing based on legitimate interest.
- **Withdraw consent** — disconnect a provider; revoke a BYOAK key; turn off RAG.
- **Lodge a complaint** — with your local data-protection authority.

California residents additionally have the right to know, delete, correct, limit use of sensitive personal information, and to not be discriminated against for exercising any of these rights (CCPA Sections 1798.100–1798.150).

---

## 10. How to Exercise Your Rights

Email **hemant@wbj.team** with the subject line "Privacy request — [your right]". We will respond within 30 days (and confirm receipt within 5 days). We may need to verify your identity before acting.

Account deletion is also available in-app: Profile → Settings → Account → Delete account.

---

## 11. Cookies and Local Storage

- **Session cookie** — HttpOnly, Secure, SameSite=Lax. Holds OAuth state during the connect flow. Expires when you close the browser.
- **localStorage** — your JWT (so you stay logged in), panel-visibility preferences, dashboard layout. Not a cookie; not accessible to third parties.

No advertising cookies. No analytics cookies. No tracking. See COOKIE_POLICY.md for the full breakdown.

---

## 12. Children

JARVIS is not intended for anyone under 16. If we discover an account belongs to a child under 16, we will delete it. Parents/guardians can email hemant@wbj.team to request deletion.

---

## 13. Changes to This Policy

We will email you 30 days before any material change. The current version always lives at /privacy on our domain and in the repository at `legal/PRIVACY_POLICY.md`.

---

## 14. Contact

Privacy questions, data requests, or breach reports:

- **Email:** hemant@wbj.team
- **Postal:** WBJ Team Private Limited, Bengaluru, Karnataka, India (full street address available on written request)
- **EU/UK representative:** Not currently appointed — Braivex does not exceed the GDPR Article 27 / UK GDPR threshold for compulsory representation. We will appoint a representative once we exceed 5,000 EU users or undertake material monitoring activity.
- **Data Protection Officer:** Not currently required under DPDP Act §10 thresholds; will appoint if processing volume escalates.

---

## 15. Effective Date

This policy is effective from 2026-05-20.

— Braivex
