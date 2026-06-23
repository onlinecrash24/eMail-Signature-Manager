import csv
import html
import html.entities
import io
import os
import shutil

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from jinja2 import Environment
from sqlalchemy import or_

from app import db
from app.models import Tenant, Employee
from app.smb_utils import upload_to_smb
from app.translations import t as translate

signatures_bp = Blueprint('signatures', __name__)


@signatures_bp.route('/all')
@login_required
def all_employees():
    """Global employee list across all tenants."""
    search = request.args.get('q', '').strip()

    query = (
        db.session.query(Employee)
        .join(Tenant, Employee.tenant_id == Tenant.id)
    )

    if search:
        like = f'%{search}%'
        query = query.filter(
            or_(
                Employee.vorname.ilike(like),
                Employee.nachname.ilike(like),
                Employee.email.ilike(like),
                Employee.abteilung.ilike(like),
                Employee.titel.ilike(like),
                Employee.durchwahl.ilike(like),
                Tenant.name.ilike(like),
            )
        )

    employee_list = query.order_by(Tenant.name, Employee.nachname, Employee.vorname).all()
    tenants = db.session.query(Tenant).order_by(Tenant.name).all()

    return render_template(
        'signatures/all_employees.html',
        employees=employee_list,
        tenants=tenants,
        search=search,
    )


def _render_template_string(template_text, variables):
    """Render a Jinja2 template string with the given variables."""
    env = Environment()
    try:
        tmpl = env.from_string(template_text)
        return tmpl.render(**variables)
    except Exception as e:
        return f'Template render error: {e}'


def _encode_html_entities(text):
    """Convert non-ASCII characters to HTML entities.

    e.g. ä → &auml;  ö → &ouml;  ü → &uuml;  ß → &szlig;
    Leaves HTML tags and ASCII characters untouched.
    """
    result = []
    for char in text:
        if ord(char) > 127:
            # Use named entity if available (e.g. &auml;), otherwise numeric (&#1234;)
            named = html.entities.codepoint2name.get(ord(char))
            if named:
                result.append(f'&{named};')
            else:
                result.append(f'&#{ord(char)};')
        else:
            result.append(char)
    return ''.join(result)


