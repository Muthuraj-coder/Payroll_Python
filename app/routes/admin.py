from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from app.database import execute_db, query_db, get_db
from werkzeug.security import generate_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

bp = Blueprint('admin', __name__)

@bp.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    try:
        # Get statistics
        employee_count = query_db("SELECT COUNT(*) FROM employees", one=True)[0]
        record_count = query_db("SELECT COUNT(*) FROM work_records", one=True)[0]
        today_records = query_db(
            "SELECT COUNT(*) FROM work_records WHERE date = ?",
            (date.today().isoformat(),),
            one=True
        )[0]
        total_payments = query_db(
            "SELECT COALESCE(SUM(amount_earned), 0) FROM work_records",
            one=True
        )[0]
        
        stats = {
            'employee_count': employee_count,
            'record_count': record_count,
            'today_records': today_records,
            'total_payments': total_payments
        }
        
        # Get recent records with employee names
        recent_records = query_db("""
            SELECT wr.*, e.name as employee_name
            FROM work_records wr
            JOIN employees e ON wr.employee_id = e.id
            ORDER BY wr.date DESC
            LIMIT 10
        """)
        
        # Get all employees
        employees = query_db("SELECT * FROM employees ORDER BY name")
        
        return render_template('admin/dashboard.html',
                             stats=stats,
                             recent_records=recent_records,
                             employees=employees)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/employees')
@login_required
def employees():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
        
    try:
        employees = query_db("SELECT * FROM employees ORDER BY name")
        return render_template('admin/employees.html', employees=employees)
    except Exception as e:
        flash(f'Error loading employees: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
        
    if request.method == 'POST':
        try:
            name = request.form['name']
            hourly_rate = float(request.form['hourly_rate'])
            
            if not name:
                flash('Employee name is required', 'error')
                return redirect(url_for('admin.add_employee'))
            
            if hourly_rate <= 0:
                flash('Hourly rate must be greater than 0', 'error')
                return redirect(url_for('admin.add_employee'))
            
            # Check if username already exists
            existing_user = query_db(
                "SELECT id FROM users WHERE username = ?",
                (name.lower(),),
                one=True
            )
            
            if existing_user:
                flash(f'An employee with username {name.lower()} already exists', 'error')
                return redirect(url_for('admin.add_employee'))
            
            # Create user account first
            default_password = "password123"  # Default password for all new employees
            hashed_password = generate_password_hash(default_password)
            
            db = get_db()
            cursor = db.cursor()
            
            try:
                # Start transaction
                cursor.execute("BEGIN")
                
                # Insert the user
                cursor.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                    (name.lower(), hashed_password, False)
                )
                user_id = cursor.lastrowid
                
                # Create the employee record
                cursor.execute(
                    "INSERT INTO employees (name, hourly_rate, user_id) VALUES (?, ?, ?)",
                    (name, hourly_rate, user_id)
                )
                employee_id = cursor.lastrowid
                
                # Update the user with the employee_id
                cursor.execute(
                    "UPDATE users SET employee_id = ? WHERE id = ?",
                    (employee_id, user_id)
                )
                
                # Commit transaction
                db.commit()
                
                flash(f'''Employee {name} added successfully! 
                      They can login with:
                      Username: {name.lower()}
                      Password: {default_password}''', 'success')
                return redirect(url_for('admin.employees'))
                
            except Exception as e:
                # Rollback transaction on error
                db.rollback()
                raise e
            
        except Exception as e:
            flash(f'Error adding employee: {str(e)}', 'error')
            return redirect(url_for('admin.add_employee'))
    
    return render_template('admin/add_employee.html')

@bp.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    try:
        employee = query_db(
            "SELECT * FROM employees WHERE id = ?",
            (id,),
            one=True
        )
        
        if not employee:
            flash('Employee not found', 'error')
            return redirect(url_for('admin.employees'))
        
        if request.method == 'POST':
            name = request.form['name']
            hourly_rate = float(request.form['hourly_rate'])
            
            if not name:
                flash('Employee name is required', 'error')
                return redirect(url_for('admin.edit_employee', id=id))
            
            if hourly_rate <= 0:
                flash('Hourly rate must be greater than 0', 'error')
                return redirect(url_for('admin.edit_employee', id=id))
            
            execute_db(
                "UPDATE employees SET name = ?, hourly_rate = ? WHERE id = ?",
                (name, hourly_rate, id)
            )
            
            flash('Employee updated successfully', 'success')
            return redirect(url_for('admin.employees'))
        
        return render_template('admin/edit_employee.html', employee=employee)
    except Exception as e:
        flash(f'Error editing employee: {str(e)}', 'error')
        return redirect(url_for('admin.employees'))

