# Metric Modules Frontend Integration Guide

This guide explains how to integrate the optional metric-module flow in your frontend.

Base path: `/api/ideaboard`

Authentication: required on all endpoints (cookie session or Bearer token).

---

## Feature Flow

1. Fetch all available modules.
2. Enable one or more modules for an idea.
3. Fetch module questions for each enabled module.
4. Save module answers.
5. Trigger report generation (`/api/report/generate/{idea_id}`) to include enabled module analysis.

---

## API Contracts

### 1) List Available Modules

`GET /api/ideaboard/modules`

Response `200`:

```json
[
  {
    "id": 1,
    "slug": "unit_economics",
    "title": "Unit Economics",
    "description": "Evaluate the financial health signals of your SaaS.",
    "max_score": 9,
    "sort_order": 1
  }
]
```

---

### 2) Enable Module For Idea

`POST /api/ideaboard/ideas/{idea_id}/modules`

Request body:

```json
{
  "module_id": 1
}
```

Response `201`:

```json
{
  "id": 12,
  "idea_id": 45,
  "module_id": 1,
  "module_slug": "unit_economics",
  "module_title": "Unit Economics",
  "created_at": "2026-03-14T10:31:02.000000"
}
```

Common errors:
- `403`: plan does not include metric modules.
- `429`: module selection limit reached for current plan.
- `400`: module already enabled for idea.
- `404`: idea or module not found.

---

### 3) List Enabled Modules For Idea

`GET /api/ideaboard/ideas/{idea_id}/modules`

Response `200`:

```json
{
  "idea_id": 45,
  "modules": [
    {
      "id": 12,
      "idea_id": 45,
      "module_id": 1,
      "module_slug": "unit_economics",
      "module_title": "Unit Economics",
      "created_at": "2026-03-14T10:31:02.000000"
    }
  ]
}
```

---

### 4) Disable Module

`DELETE /api/ideaboard/ideas/{idea_id}/modules/{module_id}`

Response `200`:

```json
{
  "message": "Module disabled successfully"
}
```

---

### 5) Get Questions For Enabled Module

`GET /api/ideaboard/ideas/{idea_id}/module-questions/{module_slug}`

Response `200`:

```json
{
  "module_slug": "unit_economics",
  "module_title": "Unit Economics",
  "questions": [
    {
      "id": "cac_estimate",
      "question_text": "What is your estimated Customer Acquisition Cost (CAC)?",
      "description": null,
      "question_type": "single_choice",
      "options": ["<$50", "$50-$200", "$200-$500"]
    }
  ]
}
```

Common errors:
- `400`: module not enabled for this idea.
- `404`: idea or module not found.

---

### 6) Save Answers For Module

`POST /api/ideaboard/ideas/{idea_id}/module-answers/{module_slug}`

Request body:

```json
{
  "questions": [
    {
      "id": "cac_estimate",
      "type": "single_choice",
      "value": "$50-$200"
    },
    {
      "id": "content_strategy",
      "type": "textarea",
      "value": "We will lead with SEO + founder-led social."
    }
  ]
}
```

Response `200`:

```json
{
  "message": "Module answers saved successfully",
  "module_slug": "unit_economics",
  "idea_id": 45
}
```

Important note: unknown question IDs are ignored by backend save logic. You should validate IDs client-side to prevent silent drops.

---

## TypeScript Types

```typescript
export type ModuleQuestionType =
  | "text"
  | "textarea"
  | "single_choice"
  | "multiple_choice"
  | "slider";

export interface MetricModule {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  max_score: number;
  sort_order: number;
}

export interface ModuleSelection {
  id: number;
  idea_id: number;
  module_id: number;
  module_slug: string;
  module_title: string;
  created_at: string;
}

export interface IdeaModulesResponse {
  idea_id: number;
  modules: ModuleSelection[];
}

export interface ModuleQuestion {
  id: string;
  question_text: string;
  description: string | null;
  question_type: ModuleQuestionType;
  options: string[] | null;
}

export interface ModuleQuestionsResponse {
  module_slug: string;
  module_title: string;
  questions: ModuleQuestion[];
}

export interface ModuleAnswerItem {
  id: string;
  type: string;
  value: string | string[];
}

export interface ModuleAnswerCreate {
  questions: ModuleAnswerItem[];
}
```

---

## Recommended UI Mapping

- `text` and `textarea`: free text input.
- `single_choice`: radio/select (single value string).
- `multiple_choice`: checkbox group (string array).
- `slider`: range input (submit as string or numeric string based on your app conventions).

Keep submitted `type` aligned with rendered input to simplify analytics and debugging.

---

## Frontend Service Example (TypeScript)

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface RequestOptions extends RequestInit {
  accessToken?: string;
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message = errorBody.detail ?? "Request failed";
    throw new Error(`${response.status}: ${message}`);
  }

  return response.json() as Promise<T>;
}

export async function listModules(accessToken?: string) {
  return apiRequest<MetricModule[]>("/api/ideaboard/modules", { accessToken });
}

export async function enableIdeaModule(ideaId: number, moduleId: number, accessToken?: string) {
  return apiRequest<ModuleSelection>(`/api/ideaboard/ideas/${ideaId}/modules`, {
    method: "POST",
    body: JSON.stringify({ module_id: moduleId }),
    accessToken,
  });
}

export async function getIdeaModules(ideaId: number, accessToken?: string) {
  return apiRequest<IdeaModulesResponse>(`/api/ideaboard/ideas/${ideaId}/modules`, { accessToken });
}

export async function getModuleQuestions(ideaId: number, moduleSlug: string, accessToken?: string) {
  return apiRequest<ModuleQuestionsResponse>(
    `/api/ideaboard/ideas/${ideaId}/module-questions/${moduleSlug}`,
    { accessToken }
  );
}

export async function saveModuleAnswers(
  ideaId: number,
  moduleSlug: string,
  payload: ModuleAnswerCreate,
  accessToken?: string
) {
  return apiRequest<{ message: string; module_slug: string; idea_id: number }>(
    `/api/ideaboard/ideas/${ideaId}/module-answers/${moduleSlug}`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      accessToken,
    }
  );
}
```

---

## Suggested Screen/UX Sequence

1. On idea details page, call `GET /modules` and `GET /ideas/{idea_id}/modules`.
2. Show enabled state and plan guard messages:
   - `403`: show upgrade CTA.
   - `429`: show "module limit reached" CTA.
3. After enabling a module, fetch its questions immediately.
4. Autosave or explicit save to `/module-answers/{module_slug}`.
5. On report generation page, explain that enabled modules add extra analysis sections.

---

## Security Notes For Frontend

- Do not store long-lived tokens in `localStorage`.
- Prefer secure, httpOnly cookies for session/token storage.
- Send CSRF token on state-changing requests if your frontend already has CSRF middleware in place.
- Treat all backend errors as user-safe strings (`detail`) and avoid exposing internal debug data.

---

## Seeded Module Slugs (Current)

- `unit_economics`
- `go_to_market`
- `technical_feasibility`
- `network_effects`
- `regulatory_risk`

Use `GET /api/ideaboard/modules` as the source of truth instead of hardcoding this list in UI.
