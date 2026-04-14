import os

from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Bitte melden Sie sich an.'


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

    # Create tables, run migrations, and create default admin
    with app.app_context():
        db.create_all()
        _run_migrations()
        _create_default_admin()

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