@bp.route('/delete_employee/<int:id>')
@login_required
def delete_employee(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
        
    try:
        # First get the employee to find their user_id
        employee = query_db(
            "SELECT e.*, u.is_admin FROM employees e JOIN users u ON e.user_id = u.id WHERE e.id = ?",
            (id,),
            one=True
        )
        
        if not employee:
            flash('Employee not found', 'error')
            return redirect(url_for('admin.employees'))
            
        # Prevent deletion of admin users
        if employee['is_admin']:
            flash('Cannot delete admin users', 'error')
            return redirect(url_for('admin.employees'))
            
        # Delete the user account first
        if employee['user_id']:
            execute_db("DELETE FROM users WHERE id = ?", (employee['user_id'],))
            
        # Delete work records for this employee
        execute_db("DELETE FROM work_records WHERE employee_id = ?", (id,))
            
        # Then delete the employee record
        execute_db("DELETE FROM employees WHERE id = ?", (id,))
        
        flash('Employee deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting employee: {str(e)}', 'error')
    return redirect(url_for('admin.employees'))

@bp.route('/admin/work_records')
@login_required
def work_records():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        records = query_db("""
            SELECT wr.*, e.name as employee_name
            FROM work_records wr
            JOIN employees e ON wr.employee_id = e.id
            ORDER BY wr.date DESC
        """)
        return render_template('admin/work_records.html', records=records)
    except Exception as e:
        flash(f'Error loading work records: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/admin/add_work_record', methods=['GET', 'POST'])
@login_required
def add_work_record():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            employee_id = int(request.form.get('employee_id'))
            date = request.form.get('date')
            hours_worked = float(request.form.get('hours_worked'))
            
            # Get employee's hourly rate
            employee = query_db(
                "SELECT hourly_rate FROM employees WHERE id = ?",
                (employee_id,),
                one=True
            )
            
            if not employee:
                flash('Employee not found.', 'danger')
                return redirect(url_for('admin.add_work_record'))
            
            amount_earned = hours_worked * employee['hourly_rate']
            
            # Insert work record
            execute_db(
                """INSERT INTO work_records 
                   (employee_id, date, hours_worked, amount_earned)
                   VALUES (?, ?, ?, ?)""",
                (employee_id, date, hours_worked, amount_earned)
            )
            
            flash('Work record added successfully!', 'success')
            return redirect(url_for('admin.work_records'))
            
        except ValueError:
            flash('Invalid input. Please check your values.', 'danger')
        except Exception as e:
            flash(f'Error adding work record: {str(e)}', 'danger')
    
    # Get employees for the form
    employees = query_db("SELECT id, name FROM employees ORDER BY name")
    return render_template('admin/add_work_record.html', employees=employees)

@bp.route('/edit_work_record/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_work_record(id):
    try:
        # Get the work record
        record = query_db(
            "SELECT * FROM work_records WHERE id = ?",
            (id,),
            one=True
        )
        
        if not record:
            flash('Work record not found', 'error')
            return redirect(url_for('admin.work_records'))
        
        if request.method == 'POST':
            try:
                date = request.form['date']
                hours_worked = float(request.form['hours_worked'])
                
                if not date:
                    flash('Date is required', 'error')
                    return redirect(url_for('admin.edit_work_record', id=id))
                
                if hours_worked <= 0:
                    flash('Hours worked must be greater than 0', 'error')
                    return redirect(url_for('admin.edit_work_record', id=id))
                
                # Get employee's hourly rate
                employee = query_db(
                    "SELECT hourly_rate FROM employees WHERE id = ?",
                    (record['employee_id'],),
                    one=True
                )
                
                if not employee:
                    flash('Employee not found', 'error')
                    return redirect(url_for('admin.edit_work_record', id=id))
                
                # Calculate new amount earned
                amount_earned = hours_worked * employee['hourly_rate']
                
                # Update the work record
                execute_db(
                    """UPDATE work_records 
                       SET date = ?, hours_worked = ?, amount_earned = ?
                       WHERE id = ?""",
                    (date, hours_worked, amount_earned, id)
                )
                
                flash('Work record updated successfully', 'success')
                return redirect(url_for('admin.work_records'))
                
            except ValueError:
                flash('Invalid input. Please check your values.', 'error')
                return redirect(url_for('admin.edit_work_record', id=id))
            except Exception as e:
                flash(f'Error updating work record: {str(e)}', 'error')
                return redirect(url_for('admin.edit_work_record', id=id))
        
        # Get employee name for display
        employee = query_db(
            "SELECT name FROM employees WHERE id = ?",
            (record['employee_id'],),
            one=True
        )
        
        if employee:
            record['employee_name'] = employee['name']
        
        return render_template('admin/edit_work_record.html', record=record)
        
    except Exception as e:
        flash(f'Error loading work record: {str(e)}', 'error')
        return redirect(url_for('admin.work_records'))

@bp.route('/delete_work_record/<int:id>')
@login_required
def delete_work_record(id):
    try:
        # Delete the work record
        execute_db("DELETE FROM work_records WHERE id = ?", (id,))
        flash('Work record deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting work record: {str(e)}', 'error')
    return redirect(url_for('admin.work_records'))

@bp.route('/admin/reports')
@login_required
def reports():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    try:
        # Get all employees for the dropdown
        employees = query_db("SELECT id, name FROM employees ORDER BY name")
        
        # Get recent reports
        recent_reports = query_db("""
            SELECT r.*, e.name as employee_name
            FROM reports r
            LEFT JOIN employees e ON r.employee_id = e.id
            ORDER BY r.date_created DESC
            LIMIT 10
        """)
        
        return render_template('admin/reports.html', 
                             employees=employees,
                             recent_reports=recent_reports)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))

