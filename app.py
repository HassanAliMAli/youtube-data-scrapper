import os
import json
import logging
import tempfile
import time
import glob
from datetime import datetime, timedelta
from urllib.parse import urlparse
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file

from main import app
from yt_scraper.api import YouTubeAPI
from yt_scraper.utils import validate_youtube_url, extract_channel_id
from yt_scraper.exporter import export_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure session storage directory exists
SESSION_FILE_DIR = 'session_data'
os.makedirs(SESSION_FILE_DIR, exist_ok=True)

# Session cleanup configuration
SESSION_MAX_AGE_HOURS = 24  # Files older than this will be deleted

def store_session_data(data, session_id=None):
    """Store large session data in a file instead of in the cookie."""
    if not session_id:
        # Generate a random ID if none provided
        session_id = os.urandom(16).hex()
    
    # Create a file path
    file_path = os.path.join(SESSION_FILE_DIR, f"{session_id}.json")
    
    try:
        # Write the data to the file
        with open(file_path, 'w') as f:
            json.dump(data, f)
        return session_id
    except Exception as e:
        logger.error(f"Error storing session data: {e}")
        return None

def get_session_data(session_id):
    """Retrieve session data from file."""
    file_path = os.path.join(SESSION_FILE_DIR, f"{session_id}.json")
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error retrieving session data: {e}")
        return None

def cleanup_old_sessions():
    """Clean up session files older than SESSION_MAX_AGE_HOURS"""
    try:
        # Get the current time
        now = time.time()
        # Maximum file age in seconds
        max_age = SESSION_MAX_AGE_HOURS * 3600
        # Counter for deleted files
        deleted_count = 0
        
        # Get all session files
        session_files = glob.glob(os.path.join(SESSION_FILE_DIR, "*.json"))
        
        for file_path in session_files:
            # Get file modification time
            file_mtime = os.path.getmtime(file_path)
            # Check if file is older than max age
            if now - file_mtime > max_age:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError as e:
                    logger.error(f"Error deleting old session file {file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old session files")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
        return 0


@app.route('/')
def index():
    """Homepage and search form"""
    # Run cleanup of old session files (non-blocking)
    try:
        # Run cleanup in background
        cleanup_old_sessions()
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
    
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """Process the scrape request"""
    # Run cleanup before creating new session data
    try:
        cleanup_old_sessions()
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
        
    channel_url = request.form.get('channel_url', '').strip()
    api_key = request.form.get('api_key', '').strip()
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    
    # Validate inputs
    if not channel_url or not api_key:
        flash('Please provide both a channel URL and your API key.', 'danger')
        return redirect(url_for('index'))
    
    # Validate YouTube URL
    if not validate_youtube_url(channel_url):
        flash('Please enter a valid YouTube channel or video URL.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Initialize the API client
        yt_api = YouTubeAPI(api_key)
        
        # Extract channel ID from URL
        channel_id = extract_channel_id(yt_api, channel_url)
        
        if not channel_id:
            flash('Could not extract a valid channel ID from the provided URL.', 'danger')
            return redirect(url_for('index'))
        
        # Get channel data
        channel_data = yt_api.get_channel_data(channel_id)
        
        if not channel_data:
            flash('Failed to retrieve channel data. Please check your API key and channel URL.', 'danger')
            return redirect(url_for('index'))
        
        # Get videos in date range
        videos_data = yt_api.get_videos_in_date_range(channel_id, start_date, end_date)
        
        # Store large data in file-based session
        session_data = {
            'channel_data': channel_data,
            'videos_data': videos_data
        }
        session_id = store_session_data(session_data)
        
        if not session_id:
            flash('Failed to store session data.', 'danger')
            return redirect(url_for('index'))
        
        # Store references in cookie session
        session['data_session_id'] = session_id
        session['start_date'] = start_date
        session['end_date'] = end_date
        
        # Instead of rendering here, redirect to the results route for page 1
        return redirect(url_for('results', page=1))
    
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))

# These routes were removed as the database functionality is no longer needed

