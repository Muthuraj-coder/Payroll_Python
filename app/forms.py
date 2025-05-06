from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, DateField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
from datetime import date

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[DataRequired(), Length(min=2, max=64)])
    hourly_rate = FloatField('Hourly Rate ($)', validators=[
        DataRequired(),
        NumberRange(min=0, message="Hourly rate must be positive")
    ])
    submit = SubmitField('Add Employee')

class DailyWorkRecordForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    hours_worked = FloatField('Hours Worked', validators=[
        DataRequired(),
        NumberRange(min=0, max=24, message="Hours must be between 0 and 24")
    ])
    submit = SubmitField('Add Record')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')

    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError('Passwords must match.') 