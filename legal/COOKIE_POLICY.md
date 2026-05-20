# Cookie Policy

**Effective date:** 2026-05-20

JARVIS uses the absolute minimum amount of browser storage required to run. No advertising cookies. No analytics cookies. No tracking.

This page lists every cookie and localStorage key we use, why, and how to remove it.

---

## 1. Cookies

| Name | Type | Purpose | Lifetime | Set by |
|---|---|---|---|---|
| `session` <!-- TODO confirm cookie name in Starlette SessionMiddleware --> | HttpOnly, Secure, SameSite=Lax | Holds OAuth `state` parameter during the connect flow so we can verify the callback. Required for OAuth security (CSRF protection). | Browser session | JARVIS backend |

That's the only cookie we set. No third-party JavaScript sets cookies on our domain.

---

## 2. localStorage

`localStorage` is not a cookie. It's per-origin browser storage accessed only by code from our domain. We disclose our use for full transparency.

| Key | Purpose | When set | When cleared |
|---|---|---|---|
| `jarvis_token` | Your JWT auth token (HS256, 30-day expiry). Keeps you logged in across reloads. | On successful login or registration | On logout, or when you clear browser storage |
| `jarvis_panels` | Which dashboard panels you have visible (Calendar/Email/Tasks/Projects). Not personal data. | Whenever you toggle a panel | On clearing browser storage |

That's it. We do not store conversation history, persona, or any sensitive data in localStorage.

---

## 3. What we do NOT use

- Google Analytics, Mixpanel, Amplitude, Heap, PostHog, Segment, or any other analytics SDK in the production frontend.
- Facebook Pixel, LinkedIn Insight, X Pixel, TikTok Pixel.
- Advertising / retargeting cookies.
- Third-party fonts that set cookies.
- Cross-domain tracking IDs.

If we add any of the above in future, we will update this policy 30 days in advance and require explicit opt-in.

---

## 4. Clearing your data

- **Logout:** Profile → Sign Out. Clears `jarvis_token` from localStorage.
- **Full clear:** in your browser settings, clear "cookies and site data" for the JARVIS domain. Removes both the session cookie and all localStorage.
- **Account deletion:** Profile → Settings → Account → Delete account. This removes server-side data too. See `PRIVACY_POLICY.md` §7 for retention details.

---

## 5. Browser controls

You can block cookies from JARVIS entirely in your browser settings — but you will not be able to complete OAuth flows (we cannot verify the state without the session cookie) and you may be logged out frequently. localStorage is similarly required for staying logged in.

---

## 6. Changes

If we add or remove any cookie, we will update this page and announce on the dashboard for 30 days.

---

## 7. Contact

Cookie or storage questions: **hemant@wbj.team**

— Braivex, 2026-05-20
