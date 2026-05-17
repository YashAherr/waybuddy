# WayBuddy — Airport Companion Matching Platform

> Connecting solo travellers with volunteer helpers at airports.

**Live at [way-buddy.in](https://way-buddy.in)**

---

## What is WayBuddy?

Solo travellers — especially elderly passengers, first-time flyers, and people with disabilities — often struggle to navigate airports alone. WayBuddy is a platform that connects them with experienced volunteer helpers before their flight.

Seekers register their travel details. Helpers register their availability and skills. An admin manually reviews and matches pairs, then notifies both parties by email with each other's contact details.

---

## Architecture

```
Browser
   │
   ├── way-buddy.in/              → Landing page (HTML)
   ├── way-buddy.in/seeker-form   → Seeker registration (HTML + JS)
   ├── way-buddy.in/helper-form   → Helper registration (HTML + JS)
   └── way-buddy.in/dashboard     → Admin dashboard (HTML + JS, login protected)
         │
         └── POST/GET /api/*
               │
               └── Flask (Python) on Render
                     │
                     └── PostgreSQL on Neon
```

All static files are served by Flask itself — no separate static host needed. The frontend makes API calls to relative paths (`/api/admin/seekers`) so there are no CORS issues.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Vanilla HTML + CSS + JavaScript | Zero build complexity. No framework needed for an admin tool. |
| Backend | Python Flask 3.x | Lightweight, well-documented, large ecosystem. |
| ORM | SQLAlchemy via Flask-SQLAlchemy | Maps DB rows to Python objects. Prevents SQL injection. |
| Database | PostgreSQL 16 on Neon | Relational data model with foreign key constraints. Free tier. |
| Hosting | Render (free tier) | Zero cost for low-traffic apps. Auto-deploys from GitHub on push. |
| Email | Gmail SMTP via Python smtplib | Sends match confirmation emails with contact details to both parties. |
| Auth | Flask session-based login | Session cookie with 7-day expiry protects the admin dashboard. |
| DNS | AWS Route 53 | Manages way-buddy.in domain. |

**Monthly cost: ~$1.17** (Route 53 $0.50 + domain $0.67/month)

---

## Database Schema

```
seekers     — Solo traveller registrations
helpers     — Volunteer helper registrations
matches     — Admin-confirmed seeker-helper pairings
payments    — Razorpay payment records (ready, not yet integrated)
```

**Status lifecycles:**

```
Seeker:  approved → matched → completed
Helper:  pending_approval → approved → matched
Match:   confirmed → notified → completed
```

---

## API Routes

| Method | Route | Description | Auth |
|---|---|---|---|
| GET | `/health` | Health check | Public |
| POST | `/api/register/seeker` | Register a seeker | Public |
| POST | `/api/register/helper` | Register a helper | Public |
| GET | `/api/admin/seekers` | List seekers, filterable by status | Session |
| GET | `/api/admin/helpers` | List helpers, filterable by status | Session |
| GET | `/api/admin/matches` | List all confirmed matches | Session |
| POST | `/api/admin/match` | Confirm a seeker-helper pair | Session |
| POST | `/api/admin/approve-helper` | Approve a pending helper | Session |
| POST | `/api/admin/unmatch` | Remove a match, reset both statuses | Session |
| POST | `/api/notify/match` | Send email notifications to both parties | Session |
| GET | `/login` | Admin login page | Public |
| POST | `/login` | Authenticate admin | Public |
| GET | `/logout` | End admin session | Session |

---

## Project Structure

```
waybuddy/
├── wsgi.py                    # Gunicorn entry point
├── Procfile                   # Render start command
├── runtime.txt                # Python 3.11.0
├── requirements.txt           # Python dependencies
├── app/
│   ├── __init__.py            # Flask app factory, routes, auth
│   ├── models.py              # SQLAlchemy models: Seeker, Helper, Match, Payment
│   └── routes/
│       ├── register.py        # Seeker and helper registration endpoints
│       ├── admin.py           # Admin matching and management endpoints
│       └── notify.py          # SMTP email notification endpoint
└── static/
    ├── index.html             # Landing page
    ├── login.html             # Admin login page
    ├── dashboard.html         # Admin dashboard (all panels)
    ├── seeker-form.html       # Seeker registration form
    └── helper-form.html       # Helper registration form
```

---

## Running Locally

**Prerequisites:** Python 3.11, a PostgreSQL database (local or Neon free tier)

```bash
# Clone the repo
git clone https://github.com/YashAherr/waybuddy.git
cd waybuddy

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@host/dbname"
export SECRET_KEY="your-secret-key"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM="your@gmail.com"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="your-admin-password"

# Run the app
gunicorn --workers=2 --bind=0.0.0.0:5000 wsgi:flask_app
```

Open `http://localhost:5000` in your browser.

---

## Deployment

The app is deployed on **Render** with automatic deploys from the `main` branch. Every `git push` to `main` triggers a new deploy.

The database is hosted on **Neon** (free PostgreSQL). The connection string is passed via the `DATABASE_URL` environment variable set in the Render dashboard.

---

## Key Engineering Decisions

**No frontend framework** — The dashboard is an internal admin tool used by one operator. Vanilla JavaScript eliminates build tooling complexity and is easier to debug in production.

**Session auth over JWT** — For a single-admin tool, Flask sessions are simpler, more secure by default (httpOnly cookies), and require no client-side token management.

**Separate ID sets for matched seekers and helpers** — Seekers and helpers share integer IDs starting from 1. Using a single `matchedIds` Set caused false positives where seeker id=2 was incorrectly flagged as matched because helper id=2 was in the set. The fix was maintaining `matchedSeekerIds` and `matchedHelperIds` as separate Sets.

**Render over AWS EC2** — AWS EC2 + RDS projected to $97/month after the 12-month free tier expired. Render + Neon delivers the same functionality for $1.17/month. The tradeoff is a ~50 second cold start after 15 minutes of inactivity on the free tier.

---

## Deployment History

| Phase | What was built |
|---|---|
| Phase 0 | HTML prototypes — landing page, dashboard mockup, form buttons |
| Phase 1 | AWS infrastructure — VPC, EC2, RDS PostgreSQL, S3, security groups |
| Phase 2 | Flask REST API, Docker + Nginx on EC2, dashboard connected to live DB |
| Phase 3 | SMTP email notifications, helper approval flow, admin matching dashboard |
| Phase 4 | Domain (way-buddy.in), SSL via Let's Encrypt, Terraform IaC, CloudWatch |
| Migration | Moved from AWS ($97/mo projected) to Render + Neon ($1.17/mo) |

---

## What's Next

- [ ] **Razorpay payments** — Service fee collection with webhook-based verification
- [ ] **WhatsApp notifications** — Via Twilio or Meta Direct
- [ ] **Automated matching suggestions** — Score pairs by language overlap and flight proximity
- [ ] **Terraform** — Recreate entire AWS infrastructure with one command

---

## Author

Built by **Yash Aher**

[GitHub](https://github.com/YashAherr)
