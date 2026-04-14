# E-Mail Signatur Manager

Webbasiertes Tool zur Erstellung und Verwaltung von E-Mail-Signaturen für mehrere Mandanten (Firmen). Mitarbeiterdaten werden per CSV importiert oder manuell gepflegt, Signaturen in HTML, TXT und RTF generiert und optional auf einen SMB-Share deployt.

---

## Features

- **Mandantenverwaltung** – Mehrere Firmen mit eigenen Vorlagen und SMB-Einstellungen
- **Template-Editor** – HTML, TXT und RTF Vorlagen mit CodeMirror-Editor, Live-Vorschau und Variablen-Referenz
- **Mitarbeiterverwaltung** – CSV-Import (Semikolon-getrennt, UTF-8), manuelles Anlegen, Bearbeiten und Löschen
- **Globale Mitarbeiterübersicht** – Alle Mitarbeiter mandantenübergreifend mit Suchfunktion
- **Signatur-Generierung** – Automatische Erstellung von `signature.html`, `signature.txt` und `signature.rtf` pro Mitarbeiter
- **HTML-Entity-Kodierung** – Umlaute in HTML-Signaturen werden als HTML-Entities gespeichert (z.B. `ä` → `&auml;`) für maximale E-Mail-Client-Kompatibilität
- **SMB-Deployment** – Generierte Signaturen direkt auf einen Netzwerk-Share hochladen (alte Ordner werden automatisch bereinigt)
- **SMB-Verbindungstest** – Integrierter Test-Button zum Prüfen der SMB-Konfiguration
- **Login** – Admin-Zugangsdaten konfigurierbar über `docker-compose.yml` (kein erzwungener Passwortwechsel)
- **UTF-8 / Umlaute** – Vollständige Unterstützung von Sonderzeichen (ä, ö, ü, ß, etc.)
- **Docker-ready** – Dockerfile und docker-compose.yml inklusive, konfigurierbarer Port

---

## Dateistruktur

```
signature-tool/
├── Dockerfile                          # Docker-Image Definition
├── docker-compose.yml                  # Docker Compose Konfiguration
├── entrypoint.sh                       # Gunicorn-Start mit konfigurierbarem Port
├── requirements.txt                    # Python-Abhängigkeiten
├── run.py                              # Anwendungs-Einstiegspunkt
├── .dockerignore                       # Docker Build-Ausschlüsse
│
├── app/
│   ├── __init__.py                     # Flask App-Factory, Blueprints, Default-Admin
│   ├── config.py                       # Konfiguration (DB, Pfade, Secret Key)
│   ├── models.py                       # Datenbank-Modelle (User, Tenant, Employee)
│   ├── auth.py                         # Login, Logout, Passwortwechsel
│   ├── tenants.py                      # Mandanten-CRUD, Template-Editor, SMB-Test
│   ├── signatures.py                   # Mitarbeiter, CSV-Import, Generierung, SMB-Deploy
│   ├── smb_utils.py                    # SMB-Verbindung, Test, Upload, Bereinigung
│   ├── rtf_utils.py                    # HTML-zu-RTF Konvertierung
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css               # Ergänzende Styles (Bootstrap 5 Basis)
│   │   ├── js/
│   │   │   └── editor.js               # CodeMirror-Initialisierung, Live-Vorschau
│   │   └── img/
│   │       ├── logo.png                # Logo für den Login-Screen
│   │       └── logo_small.png          # Logo für die Navbar (oben links)
│   │
│   └── templates/
│       ├── base.html                   # Basis-Layout (Navbar mit Logo, Footer, Flash-Messages)
│       ├── login.html                  # Login-Seite mit großem Logo
│       ├── change_password.html        # Passwortwechsel
│       ├── dashboard.html              # Dashboard (Mandanten, Mitarbeiter, Signaturen-Zähler)
│       │
│       ├── tenants/
│       │   ├── list.html               # Mandanten-Übersicht
│       │   ├── form.html               # Mandant anlegen/bearbeiten (inkl. SMB-Test)
│       │   └── template_editor.html    # Vorlagen-Editor (HTML/TXT/RTF, col-4/col-8 Layout)
│       │
│       └── signatures/
│           ├── all_employees.html      # Globale Mitarbeiterübersicht
│           ├── list.html               # Mitarbeiter pro Mandant
│           ├── employee_form.html      # Mitarbeiter anlegen/bearbeiten
│           ├── import.html             # CSV-Import
│           └── preview.html            # Signatur-Vorschau
│
└── data/                               # (wird automatisch erstellt)
    ├── signatures.db                   # SQLite-Datenbank
    └── generated/                      # Generierte Signaturen
        └── <tenant_id>/
            └── <ad-username>-<Mandant>/
                ├── signature.html      # HTML-Signatur (mit HTML-Entities)
                ├── signature.txt       # Text-Signatur (UTF-8)
                └── signature.rtf       # RTF-Signatur
```

---

## Installation

### Docker (empfohlen)

```bash
git clone <repository-url>
cd signature-tool
```

**docker-compose.yml anpassen** (Zugangsdaten, Secret Key, Port):

```yaml
version: '3.8'
services:
  signature-tool:
    build: .
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

### Lokal (Entwicklung)

```bash
cd signature-tool
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

## CSV-Format

Die CSV-Datei muss **Semikolon-getrennt** und **UTF-8**-kodiert sein (UTF-8 mit BOM wird ebenfalls unterstützt):

```csv
Vorname;Nachname;Titel;Durchwahl;E-Mail Adresse;Optionale Rufnummer;Abteilung
Jürgen;Müller;Dr.;0441 12345 - 100;juergen.mueller@firma.de;0175 1234567;Geschäftsführung
Käthe;Schröder;;0441 12345 - 101;kaethe.schroeder@firma.de;;Buchhaltung
```

**Spalten:**

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

Folgende Platzhalter stehen in den Vorlagen (HTML, TXT, RTF) zur Verfügung:

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

Generierte Signaturen werden pro Mitarbeiter in einem Ordner abgelegt. Der Ordnername wird aus dem **AD-Benutzernamen** (Teil vor dem `@` der E-Mail-Adresse) und dem **Mandantennamen** gebildet:

```
<ad-username>-<Mandant>/
├── signature.html
├── signature.txt
└── signature.rtf
```

**Beispiel:** E-Mail `m.baeumer@eriksen.de`, Mandant `EBV` → Ordner `m.baeumer-EBV`

- Umlaute im Ordnernamen werden automatisch ersetzt (ä→ae, ö→oe, ü→ue, ß→ss)
- In der HTML-Signatur werden Umlaute als HTML-Entities kodiert (z.B. `ä` → `&auml;`)
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
| Container | Docker mit `network_mode: host` |

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
# Erstmalig bauen und starten
docker compose up -d

# Neu bauen nach Änderungen (Cache löschen)
docker compose build --no-cache && docker compose up -d

# Logs anzeigen
docker logs -f signature-manager

# SMB-Verbindung aus dem Container testen
docker exec -it signature-manager python -c "
from app.smb_utils import test_smb_connection
ok, msg = test_smb_connection(r'\\\\server\\share\\pfad', 'DOMAIN\\\\user', 'passwort')
print(msg)
"

# Container stoppen
docker compose down
```

---

## Lizenz

Internes Tool – nicht zur Weitergabe bestimmt.
