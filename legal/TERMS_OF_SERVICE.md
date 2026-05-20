# Terms of Service

**Effective date:** 2026-05-20
**Last updated:** 2026-05-20

These Terms govern your use of JARVIS, an AI assistant service operated by Braivex <!-- TODO: legal entity name -->, an Indian company. "We" means Braivex. "You" means the person or organisation using JARVIS.

By creating an account or using the Service you agree to these Terms. If you don't agree, don't use the Service.

---

## 1. Eligibility

You must be at least 16 years old and legally able to enter a contract. If you use JARVIS on behalf of an organisation, you confirm you have authority to bind that organisation.

---

## 2. Service Description

JARVIS is an AI assistant that:
- Lets you chat with large language models (Anthropic Claude by default; OpenAI, Groq, Mistral, Google Gemini if you bring your own key).
- Connects to your external accounts (Gmail, Outlook, Slack, Teams, GitHub, Linear, Jira, Notion, WhatsApp, Shopify, Freshdesk) via OAuth so you can ask it to triage, summarise, draft, or act on data in those accounts.
- Provides a Retrieval-Augmented Generation (RAG) knowledge base, file uploads, scheduled "Intel Briefs" pulling public web data, and a Decision Inbox.

JARVIS is a tool. It does not autonomously act on your accounts without your explicit instruction.

---

## 3. Account Registration

- One human per account. No shared logins.
- You must provide a valid email and a password ≥ 8 characters.
- You provide your industry at signup so JARVIS can personalise default behaviour.
- You are responsible for keeping your credentials secret. Notify us at hemant@wbj.team if you suspect unauthorised access.

---

## 4. Acceptable Use

You will not, and will not permit anyone else to:

- Use the Service for any illegal purpose.
- Send spam, phishing, harassment, hate speech, or CSAM through your connected accounts via JARVIS.
- Try to extract our model weights, prompts, or proprietary code.
- Reverse-engineer or sublicense the Service.
- Scrape AI inference through our infrastructure to resell or evade your own provider's rate limits.
- Run automated bots against the API beyond documented rate limits.
- Use JARVIS to violate any third-party's terms (Gmail's ToS still binds you when you connect Gmail).
- Conduct security testing or penetration testing without prior written consent.
- Misrepresent JARVIS outputs as human-authored where disclosure is required by law (some jurisdictions require AI disclosure in advertising, journalism, academic work).

We reserve the right to suspend or terminate accounts violating these rules. See `ACCEPTABLE_USE_POLICY.md` for the full list.

---

## 5. Your Content and Data

You own your data. You own the AI outputs JARVIS generates for you (subject to the terms of the AI provider you used — Anthropic, OpenAI, Groq, etc., each have their own usage rights you accept when you BYOAK).

You grant us a limited, non-exclusive, royalty-free licence to host, process, and transmit your content **only** to the extent necessary to operate the Service for you. This licence ends when you delete the content or your account.

We do **NOT** train any model on your data. We do **NOT** share your content with anyone except the sub-processors listed in our Privacy Policy.

---

## 6. AI Disclaimer

AI can be wrong. AI hallucinates. AI is fluent and confident even when incorrect.

You are responsible for verifying any output JARVIS produces before acting on it — especially:
- Sending emails on your behalf
- Creating tasks, issues, or PRs
- Pushing files to your GitHub repo
- Approving Decision Inbox items
- Drafting customer replies
- Any financial, legal, medical, or safety-critical decision

JARVIS is an assistant, not an oracle.

---

## 7. Third-Party Integrations

JARVIS connects to many third-party services. We are not responsible for:
- Outages or rate limits imposed by those services.
- Data lost or corrupted on those services.
- Changes to their APIs that break our integration.
- Their pricing, terms, or content policies.

When you connect a service, you accept that service's terms in addition to ours.

---

## 8. Subscriptions and Billing

JARVIS has a free tier and paid plans (Pro, Founder — Stripe-billed).

