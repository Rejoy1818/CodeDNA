# Security Policy

## Supported Versions

The following versions of CodeDNA are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of CodeDNA seriously. If you discover a security vulnerability, please follow the process below.

### Reporting Process

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer at `security@codedna.local` with a detailed description of the issue.
3. Include steps to reproduce, affected versions, and any proposed remediation.
4. Allow up to 7 business days for an initial response.

### What to Include

- Summary of the vulnerability
- Affected component(s) and version(s)
- Steps to reproduce (with example payloads if applicable)
- Potential impact
- Suggested fix or workaround (optional)

## Security Measures Implemented

- **Secret management**: All secrets are loaded from environment variables via `.env` (never committed). See `.env.example`.
- **Authentication**: API key-based authentication with bcrypt password hashing for admin access.
- **Authorization**: Role-based access control (RBAC) protecting admin routes.
- **Security headers**: Flask-Talisman enforces HTTPS, HSTS, CSP, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy.
- **Rate limiting**: Flask-Limiter protects API endpoints from brute-force and abuse.
- **CORS**: Configured via `CORS_ORIGIN` to restrict cross-origin requests to trusted frontends only.
- **Input sanitization**: Form inputs are validated and sanitized to prevent XSS and injection attacks.
- **Debug mode**: `FLASK_DEBUG=false` in production; debug mode is disabled.
- **Dependency management**: Dependencies are pinned to secure versions; unused packages are removed.
- **Git hygiene**: `.env`, `*.pkl`, `models/`, `instance/`, `.flaskenv`, and `web.config` are ignored to prevent leaking secrets and artifacts.

## Secure Configuration

Copy `.env.example` to `.env` and set production-safe values:

```
SECRET_KEY=<strong-random-secret>
FLASK_ENV=production
FLASK_DEBUG=false
CORS_ORIGIN=https://your-frontend-domain.com
RATELIMIT_STORAGE_URL=redis://localhost:6379
```

Never commit `.env` to version control.

## Dependency Scanning

Run `bandit` to scan for common security issues:

```bash
pip install -r requirements-dev.txt
bandit -r backend/
```

## Disclosure Policy

Security reports are acknowledged within 7 business days. Maintainers will work with the reporter to validate, remediate, and disclose the issue in a coordinated manner. Public disclosure will be delayed until a fix is available or a reasonable remediation timeline has passed.
