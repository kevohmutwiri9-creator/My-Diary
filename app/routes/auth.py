from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from .. import db
from ..forms import LoginForm, RegisterForm, PasswordResetRequestForm, PasswordResetForm
from ..models import User
from ..email_service import email_service


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/register")
@auth_bp.post("/register")
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered.", "error")
            return render_template("auth/register.html", form=form)

        user = User(email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.get("/login")
@auth_bp.post("/login")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.get("/reset-password")
@auth_bp.post("/reset-password")
def reset_password_request():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            if email_service.send_password_reset(email, token):
                flash("Password reset email sent. Check your inbox.", "success")
            else:
                flash("Failed to send reset email. Please try again later.", "error")
        else:
            flash("If that email exists, a reset link has been sent.", "info")
        
        return redirect(url_for("auth.login"))
    
    return render_template("auth/reset_password_request.html", form=form)


@auth_bp.get("/reset-password/confirm")
@auth_bp.post("/reset-password/confirm")
def reset_password_confirm():
    token = request.args.get("token")
    if not token:
        flash("Invalid reset link.", "error")
        return redirect(url_for("auth.login"))
    
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.verify_reset_token(token):
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.login"))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash("Passwords do not match.", "error")
            return render_template("auth/reset_password.html", form=form)
        
        user.set_password(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/reset_password.html", form=form)
