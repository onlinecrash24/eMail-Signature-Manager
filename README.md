# E-Mail Signatur Manager

Webbasiertes Tool zur Erstellung und Verwaltung von E-Mail-Signaturen für mehrere Mandanten (Firmen). Mitarbeiterdaten werden per CSV importiert oder manuell gepflegt, Signaturen in HTM, TXT und RTF generiert und optional auf einen SMB-Share deployt.

---

## Features

- **Mandantenverwaltung** – Mehrere Firmen mit eigenen Vorlagen, Firmenkürzel und SMB-Einstellungen
- **Template-Editor** – HTML, TXT und RTF Vorlagen mit CodeMirror-Editor, Live-Vorschau und Variablen-Referenz
- **Mitarbeiterverwaltung** – CSV-Import (Semikolon-getrennt, UTF-8/CP1252/Latin-1), manuelles Anlegen, Bearbeiten und Löschen
- **Globale Mitarbeiterübersicht** – Alle Mitarbeiter mandantenübergreifend mit Suchfunktion
- **Signatur-Generierung** – Automatische Erstellung von `.htm`, `.txt` und `.rtf` pro Mitarbeiter
- **HTML-Entity-Kodierung** – Umlaute in HTM-Signaturen werden als HTML-Entities gespeichert (z.B. `ä` → `&auml;`)
- **SMB-Deployment** – Generierte Signaturen direkt auf einen Netzwerk-Share hochladen (alte Ordner werden automatisch bereinigt)
- **SMB-Verbindungstest** – Integrierter Test-Button zum Prüfen der SMB-Konfiguration
- **Login** – Admin-Zugangsdaten konfigurierbar über `docker-compose.yml` (kein erzwungener Passwortwechsel)
- **UTF-8 / Umlaute** – Vollständige Unterstützung von Sonderzeichen (ä, ö, ü, ß, etc.)
- **Docker-ready** – Docker Image via ghcr.io oder selbst bauen, konfigurierbarer Port

---

## Installation

### Docker mit ghcr.io (empfohlen)

```yaml
# docker-compose.yml
version: '3.8'
services:
  signature-tool:
    image: ghcr.io/onlinecrash24/signatur-manager:latest
    container_name: signature-manager
    network_mode: host
    environment:
      - SECRET_KEY=bitte-aendern-geheimer-schluessel-12345
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=MeinSicheresPasswort123
      - DATABASE_URL=sqlite:////opt/signature-tool/data/signatures.db
      - DATA_DIR=/opt/signature-tool/data
      - GENERATED_DIR=/opt/signature-tool/data/generated
      - UPLOAD_FOLDER=/opt/signature-tool/data/uploads
      - LISTEN_PORT=5010
    volumes:
      - signature-data:/opt/signature-tool/data
    restart: unless-stopped
volumes:
  signature-data:
```

```bash
docker compose up -d
```

Die Anwendung ist unter `http://<server-ip>:5010` erreichbar.

> **Hinweis:** `network_mode: host` wird benötigt, damit der Container SMB-Shares im LAN erreichen kann.

### Docker selbst bauen

```bash
git clone https://github.com/onlinecrash24/signatur-manager.git
cd signatur-manager
docker compose up -d
```

### Lokal (Entwicklung)

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

## Erster Start

| | |
|---|---|
| **URL** | `http://<server-ip>:5010` |
| **Benutzer** | Wert von `ADMIN_USER` (Standard: `admin`) |
| **Passwort** | Wert von `ADMIN_PASSWORD` (Standard: `password`) |

Die Zugangsdaten werden über die Umgebungsvariablen in der `docker-compose.yml` festgelegt. Ein erzwungener Passwortwechsel findet **nicht** statt.

---

## Dateistruktur

```
signatur-manager/
├── .github/workflows/
│   └── docker-publish.yml          # GitHub Actions: Auto-Build → ghcr.io
├── Dockerfile                      # Docker-Image Definition
├── docker-compose.yml              # Docker Compose Konfiguration
├── entrypoint.sh                   # Gunicorn-Start mit konfigurierbarem Port
├── requirements.txt                # Python-Abhängigkeiten
├── run.py                          # Anwendungs-Einstiegspunkt
│
├── app/
│   ├── __init__.py                 # Flask App-Factory, Blueprints, DB-Migration
│   ├── config.py                   # Konfiguration (DB, Pfade, Secret Key)
│   ├── models.py                   # Datenbank-Modelle (User, Tenant, Employee)
│   ├── auth.py                     # Login, Logout, Passwortwechsel
│   ├── tenants.py                  # Mandanten-CRUD, Template-Editor, SMB-Test
│   ├── signatures.py               # Mitarbeiter, CSV-Import, Generierung, SMB-Deploy
│   ├── smb_utils.py                # SMB-Verbindung, Test, Upload, Bereinigung
│   ├── rtf_utils.py                # HTML-zu-RTF Konvertierung
│   │
│   ├── static/
│   │   ├── css/style.css           # Ergänzende Styles
│   │   ├── js/editor.js            # CodeMirror, Live-Vorschau
│   │   ├── sample.csv              # Muster-CSV zum Download
│   │   └── img/                    # Logos
│   │
│   └── templates/                  # Jinja2-Templates (Login, Dashboard, etc.)
│
└── data/                           # (wird automatisch erstellt, nicht im Repo)
    ├── signatures.db               # SQLite-Datenbank
    └── generated/                  # Generierte Signaturen
```

---

## CSV-Format

