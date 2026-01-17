import csv
import io
import json
import markdown
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for, jsonify, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import or_

from .. import db
from ..forms import EntryForm, SettingsForm
from ..models import Entry
from ..ai_service import ai_service


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.get("/dashboard")
@login_required
def dashboard():
    q = (request.args.get("q") or "").strip()
    mood = (request.args.get("mood") or "").strip()
    category = (request.args.get("category") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    favorite = (request.args.get("favorite") or "").strip()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    query = Entry.query.filter_by(user_id=current_user.id)

    if q:
        query = query.filter(or_(Entry.title.ilike(f"%{q}%"), Entry.body.ilike(f"%{q}%")))

    if mood:
        query = query.filter(Entry.mood == mood)
    
    if category:
        query = query.filter(Entry.category == category)

    if tag:
        query = query.filter(Entry.tags.ilike(f"%{tag}%"))

    if favorite == "1":
        query = query.filter(Entry.is_favorite.is_(True))

    pagination = query.order_by(Entry.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "dashboard.html",
        entries=pagination.items,
        pagination=pagination,
        q=q,
        mood=mood,
        category=category,
        tag=tag,
        favorite=favorite,
        per_page=per_page,
    )


@main_bp.get("/entries/new")
@main_bp.post("/entries/new")
@login_required
def new_entry():
    form = EntryForm()
    suggestions = None
    sentiment_analysis = None
    
    if form.validate_on_submit():
        if form.get_suggestions.data:
            suggestions = ai_service.generate_entry_suggestions(
                mood=form.mood.data, 
                tags=form.tags.data,
                category=form.category.data
            )
            return render_template("entry_form.html", form=form, suggestions=suggestions)
        
        if form.analyze_sentiment.data and form.body.data:
            sentiment_analysis = ai_service.analyze_entry_sentiment(form.body.data)
            return render_template("entry_form.html", form=form, sentiment_analysis=sentiment_analysis)
        
        entry = Entry(
            title=form.title.data.strip(),
            body=form.body.data,
            mood=form.mood.data or None,
            category=form.category.data or None,
            tags=(form.tags.data or "").strip() or None,
            is_favorite=bool(form.is_favorite.data),
            user_id=current_user.id,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Entry saved.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("entry_form.html", form=form)


@main_bp.get("/entries/<int:entry_id>")
@login_required
def entry_detail(entry_id: int):
    entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        abort(404)
    return render_template("entry_detail.html", entry=entry)


@main_bp.get("/entries/<int:entry_id>/edit")
@main_bp.post("/entries/<int:entry_id>/edit")
@login_required
def edit_entry(entry_id: int):
    entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        abort(404)

    form = EntryForm(obj=entry)
    if request.method == "GET":
        form.mood.data = entry.mood or ""
        form.tags.data = entry.tags or ""
        form.is_favorite.data = bool(entry.is_favorite)

    if form.validate_on_submit():
        entry.title = form.title.data.strip()
        entry.body = form.body.data
        entry.mood = form.mood.data or None
        entry.tags = (form.tags.data or "").strip() or None
        entry.is_favorite = bool(form.is_favorite.data)
        entry.touch()
        db.session.commit()
        flash("Entry updated.", "success")
        return redirect(url_for("main.entry_detail", entry_id=entry.id))

    return render_template("entry_form.html", form=form, entry=entry)


@main_bp.post("/entries/<int:entry_id>/delete")
@login_required
def delete_entry(entry_id: int):
    entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        abort(404)
    db.session.delete(entry)
    db.session.commit()
    flash("Entry deleted.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.post("/entries/<int:entry_id>/favorite")
@login_required
def toggle_favorite(entry_id: int):
    entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        abort(404)
    entry.is_favorite = not bool(entry.is_favorite)
    entry.touch()
    db.session.commit()
    return redirect(request.referrer or url_for("main.dashboard"))


@main_bp.get("/wellness")
@login_required
def wellness():
    entries = (
        Entry.query.filter_by(user_id=current_user.id)
        .order_by(Entry.created_at.desc())
        .limit(10)
        .all()
    )
    
    if not entries:
        flash("Write some entries first to get wellness insights.", "info")
        return redirect(url_for("main.dashboard"))
    
    entries_text = [entry.body for entry in entries]
    insights = ai_service.generate_wellness_insights(entries_text)
    
    mood_counts = {}
    for entry in entries:
        if entry.mood:
            mood_counts[entry.mood] = mood_counts.get(entry.mood, 0) + 1
    
    return render_template("wellness.html", 
                         insights=insights, 
                         mood_counts=mood_counts,
                         recent_entries=entries[:5])


@main_bp.get("/export/<string:fmt>")
@login_required
def export_entries(fmt: str):
    entries = (
        Entry.query.filter_by(user_id=current_user.id)
        .order_by(Entry.created_at.desc())
        .all()
    )

    if fmt == "json":
        payload = [
            {
                "id": e.id,
                "title": e.title,
                "body": e.body,
                "mood": e.mood,
                "tags": e.tags,
                "is_favorite": bool(e.is_favorite),
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in entries
        ]
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        return Response(
            data,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=diary-export.json"},
        )

    if fmt == "txt":
        out = io.StringIO()
        for e in entries:
            out.write(f"{e.created_at:%Y-%m-%d %H:%M} - {e.title}\n")
            if e.mood:
                out.write(f"Mood: {e.mood}\n")
            if e.tags:
                out.write(f"Tags: {e.tags}\n")
            out.write(e.body)
            out.write("\n\n" + ("-" * 40) + "\n\n")
        return Response(
            out.getvalue(),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=diary-export.txt"},
        )

    if fmt == "csv":
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(["id", "title", "mood", "tags", "is_favorite", "created_at", "updated_at", "body"])
        for e in entries:
            writer.writerow(
                [
                    e.id,
                    e.title,
                    e.mood or "",
                    e.tags or "",
                    int(bool(e.is_favorite)),
                    e.created_at.isoformat(),
                    e.updated_at.isoformat() if e.updated_at else "",
                    e.body,
                ]
            )
        return Response(
            out.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=diary-export.csv"},
        )

    if fmt == "pdf":
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        for e in entries:
            title_style = styles['Heading1']
            story.append(Paragraph(e.title, title_style))
            story.append(Spacer(1, 12))
            
            meta_style = styles['Normal']
            meta_text = f"{e.created_at.strftime('%Y-%m-%d %H:%M')}"
            if e.mood:
                meta_text += f" | Mood: {e.mood.title()}"
            story.append(Paragraph(meta_text, meta_style))
            story.append(Spacer(1, 12))
            
            body_style = styles['BodyText']
            story.append(Paragraph(e.body.replace('\n', '<br/>'), body_style))
            story.append(Spacer(1, 20))
        
        doc.build(story)
        buffer.seek(0)
        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=diary-export.pdf"},
        )

    if fmt == "md":
        out = io.StringIO()
        out.write("# My Diary Export\n\n")
        for e in entries:
            out.write(f"## {e.title}\n\n")
            out.write(f"**Date:** {e.created_at.strftime('%Y-%m-%d %H:%M')}\n")
            if e.mood:
                out.write(f"**Mood:** {e.mood.title()}\n")
            if e.tags:
                out.write(f"**Tags:** {e.tags}\n")
            out.write(f"\n{e.body}\n\n---\n\n")
        return Response(
            out.getvalue(),
            mimetype="text/markdown",
            headers={"Content-Disposition": "attachment; filename=diary-export.md"},
        )

    abort(404)


@main_bp.get("/settings")
@main_bp.post("/settings")
@login_required
def settings():
    form = SettingsForm()
    if request.method == "GET":
        form.theme.data = getattr(current_user, "theme", "dark")

    if form.validate_on_submit():
        current_user.theme = form.theme.data
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))

    return render_template("settings.html", form=form)


@main_bp.get("/ads.txt")
def ads_txt():
    """Serve ads.txt file for AdSense verification"""
    return send_from_directory('static', 'ads.txt', mimetype='text/plain')
