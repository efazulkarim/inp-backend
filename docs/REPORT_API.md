# Report Generation API Guide

Report generation is **asynchronous**. Request generation → poll status → fetch report when complete.

**Base path:** `/api/report`

**Authentication:** All endpoints require a valid session (cookie) or Bearer token.

---

## Flow Overview

```
POST /api/report/generate/{idea_id}  →  Get report_id
         ↓
GET /api/report/status/{report_id}   →  Poll until status = "completed"
         ↓
GET /api/report/report/{idea_id}    →  Fetch report JSON
GET /api/report/download/{idea_id}  →  Download PDF
```

---

## Endpoints

### 1. Request Report Generation

**`POST /api/report/generate/{idea_id}`**

Queues report generation. Returns immediately with `report_id` for status polling.

| Param    | Type | Description        |
|----------|------|--------------------|
| `idea_id`| int  | Path. Idea board ID |

**Request:** No body. `idea_id` in path.

**Response:** `201` or `200`

```json
{
  "report_id": 42,
  "status": "queued",
  "message": "Report generation has been queued"
}
```

**When report already exists:**

```json
{
  "report_id": 42,
  "status": "completed",
  "message": "Report already exists"
}
```

**When report is in progress:**

```json
{
  "report_id": 42,
  "status": "processing",
  "message": "Report generation in progress"
}
```

**Error responses:**

| Status | Condition | Response body |
|--------|-----------|---------------|
| 400 | Idea incomplete | `{"detail": "Cannot generate report for incomplete idea. All steps must be completed."}` |
| 403 | No subscription | `{"detail": "Active subscription required to generate reports."}` |
| 404 | Idea not found | `{"detail": "Idea not found"}` |
| 429 | Quota exceeded | `{"detail": "Report limit reached (10 per billing period). Upgrade to generate more."}` |

---

### 2. Check Report Status

**`GET /api/report/status/{report_id}`**

Poll this endpoint until `status` is `"completed"` or `"failed"`.

| Param     | Type | Description |
|-----------|------|-------------|
| `report_id` | int | Path. Report ID from generate response |

**Request:** No body.

**Response:** `200`

```json
{
  "report_id": 42,
  "status": "completed",
  "created_at": "2025-02-28T10:00:00",
  "updated_at": "2025-02-28T10:05:23",
  "error_message": null
}
```

**Status values:** `queued` | `processing` | `completed` | `failed`

**When failed:**

```json
{
  "report_id": 42,
  "status": "failed",
  "created_at": "2025-02-28T10:00:00",
  "updated_at": "2025-02-28T10:02:15",
  "error_message": "No answers found for this idea"
}
```

**Error responses:**

| Status | Condition | Response body |
|--------|-----------|---------------|
| 404 | Report not found | `{"detail": "Report not found"}` |

---

### 3. Get Report Content

**`GET /api/report/report/{idea_id}`**

Returns the full report JSON when generation is complete.

| Param    | Type | Description        |
|----------|------|--------------------|
| `idea_id`| int  | Path. Idea board ID |

**Request:** No body.

**Response:** `200`

```json
{
  "idea_name": "AI-Powered Task Manager",
  "overall_score": 78,
  "report_overview": "The idea demonstrates strong market potential with clear problem-solution fit. Key strengths include well-defined target audience and compelling value proposition. Areas for improvement: competitive differentiation and feasibility validation.",
  "sections": [
    {
      "category": "Target audience",
      "score": 8,
      "weighted_score": 9,
      "insight": "Clear demographic and psychographic definition. Strong alignment with identified pain points.",
      "recommendations": [
        "Consider adding behavioral segmentation",
        "Validate assumptions with customer interviews"
      ]
    },
    {
      "category": "Problem Identification",
      "score": 7,
      "weighted_score": 9,
      "insight": "Problem is well articulated but could benefit from quantitative validation.",
      "recommendations": [
        "Add market research data to support problem magnitude",
        "Include competitor gap analysis"
      ]
    }
  ],
  "strategic_next_steps": [
    "Conduct 5–10 customer interviews to validate problem-solution fit",
    "Build a minimal prototype for usability testing",
    "Define success metrics and set up tracking"
  ]
}
```

**Error responses:**

| Status | Condition | Response body |
|--------|-----------|---------------|
| 202 | Report in progress | `{"detail": "Report is processing. Please check status endpoint."}` |
| 404 | No report / idea not found | `{"detail": "No report found. Please request a report generation first."}` or `{"detail": "Idea not found"}` |

---

### 4. Download Report as PDF

**`GET /api/report/download/{idea_id}`**

Returns a PDF file for download.

| Param    | Type | Description        |
|----------|------|--------------------|
| `idea_id`| int  | Path. Idea board ID |

**Request:** No body.

**Response:** `200`

- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="Idea_Name_Report.pdf"`
- **Body:** Binary PDF

**Error responses:**

| Status | Condition | Response body |
|--------|-----------|---------------|
| 404 | Report not found or incomplete | `{"detail": "Report not found or incomplete"}` |

---

## Example: Full Flow (cURL)

```bash
# 1. Request generation
curl -X POST "https://api.example.com/api/report/generate/5" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json"

# Response: {"report_id": 42, "status": "queued", "message": "Report generation has been queued"}

# 2. Poll status (repeat every 3–5 seconds)
curl "https://api.example.com/api/report/status/42" \
  -H "Cookie: session=..."

# Response (when done): {"report_id": 42, "status": "completed", ...}

# 3. Fetch report JSON
curl "https://api.example.com/api/report/report/5" \
  -H "Cookie: session=..."

# 4. Download PDF
curl -o report.pdf "https://api.example.com/api/report/download/5" \
  -H "Cookie: session=..."
```

---

## Example: Frontend Polling (TypeScript)

```typescript
async function generateAndWaitForReport(ideaId: number): Promise<Report> {
  const { report_id } = await fetch(`/api/report/generate/${ideaId}`, {
    method: "POST",
    credentials: "include",
  }).then((r) => r.json());

  while (true) {
    const status = await fetch(`/api/report/status/${report_id}`, {
      credentials: "include",
    }).then((r) => r.json());

    if (status.status === "completed") break;
    if (status.status === "failed") {
      throw new Error(status.error_message ?? "Report generation failed");
    }

    await new Promise((r) => setTimeout(r, 3000));
  }

  return fetch(`/api/report/report/${ideaId}`, {
    credentials: "include",
  }).then((r) => r.json());
}
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors, `detail` may be an object with field-level messages.