- **Free tier limits:** <!-- TODO: token budget, file uploads, intel briefs per month --> per month. Hit a limit and the relevant feature pauses until next month or until you upgrade.
- **Paid plans:** monthly or annual. Billed in advance. Auto-renew unless cancelled.
- **Cancellation:** any time from Settings → Account. Cancellation stops auto-renewal; access continues until the period ends.
- **Refunds:** <!-- TODO: full refund within 14 days, prorated otherwise? -->
- **Plan changes:** upgrades take effect immediately and we prorate. Downgrades take effect at next renewal.
- **Taxes:** prices exclude taxes unless stated. GST/VAT charged where applicable.

We may change pricing for future billing cycles with at least 30 days' notice. Existing paid subscriptions are honoured at the price you signed up for until renewal.

---

## 9. BYOAK (Bring Your Own API Key)

If you provide an API key for Anthropic, OpenAI, Groq, Mistral, or Google Gemini:
- Your usage of that provider is governed by that provider's terms, not ours.
- You are responsible for any charges from that provider.
- We encrypt your key at rest and never log it.
- Removing the key from Settings deletes it from our database immediately.

---

## 10. Termination

You may delete your account at any time (Settings → Account → Delete). Deletion removes all your data within 35 days (see Privacy Policy §7).

We may suspend or terminate your account if you breach these Terms, with 7 days' written notice for fixable breaches, or immediately for severe breaches (illegal use, security incidents, payment fraud). Where reasonable, we will let you export your data first.

Surviving sections (10, 11, 12, 13, 14, 15) continue to apply after termination.

---

## 11. Warranties Disclaimer

JARVIS is provided **AS IS** and **AS AVAILABLE**, without warranty of any kind, express or implied — including merchantability, fitness for a particular purpose, non-infringement, accuracy, or availability. We do not warrant that the Service will be uninterrupted, error-free, or that AI outputs will be correct or useful.

Some jurisdictions don't allow this disclaimer; in those, our warranties are limited to the minimum required by law.

---

## 12. Limitation of Liability

To the maximum extent permitted by law:

- Our total liability to you for any claim is capped at the fees you paid us in the 12 months before the claim, or USD 100, whichever is higher.
- We are not liable for indirect, incidental, consequential, special, exemplary, or punitive damages — including lost profits, lost data, business interruption, or AI hallucination consequences — even if advised of the possibility.

These limits do not exclude liability we cannot exclude by law (gross negligence, wilful misconduct, fraud, death or personal injury caused by our negligence).

---

## 13. Indemnification

You will indemnify and hold us harmless from any third-party claim arising from:
- Your breach of these Terms or our Acceptable Use Policy.
- Your use of JARVIS to violate any third-party's rights (including the ToS of services you connect).
- Content you submit to or generate with JARVIS that infringes someone's IP, privacy, or other rights.

---

## 14. Disputes and Governing Law

These Terms are governed by the laws of India.

Any dispute will be resolved by binding arbitration seated in Bengaluru, India <!-- TODO: confirm venue with founder -->, conducted under the Arbitration and Conciliation Act, 1996, in English, by a single arbitrator. Each party bears its own legal costs unless the arbitrator awards otherwise.

EU consumers may have additional rights under their local law that cannot be waived — those rights still apply.

---

## 15. Modifications to These Terms

We can update these Terms. For material changes, we will email you 30 days before they take effect. Continued use after the effective date means acceptance.

If you don't accept a change, your remedy is to stop using the Service before the change takes effect and delete your account.

---

## 16. General

- **Entire agreement:** these Terms + the Privacy Policy + the Acceptable Use Policy = the whole agreement.
- **Assignment:** you can't assign these Terms; we can assign them to a successor (e.g. acquisition).
- **No waiver:** if we don't enforce something, we haven't waived our right to enforce it later.
- **Severability:** if a clause is unenforceable, the rest survives.
- **Force majeure:** neither party is liable for delays caused by events outside reasonable control (natural disasters, war, ISP outages, sub-processor failures).

---

## 17. Contact

Questions about these Terms: **hemant@wbj.team**

— Braivex, 2026-05-20
