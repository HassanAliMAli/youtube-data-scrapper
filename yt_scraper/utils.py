import re
import logging
import isodate
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def validate_youtube_url(url):
    """Validate if the provided URL is a valid YouTube URL."""
    if not url:
        return False
    
    # Check if it's a valid URL format
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc not in ['www.youtube.com', 'youtube.com', 'youtu.be']:
            return False
    except:
        return False
    
    # Check if it's a channel, user, or custom URL
    path = parsed_url.path
    if path.startswith('/channel/') or path.startswith('/user/') or path.startswith('/c/') or path.startswith('/@'):
        return True
    
    # Check if it's a valid video URL that we can extract channel from
    if '/watch' in path:
        return True
    
    # For shortened URLs
    if parsed_url.netloc == 'youtu.be':
        return True
    
    return False

def extract_channel_id(youtube_api, url):
    """Extract channel ID from various YouTube URL formats."""
    logger.debug(f"Attempting to extract channel ID from URL: {url}")
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Direct channel URL
        if path.startswith('/channel/'):
            channel_id = path.split('/channel/')[1].split('/')[0]
            logger.debug(f"Direct channel ID extracted: {channel_id}")
            return channel_id
        
        # Username URL
        elif path.startswith('/user/'):
            username = path.split('/user/')[1].split('/')[0]
            logger.debug(f"Username found: {username}, fetching channel ID...")
            return _get_channel_id_from_username(youtube_api, username)
        
        # Custom URL
        elif path.startswith('/c/'):
            custom_name = path.split('/c/')[1].split('/')[0]
            logger.debug(f"Custom URL found: {custom_name}, fetching channel ID...")
            return _get_channel_id_from_custom_url(youtube_api, custom_name)
        
        # Handle @ URLs (new format)
        elif path.startswith('/@'):
            handle = path.split('/@')[1].split('/')[0]
            logger.debug(f"Handle found: {handle}, fetching channel ID...")
            return _get_channel_id_from_handle(youtube_api, handle)
        
        # Extract from video URL
        elif '/watch' in path:
            query = parse_qs(parsed_url.query)
            video_id = query.get('v', [None])[0]
            if video_id:
                logger.debug(f"Video ID found: {video_id}, fetching channel ID...")
                return _get_channel_id_from_video(youtube_api, video_id)
        
        # Shortened URL
        elif parsed_url.netloc == 'youtu.be':
            video_id = path.strip('/')
            logger.debug(f"Shortened URL video ID found: {video_id}, fetching channel ID...")
            return _get_channel_id_from_video(youtube_api, video_id)
        
        # If none of the above, try a search for the URL
        logger.debug("No standard format recognized, trying direct search...")
        return _search_for_channel(youtube_api, url)
    
    except Exception as e:
        logger.error(f"Error extracting channel ID: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def _get_channel_id_from_username(youtube_api, username):
    """Get channel ID from username."""
    try:
        logger.debug(f"Looking up channel ID for username: {username}")
        response = youtube_api.youtube.channels().list(
            part='id',
            forUsername=username
        ).execute()
        
        if response['items']:
            channel_id = response['items'][0]['id']
            logger.debug(f"Found channel ID: {channel_id} for username: {username}")
            return channel_id
        
        # If no direct match, try searching
        logger.debug(f"No direct match for username: {username}, trying search...")
        return _search_for_channel(youtube_api, username)
    except Exception as e:
        logger.error(f"Error getting channel ID from username: {e}")
        return None

def _get_channel_id_from_custom_url(youtube_api, custom_name):
    """Get channel ID from custom URL."""
    try:
        logger.debug(f"Searching for channel with custom URL: {custom_name}")
        # Search for the channel using the custom name
        response = youtube_api.youtube.search().list(
            part='snippet',
            q=custom_name,
            type='channel',
            maxResults=5
        ).execute()
        
        if response['items']:
            # Try to find an exact match
            for item in response['items']:
                if item['snippet']['title'].lower() == custom_name.lower():
                    channel_id = item['snippet']['channelId']
                    logger.debug(f"Found exact match channel ID: {channel_id} for custom URL: {custom_name}")
                    return channel_id
            
            # If no exact match, return the first result
            channel_id = response['items'][0]['snippet']['channelId']
            logger.debug(f"Using first match channel ID: {channel_id} for custom URL: {custom_name}")
            return channel_id
        
        logger.debug(f"No results found for custom URL: {custom_name}")
        return None
    except Exception as e:
        logger.error(f"Error getting channel ID from custom URL: {e}")
        return None

def _get_channel_id_from_handle(youtube_api, handle):
    """Get channel ID from @ handle."""
    try:
        logger.debug(f"Searching for channel with handle: {handle}")
        # Search for the channel using the handle
        response = youtube_api.youtube.search().list(
            part='snippet',
            q=handle,
            type='channel',
            maxResults=5
        ).execute()
        
        if response['items']:
            channel_id = response['items'][0]['snippet']['channelId']
            logger.debug(f"Found channel ID: {channel_id} for handle: {handle}")
            return channel_id
        
        logger.debug(f"No results found for handle: {handle}")
        return None
    except Exception as e:
        logger.error(f"Error getting channel ID from handle: {e}")
        return None

def _get_channel_id_from_video(youtube_api, video_id):
    """Extract channel ID from a video ID."""
    try:
        logger.debug(f"Looking up channel ID for video: {video_id}")
        response = youtube_api.youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()
        
        if response['items']:
            channel_id = response['items'][0]['snippet']['channelId']
            logger.debug(f"Found channel ID: {channel_id} for video: {video_id}")
            return channel_id
        
        logger.debug(f"No video found with ID: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting channel ID from video: {e}")
        return None

def _search_for_channel(youtube_api, query):
    """General search for channel based on query."""
    try:
        logger.debug(f"Performing general channel search for: {query}")
        response = youtube_api.youtube.search().list(
            part='snippet',
            q=query,
            type='channel',
            maxResults=1
        ).execute()
        
        if response['items']:
            channel_id = response['items'][0]['snippet']['channelId']
            logger.debug(f"Found channel ID: {channel_id} for query: {query}")
            return channel_id
        
        logger.debug(f"No channel found for query: {query}")
        return None
    except Exception as e:
        logger.error(f"Error searching for channel: {e}")
        return None

def format_duration(duration_str):
    """Convert ISO 8601 duration string (e.g., PT1M30S) to HH:MM:SS or MM:SS format."""
    if not duration_str:
        return "00:00"
    try:
        duration = isodate.parse_duration(duration_str)
        total_seconds = int(duration.total_seconds())
        
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        logger.error(f"Error formatting duration '{duration_str}': {e}")
        return "00:00" # Return default on error

def format_date_for_display(date_str):
    """Format a date string for display."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%B %d, %Y')
    except ValueError:
        return date_str
