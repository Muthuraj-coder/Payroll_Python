from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime
from app.database import query_db

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    if current_user.is_admin:
        try:
            # Get all employees
            employees = query_db("SELECT * FROM employees ORDER BY name")
            
            # Get all work records
            work_records = query_db("SELECT * FROM work_records ORDER BY date DESC")
            
            # Get today's records
            today = datetime.now().strftime('%Y-%m-%d')
            today_records = query_db(
                "SELECT * FROM work_records WHERE date = ?",
                (today,)
            )
            
            # Get recent records (last 5)
            recent_records = query_db(
                "SELECT * FROM work_records ORDER BY date DESC LIMIT 5"
            )
            
            # Calculate statistics
            stats = {
                'employee_count': len(employees),
                'record_count': len(work_records),
                'today_records': len(today_records),
                'total_payments': sum(record['amount_earned'] for record in work_records) if work_records else 0
            }
            
            return render_template('admin/dashboard.html',
                                 employees=employees,
                                 work_records=work_records,
                                 today_records=today_records,
                                 recent_records=recent_records,
                                 stats=stats)
        except Exception as e:
            return render_template('error.html', error=str(e))
    else:
        try:
            # Get employee's work records
            employee_id = current_user.employee_id
            work_records = query_db("""
                SELECT * FROM work_records
                WHERE employee_id = ?
                ORDER BY date DESC
            """, (employee_id,))
            
            # Calculate statistics
            total_hours = sum(record['hours_worked'] for record in work_records)
            total_earnings = sum(record['amount_earned'] for record in work_records)
            month_earnings = sum(
                record['amount_earned'] for record in work_records
                if record['date'].startswith(date.today().strftime('%Y-%m'))
            )
            
            stats = {
                'total_hours': total_hours,
                'total_earnings': total_earnings,
                'month_earnings': month_earnings
            }
            
            # Get recent records
            recent_records = work_records[:10]
            
            return render_template('employee/dashboard.html',
                                 stats=stats,
                                 recent_records=recent_records)
        except Exception as e:
            return render_template('error.html', error=str(e)) 