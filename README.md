# eMail Signature Manager

Web-based tool for creating and managing email signatures across multiple tenants (companies). Employee data can be imported via CSV or managed manually. Signatures are generated in HTM, TXT, and RTF format and optionally deployed to an SMB network share.

---

## Features

- **Multi-tenant management** – Multiple companies with individual templates, short names, and SMB settings
- **Template editor** – HTML, TXT, and RTF templates with CodeMirror editor, live preview, and variable reference
- **Employee management** – CSV import (semicolon-delimited, UTF-8/CP1252/Latin-1), manual CRUD operations
- **Global employee overview** – Cross-tenant employee list with search
- **Signature generation** – Automatic creation of `.htm`, `.txt`, and `.rtf` per employee
- **HTML entity encoding** – Umlauts in HTM signatures are stored as HTML entities (e.g. `ä` → `&auml;`)
- **SMB deployment** – Deploy generated signatures directly to a network share (old folders are cleaned up automatically)
- **SMB connection test** – Built-in test button to verify SMB configuration
- **Bilingual UI** – English (default) and German, switchable via navbar
- **Login** – Admin credentials configurable via `docker-compose.yml`
- **Demo data** – Sample company and employee created on first run
- **Docker-ready** – Docker image via ghcr.io or self-build, configurable port

---

## Installation

### Docker with ghcr.io (recommended)

```yaml
# docker-compose.yml
version: '3.8'
services:
  signature-tool:
    image: ghcr.io/onlinecrash24/signatur-manager:latest
    container_name: signature-manager
    network_mode: host
    environment:
      - SECRET_KEY=change-me-to-a-secure-secret-key-12345
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=MySecurePassword123
      - DATABASE_URL=sqlite:////opt/signature-tool/data/signatures.db
      - DATA_DIR=/opt/signature-tool/data
      - GENERATED_DIR=/opt/signature-tool/data/generated
      - UPLOAD_FOLDER=/opt/signature-tool/data/uploads
      - LISTEN_PORT=5010
      - DEFAULT_LANG=en
    volumes:
      - signature-data:/opt/signature-tool/data
    restart: unless-stopped
volumes:
  signature-data:
```

```bash
docker compose up -d
```

The application is available at `http://<server-ip>:5010`.

> **Note:** `network_mode: host` is required so the container can reach SMB shares on the local network.

### Build Docker image locally

```bash
git clone https://github.com/onlinecrash24/signatur-manager.git
cd signatur-manager
docker compose up -d
```

### Local development

```bash
cd signatur-manager
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
python run.py
```

---

## First Start

| | |
|---|---|
| **URL** | `http://<server-ip>:5010` |
| **Username** | Value of `ADMIN_USER` (default: `admin`) |
| **Password** | Value of `ADMIN_PASSWORD` (default: `password`) |

Credentials are configured via environment variables in `docker-compose.yml`.

On first start, a demo company (**Demo Corp GmbH**) with one sample employee and signature templates is created automatically.

---

## File Structure

```
signatur-manager/
├── .github/workflows/
│   └── docker-publish.yml          # GitHub Actions: Auto-build → ghcr.io
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # Docker Compose configuration
├── entrypoint.sh                   # Gunicorn startup with configurable port
├── requirements.txt                # Python dependencies
├── run.py                          # Application entry point
│
├── app/
│   ├── __init__.py                 # Flask app factory, blueprints, DB migration
│   ├── config.py                   # Configuration (DB, paths, secret key)
│   ├── models.py                   # Database models (User, Tenant, Employee)
│   ├── auth.py                     # Login, logout, password change
│   ├── tenants.py                  # Tenant CRUD, template editor, SMB test
│   ├── signatures.py               # Employees, CSV import, generation, SMB deploy
│   ├── smb_utils.py                # SMB connection, test, upload, cleanup
│   ├── translations.py             # Bilingual i18n (EN/DE)
│   │
│   ├── static/
│   │   ├── css/style.css           # Additional styles
│   │   ├── js/editor.js            # CodeMirror, live preview
│   │   ├── sample.csv              # Sample CSV for download
│   │   └── img/                    # Logos
│   │
│   └── templates/                  # Jinja2 templates (login, dashboard, etc.)
│
└── data/                           # (created automatically, not in repo)
    ├── signatures.db               # SQLite database
    └── generated/                  # Generated signatures
```

---

## CSV Format

