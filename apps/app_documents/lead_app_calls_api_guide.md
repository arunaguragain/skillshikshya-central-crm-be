# Lead App — Calls API Guide

**Base URL:** `http://localhost:8188`

## Endpoints

All CRUD endpoints are nested under a specific lead. A flat cross-lead call log is also available.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/calls/` | **All calls across leads** (paginated, newest first) | Authenticated |
| GET | `/api/leads/{lead_id}/calls/` | List calls for one lead (paginated) | Authenticated |
| POST | `/api/leads/{lead_id}/calls/` | Add a call (consumes call minutes) | Staff or `lead.add_leadcall` permission |
| GET | `/api/leads/{lead_id}/calls/{id}/` | Get call detail | Authenticated |
| PATCH | `/api/leads/{lead_id}/calls/{id}/` | Update call notes/outcome etc. | Staff or `lead.change_leadcall` permission |

> **DELETE is disabled** — call records are permanent and cannot be deleted via the API (`405 Method Not Allowed`), so the call-minutes ledger stays trustworthy.

## Global Call Log — `GET /api/calls/`

Read-only list of every call across all leads, **branch-scoped** (staff see all / `?branch_id=X`; non-staff locked to their branch). Ordered by `call_timestamp` descending by default.

**Query params:**

| Parameter | Description |
|-----------|-------------|
| `direction` | `inbound` or `outbound` |
| `created_by` | User ID — calls logged by that user |
| `student` | Student ID — calls on the lead linked to that student |
| `lead` | Lead ID |
| `call_timestamp__gte` / `__lte` | Date/time range (ISO 8601) |
| `search` | Matches caller, phone number, outcome, notes, lead name & reference number |
| `ordering` | `call_timestamp`, `duration_seconds`, `created_at` (prefix `-` for desc) |
| `page` / `page_size` | Standard pagination |

**Example response row:**
```json
{
    "id": 24,
    "lead": 101,
    "lead_name": "Sita Kumari InvoiceTest",
    "lead_reference_number": "LD-2026-000086",
    "call_timestamp": "2026-08-26T05:48:13Z",
    "direction": "outbound",
    "caller": "Shikhar",
    "phone_number": "9877700111",
    "duration_seconds": 270,
    "outcome": "Interested",
    "notes": "",
    "branch": 1,
    "created_by": 9,
    "created_by_name": "Shikhar"
}
```

The `lead` field is auto-set from the URL. `created_by` is auto-set to the requesting user.

## Global Call Summary — `GET /api/calls/summary/`

Returns an unpaginated summary of calls after applying the same filters, search, ordering, and branch scoping as the global call log.

**Query params:** the same call filters as [`GET /api/calls/`](#global-call-log--get-apicalls), including `direction`, `created_by`, `student`, `lead`, `call_timestamp__gte` / `call_timestamp__lte`, `search`, and `ordering`. `branch_id` narrows results for staff and superusers; it does not override a non-staff user's assigned branch.

**Response:**
```json
{
    "total_calls": 2,
    "inbound": 1,
    "outbound": 1,
    "total_seconds": 180,
    "total_formatted": "03:00",
    "avg_seconds": 90,
    "connected_calls": 2,
    "connect_rate": 1.0,
    "by_day": [
        {"date": "2026-10-29", "calls": 2, "seconds": 180}
    ],
    "by_user": [
        {"user_id": 9, "name": "Counselor", "calls": 2, "seconds": 180}
    ]
}
```

`by_day` dates use Nepal time. `by_user` contains up to 10 users, ordered by call count descending; calls without a creator use `user_id: null` and `name: "Unknown"`. `connect_rate` is the connected-call share rounded to three decimal places; a call is connected when `duration_seconds > 0`.

Staff and superusers see calls from all branches by default and may provide `branch_id`. Non-staff users with an assigned branch only see that branch, even if they provide another `branch_id`. A non-staff user without an assigned branch currently receives the unscoped call queryset.

## Global Call Export — `GET /api/calls/export/`

Downloads a streamed UTF-8 CSV using the same call filters, search, ordering, and branch scoping as the global call log. The export is not paginated.

**Query params:** the same call filters as [`GET /api/calls/`](#global-call-log--get-apicalls), including `direction`, `created_by`, `student`, `lead`, `call_timestamp__gte` / `call_timestamp__lte`, `search`, and `ordering`. Staff and superusers may use `branch_id` to select a branch.

**Filename:** `calls-YYYY-MM-DD.csv`, with the date based on Asia/Kathmandu.

**CSV columns, in order:**
1. Date & time (NPT)
2. Direction
3. Lead
4. Reference
5. Phone
6. Caller
7. Logged by
8. Duration (MM:SS)
9. Seconds
10. Outcome
11. Notes
12. Recording

Date & time values use `YYYY-MM-DD HH:MM:SS` in Nepal time. The CSV begins with a UTF-8 BOM for spreadsheet compatibility.

Staff and superusers see calls from all branches by default and may provide `branch_id`. Non-staff users with an assigned branch only see that branch, even if they provide another `branch_id`. A non-staff user without an assigned branch currently receives the unscoped call queryset.

## Call Minutes Deduction

Creating a call **deducts minutes from the requesting user's balance**:

- Minutes charged = the call's **exact `duration_seconds`** (no rounding). A 4m30s (270s) call deducts exactly 270 seconds; a 0-second call is recorded but deducts nothing.
- If the balance is lower than the required minutes, the call is **rejected** with:
  ```json
  { "detail": "Insufficient call minutes (required 270 seconds, available 120 seconds)." }
  ```
- On success, the response includes: `seconds_used`, `remaining_seconds`, plus floored `minutes_used` / `remaining_minutes` for convenience.
- Every deduction writes a row in the immutable ledger in **seconds** (see [Call Minutes](account_app_apis_guide.md#call-minutes)).
- `duration_seconds` and `caller` are **locked after creation** — PATCH requests silently ignore changes to them.

### Flexible duration input (`duration_input`)

Send `duration_input` instead of `duration_seconds` — the backend parses these formats into seconds:

| Input | Meaning | Stored |
|-------|---------|--------|
| `"4:19"` | 4 min 19 sec | `259` |
| `"4.19"` | 4 min 19 sec (dot = MM.SS) | `259` |
| `"04:19"` | 4 min 19 sec (leading zero) | `259` |
| `"4m19s"` | 4 min 19 sec (suffix) | `259` |
| `"1:02:30"` | 1 hr 2 min 30 sec | `3750` |
| `"259"` | raw seconds | `259` |
| `"4.5"` | 4 min **05** sec (single digit = seconds, zero-padded) | `245` |
| `"7.89"` | **carries**: 7 min 89 sec → 8 min 29 sec | `509` |
| `"7:89"` | carries: 8 min 29 sec | `509` |

> **Overflow carry:** any seconds/minutes part ≥ 60 automatically rolls up (stopwatch style) — `7.89` → 8:29, `1:99:99` → 2:40:39.

**Request:**
```json
{
    "call_timestamp": "2026-08-26T05:48:00Z",
    "caller": "Counselor",
    "phone_number": "9800000001",
    "duration_input": "4:19",
    "outcome": "Interested"
}
```
Invalid formats return `400 {"duration_input": ["Invalid duration format: …"]}`. The plain integer `duration_seconds` field is still accepted unchanged.

### Formatted duration in responses

Every call response includes `duration_formatted` (`"MM:SS"`, e.g. `"04:19"`) for display.

**Example POST response (201):**
```json
{
    "id": 21,
    "duration_seconds": 259,
    "duration_formatted": "04:19",
    "seconds_used": 259,
    "remaining_seconds": 330,
    "minutes_used": 4,
    "remaining_minutes": 5,
    "...": "…other standard fields…"
}
```

---

## Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-generated |
| `lead` | int (FK, read-only) | Auto-set from URL |
| `call_timestamp` | datetime | When the call occurred |
| `direction` | string | `inbound` or `outbound` |
| `caller` | string | Caller name |
| `phone_number` | string | Phone number called/received |
| `duration_seconds` | int | Duration in seconds |
| `duration_input` | string (write-only) | Flexible duration input — accepts `"4:19"`, `"4.19"`, `"04:19"`, `"4m19s"`, raw seconds, `"H:MM:SS"`. Parsed to `duration_seconds`. |
| `duration_formatted` | string (read-only) | Display format `"MM:SS"` (e.g. `"04:19"`) |
| `outcome` | string | Call outcome description |
| `notes` | text | Notes |
| `recording_url` | string | URL to call recording |
| `next_followup_at` | datetime | Suggested next followup time |
| `next_action` | text | Suggested next action |
| `branch` | int (FK) | Branch ID |
| `created_by` | int (FK, read-only) | Auto-set |
| `created_by_name` | string (read-only) | Creator display name |
| `created_at` | datetime (read-only) | Created timestamp |

### Auto-updates on Lead

When a call is created, the parent lead is automatically updated:

| Lead field | Effect |
|------------|--------|
| `last_contact_at` | Set to `call_timestamp` if newer than existing value |
| `lead_score` | Recalculated (engagement factor) |

---

## POST `/api/leads/{lead_id}/calls/` — Add a Call

**Request:**
```json
{
    "call_timestamp": "2026-07-21T12:00:00Z",
    "direction": "inbound",
    "caller": "Rahul Sharma",
    "phone_number": "9812345678",
    "duration_seconds": 120,
    "outcome": "Interested, requested demo",
    "notes": "Wants to know about pricing",
    "recording_url": null,
    "next_followup_at": null,
    "next_action": null
}
```

`direction` options: `inbound`, `outbound`

---

## GET `/api/leads/{lead_id}/calls/` — List Calls

**Query params:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `direction` | string | Filter by direction (`inbound`, `outbound`) |
| `call_timestamp__gte` | datetime | Called after |
| `call_timestamp__lte` | datetime | Called before |
| `ordering` | string | Order by `call_timestamp`, `duration_seconds` (prefix `-` for desc) |
| `page` | int | Page number |
| `page_size` | int | Items per page (max 100) |

**Examples:**
```
GET /api/leads/1/calls/?direction=inbound
GET /api/leads/1/calls/?call_timestamp__gte=2026-07-01T00:00:00Z
GET /api/leads/1/calls/?ordering=-call_timestamp
```

---

## PATCH `/api/leads/{lead_id}/calls/{id}/` — Update Call

```json
{
    "outcome": "Demo scheduled for July 25",
    "next_followup_at": "2026-07-25T10:00:00Z"
}
```

---

## DELETE `/api/leads/{lead_id}/calls/{id}/` — Delete Call

**Response:** `204 No Content`