@signatures_bp.route('/<int:tenant_id>/employees')
@login_required
def employees(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash(translate('flash.tenant_not_found'), 'danger')
        return redirect(url_for('tenants.list_tenants'))

    employee_list = (
        db.session.query(Employee)
        .filter_by(tenant_id=tenant_id)
        .order_by(Employee.nachname, Employee.vorname)
        .all()
    )
    return render_template(
        'signatures/list.html',
        tenant=tenant,
        employees=employee_list,
    )


@signatures_bp.route('/<int:tenant_id>/import', methods=['GET', 'POST'])
@login_required
def import_csv(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash(translate('flash.tenant_not_found'), 'danger')
        return redirect(url_for('tenants.list_tenants'))

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash(translate('flash.no_file'), 'danger')
            return redirect(url_for('signatures.import_csv', tenant_id=tenant_id))

        file = request.files['csv_file']
        if file.filename == '':
            flash(translate('flash.no_file'), 'danger')
            return redirect(url_for('signatures.import_csv', tenant_id=tenant_id))

        if not file.filename.lower().endswith('.csv'):
            flash(translate('flash.only_csv'), 'danger')
            return redirect(url_for('signatures.import_csv', tenant_id=tenant_id))

        try:
            # Read file with encoding detection (UTF-8, UTF-8-BOM, Latin-1/Windows-1252)
            raw_data = file.read()
            for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
                try:
                    content = raw_data.decode(encoding)
                    break
                except (UnicodeDecodeError, ValueError):
                    continue
            else:
                content = raw_data.decode('latin-1')  # Latin-1 accepts all bytes

            # Default column order (used when CSV has no header)
            default_fields = [
                'Vorname', 'Nachname', 'Titel', 'Durchwahl',
                'E-Mail Adresse', 'Optionale Rufnummer', 'Abteilung',
            ]

            # Known header names
            known_headers = {
                'Vorname', 'vorname', 'Nachname', 'nachname', 'Titel', 'titel',
                'Durchwahl', 'durchwahl', 'E-Mail Adresse', 'E-Mail', 'email',
                'Email', 'Optionale Rufnummer', 'optionale_rufnummer',
                'Abteilung', 'abteilung',
            }

            # Detect if first line is a header or data
            lines = content.strip().splitlines()
            first_line_fields = [f.strip() for f in lines[0].split(';')] if lines else []
            has_header = any(f in known_headers for f in first_line_fields)

            if has_header:
                reader = csv.DictReader(io.StringIO(content), delimiter=';')
            else:
                # No header: use default column names
                reader = csv.DictReader(
                    io.StringIO(content), delimiter=';',
                    fieldnames=default_fields,
                )

            # Map CSV column names to model fields
            column_map = {
                'Vorname': 'vorname',
                'vorname': 'vorname',
                'Nachname': 'nachname',
                'nachname': 'nachname',
                'Titel': 'titel',
                'titel': 'titel',
                'Durchwahl': 'durchwahl',
                'durchwahl': 'durchwahl',
                'E-Mail Adresse': 'email',
                'E-Mail': 'email',
                'email': 'email',
                'Email': 'email',
                'Optionale Rufnummer': 'optionale_rufnummer',
                'optionale_rufnummer': 'optionale_rufnummer',
                'Abteilung': 'abteilung',
                'abteilung': 'abteilung',
            }

            imported_count = 0
            updated_count = 0

            for row in reader:
                # Build employee data from row
                emp_data = {}
                for csv_col, model_field in column_map.items():
                    if csv_col in row:
                        emp_data[model_field] = (row[csv_col] or '').strip()

                if not emp_data.get('email') and not emp_data.get('nachname'):
                    continue  # Skip empty rows

                email = emp_data.get('email', '')

                # Check for existing employee by email (update if exists)
                existing = None
                if email:
                    existing = (
                        db.session.query(Employee)
                        .filter_by(tenant_id=tenant_id, email=email)
                        .first()
                    )

                if existing:
                    existing.vorname = emp_data.get('vorname', existing.vorname)
                    existing.nachname = emp_data.get('nachname', existing.nachname)
                    existing.titel = emp_data.get('titel', existing.titel)
                    existing.durchwahl = emp_data.get('durchwahl', existing.durchwahl)
                    existing.email = emp_data.get('email', existing.email)
                    existing.optionale_rufnummer = emp_data.get(
                        'optionale_rufnummer', existing.optionale_rufnummer
                    )
                    existing.abteilung = emp_data.get('abteilung', existing.abteilung)
                    updated_count += 1
                else:
                    employee = Employee(
                        tenant_id=tenant_id,
                        vorname=emp_data.get('vorname', ''),
                        nachname=emp_data.get('nachname', ''),
                        titel=emp_data.get('titel', ''),
                        durchwahl=emp_data.get('durchwahl', ''),
                        email=emp_data.get('email', ''),
                        optionale_rufnummer=emp_data.get('optionale_rufnummer', ''),
                        abteilung=emp_data.get('abteilung', ''),
                    )
                    db.session.add(employee)
                    imported_count += 1

            db.session.commit()

            msg_parts = []
            if imported_count:
                msg_parts.append(translate('flash.imported', count=imported_count))
            if updated_count:
                msg_parts.append(translate('flash.updated', count=updated_count))
            if not msg_parts:
                msg_parts.append(translate('flash.no_records'))

            flash(', '.join(msg_parts) + '.', 'success')
            return redirect(url_for('signatures.employees', tenant_id=tenant_id))

        except Exception as e:
            db.session.rollback()
            flash(translate('flash.import_error', error=str(e)), 'danger')
            return redirect(url_for('signatures.import_csv', tenant_id=tenant_id))

    return render_template('signatures/import.html', tenant=tenant)


@signatures_bp.route('/<int:tenant_id>/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash(translate('flash.tenant_not_found'), 'danger')
        return redirect(url_for('tenants.list_tenants'))

    if request.method == 'POST':
        employee = Employee(
            tenant_id=tenant_id,
            vorname=request.form.get('vorname', '').strip(),
            nachname=request.form.get('nachname', '').strip(),
            titel=request.form.get('titel', '').strip(),
            durchwahl=request.form.get('durchwahl', '').strip(),
            email=request.form.get('email', '').strip(),
            optionale_rufnummer=request.form.get('optionale_rufnummer', '').strip(),
            abteilung=request.form.get('abteilung', '').strip(),
        )
        db.session.add(employee)
        db.session.commit()
        flash(translate('flash.employee_created', name=f'{employee.vorname} {employee.nachname}'), 'success')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    return render_template('signatures/employee_form.html', tenant=tenant, employee=None, action='add')


@signatures_bp.route('/<int:tenant_id>/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(tenant_id, employee_id):
    tenant = db.session.get(Tenant, tenant_id)
    employee = db.session.get(Employee, employee_id)
    if not tenant or not employee or employee.tenant_id != tenant_id:
        flash(translate('flash.not_found'), 'danger')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    if request.method == 'POST':
        employee.vorname = request.form.get('vorname', '').strip()
        employee.nachname = request.form.get('nachname', '').strip()
        employee.titel = request.form.get('titel', '').strip()
        employee.durchwahl = request.form.get('durchwahl', '').strip()
        employee.email = request.form.get('email', '').strip()
        employee.optionale_rufnummer = request.form.get('optionale_rufnummer', '').strip()
        employee.abteilung = request.form.get('abteilung', '').strip()
        db.session.commit()
        flash(translate('flash.employee_updated', name=f'{employee.vorname} {employee.nachname}'), 'success')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    return render_template('signatures/employee_form.html', tenant=tenant, employee=employee, action='edit')


@signatures_bp.route('/<int:tenant_id>/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
def delete_employee(tenant_id, employee_id):
    employee = db.session.get(Employee, employee_id)
    if not employee or employee.tenant_id != tenant_id:
        flash(translate('flash.employee_not_found'), 'danger')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    name = f'{employee.vorname} {employee.nachname}'
    db.session.delete(employee)
    db.session.commit()

    flash(translate('flash.employee_deleted', name=name), 'success')
    return redirect(url_for('signatures.employees', tenant_id=tenant_id))


@signatures_bp.route('/<int:tenant_id>/employees/<int:employee_id>/preview')
@login_required
def preview_employee(tenant_id, employee_id):
    tenant = db.session.get(Tenant, tenant_id)
    employee = db.session.get(Employee, employee_id)
    if not tenant or not employee or employee.tenant_id != tenant_id:
        flash(translate('flash.not_found'), 'danger')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    variables = employee.to_template_vars(tenant)

    html_rendered = _render_template_string(tenant.html_template or '', variables)
    txt_rendered = _render_template_string(tenant.txt_template or '', variables)
    rtf_rendered = _render_template_string(tenant.rtf_template or '', variables)

    return render_template(
        'signatures/preview.html',
        tenant=tenant,
        employee=employee,
        html_signature=html_rendered,
        txt_signature=txt_rendered,
        rtf_signature=rtf_rendered,
    )


@signatures_bp.route('/<int:tenant_id>/generate', methods=['POST'])
@login_required
def generate_signatures(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash(translate('flash.tenant_not_found'), 'danger')
        return redirect(url_for('tenants.list_tenants'))

    employee_list = db.session.query(Employee).filter_by(tenant_id=tenant_id).all()
    if not employee_list:
        flash(translate('flash.no_employees'), 'warning')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    generated_dir = current_app.config['GENERATED_DIR']
    tenant_dir = os.path.join(generated_dir, str(tenant_id))

    # Clean up old generated folders to avoid duplicates
    if os.path.exists(tenant_dir):
        shutil.rmtree(tenant_dir)

    count = 0
    for employee in employee_list:
        variables = employee.to_template_vars(tenant)

        # Folder name: AD-Username-Mandant (e.g. m.mustermann-EBV)
        # AD username = part before @ in email address
        email = (employee.email or '').strip()
        if '@' in email:
            ad_user = email.split('@')[0]
        else:
            ad_user = (employee.vorname[:1] + '.' + employee.nachname).strip().lower() if employee.nachname else 'unbekannt'
        mandant = (tenant.short_name or tenant.name or 'default').strip()
        folder_name = f'{ad_user}-{mandant}'
        # Replace German umlauts
        umlaut_map = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
                       'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'}
        for char, repl in umlaut_map.items():
            folder_name = folder_name.replace(char, repl)
        folder_name = ''.join(c for c in folder_name if c.isalnum() or c in ('_', '-', '.'))

        emp_dir = os.path.join(tenant_dir, folder_name)
        os.makedirs(emp_dir, exist_ok=True)

        # Generate HTML (with HTML entities for umlauts etc.)
        if tenant.html_template:
            html_content = _render_template_string(tenant.html_template, variables)
            html_content = _encode_html_entities(html_content)
            with open(os.path.join(emp_dir, f'{folder_name}.htm'), 'w', encoding='utf-8') as f:
                f.write(html_content)

        # Generate TXT — UTF-8 with BOM so Outlook Classic detects the encoding
        # and renders umlauts (ä, ö, ü, ß) correctly instead of treating the file as CP1252.
        if tenant.txt_template:
            txt_content = _render_template_string(tenant.txt_template, variables)
            with open(os.path.join(emp_dir, f'{folder_name}.txt'), 'w', encoding='utf-8-sig') as f:
                f.write(txt_content)

        # Generate RTF
        if tenant.rtf_template:
            rtf_content = _render_template_string(tenant.rtf_template, variables)
            with open(os.path.join(emp_dir, f'{folder_name}.rtf'), 'w', encoding='utf-8') as f:
                f.write(rtf_content)

        count += 1

    flash(translate('flash.signatures_generated', count=count), 'success')
    return redirect(url_for('signatures.employees', tenant_id=tenant_id))


@signatures_bp.route('/<int:tenant_id>/deploy', methods=['POST'])
@login_required
def deploy_signatures(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        flash(translate('flash.tenant_not_found'), 'danger')
        return redirect(url_for('tenants.list_tenants'))

    if not tenant.smb_path:
        flash(translate('flash.no_smb_path'), 'danger')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    generated_dir = current_app.config['GENERATED_DIR']
    tenant_dir = os.path.join(generated_dir, str(tenant_id))

    if not os.path.exists(tenant_dir):
        flash(translate('flash.no_generated'), 'warning')
        return redirect(url_for('signatures.employees', tenant_id=tenant_id))

    try:
        upload_to_smb(
            tenant.smb_path,
            tenant.smb_username,
            tenant.smb_password,
            tenant_dir,
        )
        flash(translate('flash.deploy_success'), 'success')
    except Exception as e:
        flash(translate('flash.deploy_error', error=str(e)), 'danger')

    return redirect(url_for('signatures.employees', tenant_id=tenant_id))
