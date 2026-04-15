import os

from flask import Flask, redirect, url_for, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = ''


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Allow local development by adjusting paths when not in Docker
    if not os.path.exists('/opt/signature-tool/data'):
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'signatures.db')
        app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'uploads')
        app.config['DATA_DIR'] = data_dir
        app.config['GENERATED_DIR'] = os.path.join(data_dir, 'generated')

    # Ensure directories exist
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GENERATED_DIR'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.tenants import tenants_bp
    from app.signatures import signatures_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tenants_bp, url_prefix='/tenants')
    app.register_blueprint(signatures_bp, url_prefix='/signatures')

    # Translation context processor
    from app.translations import TRANSLATIONS

    @app.context_processor
    def inject_translation():
        lang = session.get('lang', app.config.get('DEFAULT_LANG', 'en'))
        strings = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
        fallback = TRANSLATIONS['en']

        def t(key, **kwargs):
            text = strings.get(key, fallback.get(key, key))
            if kwargs:
                text = text.format(**kwargs)
            return text

        return {'t': t, 'current_lang': lang}

    # Create tables, run migrations, create default admin and demo data
    # Use a file lock to prevent race conditions with multiple Gunicorn workers
    with app.app_context():
        _init_database(app)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        from app.models import Tenant, Employee
        tenant_count = db.session.query(Tenant).count()
        employee_count = db.session.query(Employee).count()
        tenants = db.session.query(Tenant).all()

        # Count generated signatures (each subfolder in GENERATED_DIR is a tenant,
        # each subfolder within that is an employee signature)
        generated_dir = app.config.get('GENERATED_DIR', '')
        signature_count = 0
        if os.path.isdir(generated_dir):
            for tenant_folder in os.listdir(generated_dir):
                tenant_path = os.path.join(generated_dir, tenant_folder)
                if os.path.isdir(tenant_path):
                    for emp_folder in os.listdir(tenant_path):
                        if os.path.isdir(os.path.join(tenant_path, emp_folder)):
                            signature_count += 1

        return render_template(
            'dashboard.html',
            tenant_count=tenant_count,
            employee_count=employee_count,
            signature_count=signature_count,
            tenants=tenants,
        )

    return app


def _init_database(app):
    """Initialize database with file lock to handle multiple Gunicorn workers."""
    lock_path = os.path.join(app.config['DATA_DIR'], '.db_init.lock')
    lock_file = open(lock_path, 'w')
    try:
        # fcntl is Unix-only; on Windows (dev) we skip locking
        import fcntl
        fcntl.flock(lock_file, fcntl.LOCK_EX)
    except ImportError:
        pass

    try:
        db.create_all()
        _run_migrations()
        _create_default_admin()
        _create_demo_data()
    finally:
        try:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        except ImportError:
            pass
        lock_file.close()


def _run_migrations():
    """Add missing columns to existing database tables."""
    import sqlalchemy

    with db.engine.connect() as conn:
        # Check if tenants.short_name exists
        result = conn.execute(sqlalchemy.text("PRAGMA table_info(tenants)"))
        columns = [row[1] for row in result]
        if 'short_name' not in columns:
            conn.execute(sqlalchemy.text(
                "ALTER TABLE tenants ADD COLUMN short_name VARCHAR(50) NOT NULL DEFAULT ''"
            ))
            conn.commit()


def _create_default_admin():
    from flask import current_app
    from app.models import User

    admin_user = os.environ.get('ADMIN_USER', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'password')

    existing = db.session.query(User).filter_by(username=admin_user).first()
    if existing:
        # Update password if environment changed
        if not existing.check_password(admin_pass):
            existing.set_password(admin_pass)
            existing.must_change_password = False
            db.session.commit()
    elif db.session.query(User).count() == 0:
        admin = User(
            username=admin_user,
            is_admin=True,
            must_change_password=False,
        )
        admin.set_password(admin_pass)
        db.session.add(admin)
        db.session.commit()


def _create_demo_data():
    """Create a demo tenant with one employee and sample templates on first run."""
    from app.models import Tenant, Employee

    # Only create demo data if no tenants exist yet
    if db.session.query(Tenant).count() > 0:
        return

    demo_html = r"""<table cellpadding="0" cellspacing="0" border="0" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; color: #333333;">
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
            {% if telefon %}Tel: {{telefon}}{% endif %}{% if durchwahl %} | Direct: {{durchwahl}}{% endif %}<br />
            {% if optionale_rufnummer %}Mobile: {{optionale_rufnummer}}<br />{% endif %}
            {% if fax %}Fax: {{fax}}<br />{% endif %}
            E-Mail: <a href="mailto:{{email}}" style="color: #0056b3; text-decoration: none;">{{email}}</a><br />
            {% if website %}Web: <a href="{{website}}" style="color: #0056b3; text-decoration: none;">{{website}}</a>{% endif %}
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td colspan="2" style="padding-top: 10px; font-size: 9px; color: #999999; line-height: 1.4;">
      {{firma}} | Managing Director: John Miller | Register Court: District Court Hamburg HRB 12345
    </td>
  </tr>
</table>"""

    demo_txt = """--
{% if titel %}{{titel}} {% endif %}{{vorname}} {{nachname}}
{% if abteilung %}{{abteilung}}
{% endif %}
{{firma}}
{{strasse}}
{{plz}} {{ort}}

{% if telefon %}Phone:    {{telefon}}
{% endif %}{% if durchwahl %}Direct:   {{durchwahl}}
{% endif %}{% if optionale_rufnummer %}Mobile:   {{optionale_rufnummer}}
{% endif %}{% if fax %}Fax:      {{fax}}
{% endif %}E-Mail:   {{email}}
{% if website %}Web:      {{website}}
{% endif %}"""

    demo_rtf = r"""{\rtf1\ansi\ansicpg1252\deff0
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
{% if telefon %}Phone: {{telefon}}\par
{% endif %}{% if durchwahl %}Direct: {{durchwahl}}\par
{% endif %}{% if optionale_rufnummer %}Mobile: {{optionale_rufnummer}}\par
{% endif %}{% if fax %}Fax: {{fax}}\par
{% endif %}E-Mail: {{email}}\par
{% if website %}Web: {{website}}\par
{% endif %}\par
\fs16\cf3 {{firma}} | Managing Director: John Miller | Register Court: District Court Hamburg HRB 12345\par
}"""

    tenant = Tenant(
        name='Northwind Solutions GmbH',
        short_name='NWS',
        street='Jungfernstieg 42',
        zip_code='20354',
        city='Hamburg',
        phone='+49 40 12345-0',
        fax='+49 40 12345-99',
        website='https://www.northwind-solutions.de',
        logo_url='https://via.placeholder.com/150x60?text=Northwind',
        html_template=demo_html,
        txt_template=demo_txt,
        rtf_template=demo_rtf,
    )
    db.session.add(tenant)
    db.session.flush()  # get tenant.id

    employee = Employee(
        tenant_id=tenant.id,
        vorname='Julia',
        nachname='Bergmann',
        titel='',
        durchwahl='+49 40 12345-67',
        email='j.bergmann@northwind-solutions.de',
        optionale_rufnummer='+49 177 12345678',
        abteilung='IT Department',
    )
    db.session.add(employee)
    db.session.commit()
