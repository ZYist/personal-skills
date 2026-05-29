---
name: free-cf-temp-email
description: |
  Deploy a free temporary email system on Cloudflare using Workers, D1, Pages, and Email Routing. Use this skill when the user wants to set up a temp mail system, disposable email service, or Cloudflare-based email receiving platform. Covers the full workflow: free domain registration, DNS hosting, D1 database, Worker backend, Email Routing, Pages frontend, admin config, user registration, and send mail setup. Also covers DigitalPlat free domain (*.dpdns.org) setup.
---

# Free Cloudflare Temporary Email Deployment Guide

Deploy the [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) project on Cloudflare's free tier. The system provides temporary/disposable email addresses with a web UI, admin panel, user registration, and optional send-mail support.

Total cost: **$0** (using Cloudflare free tier + optional free domain from DigitalPlat).

## Step 0: Get a Free Domain (Optional)

If you don't already have a domain, you can get a free one from [DigitalPlat](https://www.digitalplat.org/). DigitalPlat provides free `*.dpdns.org` domains with full Cloudflare compatibility.

### 0.1 Register a DigitalPlat Account

Go to the DigitalPlat dashboard and create an account. Use a real email address for verification.

### 0.2 Register a Free Domain

In the DigitalPlat dashboard, search for an available domain name (e.g., `yourname.dpdns.org`) and register it. The domain is free and renewable.

