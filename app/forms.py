from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])


class EntryForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    body = TextAreaField("Body", validators=[DataRequired()])
    mood = SelectField(
        "Mood",
        choices=[
            ("", "--"),
            ("happy", "Happy"),
            ("sad", "Sad"),
            ("angry", "Angry"),
            ("anxious", "Anxious"),
            ("calm", "Calm"),
            ("excited", "Excited"),
            ("tired", "Tired"),
        ],
        default="",
    )
    category = SelectField(
        "Category",
        choices=[
            ("", "--"),
            ("personal", "Personal"),
            ("work", "Work"),
            ("family", "Family"),
            ("health", "Health"),
            ("travel", "Travel"),
            ("hobbies", "Hobbies"),
            ("goals", "Goals"),
            ("gratitude", "Gratitude"),
            ("reflection", "Reflection"),
            ("dreams", "Dreams"),
            ("other", "Other"),
        ],
        default="",
    )
    tags = StringField("Tags", validators=[Length(max=300)])
    is_favorite = BooleanField("Favorite")
    get_suggestions = SubmitField("Get AI Suggestions")
    analyze_sentiment = SubmitField("Analyze Sentiment")


class SettingsForm(FlaskForm):
    theme = SelectField(
        "Theme",
        choices=[("dark", "Dark"), ("light", "Light")],
        validators=[DataRequired()],
    )


class PasswordResetRequestForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])


class PasswordResetForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), Length(min=6, max=128)])
