from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


def default_html_template():
    return """<table cellpadding="0" cellspacing="0" border="0" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; color: #333333;">
  <tr>
    <td style="padding-right: 15px; border-right: 2px solid #0056b3; vertical-align: top;">
      {% if logo_url %}<img src="{{logo_url}}" alt="{{firma}}" style="max-width: 150px; max-height: 80px;" />{% endif %}
    </td>
    <td style="padding-left: 15px; vertical-align: top;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="font-size: 16px; font-weight: bold; color: #0056b3; padding-bottom: 2px;">
            {% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}
          </td>
        </tr>
        {% if abteilung %}
        <tr>
          <td style="font-size: 12px; color: #666666; padding-bottom: 8px;">
            {{abteilung}}
          </td>
        </tr>
        {% endif %}
        <tr>
          <td style="font-size: 14px; font-weight: bold; color: #333333; padding-bottom: 6px;">
            {{firma}}
          </td>
        </tr>
        <tr>
          <td style="font-size: 12px; color: #555555; line-height: 1.6;">
            {{strasse}}<br />
            {{plz}} {{ort}}<br />
            {% if telefon %}Tel: {{telefon}}{% endif %}{% if durchwahl %} | Durchwahl: {{durchwahl}}{% endif %}<br />
            {% if optionale_rufnummer %}Tel: {{optionale_rufnummer}}<br />{% endif %}
            {% if fax %}Fax: {{fax}}<br />{% endif %}
            E-Mail: <a href="mailto:{{email}}" style="color: #0056b3; text-decoration: none;">{{email}}</a><br />
            {% if website %}Web: <a href="{{website}}" style="color: #0056b3; text-decoration: none;">{{website}}</a>{% endif %}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


def default_txt_template():
    return """--
{% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}
{% if abteilung %}{{abteilung}}
{% endif %}
{{firma}}
{{strasse}}
{{plz}} {{ort}}

{% if telefon %}Tel:       {{telefon}}
{% endif %}{% if durchwahl %}Durchwahl: {{durchwahl}}
{% endif %}{% if optionale_rufnummer %}Tel:       {{optionale_rufnummer}}
{% endif %}{% if fax %}Fax:       {{fax}}
{% endif %}E-Mail:    {{email}}
{% if website %}Web:       {{website}}
{% endif %}"""


def default_rtf_template():
    return r"""{\rtf1\ansi\ansicpg1252\deff0
{\fonttbl{\f0\fswiss\fcharset0 Arial;}}
{\colortbl;\red0\green86\blue179;\red51\green51\blue51;\red102\green102\blue102;}
\viewkind4\uc1
\pard\f0\fs28\cf1\b {% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}\b0\fs20\cf2\par
{% if abteilung %}\cf3\fs20 {{abteilung}}\cf2\par
{% endif %}\par
\b {{firma}}\b0\par
{{strasse}}\par
{{plz}} {{ort}}\par
\par
{% if telefon %}Tel: {{telefon}}\par
{% endif %}{% if durchwahl %}Durchwahl: {{durchwahl}}\par
{% endif %}{% if optionale_rufnummer %}Tel: {{optionale_rufnummer}}\par
{% endif %}{% if fax %}Fax: {{fax}}\par
{% endif %}E-Mail: {{email}}\par
{% if website %}Web: {{website}}\par
{% endif %}}"""


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    must_change_password = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    short_name = db.Column(db.String(50), nullable=False, default='')
    street = db.Column(db.String(200), default='')
    zip_code = db.Column(db.String(10), default='')
    city = db.Column(db.String(100), default='')
    phone = db.Column(db.String(50), default='')
    fax = db.Column(db.String(50), default='')
    website = db.Column(db.String(200), default='')
    logo_url = db.Column(db.String(500), default='')
    smb_path = db.Column(db.String(500), default='')
    smb_username = db.Column(db.String(100), default='')
    smb_password = db.Column(db.String(200), default='')
    html_template = db.Column(db.Text, default=default_html_template)
    txt_template = db.Column(db.Text, default=default_txt_template)
    rtf_template = db.Column(db.Text, default=default_rtf_template)
    employees = db.relationship(
        'Employee', backref='tenant', lazy=True, cascade='all, delete-orphan'
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f'<Tenant {self.name}>'


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey('tenants.id'), nullable=False
    )
    vorname = db.Column(db.String(100), default='')
    nachname = db.Column(db.String(100), default='')
    titel = db.Column(db.String(100), default='')
    durchwahl = db.Column(db.String(100), default='')
    email = db.Column(db.String(200), default='')
    optionale_rufnummer = db.Column(db.String(100), default='')
    abteilung = db.Column(db.String(200), default='')
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f'<Employee {self.vorname} {self.nachname}>'

    def to_template_vars(self, tenant):
        """Return a dict of all template variables for this employee and tenant."""
        return {
            'vorname': self.vorname or '',
            'nachname': self.nachname or '',
            'titel': self.titel or '',
            'durchwahl': self.durchwahl or '',
            'email': self.email or '',
            'optionale_rufnummer': self.optionale_rufnummer or '',
            'abteilung': self.abteilung or '',
            'firma': tenant.name or '',
            'strasse': tenant.street or '',
            'plz': tenant.zip_code or '',
            'ort': tenant.city or '',
            'telefon': tenant.phone or '',
            'fax': tenant.fax or '',
            'website': tenant.website or '',
            'logo_url': tenant.logo_url or '',
        }
