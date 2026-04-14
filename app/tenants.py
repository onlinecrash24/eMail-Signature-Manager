from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required

from app import db
from app.models import Tenant
from app.smb_utils import test_smb_connection

tenants_bp = Blueprint('tenants', __name__)


def _get_sample_data():
    """Return sample data for template preview."""
    return {
        'vorname': 'Max',
        'nachname': 'Mustermann',
        'titel': 'Dr.',
        'durchwahl': '0441 12345 - 422',
        'email': 'max.mustermann@example.de',
        'optionale_rufnummer': '0441 12345 - 400 (Zentrale)',
        'abteilung': 'Abteilungsleiter IT',
        'firma': 'Musterfirma GmbH',
        'strasse': 'Musterstraße 1',
        'plz': '26121',
        'ort': 'Oldenburg',
        'telefon': '0441 12345 - 0',
        'fax': '0441 12345 - 999',
        'website': 'https://www.musterfirma.de',
        'logo_url': 'https://via.placeholder.com/150x60?text=Logo',
    }


def _render_template_string(template_text, variables):
    """Render a template by replacing {{variable}} placeholders.

    Handles Jinja2-style {% if var %} blocks and {{var}} substitution.
    """
    from jinja2 import Environment

    env = Environment()
    try:
        tmpl = env.from_string(template_text)
        return tmpl.render(**variables)
    except Exception as e:
        return f'Fehler beim Rendern: {e}'


@tenants_bp.route('/')
@login_required
def list_tenants():
    tenants = db.session.query(Tenant).order_by(Tenant.name).all()
    return render_template('tenants/list.html', tenants=tenants)


@tenants_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_tenant():
    if request.method == 'POST':
        short_name = request.form.get('short_name', '').strip().replace(' ', '')
        tenant = Tenant(
            name=request.form.get('name', '').strip(),
            short_name=short_name,
            street=request.form.get('street', '').strip(),
            zip_code=request.form.get('zip_code', '').strip(),
            city=request.form.get('city', '').strip(),
            phone=request.form.get('phone', '').strip(),
            fax=request.form.get('fax', '').strip(),
            website=request.form.get('website', '').strip(),
            logo_url=request.form.get('logo_url', '').strip(),
            smb_path=request.form.get('smb_path', '').strip(),
            smb_username=request.form.get('smb_username', '').strip(),
            smb_password=request.form.get('smb_password', '').strip(),
        )

        if not tenant.name or not tenant.short_name:
            flash('Firmenname und Firmenkürzel sind erforderlich.', 'danger')
            return render_template('tenants/form.html', tenant=tenant, action='add')

        db.session.add(tenant)
        db.session.commit()
        flash(f'Mandant "{tenant.name}" wurde erstellt.', 'success')
        return redirect(url_for('tenants.list_tenants'))

    return render_template('tenants/form.html', tenant=Tenant(), action='add')


@tenants_bp.route('/<int:tenant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash('Mandant nicht gefunden.', 'danger')
        return redirect(url_for('tenants.list_tenants'))

    if request.method == 'POST':
        tenant.name = request.form.get('name', '').strip()
        tenant.short_name = request.form.get('short_name', '').strip().replace(' ', '')
        tenant.street = request.form.get('street', '').strip()
        tenant.zip_code = request.form.get('zip_code', '').strip()
        tenant.city = request.form.get('city', '').strip()
        tenant.phone = request.form.get('phone', '').strip()
        tenant.fax = request.form.get('fax', '').strip()
        tenant.website = request.form.get('website', '').strip()
        tenant.logo_url = request.form.get('logo_url', '').strip()
        tenant.smb_path = request.form.get('smb_path', '').strip()
        tenant.smb_username = request.form.get('smb_username', '').strip()
        smb_password = request.form.get('smb_password', '').strip()
        if smb_password:
            tenant.smb_password = smb_password

        if not tenant.name or not tenant.short_name:
            flash('Firmenname und Firmenkürzel sind erforderlich.', 'danger')
            return render_template('tenants/form.html', tenant=tenant, action='edit')

        db.session.commit()
        flash(f'Mandant "{tenant.name}" wurde aktualisiert.', 'success')
        return redirect(url_for('tenants.list_tenants'))

    return render_template('tenants/form.html', tenant=tenant, action='edit')


@tenants_bp.route('/<int:tenant_id>/delete', methods=['POST'])
@login_required
def delete_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash('Mandant nicht gefunden.', 'danger')
        return redirect(url_for('tenants.list_tenants'))

    name = tenant.name
    db.session.delete(tenant)
    db.session.commit()

    flash(f'Mandant "{name}" und alle Mitarbeiter wurden gelöscht.', 'success')
    return redirect(url_for('tenants.list_tenants'))


@tenants_bp.route('/<int:tenant_id>/templates', methods=['GET', 'POST'])
@login_required
def templates(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash('Mandant nicht gefunden.', 'danger')
        return redirect(url_for('tenants.list_tenants'))

    if request.method == 'POST':
        tenant.html_template = request.form.get('html_template', '')
        tenant.txt_template = request.form.get('txt_template', '')
        tenant.rtf_template = request.form.get('rtf_template', '')
        db.session.commit()
        flash('Vorlagen wurden gespeichert.', 'success')
        return redirect(url_for('tenants.templates', tenant_id=tenant_id))

    sample = _get_sample_data()
    html_preview = _render_template_string(tenant.html_template or '', sample)
    txt_preview = _render_template_string(tenant.txt_template or '', sample)
    rtf_preview = _render_template_string(tenant.rtf_template or '', sample)

    return render_template(
        'tenants/template_editor.html',
        tenant=tenant,
        html_preview=html_preview,
        txt_preview=txt_preview,
        rtf_preview=rtf_preview,
    )


@tenants_bp.route('/api/<int:tenant_id>/preview', methods=['POST'])
@login_required
def preview_template(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({'error': 'Mandant nicht gefunden'}), 404

    template_text = request.json.get('template', '')
    format_type = request.json.get('format', 'html')

    sample = _get_sample_data()
    # Override company data with actual tenant data
    sample['firma'] = tenant.name or sample['firma']
    sample['strasse'] = tenant.street or sample['strasse']
    sample['plz'] = tenant.zip_code or sample['plz']
    sample['ort'] = tenant.city or sample['ort']
    sample['telefon'] = tenant.phone or sample['telefon']
    sample['fax'] = tenant.fax or sample['fax']
    sample['website'] = tenant.website or sample['website']
    sample['logo_url'] = tenant.logo_url or sample['logo_url']

    rendered = _render_template_string(template_text, sample)

    return jsonify({
        'rendered': rendered,
        'format': format_type,
    })


@tenants_bp.route('/api/test-smb', methods=['POST'])
@login_required
def test_smb():
    """AJAX endpoint to test SMB connection."""
    data = request.get_json()
    smb_path = (data.get('smb_path') or '').strip()
    smb_username = (data.get('smb_username') or '').strip()
    smb_password = (data.get('smb_password') or '').strip()

    if not smb_path:
        return jsonify({'success': False, 'error': 'Kein SMB-Pfad angegeben.'})

    if not smb_username or not smb_password:
        return jsonify({'success': False, 'error': 'Benutzername und Passwort erforderlich.'})

    success, message = test_smb_connection(smb_path, smb_username, smb_password)
    return jsonify({'success': success, 'error': message if not success else None, 'message': message})
