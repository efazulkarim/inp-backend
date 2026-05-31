# Neon PostgreSQL Setup

Your project is configured for **Neon** (org: `org-old-mouse-87240142`, project: `dawn-brook-04644246`).

## 1. Get your connection string

### Option A: Neon Console (recommended)

1. Go to [console.neon.tech](https://console.neon.tech)
2. Select org **org-old-mouse-87240142** and project **dawn-brook-04644246**
3. Click **Connect** (or **Connection Details**)
4. Copy the connection string (use **Pooled connection** for serverless/Vercel)

### Option B: Neon CLI

```bash
# Install Neon CLI
npm i -g neonctl

# Authenticate (opens browser)
neonctl auth

# Get connection string for your project
neonctl connection-string --project-id dawn-brook-04644246 --pooled
```

## 2. Update your environment

Add to `app/.env` (or Vercel Environment Variables):

```
DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/DBNAME?sslmode=require&channel_binding=require
```

**For serverless (Vercel):** Use the **pooled** connection string (host contains `-pooler`).

## 3. Run migrations

```bash
# From project root
alembic upgrade head
```

Or for a fresh database:

```bash
python scripts/database/create_tables.py
alembic stamp head
```

## 4. Verify connection

```bash
python scripts/checks/check_db_connection.py
```
