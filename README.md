# FairGig — Backend Documentation

## 1. System Architecture Overview

FairGig's backend is built using a **Microservice Architecture** that segregates responsibilities across different domains to ensure scalability, modularity, and privacy. 

The ecosystem leverages:
- **Python (FastAPI)** for core transaction-level services (Auth, Users, Jobs, Earnings, Anomaly Detection).
- **Node.js** for asynchronous processing and specific domain tasks (Analytics, Certificates, Grievances).
- **PostgreSQL 17+** / **Supabase** as the master database, partitioned via schemas for different logical domains.
- **Docker & Docker Compose** for local orchestration.

---

## 2. Service Breakdown

### Python Services (`/services`)
Running on FastAPI and managed with the `uv` package manager:
- **Auth Service (`port 8001`)**: Handles JWT authentication, user registration, and identity.
- **Users Service (`port 8002`)**: Manages user profiles (Workers, Verifiers, Advocates).
- **Jobs Service (`port 8003`)**: Orchestrates job or gig postings and applications.
- **Earnings Service**: Processes shift logs, platform fee deductions, and verification screenshots.
- **Anomaly-Service**: An AI/ML or statistical service to flag suspicious activities or unverified shifts.

### Node.js Services (`/services-node`)
- **Analytics Service**: Aggregates anonymous data for market trends, average pay, and geographic analysis.
- **Certificate Service**: Generates compliance or proof-of-work certificates for cross-platform sharing.
- **Grievance Service**: Handles worker complaints, categorizes them, and tracks their resolution workflow securely.

---

## 3. Database Schema Design (`schema.sql`)

The database is heavily namespaced using PostgreSQL schemas to map directly to the microservice architecture.

### Schema: `auth_svc` (Identity & Roles)
Handles user identity and role-based access control.
- **`roles`**: Table for system roles (`Worker`, `Verifier`, `Advocate`).
- **`users`**: Central users table containing `email`, `password_hash`, `full_name`, `phone`, and `city_zone` (for anonymized geography).
- **`user_roles`**: Junction table allowing many-to-many relationships (a user can hold multiple roles).

### Schema: `earnings_svc` (Shifts & Verifications)
Handles financial and work logs.
- **`shifts`**: Primary shift records with `hours_worked`, `gross_earned`, `platform_deductions`, and `net_received`. Links to the `users` table (`worker_id`).
- **`screenshots`**: Pay-slip evidence attached to shifts. Tracked via `status` (`Pending`, `Confirmed`, `Flagged`, `Unverifiable`) and reviewed by a `verifier_id`.
- **`anonymized_shifts (View)`**: Secure, read-only view that strips PII (`worker_id`, name, phone) but retains `city_zone` and earnings metrics. The **Analytics Service** interacts strictly with this view.

### Schema: `grievance_svc` (Dispute Resolution)
Manages worker complaints against platforms.
- **`grievances`**: Tickets with `category` (e.g. Unfair Deduction) and `status` (Open, Under Review, Resolved). Includes an `is_anonymous` flag.
- **`grievance_comments`**: Community or advocate replies linked to a grievance.
- **`grievance_tags`**: Hashtags assigned to grievances to enable clustering and trending topic algorithms.

---

## 4. Development & Deployment

### Environments
The app seamlessly switches databases using the `ENV` variable defined in `.env`:
- `ENV=local`: Connects to local PostgreSQL using `DATABASE_URL`.
- `ENV=prod`: Connects to `SUPABASE_DB_URL` for production.

### Local Initialization
```bash
# Sync python dependencies (cached locally)
uv sync

# Run services
uv run uvicorn services.auth.app:app --reload --port 8001
uv run uvicorn services.users.app:app --reload --port 8002
uv run uvicorn services.jobs.app:app --reload --port 8003
```

Docker Compose provides a complete bundled container setup for out-of-the-box local testing. 

## 5. Security & Privacy Implementation
- Passwords are strictly hashed with **bcrypt**; raw passwords are never kept.
- Privacy-first views (like `anonymized_shifts`) actively prevent the analytics dashboards and aggregation queries from inadvertently accessing personally identifiable data.
- User Identity schema (`auth_svc`) serves as the root of trust, and other services use `ON DELETE CASCADE` appropriately to handle user data requests and GDPR/deletion policies effectively.
