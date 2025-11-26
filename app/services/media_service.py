import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from app.models.media import Media

def allowed_file(filename):
    """Check if the file extension is allowed"""
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',  # Images
        'mp4', 'mov', 'webm',  # Videos
        'pdf', 'doc', 'docx', 'txt', 'md'  # Documents
    }
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type from extension"""
    image_ext = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    video_ext = {'mp4', 'mov', 'webm'}
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext in image_ext:
        return 'image'
    elif ext in video_ext:
        return 'video'
    return 'document'

def save_media(file, user_id, entry_id=None):
    """Save uploaded file and create media record"""
    if not file or file.filename == '':
        return None, 'No file selected'
    
    if not allowed_file(file.filename):
        return None, 'File type not allowed'
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(current_app.root_path, '..', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    try:
        # Save file
        file.save(filepath)
        filesize = os.path.getsize(filepath)
        
        # Create media record
        media = Media(
            user_id=user_id,
            entry_id=entry_id,
            filename=filename,
            filepath=filepath,
            filetype=get_file_type(file.filename),
            filesize=filesize
        )
        db.session.add(media)
        db.session.commit()
        
        return media, None
        
    except Exception as e:
        # Clean up file if there was an error
        if os.path.exists(filepath):
            os.remove(filepath)
        return None, str(e)

def delete_media(media_id, user_id):
    """Delete a media file and its record"""
    media = Media.query.filter_by(id=media_id, user_id=user_id).first()
    if not media:
        return False, 'Media not found'
    
    try:
        # Delete file
        if os.path.exists(media.filepath):
            os.remove(media.filepath)
        
        # Delete record
        db.session.delete(media)
        db.session.commit()
        return True, None
    except Exception as e:
        return False, str(e)

def get_user_media(user_id, entry_id=None):
    """Get all media for a user, optionally filtered by entry"""
    query = Media.query.filter_by(user_id=user_id)
    if entry_id is not None:
        query = query.filter_by(entry_id=entry_id)
    return query.order_by(Media.created_at.desc()).all()

def link_media_to_entry(media_ids, entry_id, user_id):
    """Link media files to an entry"""
    if not media_ids:
        return True, None
    
    try:
        media_list = Media.query.filter(
            Media.id.in_(media_ids),
            Media.user_id == user_id
        ).all()
        
        for media in media_list:
            media.entry_id = entry_id
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)
