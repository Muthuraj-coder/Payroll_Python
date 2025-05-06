from flask import Blueprint, render_template, flash, redirect, url_for, request, make_response
from flask_login import login_required, current_user
from app.models import DailyWorkRecord, Employee
from datetime import datetime, timedelta, date
from app.database import query_db, execute_db
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

bp = Blueprint('employee', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    try:
        # Get employee details
        employee = query_db(
            "SELECT * FROM employees WHERE id = ?",
            (current_user.employee_id,),
            one=True
        )
        if not employee:
            flash('Employee not found', 'error')
            return redirect(url_for('auth.login'))
            
        # Get employee's work records
        work_records = query_db("""
            SELECT * FROM work_records 
            WHERE employee_id = ? 
            ORDER BY date DESC
        """, (current_user.employee_id,))
        
        # Calculate statistics
        total_hours = sum(record['hours_worked'] for record in work_records)
        total_earnings = sum(record['amount_earned'] for record in work_records)
        
        # Calculate this month's earnings
        today = date.today()
        first_day = today.replace(day=1)
        month_earnings = sum(
            record['amount_earned'] for record in work_records 
            if isinstance(record['date'], date) and record['date'] >= first_day
        )
        
        # Get recent records (last 10)
        recent_records = work_records[:10]
        
        # Get recent reports
        recent_reports = query_db("""
            SELECT * FROM reports 
            WHERE employee_id = ? 
            ORDER BY date_created DESC
            LIMIT 10
        """, (current_user.employee_id,))
        
        stats = {
            'total_hours': total_hours,
            'total_earnings': total_earnings,
            'month_earnings': month_earnings,
            'hourly_rate': employee['hourly_rate']
        }
        
        return render_template('employee/dashboard.html', 
                             employee=employee,
                             stats=stats,
                             work_records=work_records,
                             recent_records=recent_records,
                             recent_reports=recent_reports)
    except Exception as e:
        flash('Error loading dashboard: ' + str(e), 'error')
        return redirect(url_for('auth.login'))

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('employee.dashboard'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('employee.dashboard'))
        
        # Get user from database
        user = query_db(
            "SELECT * FROM users WHERE id = ?",
            (current_user.id,),
            one=True
        )
        
        if user and check_password_hash(user['password'], current_password):
            # Update password
            hashed_password = generate_password_hash(new_password)
            query_db(
                "UPDATE users SET password = ? WHERE id = ?",
                (hashed_password, current_user.id),
                commit=True
            )
            flash('Your password has been updated!', 'success')
            return redirect(url_for('employee.dashboard'))
        
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    return redirect(url_for('employee.dashboard'))

@bp.route('/work_records')
@login_required
def work_records():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    try:
        # Get all work records for the current employee
        work_records = query_db("""
            SELECT * FROM work_records 
            WHERE employee_id = ? 
            ORDER BY date DESC
        """, (current_user.employee_id,))
        
        return render_template('employee/work_records.html', 
                             work_records=work_records)
    except Exception as e:
        flash('Error loading work records: ' + str(e), 'error')
        return redirect(url_for('employee.dashboard'))

@bp.route('/profile')
@login_required
def profile():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    try:
        # Get employee details
        employee = query_db(
            "SELECT * FROM employees WHERE id = ?",
            (current_user.employee_id,),
            one=True
        )
        if not employee:
            flash('Employee not found', 'error')
            return redirect(url_for('employee.dashboard'))
            
        return render_template('employee/profile.html', employee=employee)
    except Exception as e:
        flash('Error loading profile: ' + str(e), 'error')
        return redirect(url_for('employee.dashboard'))

@bp.route('/reports')
@login_required
def reports():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Get recent reports for the current employee
        recent_reports = query_db("""
            SELECT * FROM reports 
            WHERE employee_id = ? 
            ORDER BY date_created DESC
            LIMIT 10
        """, (current_user.employee_id,))
        
        return render_template('employee/reports.html', 
                             recent_reports=recent_reports)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return redirect(url_for('employee.dashboard'))

@bp.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        report_type = request.form.get('report_type')
        
        # Validate dates
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if end_date < start_date:
            flash('End date must be after start date', 'danger')
            return redirect(url_for('employee.dashboard'))
        
        # Build query based on report type
        if report_type == 'work_records':
            query = """
                SELECT wr.*, e.name as employee_name
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.employee_id = ? AND wr.date BETWEEN ? AND ?
                ORDER BY wr.date DESC
            """
            records = query_db(query, (current_user.employee_id, start_date, end_date))
            pdf_content = generate_work_records_pdf(records, start_date, end_date)
            
        elif report_type == 'earnings':
            query = """
                SELECT e.name as employee_name, 
                       SUM(wr.hours_worked) as total_hours,
                       SUM(wr.amount_earned) as total_earnings
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.employee_id = ? AND wr.date BETWEEN ? AND ?
                GROUP BY e.id, e.name
            """
            records = query_db(query, (current_user.employee_id, start_date, end_date))
            pdf_content = generate_earnings_pdf(records, start_date, end_date)
            
        else:  # detailed report
            query = """
                SELECT wr.*, e.name as employee_name, e.hourly_rate
                FROM work_records wr
                JOIN employees e ON wr.employee_id = e.id
                WHERE wr.employee_id = ? AND wr.date BETWEEN ? AND ?
                ORDER BY wr.date DESC
            """
            records = query_db(query, (current_user.employee_id, start_date, end_date))
            pdf_content = generate_detailed_pdf(records, start_date, end_date)
        
        # Save report to database
        report_id = execute_db(
            """INSERT INTO reports 
               (employee_id, report_type, start_date, end_date, content)
               VALUES (?, ?, ?, ?, ?)""",
            (current_user.employee_id,
             report_type,
             start_date,
             end_date,
             pdf_content)
        )
        
        flash('Report generated successfully!', 'success')
        return redirect(url_for('employee.download_report', report_id=report_id))
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('employee.dashboard'))

@bp.route('/download_report/<int:report_id>')
@login_required
def download_report(report_id):
    if current_user.is_admin:
        flash('Access denied. This is an employee-only page.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        report = query_db(
            "SELECT * FROM reports WHERE id = ? AND employee_id = ?",
            (report_id, current_user.employee_id),
            one=True
        )
        
        if not report:
            flash('Report not found', 'danger')
            return redirect(url_for('employee.dashboard'))
        
        # Create response with report content
        response = make_response(report['content'])
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_id}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', 'danger')
        return redirect(url_for('employee.dashboard'))

def generate_work_records_pdf(records, start_date, end_date):
    """Generate PDF content for work records report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title and Employee Info
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Work Records Report', title_style))
    if records:
        elements.append(Paragraph(f'Employee: {records[0]["employee_name"]}', styles['Normal']))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Date', 'Hours Worked', 'Amount Earned']]
    for record in records:
        data.append([
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
    
    # Title and Employee Info
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Earnings Summary Report', title_style))
    if records:
        elements.append(Paragraph(f'Employee: {records[0]["employee_name"]}', styles['Normal']))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Total Hours', 'Total Earnings']]
    for record in records:
        data.append([
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
    
    # Title and Employee Info
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    elements.append(Paragraph('Detailed Report', title_style))
    if records:
        elements.append(Paragraph(f'Employee: {records[0]["employee_name"]}', styles['Normal']))
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['Date', 'Hourly Rate', 'Hours Worked', 'Amount Earned']]
    for record in records:
        data.append([
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