@bp.route('/admin/generate_report', methods=['POST'])
@login_required
def generate_report():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    try:
        employee_id = request.form.get('employee_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        report_type = request.form.get('report_type')
        
        # Validate dates
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if end_date < start_date:
            flash('End date must be after start date', 'danger')
            return redirect(url_for('admin.reports'))
        
        # Build query based on report type
        if report_type == 'work_records':
            query = """
                SELECT wr.*, e.name as employee_name
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.date BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            
            if employee_id != 'all':
                query += " AND wr.employee_id = ?"
                params.append(employee_id)
            
            query += " ORDER BY e.name, wr.date DESC"
            records = query_db(query, params)
            
            # Generate report content
            pdf_content = generate_work_records_pdf(records, start_date, end_date)
            
        elif report_type == 'earnings':
            query = """
                SELECT e.name as employee_name, 
                       SUM(wr.hours_worked) as total_hours,
                       SUM(wr.amount_earned) as total_earnings
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.date BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            
            if employee_id != 'all':
                query += " AND wr.employee_id = ?"
                params.append(employee_id)
            
            query += " GROUP BY e.id, e.name ORDER BY e.name"
            records = query_db(query, params)
            
            # Generate report content
            pdf_content = generate_earnings_pdf(records, start_date, end_date)
            
        else:  # detailed report
            query = """
                SELECT wr.*, e.name as employee_name, e.hourly_rate
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.date BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            
            if employee_id != 'all':
                query += " AND wr.employee_id = ?"
                params.append(employee_id)
            
            query += " ORDER BY e.name, wr.date DESC"
            records = query_db(query, params)
            
            # Generate report content
            pdf_content = generate_detailed_pdf(records, start_date, end_date)
        
        # Save report to database
        report_id = execute_db(
            """INSERT INTO reports 
               (employee_id, report_type, start_date, end_date, content)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id if employee_id != 'all' else None,
             report_type,
             start_date,
             end_date,
             pdf_content)
        )
        
        flash('Report generated successfully!', 'success')
        return redirect(url_for('admin.download_report', report_id=report_id))
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('admin.reports'))

@bp.route('/admin/download_report/<int:report_id>')
@login_required
def download_report(report_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    try:
        report = query_db(
            "SELECT * FROM reports WHERE id = ?",
            (report_id,),
            one=True
        )
        
        if not report:
            flash('Report not found', 'danger')
            return redirect(url_for('admin.reports'))
        
        # Create response with report content
        response = make_response(report['content'])
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_id}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', 'danger')
        return redirect(url_for('admin.reports'))

def generate_work_records_pdf(records, start_date, end_date):
    """Generate PDF content for work records report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Work Records Report', title_style))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Employee', 'Date', 'Hours Worked', 'Amount Earned']]
    for record in records:
        data.append([
            record['employee_name'],
            record['date'].strftime('%Y-%m-%d'),
            f"{record['hours_worked']:.2f}",
            f"${record['amount_earned']:.2f}"
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_earnings_pdf(records, start_date, end_date):
    """Generate PDF content for earnings report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Earnings Summary Report', title_style))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Employee', 'Total Hours', 'Total Earnings']]
    for record in records:
        data.append([
            record['employee_name'],
            f"{record['total_hours']:.2f}",
            f"${record['total_earnings']:.2f}"
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_detailed_pdf(records, start_date, end_date):
    """Generate PDF content for detailed report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Detailed Report', title_style))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Employee', 'Date', 'Hourly Rate', 'Hours Worked', 'Amount Earned']]
    for record in records:
        data.append([
            record['employee_name'],
            record['date'].strftime('%Y-%m-%d'),
            f"${record['hourly_rate']:.2f}",
            f"{record['hours_worked']:.2f}",
            f"${record['amount_earned']:.2f}"
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue() 