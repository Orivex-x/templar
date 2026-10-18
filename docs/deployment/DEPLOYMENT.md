# Deployment Guide

## Table of Contents
- [Development to Production](#development-to-production)
- [Docker Deployment](#docker-deployment)
- [Templar + Nginx](#templar--nginx)
- [Cloud Platforms](#cloud-platforms)
- [Production Checklist](#production-checklist)

## Development to Production

### 1. Environment Configuration

Create a `.env` file for production settings:

```env
TEMPLAR_ENV=prod
TEMPLAR_HOST=0.0.0.0
TEMPLAR_PORT=8000
TEMPLAR_DEBUG=false
TEMPLAR_SECRET_KEY=your-very-secure-random-key-here
DATABASE_URL=postgresql://user:password@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

Update `templar.config.yml`:

```yaml
prod:
  mode: prod
  host: 0.0.0.0
  port: 8000
  debug: false
  deployment_domain: yourdomain.com
  session_secret: ${TEMPLAR_SECRET_KEY}
  db_engine: postgresql
  db_uri: ${DATABASE_URL}
  cache_backend: redis
  cache_redis_url: ${REDIS_URL}
  ssl_cert_path: /etc/ssl/certs/cert.pem
  ssl_key_path: /etc/ssl/private/key.pem
```

Templar resolves `${NAME}` placeholders for the selected environment from the
process environment, then that project's own `.env` file. `.env` values stay
within that `Config` instance and never mutate the process environment, so
multiple projects in one Python process cannot share dotenv secrets. Real
deployment secret stores should inject variables into the process instead.
Missing variables are startup errors, and
`templar config set` preserves placeholder expressions rather than writing
their resolved values into the configuration file.

`TEMPLAR_ENV`, `TEMPLAR_HOST`, `TEMPLAR_PORT`, and `TEMPLAR_DEBUG` override the
selected environment, host, port, and debug flag at runtime. `TEMPLAR_SESSION_SECRET`
is the preferred runtime secret override; `TEMPLAR_SECRET_KEY` remains a
supported alias and is used in the example above.

### 1a. HTTP boundary settings

`allowed_hosts` is enforced against the incoming `Host` header (include every
public hostname, or `*` only when another trusted layer performs validation).
`cors: true` enables public, non-credentialed CORS for GET, POST, HEAD, and
OPTIONS. `gzip: true` compresses responses for clients that send
`Accept-Encoding: gzip`; do not also compress the same proxied responses in
Nginx. `use_async_db` is unsupported because Templar's database API is
synchronous and is rejected at startup when set to `true`.

Server caches are namespaced from `project_root` by default. Set a stable,
unique `cache_namespace` when separate projects intentionally share a Redis
instance; this prevents one project's result-cache entries from being visible
to another.

### 2. Database Setup

Run migrations before deployment:

```bash
templar migrate run
```

Verify all tables are created:

```bash
python -c "from templar.db.Database import Database; db = Database(...); print(db.fetchall('SELECT name FROM sqlite_master WHERE type=\"table\"'))"
```

### 3. Static Files

Collect all static files:

```bash
mkdir -p static_dist
cp -r static/* static_dist/
```

Serve static files from Nginx (not from Templar app).

### 4. SSL Certificates

Obtain SSL certificates (Let's Encrypt recommended):

```bash
# Using Certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy to secure location
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /etc/ssl/certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/privkey.pem
```

---

## Docker Deployment

### Dockerfile

Before building, add a `.dockerignore` beside the Dockerfile. Docker applies
this file to `COPY . .`, keeping local secrets and mutable development state
out of the image context:

```dockerignore
.git/
.env
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
logs/
db/
*.db
templar_packages/
*.pem
*.key
*.crt
```

Pass `TEMPLAR_SECRET_KEY` and other secrets through the runtime environment or
your platform's secret manager. Do not copy `.env`, certificates, local
databases, marketplace registries, or virtual environments into an image.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run migrations
RUN templar migrate run

# Expose port
EXPOSE 8000

# Start server
CMD ["templar", "run", "--prod"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      TEMPLAR_ENV: prod
      TEMPLAR_SECRET_KEY: ${TEMPLAR_SECRET_KEY}
      DATABASE_URL: postgresql://templar:password@db:5432/templar
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: templar
      POSTGRES_PASSWORD: password
      POSTGRES_DB: templar
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static_dist:/usr/share/nginx/html/static:ro
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro

volumes:
  postgres_data:
  redis_data:
```

### Build and Deploy

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## Templar + Nginx

### 1. Choose TLS termination

Templar enables TLS itself when both `ssl_cert_path` and `ssl_key_path` are
configured; `templar run` then serves `https://`. Keep both paths empty only
when a reverse proxy terminates TLS. In that arrangement, set
`tls_terminated_by_proxy: true`, keep `session_cookie_secure: true`, bind
Templar to `localhost` or a loopback IP, and have the proxy forward the
original `Host` header. Production startup rejects ambiguous plaintext public
binds and insecure session cookies.

Templar is its own HTTP server and does not currently expose a WSGI/ASGI app,
so it must not be launched with Gunicorn.

### 2. Systemd Service

Create `/etc/systemd/system/templar.service`:

```ini
[Unit]
Description=Templar Web Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/templar
EnvironmentFile=/var/www/templar/.env
ExecStart=/var/www/templar/.venv/bin/templar run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start templar
sudo systemctl enable templar
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/templar`:

```nginx
upstream templar_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json;

    # Static files
    location /static/ {
        alias /var/www/templar/static_dist/;
        expires 30d;
    }

    # App
    location / {
        proxy_pass http://templar_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/templar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Cloud Platforms

### Heroku

Create `Procfile`:

```
web: templar run --prod
release: templar migrate run
```

Create `runtime.txt`:

```
python-3.11.0
```

Deploy:

```bash
heroku create myapp
git push heroku main
```

### AWS EC2

```bash
# SSH into instance
ssh -i key.pem ubuntu@instance-ip

# Install dependencies
sudo apt-get update && sudo apt-get install -y \
  python3.11 python3.11-venv python3.11-dev \
  postgresql postgresql-contrib redis-server nginx

# Clone repo and setup
git clone <repo> /opt/templar
cd /opt/templar
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure and start
# ... (follow Templar + Nginx setup above)
```

### DigitalOcean App Platform

Create `app.yaml`:

```yaml
name: templar-app
services:
- name: web
  github:
    repo: username/templar
    branch: main
  build_command: pip install -r requirements.txt && templar migrate run
  http_port: 8000
  envs:
  - key: TEMPLAR_ENV
    value: prod
  - key: DATABASE_URL
    scope: RUN_AND_BUILD_TIME
    value: ${db.connection_string}
databases:
- name: db
  engine: PG
  version: "15"
```

---

## Production Checklist

### Security
- [ ] Set `debug=false` in production config
- [ ] Use strong `session_secret` (32+ random characters)
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure CORS properly
- [ ] Enable CSRF protection
- [ ] Set secure cookie flags
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting
- [ ] Add security headers (see Nginx config)

### Performance
- [ ] Use production database (PostgreSQL/MySQL)
- [ ] Set up Redis for caching
- [ ] Enable Templar `gzip: true` or compression in the reverse proxy (not both)
- [ ] Set up CDN for static files
- [ ] Configure proper cache headers
- [ ] Run database migration and optimize indexes
- [ ] Monitor database query performance

### Monitoring & Logging
- [ ] Set up centralized logging (ELK, Datadog, etc.)
- [ ] Configure error tracking (Sentry, Rollbar)
- [ ] Set up uptime monitoring
- [ ] Configure alerts for errors/downtime
- [ ] Monitor application performance
- [ ] Track database performance

### Backup & Recovery
- [ ] Set up automated database backups
- [ ] Test backup restoration
- [ ] Document disaster recovery procedure
- [ ] Back up SSL certificates
- [ ] Back up configuration files

### Scaling
- [ ] Run multiple Templar processes behind a reverse proxy only with shared session storage
- [ ] Use load balancer for multiple servers
- [ ] Consider database replication
- [ ] Set up auto-scaling if cloud platform
- [ ] Monitor resource usage

### Maintenance
- [ ] Keep dependencies updated
- [ ] Monitor security advisories
- [ ] Plan database maintenance windows
- [ ] Document deployment procedures
- [ ] Test deployment in staging first
- [ ] Have rollback plan for deployments

### Domain & DNS
- [ ] Configure DNS records
- [ ] Set up automatic SSL renewal
- [ ] Configure email for domain
- [ ] Test SSL certificate validity
