# Data Endpoints Documentation

## User Data
- **Endpoint:** `GET /v1/users/{userId}`
- **Description:** Retrieves profile information for a specific user.
- **Required Scope:** `users:read`

- **Endpoint:** `POST /v1/users`
- **Description:** Creates a new user in the system. The request body must contain the user's name and email.
- **Required Scope:** `users:write`

## Project Data
- **Endpoint:** `GET /v1/projects`
- **Description:** Fetches a list of all projects accessible to the authenticated user.
- **Required Scope:** `projects:read`

- **Endpoint:** `GET /v1/projects/{projectId}/details`
- **Description:** Retrieves detailed information, including team members and milestones, for a specific project.
- **Required Scope:** `projects:read`