The CSV file must be **semicolon-delimited**. Supported encodings: UTF-8, UTF-8 with BOM, Windows-1252, Latin-1.

CSV files **with and without header rows** are detected automatically.

```csv
Vorname;Nachname;Titel;Durchwahl;E-Mail Adresse;Optionale Rufnummer;Abteilung
Max;Mustermann;Dr.;+49 40 12345-22;max.mustermann@firma.de;+49 177 12345678;IT
Erika;Musterfrau;;+49 40 12345-23;erika.musterfrau@firma.de;;Sales
```

| Column | Required | Description |
|---|---|---|
| Vorname | Yes | First name |
| Nachname | Yes | Last name |
| Titel | No | e.g. Dr., Dipl.-Ing., Prof. |
| Durchwahl | No | Direct dial number |
| E-Mail Adresse | Yes | Used as unique key for updates |
| Optionale Rufnummer | No | e.g. mobile number |
| Abteilung | No | Department |

Existing employees are matched by email address and updated on re-import.

---

## Template Variables

### Employee Variables

| Variable | Description |
|---|---|
| `{{vorname}}` | First name |
| `{{nachname}}` | Last name |
| `{{titel}}` | Title (Dr., Dipl.-Ing., etc.) |
| `{{durchwahl}}` | Direct dial |
| `{{email}}` | Email address |
| `{{optionale_rufnummer}}` | Optional phone number |
| `{{abteilung}}` | Department |

### Company Variables (from tenant)

| Variable | Description |
|---|---|
| `{{firma}}` | Company name |
| `{{strasse}}` | Street |
| `{{plz}}` | ZIP code |
| `{{ort}}` | City |
| `{{telefon}}` | Phone (main line) |
| `{{fax}}` | Fax |
| `{{website}}` | Website |
| `{{logo_url}}` | Company logo URL |

### Conditional Blocks

```html
{% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}
```

---

## Signature Folder Structure (SMB / local)

Generated signatures are stored per employee in a dedicated folder. The folder name is composed of the **AD username** (part before `@` in the email address) and the **company short name**:

```
<ad-username>-<ShortName>/
├── <ad-username>-<ShortName>.htm
├── <ad-username>-<ShortName>.txt
└── <ad-username>-<ShortName>.rtf
```

**Example:** Email `j.bergmann@demo-corp.example`, short name `NWS` → folder and files: `j.bergmann-NWS.htm`, `.txt`, `.rtf`

- Umlauts in folder/file names are replaced automatically (ä→ae, ö→oe, ü→ue, ß→ss)
- Umlauts in HTM signatures are encoded as HTML entities (e.g. `ä` → `&auml;`)
- On deploy, **old folders on the SMB share are deleted** before uploading new ones

---

## SMB Deployment

Each tenant can be configured with an SMB network path:

- **SMB Path**: `\\server\share\signatures`
- **Username**: `DOMAIN\user`
- **Password**: SMB password

The built-in **connection test** verifies reachability and credentials directly in the browser.

> **Important:** Docker must run with `network_mode: host` so SMB shares on the LAN are reachable.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, Flask 3.0, Gunicorn |
| Database | SQLite (via Flask-SQLAlchemy) |
| Frontend | Bootstrap 5.3, Font Awesome 6 |
| Code Editor | CodeMirror 5 (Monokai Theme) |
| Auth | Flask-Login |
| SMB | smbprotocol / smbclient |
| i18n | Dict-based (EN/DE) |
| Container | Docker, GitHub Actions, ghcr.io |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask secret key (must be changed!) |
| `ADMIN_USER` | `admin` | Admin username |
| `ADMIN_PASSWORD` | `password` | Admin password |
| `DATABASE_URL` | `sqlite:///...signatures.db` | Database connection |
| `DATA_DIR` | `/opt/signature-tool/data` | Data directory |
| `GENERATED_DIR` | `/opt/signature-tool/data/generated` | Directory for generated signatures |
| `UPLOAD_FOLDER` | `/opt/signature-tool/data/uploads` | Upload directory |
| `LISTEN_PORT` | `5010` | Port the application listens on |
| `DEFAULT_LANG` | `en` | Default UI language (`en` or `de`) |

---

## Docker Commands

```bash
# Start with ghcr.io image
docker compose up -d

# Update image
docker compose pull && docker compose up -d

# Build locally (after changes)
docker compose build --no-cache && docker compose up -d

# View logs
docker logs -f signature-manager

# Stop container
docker compose down
```

---

## License

MIT License