Die CSV-Datei muss **Semikolon-getrennt** sein. Unterstützte Encodings: UTF-8, UTF-8 mit BOM, Windows-1252, Latin-1.

CSV-Dateien **mit und ohne Kopfzeile** werden automatisch erkannt.

```csv
Vorname;Nachname;Titel;Durchwahl;E-Mail Adresse;Optionale Rufnummer;Abteilung
Jürgen;Müller;Dr.;0441 12345 - 100;juergen.mueller@firma.de;0175 1234567;Geschäftsführung
Käthe;Schröder;;0441 12345 - 101;kaethe.schroeder@firma.de;;Buchhaltung
```

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| Vorname | Ja | Vorname des Mitarbeiters |
| Nachname | Ja | Nachname des Mitarbeiters |
| Titel | Nein | z.B. Dr., Dipl.-Ing., Prof. |
| Durchwahl | Nein | Telefon-Durchwahl |
| E-Mail Adresse | Ja | Wird als eindeutiger Schlüssel verwendet |
| Optionale Rufnummer | Nein | z.B. Mobilnummer, Zentrale |
| Abteilung | Nein | Abteilungsbezeichnung |

Beim Import werden bestehende Mitarbeiter anhand der E-Mail-Adresse erkannt und aktualisiert.

---

## Template-Variablen

### Mitarbeiter-Variablen

| Variable | Beschreibung |
|---|---|
| `{{vorname}}` | Vorname |
| `{{nachname}}` | Nachname |
| `{{titel}}` | Titel (Dr., Dipl.-Ing., etc.) |
| `{{durchwahl}}` | Telefon-Durchwahl |
| `{{email}}` | E-Mail-Adresse |
| `{{optionale_rufnummer}}` | Optionale Rufnummer |
| `{{abteilung}}` | Abteilung |

### Firmen-Variablen (aus Mandant)

| Variable | Beschreibung |
|---|---|
| `{{firma}}` | Firmenname |
| `{{strasse}}` | Straße |
| `{{plz}}` | Postleitzahl |
| `{{ort}}` | Ort |
| `{{telefon}}` | Telefon (Zentrale) |
| `{{fax}}` | Fax |
| `{{website}}` | Website |
| `{{logo_url}}` | URL zum Firmenlogo |

### Bedingte Blöcke

```html
{% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}
```

---

## Signatur-Ordnerstruktur (SMB / lokal)

Generierte Signaturen werden pro Mitarbeiter in einem Ordner abgelegt. Der Ordnername wird aus dem **AD-Benutzernamen** (Teil vor dem `@` der E-Mail-Adresse) und dem **Firmenkürzel** gebildet:

```
<ad-username>-<Firmenkürzel>/
├── <ad-username>-<Firmenkürzel>.htm
├── <ad-username>-<Firmenkürzel>.txt
└── <ad-username>-<Firmenkürzel>.rtf
```

**Beispiel:** E-Mail `m.baeumer@eriksen.de`, Firmenkürzel `EBV` → Ordner und Dateien: `m.baeumer-EBV.htm`, `.txt`, `.rtf`

- Umlaute im Ordner-/Dateinamen werden automatisch ersetzt (ä→ae, ö→oe, ü→ue, ß→ss)
- In der HTM-Signatur werden Umlaute als HTML-Entities kodiert (z.B. `ä` → `&auml;`)
- Beim Deploy werden **alte Ordner auf dem SMB-Share automatisch gelöscht** bevor die neuen hochgeladen werden

---

## SMB-Deployment

Pro Mandant kann ein SMB-Netzwerkpfad konfiguriert werden:

- **SMB-Pfad**: `\\server\share\signaturen`
- **Benutzername**: `DOMAIN\benutzer`
- **Passwort**: SMB-Passwort

Der integrierte **Verbindungstest** prüft die Erreichbarkeit und Zugangsdaten direkt im Browser.

> **Wichtig:** Docker muss mit `network_mode: host` laufen, damit SMB-Shares im LAN erreichbar sind.

---

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Backend | Python 3.12, Flask 3.0, Gunicorn |
| Datenbank | SQLite (via Flask-SQLAlchemy) |
| Frontend | Bootstrap 5.3, Font Awesome 6 |
| Code-Editor | CodeMirror 5 (Monokai Theme) |
| Auth | Flask-Login |
| SMB | smbprotocol / smbclient |
| Container | Docker, GitHub Actions, ghcr.io |

---

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask Secret Key (unbedingt ändern!) |
| `ADMIN_USER` | `admin` | Admin-Benutzername |
| `ADMIN_PASSWORD` | `password` | Admin-Passwort |
| `DATABASE_URL` | `sqlite:///...signatures.db` | Datenbank-Verbindung |
| `DATA_DIR` | `/opt/signature-tool/data` | Datenverzeichnis |
| `GENERATED_DIR` | `/opt/signature-tool/data/generated` | Verzeichnis für generierte Signaturen |
| `UPLOAD_FOLDER` | `/opt/signature-tool/data/uploads` | Upload-Verzeichnis |
| `LISTEN_PORT` | `5010` | Port, auf dem die Anwendung lauscht |

---

## Docker-Befehle

```bash
# Mit ghcr.io Image starten
docker compose up -d

# Image aktualisieren
docker compose pull && docker compose up -d

# Selbst bauen (nach Änderungen)
docker compose build --no-cache && docker compose up -d

# Logs anzeigen
docker logs -f signature-manager

# Container stoppen
docker compose down
```

---

## Lizenz

Internes Tool – nicht zur Weitergabe bestimmt.
