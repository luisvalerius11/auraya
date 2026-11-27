# CRM: agent links and lead activity in the Google Sheet

The brochure stays open to everyone. What's new:

1. **Agent links.** Each agent gets their own link. On it, every contact button goes to that agent, and anything their clients do is tagged with the agent's ID.
2. **Lead activity.** Key moments from known leads and agent-link visitors go to a new n8n webhook, which adds one row per moment to an **Activity** tab in your Google Sheet. Visitors must turn on "Follow-up" in the cookie banner first.

Anonymous visitors (no agent link, no investor-pack link) send nothing to the CRM.

---

## 1. Add an agent

In `assets/ref.js`, add one line to `AGENTS`:

```js
var AGENTS = {
  'putu':  { name:'Putu Ayu',  agency:'Bali Homes', wa:'6281234567890', email:'putu@balihomes.com' },
  'james': { name:'James Lee', wa:'6587654321' },
};
```

- **id** (`putu`): lowercase letters, digits and dashes. It appears in the link.
- **wa**: WhatsApp number, country code first, digits only.
- **email** and **agency**: optional.

Then send the agent their links:

| Page | Link |
|---|---|
| Brochure | `https://auraya-villas.com/brochure/?agent=putu` |
| Payment simulator | `https://auraya-villas.com/plan/?agent=putu` |
| Landing page (investor-pack form) | `https://auraya-villas.com/?agent=putu` |

What changes on an agent link:
- **Contact buttons:** every WhatsApp and email button on the brochure, ROI model and simulator goes to the agent.
- **Brochure last page:** shows "Your agent" with their name and contact details. Auraya appears as a small "Developer" line below. To hide that line, set `SHOW_DEVELOPER_WITH_AGENT = false` in `assets/ref.js`.
- **Leads:** forms sent from the landing page carry `agent=putu`.
- **Activity:** every activity row carries `agent=putu`.

The tag follows the reader through brochure → ROI model → simulator within the same browser tab. A plan link shared from the simulator keeps the tag too.

## 2. Create the activity webhook in n8n

**Use a new workflow.** Don't reuse the investor-pack webhook, or every event would be treated as a new lead and get a WhatsApp first reply.

1. **Webhook node**
   - Method: POST
   - Respond: immediately
   - Copy the **production** URL (`/webhook/...`, not `/webhook-test/...`).
   - The site sends form-encoded fields, which n8n reads into `body`.
2. **Google Sheets node:** Append row to a new tab named **Activity**, mapping the fields below.
3. Toggle the workflow **Active**.
4. Paste the production URL into `CRM_URL` in `assets/analytics.js`.

Once `CRM_URL` is set, the cookie banner appears with a **Follow-up** option. The privacy policy already describes this feed.

### Fields sent

| Field | Example | Notes |
|---|---|---|
| `event` | `plan_built` | See the list below |
| `lid` | `3f2c…` | Lead ID from the investor-pack form; matches `lead_id` in the leads tab. Empty for agent-link visitors who never filled in the form. |
| `agent` | `putu` | Empty when not on an agent link |
| `session` | `k2j9x0lm…` | One browser tab visit. Groups the rows of one reading session. |
| `area` | `brochure` | `landing`, `brochure`, `roi` or `plan` |
| `page` | `/plan/` | |
| `sent_at` | `2026-11-27T10:12:03Z` | |
| `detail` | `Price List` | Page name for `brochure_key_page`; `whatsapp` or `email` for `contact` |
| `villa`, `tenure`, `addons`, `promos`, `total_idr`, `reserve_idr`, `reserve_date`, `plan_url` | `A4`, `free`, `jacuzzi,solar`, … | Only on `plan_built`. `plan_url` reopens the exact plan. |

### Events

Each event is sent at most once per visit, except `plan_built` (once per different plan) and `contact`.

| Event | When |
|---|---|
| `brochure_open` | The brochure is opened |
| `brochure_key_page` | Reached Price List, Payment Timeline, ROI Projection or Floorplan |
| `brochure_complete` | Reached the last page |
| `roi_model_open` | Opened the full ROI calculation from the brochure |
| `plan_open` | Opened the payment simulator |
| `plan_built` | Settled on a plan (5 s without changes) or printed / saved it as PDF |
| `plan_print` | Printed or saved the plan as PDF |
| `contact` | Tapped a WhatsApp or email button |

## 3. Score leads in the Sheet

In the leads tab, add a **score** column. If `lead_id` is column H and the Activity tab has `event` in column A and `lid` in column B:

```
=COUNTIFS(Activity!B:B,H2,Activity!A:A,"brochure_open")*1
+COUNTIFS(Activity!B:B,H2,Activity!A:A,"brochure_key_page")*2
+COUNTIFS(Activity!B:B,H2,Activity!A:A,"brochure_complete")*2
+COUNTIFS(Activity!B:B,H2,Activity!A:A,"plan_built")*5
+COUNTIFS(Activity!B:B,H2,Activity!A:A,"contact")*5
```

Then sort or filter by score. Suggested **stage** column values:

New lead → Pack opened → Engaged (price page or plan built) → Call booked → Viewing → Reserved (10%) → Notarial signing (30%)

For agent clients who never filled in the form, there is no `lid`; group the Activity tab by `agent` and `session` instead.

## 4. Optional: instant alerts for hot moments

In the activity workflow, after the Sheets node, add:

**IF** `event` is `plan_built` or `contact` → send a WhatsApp or email to sales. Include `agent`, `villa`, `tenure`, `total_idr` and `plan_url`.

For example:

> 🔥 Plan built · agent putu · A4 freehold · Rp 6.021.585.600 · <plan_url>
