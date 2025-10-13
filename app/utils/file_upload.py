"""
File upload utilities for HomeServe Pro.
Handles image and document uploads with validation.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image


def allowed_file(filename, allowed_extensions=None):
    """
    Check if file extension is allowed.
    
    Args:
        filename (str): Filename to check
        allowed_extensions (set): Set of allowed extensions
        
    Returns:
        bool: True if extension is allowed
    """
    if allowed_extensions is None:
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_upload_file(file, subfolder='general'):
    """
    Save uploaded file to upload folder.
    
    Args:
        file: FileStorage object from request
        subfolder (str): Subfolder within upload directory
        
    Returns:
        str: Relative path to saved file or None if error
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Create subfolder if it doesn't exist
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_path, unique_filename)
    file.save(file_path)
    
    # Return relative path
    return os.path.join(subfolder, unique_filename)


def save_image(file, subfolder='images', max_size=(1920, 1920)):
    """
    Save and optimize image file.
    
    Args:
        file: FileStorage object from request
        subfolder (str): Subfolder within upload directory
        max_size (tuple): Maximum dimensions (width, height)
        
    Returns:
        str: Relative path to saved file or None if error
    """
    if not file or file.filename == '':
        return None
    
    # Check if file is an image
    allowed_image_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not allowed_file(file.filename, allowed_image_extensions):
        return None
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Create subfolder if it doesn't exist
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Save and optimize image
    file_path = os.path.join(upload_path, unique_filename)
    
    try:
        # Open and resize image
        img = Image.open(file)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert RGBA to RGB if saving as JPEG
        if ext in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Save optimized image
        img.save(file_path, optimize=True, quality=85)
        
        # Return relative path
        return os.path.join(subfolder, unique_filename)
    except Exception as e:
        print(f"Error saving image: {e}")
        return None


def delete_file(file_path):
    """
    Delete a file from the upload folder.
    
    Args:
        file_path (str): Relative path to file
        
    Returns:
        bool: True if deleted successfully
    """
    try:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


def get_file_url(file_path):
    """
    Get full URL for uploaded file.
    
    Args:
        file_path (str): Relative path to file
        
    Returns:
        str: Full URL to file
    """
    if not file_path:
        return None
    
    # In production, this would return CDN URL
    # For now, return relative path
    return f"/uploads/{file_path}"

