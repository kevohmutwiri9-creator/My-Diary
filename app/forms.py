from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models.user import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=12, message='Password must be at least 12 characters long')
    ])
    password2 = PasswordField(
        'Repeat Password', 
        validators=[
            DataRequired(), 
            EqualTo('password', message='Passwords must match')
        ]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class EntryForm(FlaskForm):
    title = StringField('Title', validators=[Length(max=140)])
    content = TextAreaField('Content', validators=[DataRequired()])
    is_public = BooleanField('Make this entry public (visible on homepage)')
    submit = SubmitField('Save Entry')


class AdSettingsForm(FlaskForm):
    allow_ads = BooleanField('Show relevant ads in my dashboard')
    submit_ads = SubmitField('Save ad preferences')


class ReminderSettingsForm(FlaskForm):
    reminder_opt_in = BooleanField('Send gentle email reminders to write')
    reminder_frequency = SelectField(
        'Reminder frequency',
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
        default='weekly'
    )
    submit_reminders = SubmitField('Save reminder settings')

