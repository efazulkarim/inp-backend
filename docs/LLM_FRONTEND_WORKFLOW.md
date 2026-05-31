# Frontend Guide: AI (LLM) Integration Workflow

This guide explains how the frontend should integrate with the current AI workflow.

The backend does **not** expose direct prompt/chat endpoints for production frontend use.  
Frontend AI behavior is driven by the **report pipeline**.

---

## TL;DR

- Frontend triggers AI by calling `POST /api/report/generate/{idea_id}`.
- Generation is async: poll `GET /api/report/status/{report_id}`.
- Fetch final AI output from `GET /api/report/report/{idea_id}`.
- Optional PDF download: `GET /api/report/download/{idea_id}`.
- `GET /api/report/test-llm` is a backend diagnostic route; do not depend on it in production UX.

---

## Current Architecture

Frontend should treat AI generation as a job workflow:

1. User completes ideaboard questionnaire steps.
2. Frontend requests report generation.
3. Backend queues background generation.
4. Frontend polls status.
5. Frontend displays report JSON when completed.

The backend internally chooses LLM provider by priority:

1. OpenRouter
2. ApiFreeLLM
3. GLM
4. Vultr

Provider selection is backend-managed; frontend should not assume a specific provider.

---

## Endpoints the Frontend Should Use

Base path: `/api/report`

### 1) Start AI generation

`POST /api/report/generate/{idea_id}`

Success:

```json
{
  "report_id": 123,
  "status": "queued",
  "message": "Report generation has been queued"
}
```

Possible responses:

- `200` queued
- `200` already completed
- `200` in progress
- `400` incomplete idea
- `403` no active subscription
- `429` monthly report limit reached

### 2) Poll generation status

`GET /api/report/status/{report_id}`

```json
{
  "report_id": 123,
  "status": "processing",
  "created_at": "2026-03-17T10:00:00",
  "updated_at": "2026-03-17T10:00:20",
  "error_message": null
}
```

Status values:

- `queued`
- `processing`
- `completed`
- `failed`

### 3) Get completed AI report

`GET /api/report/report/{idea_id}`

Returns final AI report JSON (overview, section insights, recommendations, strategic next steps).

### 4) Download AI report PDF

`GET /api/report/download/{idea_id}`

Returns `application/pdf`.

---

## Frontend Implementation Pattern

```typescript
type ReportStatus = "queued" | "processing" | "completed" | "failed";

async function generateReportFlow(ideaId: number, token: string) {
  const auth = { Authorization: `Bearer ${token}` };

  const start = await fetch(`/api/report/generate/${ideaId}`, {
    method: "POST",
    headers: auth,
  });

  const startBody = await start.json();
  if (!start.ok) throw new Error(startBody.detail || "Failed to queue report");

  const reportId = startBody.report_id as number;

  while (true) {
    const statusRes = await fetch(`/api/report/status/${reportId}`, { headers: auth });
    const statusBody = await statusRes.json();
    if (!statusRes.ok) throw new Error(statusBody.detail || "Status check failed");

    const status = statusBody.status as ReportStatus;
    if (status === "completed") break;
    if (status === "failed") throw new Error(statusBody.error_message || "Report generation failed");

    await new Promise((r) => setTimeout(r, 2500));
  }

  const reportRes = await fetch(`/api/report/report/${ideaId}`, { headers: auth });
  const reportBody = await reportRes.json();
  if (!reportRes.ok) throw new Error(reportBody.detail || "Failed to load report");

  return reportBody;
}
```

---

## What Changed vs Previous Integration

Yes, the integration is changed in practice:

- Frontend should now rely on the **job-style report workflow** as the AI integration contract.
- LLM provider routing is fully backend-controlled with fallback priority; frontend no longer needs provider-specific behavior.
- Subscription gating and monthly limits are enforced before generation, so frontend must handle `403` and `429`.
- Report generation status and completion are first-class API states (`queued`, `processing`, `completed`, `failed`).

What did **not** change:

- Frontend still consumes AI output as report JSON and can download PDF.

---

## Additional Backend Changes to Know

These recent backend changes are not AI-generation logic themselves, but they affect frontend integration and testing environments:

- Billing is now **Polar-only**. Use `GET /api/polar/plans` for live plan pricing and `POST /api/polar/create-checkout` for checkout links.
- Stripe checkout/subscription fallback is removed. Frontend should not call Stripe billing endpoints.
- Report generation still enforces subscription and plan limits before queueing (`403` for inactive subscription, `429` for plan limit reached).
- Backend startup is now strict about environment variables (`DATABASE_URL`, `SECRET_KEY`). Missing values fail fast at startup.
- Deployment/runtime docs were added for infrastructure setup (`docs/deployment/NEON_SETUP.md`, `docs/deployment/VERCEL.md`) and CI was added to validate lint/import/migrations.
- If your local DB is new or changed, make sure migrations are applied before testing report flows.

Recommended frontend handling for these changes:

- Show a clear “upgrade required” state on `403` from report generation.
- Show a “monthly limit reached” state on `429` and route users to billing.
- Refresh subscription status from Polar after checkout success before allowing report actions.

---

## UX Recommendations

- Disable “Generate Report” button while request is inflight.
- Show status chips: `Queued`, `Generating`, `Completed`, `Failed`.
- Poll every 2-3s; stop polling on completion/failure/unmount.
- Retry button for transient failures.
- Show specific backend error messages (`detail`, `error_message`) to reduce support tickets.

---

## Related Docs

- `docs/REPORT_API.md`
- `docs/POLAR_FRONTEND_GUIDE.md`