### 0.3 Add Domain to Cloudflare

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) and log in (or create an account)
2. Click **Add a site** and enter your domain (e.g., `yourname.dpdns.org`)
3. Select the **Free** plan
4. Cloudflare will scan existing DNS records (may be empty for new domains — that's fine)

### 0.4 Update Nameservers

> **MANUAL ACTION REQUIRED** — Nameserver update cannot be done via CLI. You MUST use the DigitalPlat Dashboard.

Cloudflare will assign two nameservers, for example:

```
alice.ns.cloudflare.com
bob.ns.cloudflare.com
```

Steps:
1. Copy the two nameserver values from Cloudflare
2. Go to the **DigitalPlat dashboard** → your domain settings
3. Find the **Nameservers** section
4. **Delete** the existing nameservers
5. **Paste** the two Cloudflare nameservers
6. Click **Save**

DNS propagation usually takes a few minutes, but may take up to 24 hours. Cloudflare will automatically detect the change and mark your domain as **Active**.

> **CHECKPOINT**: Go back to Cloudflare Dashboard. The domain status should change to **Active**. Do NOT proceed until it's active.

### 0.5 Verify DNS Is Active

In Cloudflare Dashboard, confirm your domain status shows **Active**. Then go to **DNS → Records** to manage DNS records. Changes take effect within seconds.

> **Note**: DigitalPlat domains (`*.dpdns.org`) work seamlessly with Cloudflare Email Routing, Workers, and Pages — all required for this project.

## Prerequisites

- Node.js and npm installed
- A Cloudflare account with an **active** domain (see Step 0 if you don't have one)
- Proxy access to GitHub/npm if behind a firewall (common in China)

### Install tools

```powershell
npm install wrangler -g
npm install pnpm -g
```

### Clone the project

```powershell
git clone https://github.com/dreamhunter2333/cloudflare_temp_email.git
cd cloudflare_temp_email
```

## Step 1: Login to Cloudflare

```powershell
wrangler login
```

Opens browser for OAuth authorization. Approve access.

> **MANUAL FALLBACK** — If `wrangler login` fails (headless server, no browser):
> 1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **My Profile** → **API Tokens**
> 2. Click **Create Token** → use **Edit Cloudflare Workers** template
> 3. Set permissions: `Account > Cloudflare Workers > Edit`, `Account > D1 > Edit`, `Account > Workers KV Storage > Edit`, `Account > Cloudflare Pages > Edit`, `Zone > Email Routing > Edit`
> 4. Copy the token, then run:
>    ```powershell
>    $env:CLOUDFLARE_API_TOKEN = "your-token-here"
>    ```
> 5. All subsequent `wrangler` commands will use this token automatically.

## Step 2: Create D1 Database

```powershell
cd worker
Copy-Item wrangler.toml.template wrangler.toml
wrangler d1 create temp-email-db
```

Output gives you `database_id`. Save it — you'll need it for wrangler.toml.

> **CHECKPOINT**: Confirm `database_id` was returned successfully before proceeding.

> **MANUAL FALLBACK** — If `wrangler d1 create` fails:
> 1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **D1**
> 2. Click **Create database**
> 3. Name: `temp-email-db`, Location: **Automatic**
> 4. Click **Create**
> 5. Copy the **Database ID** from the database details page (right panel)
> 6. To run schema: in the database page → **Console** tab → paste the contents of `db/schema.sql` → click **Execute**

Run schema:

```powershell
wrangler d1 execute temp-email-db --file=../db/schema.sql --remote
```

> **CHECKPOINT**: Verify output shows "Executed N queries" with no errors.

## Step 3: Configure wrangler.toml

Edit `worker/wrangler.toml`. Replace ALL `YOUR_DOMAIN` and `<placeholder>` values:

```toml
name = "cloudflare_temp_email"
main = "src/worker.ts"
compatibility_date = "2025-04-01"
compatibility_flags = [ "nodejs_compat" ]
keep_vars = true

# Custom domain route for the Worker API
routes = [
    { pattern = "temp-email-api.YOUR_DOMAIN", custom_domain = true },
]

# Enable send_mail binding (for sending emails)
send_email = [
   { name = "SEND_MAIL" },
]

[vars]
DEFAULT_LANG = "zh"
PREFIX = "tmp"
DEFAULT_DOMAINS = ["YOUR_DOMAIN"]
DOMAINS = ["YOUR_DOMAIN"]
JWT_SECRET = "<run this to generate: python -c \"import secrets; print(secrets.token_hex(32))\">"
ADMIN_PASSWORDS = ["YOUR_ADMIN_PASSWORD"]
ENABLE_USER_CREATE_EMAIL = true
ENABLE_USER_DELETE_EMAIL = true
FRONTEND_URL = "https://mail.YOUR_DOMAIN"

[[d1_databases]]
binding = "DB"
database_name = "temp-email-db"
database_id = "<your-database-id>"
```

Replace `YOUR_DOMAIN` with your actual domain (e.g., `yujia.dpdns.org`).

## Step 4: Create KV Namespace (for user registration)

```powershell
wrangler kv namespace create KV
```

Output gives you `id`. Add to `wrangler.toml`:

> **MANUAL FALLBACK** — If `wrangler kv namespace create` fails:
> 1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **KV**
> 2. Click **Create a namespace**
> 3. Name: `KV`
> 4. Copy the **ID** from the namespace list
> 5. Add it to `wrangler.toml` manually

```toml
[[kv_namespaces]]
binding = "KV"
id = "<your-kv-id>"
```

## Step 5: Deploy Worker

```powershell
cd worker
pnpm install
pnpm run deploy
```

First deploy prompts for project name. Enter `production` for production branch.

> **CHECKPOINT**: Verify deploy output shows "Deployed cloudflare_temp_email triggers" with no errors.

> **MANUAL FALLBACK** — If `pnpm run deploy` fails repeatedly:
> 1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**
> 2. Click **Create application** → **Create Worker**
> 3. Name: `cloudflare_temp_email`, click **Deploy**
> 4. Go to the Worker → **Settings** → **Variables and Secrets**
> 5. Add all `[vars]` from your `wrangler.toml` as environment variables
> 6. Add D1 binding: **Settings** → **Bindings** → **Add** → **D1 Database** → select `temp-email-db`
> 7. Add KV binding: **Settings** → **Bindings** → **Add** → **KV Namespace** → select `KV`
> 8. Add Send Email binding: **Settings** → **Bindings** → **Add** → **Send Email**
> 9. For the code: use **Quick Edit** to paste the built `dist/worker.js`, or use `wrangler deploy --minify` with a valid token

Verify: visit `https://temp-email-api.YOUR_DOMAIN/health_check` — should return `OK`.

> **CHECKPOINT**: If health_check returns anything other than `OK`, do NOT proceed. Check wrangler.toml configuration.

## Step 6: Configure Email Routing

> **MANUAL ACTION REQUIRED** — Email Routing cannot be configured via CLI. You MUST use the Cloudflare Dashboard.

### 6.1 Enable Email Routing and verify DNS

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → select your domain
2. Left sidebar → **Email** → **Email Routing**
3. If you see "Get started with Email Routing" wizard:
   - **Custom address**: enter `admin`
   - **Domain**: should show `YOUR_DOMAIN`
   - **Action**: select `Send to an email`
   - **Destination**: enter your **real email address** (e.g., `you@gmail.com`)
   - Click **Create and continue**
4. Cloudflare will show **DNS records** that need to be configured
   - If records show a yellow warning, click **Add records and enable**
   - All records should show **green checkmarks**
5. Check your real email inbox — Cloudflare sends a confirmation email
6. Click the confirmation link to verify your destination address

### 6.2 Configure Catch-all rule (CRITICAL)

Without this step, emails will NOT reach the Worker.

1. In Email Routing → **Routing Rules** tab
2. Scroll down to find **Catch-all address**
3. Click **Edit** (or **Create action** if not exists)
4. **Action**: select `Send to a Worker`
5. **Worker**: select `cloudflare_temp_email`
6. Click **Save**
7. Confirm the rule shows status **Active**

> **CHECKPOINT**: Confirm Catch-all shows "Send to a Worker" and status is "Active". Without this, emails won't reach the Worker.

> **TROUBLESHOOTING** — If "Send to a Worker" option is missing:
> - Ensure the Worker is deployed first (Step 5)
> - Ensure the Worker has the `email` handler (this project has it by default)
> - Try refreshing the page after a few minutes

## Step 7: Build and Deploy Frontend

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env.prod
```

Edit `.env.prod`:

```
VITE_API_BASE=https://temp-email-api.YOUR_DOMAIN
```

Build and deploy:

```powershell
pnpm build --emptyOutDir
wrangler pages project create temp-email-frontend
wrangler pages deploy dist --project-name=temp-email-frontend --branch=production --commit-dirty=true
```

> **MANUAL FALLBACK** — If `wrangler pages deploy` fails:
> 1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**
> 2. Click **Create application** → **Pages** → **Upload assets**
> 3. Project name: `temp-email-frontend`
> 4. Upload the entire `frontend/dist/` folder
> 5. Set production branch to `production` and deploy
> 6. **Important**: In Pages project → **Settings** → **Functions** → **Advanced** → set "Not Found handling" to **Single-page application (SPA)**

## Step 8: Configure Custom Domain for Pages

> **MANUAL ACTION REQUIRED** — Custom domain for Pages cannot be configured via CLI. You MUST use the Cloudflare Dashboard.

### 8.1 Add custom domain in Pages project

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**
2. Click `temp-email-frontend` project
3. Click **Custom domains** tab
4. Click **Set up a custom domain**
5. Enter `mail.YOUR_DOMAIN` (or your preferred subdomain)
6. Click **Continue** → **Activate domain**
7. Wait 1-5 minutes for SSL certificate provisioning
8. Status should change from "Verifying" to "Active"

### 8.2 Add CNAME DNS record (if not auto-created)

Cloudflare usually auto-creates the DNS record. If not:

1. Go to your domain → **DNS** → **Records**
2. Click **Add record**
3. Set:
   - **Type**: `CNAME`
   - **Name**: `mail` (same as your Pages subdomain)
   - **Target**: `temp-email-frontend-<hash>.pages.dev` (from deploy output)
   - **Proxy status**: Proxied (orange cloud)
   - **TTL**: Auto
4. Click **Save**

> **CHECKPOINT**: Visit `https://mail.YOUR_DOMAIN` — should load the frontend UI. If you see 522 or SSL error, wait a few more minutes for certificate provisioning.

## Step 9: Enable User Registration

After Worker is deployed, enable user registration via admin API:

```powershell
# Enable user registration
curl -s -X POST -H "x-admin-auth: YOUR_ADMIN_PASSWORD" -H "Content-Type: application/json" -d '{"enable":true,"enableMailVerify":false,"maxAddressCount":10}' "https://temp-email-api.YOUR_DOMAIN/admin/user_settings"
```

## Verification Checklist

| Check | URL/Method |
|-------|-----------|
| Worker health | `https://temp-email-api.YOUR_DOMAIN/health_check` → OK |
| Frontend | `https://mail.YOUR_DOMAIN` → loads UI |
| Admin panel | `https://mail.YOUR_DOMAIN/admin` → login with admin password |
| Create email | POST `/api/new_address` → returns JWT + address |
| Receive email | Send to created address → check inbox via API |

## Troubleshooting

### Diagnostic Decision Tree

```
Problem: System not working
├─ Can't access frontend (mail.YOUR_DOMAIN)?
│  ├─ DNS not resolving → Check CNAME record in Cloudflare DNS
│  ├─ 522 error → Custom domain not configured in Pages project
│  └─ SSL error → Wait 1-5 min for certificate provisioning
├─ Can't access Worker API (/health_check)?
│  ├─ 404 → Worker not deployed, run `pnpm run deploy`
│  └─ 500 → Check wrangler.toml config (D1, JWT_SECRET, DOMAINS)
├─ Emails not received?
│  ├─ Catch-all not configured → Set up in Email Routing > Routing Rules
│  ├─ DNS records incomplete → Check Email Routing shows green checkmarks
│  └─ Worker error → Run `wrangler tail` to see live logs
└─ Can't create email address?
   ├─ 401 → JWT_SECRET mismatch, redeploy Worker
   └─ 403 → Check DOMAINS includes your domain
```

### Common Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pnpm install` stuck | Proxy/firewall blocking npm | Set proxy: `npm config set proxy http://127.0.0.1:PORT` |
| Build scripts ignored | pnpm v10 security | Add `"onlyBuiltDependencies": ["workerd", "esbuild"]` to package.json |
| `SEND_MAIL_DOMAINS` warning | Old wrangler field | Safe to ignore, functionality works |
| Email Routing grayed out | Domain not Active in CF | Wait for nameserver propagation |

### Proxy issues (China)
- Set npm/git proxy to your local proxy port:
  ```powershell
  npm config set proxy http://127.0.0.1:PORT
  npm config set https-proxy http://127.0.0.1:PORT
  git config --global http.proxy http://127.0.0.1:PORT
  git config --global https.proxy http://127.0.0.1:PORT
  ```

### pnpm build scripts ignored
- Add to `package.json` root level:
  ```json
  "onlyBuiltDependencies": ["workerd", "esbuild"]
  ```

## Optional Features

### Send email (Cloudflare binding)
Already configured with `send_email` binding. Users need send balance assigned in admin panel.

### Send email (Resend)
```powershell
cd worker
wrangler secret put RESEND_TOKEN
```

### Telegram Bot
```powershell
cd worker
wrangler secret put TELEGRAM_BOT_TOKEN
```

### Auto cleanup old emails
Uncomment in `wrangler.toml`:
```toml
[triggers]
crons = [ "0 0 * * *" ]
```

## Architecture

```
User Browser → mail.YOUR_DOMAIN (Pages) → temp-email-api.YOUR_DOMAIN (Worker)
                                              ↓
                                          D1 Database (emails, users)
                                          KV Namespace (sessions, settings)

Sender → Cloudflare Email Routing → Worker email handler → D1 Database

Domain Flow:
DigitalPlat (*.dpdns.org) → Cloudflare DNS → Email Routing + Workers + Pages
```

## Cost Breakdown

| Component | Free Tier Limit |
|-----------|----------------|
| Domain (DigitalPlat) | Free `*.dpdns.org` |
| Cloudflare DNS | Unlimited |
| Workers | 100k requests/day |
| D1 Database | 5GB storage, 25M reads/day |
| Pages | 500 builds/month |
| Email Routing | Unlimited received emails |
| KV Namespace | 100k reads/day, 1k writes/day |
| Send Email (Workers Paid) | 3,000/month free, then $0.35/1000 |

## Full Deployment Checklist

- [ ] DigitalPlat account registered (if using free domain)
- [ ] Domain added to Cloudflare and Active
- [ ] Nameservers updated in DigitalPlat (if using free domain)
- [ ] wrangler and pnpm installed
- [ ] wrangler logged in to Cloudflare
- [ ] D1 database created and schema applied
- [ ] wrangler.toml configured (domain, JWT, D1, KV bindings)
- [ ] KV namespace created
- [ ] Worker deployed and health check passes
- [ ] Email Routing Catch-all configured to Worker
- [ ] Frontend built and deployed to Pages
- [ ] Custom domain configured for Pages
- [ ] Admin password set
- [ ] User registration enabled (optional)
- [ ] Send email configured (optional)