@app.route('/export', methods=['POST'])
def export():
    """Export data to file"""
    if 'data_session_id' not in session:
        flash('No data available to export. Please perform a scrape first.', 'warning')
        return redirect(url_for('index'))
    
    # Get format
    export_format = request.form.get('export_format', 'csv')
    
    # Get data
    data = get_session_data(session['data_session_id'])
    if not data:
        flash('Session data has expired. Please perform a new scrape.', 'warning')
        return redirect(url_for('index'))
    
    try:
        # Export data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = export_data(data['channel_data'], data['videos_data'], export_format, timestamp)
        
        # Get filename
        channel_name = data['channel_data']['title'].replace(' ', '_')
        filename = f"{channel_name}_{timestamp}.{export_format}"
        if export_format == 'excel':
            filename = f"{channel_name}_{timestamp}.xlsx"
        
        # Send file
        return send_file(export_file, 
                        as_attachment=True, 
                        download_name=filename)
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        flash(f'Export failed: {str(e)}', 'danger')
        return redirect(url_for('results'))

@app.route('/results')
def results():
    """Show results from session data"""
    if 'data_session_id' not in session:
        flash('No data available. Please perform a scrape first.', 'warning')
        return redirect(url_for('index'))
    
    # Retrieve data from file storage
    data = get_session_data(session['data_session_id'])
    if not data:
        flash('Session data has expired. Please perform a new scrape.', 'warning')
        return redirect(url_for('index'))
    
    # Pagination logic
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'card') # Get view preference, default to 'card'
    videos_per_page = 12
    all_videos = data.get('videos_data', []) # Get all videos
    total_videos = len(all_videos)
    total_pages = (total_videos + videos_per_page - 1) // videos_per_page
    
    # Ensure page number is valid
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_index = (page - 1) * videos_per_page
    end_index = start_index + videos_per_page
    videos_to_display = all_videos[start_index:end_index] # Get slice for current page
    
    # Prepare display dates using the existing filter in the template
    start_date_display = session.get('start_date', '')
    end_date_display = session.get('end_date', '')
    
    # Prepare summary statistics (using all videos)
    summary = {
        'total_views': sum(video.get('view_count', 0) for video in all_videos),
        'total_likes': sum(video.get('like_count', 0) for video in all_videos),
        'total_comments': sum(video.get('comment_count', 0) for video in all_videos),
        'avg_engagement': sum(video.get('engagement_rate', 0) for video in all_videos) / total_videos if total_videos else 0
    }
    
    return render_template('results.html', 
                          channel=data['channel_data'], 
                          videos=videos_to_display, # Pass only the slice for display
                          summary=summary,
                          start_date=start_date_display,
                          end_date=end_date_display,
                          current_page=page,
                          total_pages=total_pages,
                          current_view=view) # Pass current view to template

@app.route('/progress')
def progress():
    """Get the current progress of the scraping process"""
    # Get progress from the API client
    progress_data = {"status": "Ready", "progress": 100}
    return jsonify(progress_data)

@app.route('/admin/cleanup_sessions')
def admin_cleanup_sessions():
    """Admin route to manually clean up old session files"""
    try:
        count = cleanup_old_sessions()
        return jsonify({
            "success": True,
            "message": f"Successfully cleaned up {count} old session files",
            "count": count
        })
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        return jsonify({
            "success": False,
            "message": f"Error during cleanup: {str(e)}"
        }), 500

# Template filters for formatting
@app.template_filter('format_number')
def format_number(value):
    """Format a number with commas as thousand separators."""
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value

@app.template_filter('format_date')
def format_date(value):
    """Format a date string or datetime object."""
    if not value:
        return ""
    
    if isinstance(value, str):
        try:
            if 'T' in value:
                # ISO format with time
                dt = datetime.strptime(value.split('T')[0], '%Y-%m-%d')
            else:
                # Just date
                dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%b %d, %Y')
        except ValueError:
            return value
    
    if isinstance(value, datetime):
        return value.strftime('%b %d, %Y')
    
    return value

@app.template_filter('format_duration')
def format_duration(iso_duration):
    """Format ISO 8601 duration to human-readable format."""
    if not iso_duration or not isinstance(iso_duration, str):
        return ""
    
    # Remove PT from the beginning
    duration = iso_duration.replace('PT', '')
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Extract hours
    if 'H' in duration:
        hours_part = duration.split('H')[0]
        hours = int(hours_part)
        duration = duration.split('H')[1]
    
    # Extract minutes
    if 'M' in duration:
        minutes_part = duration.split('M')[0]
        minutes = int(minutes_part)
        duration = duration.split('M')[1]
    
    # Extract seconds
    if 'S' in duration:
        seconds_part = duration.split('S')[0]
        seconds = int(seconds_part)
    
    # Format based on duration
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"
