"""File upload service for profile pictures and attachments."""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
PROFILE_PICTURE_SIZE = (300, 300)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def resize_profile_picture(file_path, output_path, size=PROFILE_PICTURE_SIZE):
    """Resize and crop profile picture to square format."""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize to cover the target size
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create new image with target size
            new_img = Image.new('RGB', size, (255, 255, 255))
            
            # Calculate position to center the image
            x = (size[0] - img.width) // 2
            y = (size[1] - img.height) // 2
            
            # Paste the resized image
            new_img.paste(img, (x, y))
            
            # Save the result
            new_img.save(output_path, 'JPEG', quality=85)
            return True
    except Exception as e:
        logger.error(f"Error resizing profile picture: {str(e)}")
        return False


def upload_profile_picture(file, user_id):
    """Upload and process profile picture for a user."""
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WebP"
    
    if file.content_length > MAX_FILE_SIZE:
        return None, "File too large. Maximum size is 5MB"
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{user_id}_{uuid.uuid4().hex}.jpg"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'profile_pictures')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save temporary file
        temp_path = os.path.join(upload_dir, f"temp_{unique_filename}")
        file.save(temp_path)
        
        # Resize and process the image
        output_path = os.path.join(upload_dir, unique_filename)
        if not resize_profile_picture(temp_path, output_path):
            os.remove(temp_path)
            return None, "Error processing image"
        
        # Remove temporary file
        os.remove(temp_path)
        
        return unique_filename, None
    except Exception as e:
        logger.error(f"Error uploading profile picture: {str(e)}")
        return None, "Error uploading file"


def delete_profile_picture(filename):
    """Delete a profile picture file."""
    try:
        if filename:
            file_path = os.path.join(current_app.static_folder, 'uploads', 'profile_pictures', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        return False
    except Exception as e:
        logger.error(f"Error deleting profile picture: {str(e)}")
        return False


def upload_attachment(file, entry_id):
    """Upload file attachment for an entry."""
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type"
    
    if file.content_length > MAX_FILE_SIZE:
        return None, "File too large. Maximum size is 5MB"
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{entry_id}_{uuid.uuid4().hex}_{filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'attachments')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        return unique_filename, None
    except Exception as e:
        logger.error(f"Error uploading attachment: {str(e)}")
        return None, "Error uploading file"
