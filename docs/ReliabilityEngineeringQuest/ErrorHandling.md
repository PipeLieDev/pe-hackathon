# Error Handling Documentation

This document describes how the URL Shortener API validates input and handles application-level errors.

---

## 1. Invalid / Garbage Input

| Scenario | Endpoint(s) | Response | Details |
|---|---|---|---|
| Missing required fields | `POST /users`, `POST /urls` | `422 Unprocessable Entity` | JSON body with validation errors from marshmallow schemas |
| Invalid email format | `POST /users`, `PUT /users/:id` | `422 Unprocessable Entity` | Schema rejects non-email strings |
| Invalid URL format | `POST /urls`, `PUT /urls/:id` | `422 Unprocessable Entity` | `validate.URL()` rejects non-URL strings |
| Wrong data types (e.g. int for username) | `POST /users` | `422 Unprocessable Entity` | Schema type validation |
| Empty JSON body `{}` | `POST /users`, `POST /urls` | `422 Unprocessable Entity` | Required fields missing |
| Non-JSON content type | All POST/PUT endpoints | `400 Bad Request` | flask-smorest rejects non-JSON payloads |
| Nonexistent resource ID | `GET/PUT/DELETE /users/:id`, `/urls/:id` | `404 Not Found` | JSON `{"message": "... not found"}` |
| Duplicate email on user create | `POST /users` | `409 Conflict` | `{"message": "Email already exists"}` |
| Referencing nonexistent user in URL create | `POST /urls` | `404 Not Found` | Checks user existence before creating |
| Referencing nonexistent URL/user in event create | `POST /events` | `404 Not Found` | Validates foreign keys before insert |

**Key behavior:** All error responses are returned as JSON. The app never exposes Python stack traces to the client.

---

## 2. Data Integrity Errors

| Scenario | Behavior |
|---|---|
| Short code collision on URL create | Retry loop generates a new code (up to 10 attempts). Returns `500` only if all 10 fail. |
| Deleting a URL with events | Events are explicitly deleted first (`Event.delete().where(Event.url_id == url.id)`), then the URL is removed. No orphaned records. |
| Deleting a user with URLs | **Not handled.** Deleting a user who owns URLs will fail with a foreign key constraint error (500). URLs must be deleted first. |

---

## Summary

| Error Type | User Sees | Auto-Recovery? |
|---|---|---|
| Bad input | Clean JSON error (400/404/409/422) | N/A |
| Short code collision | Transparent (retried internally) | Yes |
