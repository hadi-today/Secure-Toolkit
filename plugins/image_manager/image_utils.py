import os
import uuid
from PIL import Image
from . import config

def create_thumbnail(image_path):
    try:
        img = Image.open(image_path)
        img.thumbnail(config.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        
        # Ensure thumbnail directory exists
        os.makedirs(config.THUMBNAIL_DIR, exist_ok=True)

        # Generate a unique filename for the thumbnail
        base, ext = os.path.splitext(os.path.basename(image_path))
        thumb_filename = f"{uuid.uuid4()}{ext}"
        thumb_path = os.path.join(config.THUMBNAIL_DIR, thumb_filename)
        
        img.save(thumb_path)
        return thumb_filename
    except Exception as e:
        print(f"Error creating thumbnail for {image_path}: {e}")
        return None
    
def process_and_save_image(source_path):
    """
    Processes an image file. If it's a .webp, converts it to .jpg.
    Otherwise, copies it directly. Returns the new filename and its full path.
    """
    try:
        base_name = uuid.uuid4()
        source_ext = os.path.splitext(source_path)[1].lower()

        # --- LOGIC FOR WEBP CONVERSION ---
        if source_ext == '.webp':
            new_filename = f"{base_name}.jpg"
            dest_path = os.path.join(config.ARCHIVE_DIR, new_filename)
            
            img = Image.open(source_path)
            # IMPORTANT: JPEG does not support transparency. Convert to RGB.
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            img.save(dest_path, 'jpeg', quality=95) # Save as high-quality JPEG
            return new_filename, dest_path
        
        # --- LOGIC FOR OTHER FORMATS ---
        else:
            new_filename = f"{base_name}{source_ext}"
            dest_path = os.path.join(config.ARCHIVE_DIR, new_filename)
            shutil.copy(source_path, dest_path)
            return new_filename, dest_path

    except Exception as e:
        print(f"Error processing image {source_path}: {e}")
        return None, None