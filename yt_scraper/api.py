import logging
import re
from datetime import datetime
import isodate
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .utils import format_duration, format_datetime_for_display

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class YouTubeAPI:
    def __init__(self, api_key):
        """Initialize the YouTube API client."""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.progress = {'status': 'Initializing', 'progress': 0}
        
    def get_progress(self):
        """Get the current progress of data collection."""
        return self.progress
    
    def get_channel_data(self, channel_id):
        """Fetch channel-level data for the given channel ID."""
        self.progress = {'status': 'Fetching channel data', 'progress': 10}
        
        try:
            # Get channel details
            channel_response = self.youtube.channels().list(
                part='snippet,contentDetails,statistics,brandingSettings',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                logger.error(f"No channel found with ID: {channel_id}")
                return None
            
            channel = channel_response['items'][0]
            
            # Extract basic channel info
            custom_url = channel['snippet'].get('customUrl', '')
            channel_url = f"https://www.youtube.com/channel/{channel['id']}"
            
            # If a custom URL exists, use it instead
            if custom_url:
                channel_url = f"https://www.youtube.com/{custom_url}"
            
            channel_data = {
                'id': channel['id'],
                'title': channel['snippet']['title'],
                'description': channel['snippet']['description'],
                'custom_url': custom_url,
                'url': channel_url,
                'published_at': format_datetime_for_display(channel['snippet']['publishedAt']),
                'country': channel['snippet'].get('country', 'Unknown'),
                'view_count': int(channel['statistics'].get('viewCount', 0)),
                'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
                'video_count': int(channel['statistics'].get('videoCount', 0)),
                'topic_categories': channel.get('topicDetails', {}).get('topicCategories', []),
                'thumbnail_url': channel['snippet']['thumbnails'].get('high', {}).get('url', ''),
                'banner_url': channel.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl', '')
            }
            
            # Calculate upload frequency (estimated based on video count and channel age)
            try:
                published_at_str = channel['snippet']['publishedAt']
                # Handle different datetime formats (with or without milliseconds)
                try:
                    if '.' in published_at_str:
                        # Format with milliseconds
                        published_at = datetime.strptime(published_at_str.split('.')[0] + 'Z', '%Y-%m-%dT%H:%M:%SZ')
                    else:
                        # Format without milliseconds
                        published_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    # Fallback with flexible parsing
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                
                days_since_creation = max(1, (datetime.now() - published_at).days)  # Ensure at least 1 day
                uploads_per_day = int(channel['statistics'].get('videoCount', 0)) / days_since_creation
                uploads_per_week = uploads_per_day * 7
                uploads_per_month = uploads_per_day * 30
                
                channel_data['upload_frequency'] = {
                    'per_day': round(uploads_per_day, 2),
                    'per_week': round(uploads_per_week, 2),
                    'per_month': round(uploads_per_month, 2)
                }
            except Exception as e:
                logger.warning(f"Could not calculate upload frequency: {e}")
                channel_data['upload_frequency'] = {
                    'per_day': 0,
                    'per_week': 0,
                    'per_month': 0
                }
            
            self.progress = {'status': 'Channel data fetched successfully', 'progress': 20}
            return channel_data
            
        except HttpError as e:
            logger.error(f"HTTP error when fetching channel data: {e}")
            if e.resp.status == 403:
                raise Exception("API quota exceeded or insufficient permissions")
            elif e.resp.status == 404:
                raise Exception("Channel not found")
            else:
                raise Exception(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching channel data: {e}")
            raise Exception(f"Failed to fetch channel data: {str(e)}")
    
    def get_videos_in_date_range(self, channel_id, start_date, end_date):
        """Get all videos for a channel within the specified date range."""
        self.progress = {'status': 'Fetching video list', 'progress': 30}
        
        try:
            # Convert dates to ISO format for API
            start_date_iso = start_date.isoformat() + 'Z' if isinstance(start_date, datetime) else start_date + 'T00:00:00Z'
            end_date_iso = end_date.isoformat() + 'Z' if isinstance(end_date, datetime) else end_date + 'T23:59:59Z'
            
            # Get uploads playlist ID (all videos are in this playlist)
            channel_response = self.youtube.channels().list(
                part='contentDetails,statistics',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                logger.error(f"No channel found with ID: {channel_id}")
                return []
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get total video count to check if it's a large channel
            total_video_count = int(channel_response['items'][0]['statistics'].get('videoCount', 0))
            logger.debug(f"Channel has {total_video_count} total videos")
            
            # For large channels, we'll limit the number of videos to process
            MAX_VIDEOS_TO_PROCESS = 500 
            is_large_channel = total_video_count > 1000
            
            if is_large_channel:
                self.progress = {'status': f'Large channel detected ({total_video_count} videos). Limiting results to most recent {MAX_VIDEOS_TO_PROCESS} videos.', 'progress': 35}
                logger.warning(f"Large channel detected ({total_video_count} videos). Limiting results.")
            
            # Get videos from uploads playlist
            videos = []
            next_page_token = None
            pages_to_fetch = 10  # For large channels, limit to 10 pages (500 videos max)
            page_count = 0
            
            while True:
                # For large channels, limit the number of API requests
                if is_large_channel and page_count >= pages_to_fetch:
                    logger.info(f"Reached page limit ({pages_to_fetch}) for large channel. Stopping further requests.")
                    break
                
                try:
                    playlist_response = self.youtube.playlistItems().list(
                        part='snippet,contentDetails',
                        playlistId=uploads_playlist_id,
                        maxResults=50,
                        pageToken=next_page_token
                    ).execute()
                    
                    page_count += 1
                    
                    # Process each video in the page
                    for item in playlist_response['items']:
                        # Handle videos where the publishedAt field might be missing
                        if 'videoPublishedAt' not in item['contentDetails']:
                            continue
                            
                        published_at = item['contentDetails']['videoPublishedAt']
                        
                        # Check if video is within date range
                        if start_date_iso <= published_at <= end_date_iso:
                            video_id = item['contentDetails']['videoId']
                            videos.append({
                                'id': video_id,
                                'title': item['snippet']['title'],
                                'description': item['snippet']['description'],
                                'published_at': format_datetime_for_display(published_at),
                                'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url', '')
                            })
                    
                    # Check if there are more pages
                    next_page_token = playlist_response.get('nextPageToken')
                    if not next_page_token:
                        break
                    
                    # For large channels, limit the number of videos to process
                    if is_large_channel and len(videos) >= MAX_VIDEOS_TO_PROCESS:
                        logger.info(f"Reached video limit ({MAX_VIDEOS_TO_PROCESS}) for large channel. Stopping further requests.")
                        break
                    
                except HttpError as e:
                    logger.error(f"HTTP error when fetching playlist items: {e}")
                    # If we hit an API quota error, break out of the loop with what we have
                    if e.resp.status == 403:
                        logger.warning("API quota limit reached. Continuing with videos collected so far.")
                        break
                    raise
                
                except Exception as e:
                    logger.error(f"Error fetching playlist items: {e}")
                    # Continue with the videos we've collected so far
                    break
            
            # Update progress
            video_count = len(videos)
            self.progress = {'status': f'Found {video_count} videos in date range', 'progress': 50}
            
            if video_count == 0:
                logger.warning("No videos found in the specified date range.")
                return []
                
            # Apply additional limit for very large results
            if video_count > MAX_VIDEOS_TO_PROCESS:
                logger.warning(f"Limiting results to {MAX_VIDEOS_TO_PROCESS} most recent videos.")
                videos = videos[:MAX_VIDEOS_TO_PROCESS]
            
            # Get detailed data for each video
            return self._get_video_details(videos)
        
        except HttpError as e:
            logger.error(f"HTTP error when fetching videos: {e}")
            if e.resp.status == 403:
                raise Exception("API quota exceeded or insufficient permissions")
            else:
                raise Exception(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            raise Exception(f"Failed to fetch videos: {str(e)}")
    
    def _get_video_details(self, videos):
        """Get detailed information for a list of videos."""
        total_videos = len(videos)
        if total_videos == 0:
            return []
        
        try:
            # Process videos in batches to respect API limits
            batch_size = 50  # YouTube API allows up to 50 videos per request
            detailed_videos = []
            
            # Set a maximum number of attempts for each batch
            MAX_ATTEMPTS = 3
            
            for i in range(0, total_videos, batch_size):
                batch = videos[i:i+batch_size]
                
                # Update progress
                progress_pct = 50 + (i / total_videos) * 40
                self.progress = {'status': f'Fetching details for videos {i+1}-{i+len(batch)} of {total_videos}', 
                                'progress': progress_pct}
                
                # Extract video IDs for the batch
                video_ids = [video['id'] for video in batch]
                
                # Try multiple times with error handling
                attempt = 0
                success = False
                
                while attempt < MAX_ATTEMPTS and not success:
                    try:
                        # Get video details
                        video_response = self.youtube.videos().list(
                            part='snippet,contentDetails,statistics',
                            id=','.join(video_ids)
                        ).execute()
                        
                        # If we get here, the API call was successful
                        success = True
                        
                        # Map detailed data back to our list
                        id_to_index = {video['id']: idx for idx, video in enumerate(batch)}
                        
                        for item in video_response.get('items', []):
                            video_id = item['id']
                            if video_id in id_to_index:
                                idx = id_to_index[video_id]
                                
                                try:
                                    # Add additional data to the video
                                    batch[idx].update({
                                        'duration': format_duration(item['contentDetails'].get('duration', 'PT0S')),
                                        'dimension': item['contentDetails'].get('dimension', 'N/A'),
                                        'definition': item['contentDetails'].get('definition', 'N/A'),
                                        'caption': item['contentDetails'].get('caption', 'N/A') == 'true',
                                        'licensed_content': item['contentDetails'].get('licensedContent', False),
                                        'projection': item['contentDetails'].get('projection', 'N/A'),
                                        'view_count': int(item['statistics'].get('viewCount', 0)),
                                        'like_count': int(item['statistics'].get('likeCount', 0)),
                                        'comment_count': int(item['statistics'].get('commentCount', 0)),
                                        'tags': item['snippet'].get('tags', []),
                                        'category_id': item['snippet'].get('categoryId', 'N/A'),
                                        'live_broadcast_content': item['snippet'].get('liveBroadcastContent', 'none'),
                                        'default_language': item['snippet'].get('defaultLanguage', 'N/A'),
                                        'localized': item['snippet'].get('localized', {}),
                                        'default_audio_language': item['snippet'].get('defaultAudioLanguage', 'N/A'),
                                        'video_url': f"https://www.youtube.com/watch?v={video_id}"
                                    })
                                    
                                    # Calculate engagement rate
                                    view_count = batch[idx].get('view_count', 0)
                                    if view_count > 0:
                                        likes = batch[idx].get('like_count', 0)
                                        comments = batch[idx].get('comment_count', 0)
                                        batch[idx]['engagement_rate'] = ((likes + comments) / view_count) * 100
                                    else:
                                        batch[idx]['engagement_rate'] = 0
                                        
                                    # Extract URLs from description
                                    description = batch[idx].get('description', '')
                                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                                                    description)
                                    batch[idx]['description_urls'] = urls
                                except Exception as detail_error:
                                    logger.error(f"Error processing video details for {video_id}: {detail_error}")
                                    # Ensure the video has at least engagement_rate set to avoid template errors
                                    if 'engagement_rate' not in batch[idx]:
                                        batch[idx]['engagement_rate'] = 0
                        
                        # Get comments for each video in the batch (if available)
                        # Skip comments for large batches to reduce API calls
                        if len(batch) <= 10:
                            for video in batch:
                                try:
                                    video['comments'] = self._get_video_comments(video['id'], max_results=20)
                                except Exception as e:
                                    logger.warning(f"Could not get comments for video {video['id']}: {e}")
                                    video['comments'] = []
                        else:
                            logger.info(f"Skipping comment retrieval for large batch of {len(batch)} videos to reduce API usage")
                            for video in batch:
                                video['comments'] = []
                        
                    except HttpError as e:
                        attempt += 1
                        logger.error(f"HTTP error when fetching video details (attempt {attempt}/{MAX_ATTEMPTS}): {e}")
                        
                        # If quota exceeded, no point in retrying
                        if e.resp.status == 403:
                            logger.warning("API quota exceeded. Skipping further requests for this batch.")
                            # Skip retries for quota errors
                            attempt = MAX_ATTEMPTS
                            # Add minimal data so the template doesn't break
                            for video in batch:
                                if 'engagement_rate' not in video:
                                    video['engagement_rate'] = 0
                                if 'comments' not in video:
                                    video['comments'] = []
                        
                        # For other errors, wait briefly before retrying
                        elif attempt < MAX_ATTEMPTS:
                            import time
                            time.sleep(2)  # Wait 2 seconds before retry
                    
                    except Exception as e:
                        attempt += 1
                        logger.error(f"General error when fetching video details (attempt {attempt}/{MAX_ATTEMPTS}): {e}")
                        
                        # Add minimal data so the template doesn't break
                        for video in batch:
                            if 'engagement_rate' not in video:
                                video['engagement_rate'] = 0
                            if 'comments' not in video:
                                video['comments'] = []
                                
                        # For errors, wait briefly before retrying
                        if attempt < MAX_ATTEMPTS:
                            import time
                            time.sleep(2)  # Wait 2 seconds before retry
                
                # If we couldn't get details after MAX_ATTEMPTS, use basic info we already have
                if not success:
                    logger.warning(f"Failed to get detailed data for batch after {MAX_ATTEMPTS} attempts. Using basic data.")
                    
                # Add the batch to detailed_videos regardless of success
                # This ensures we always return at least the basic data we had
                detailed_videos.extend(batch)
            
            self.progress = {'status': 'Video data collection complete', 'progress': 100}
            return detailed_videos
            
        except HttpError as e:
            logger.error(f"HTTP error when fetching video details: {e}")
            if e.resp.status == 403:
                raise Exception("API quota exceeded or insufficient permissions")
            else:
                raise Exception(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching video details: {e}")
            raise Exception(f"Failed to fetch video details: {str(e)}")
    
    def _get_video_comments(self, video_id, max_results=20):
        """Get comments for a video, limited to max_results."""
        try:
            comments = []
            next_page_token = None
            
            # Only get up to max_results comments to avoid excessive API usage
            while len(comments) < max_results:
                comment_response = self.youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=min(100, max_results - len(comments)),
                    pageToken=next_page_token
                ).execute()
                
                for item in comment_response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'author': comment['authorDisplayName'],
                        'text': comment['textDisplay'],
                        'like_count': comment['likeCount'],
                        'published_at': format_datetime_for_display(comment['publishedAt']),
                        'updated_at': format_datetime_for_display(comment['updatedAt'])
                    })
                
                next_page_token = comment_response.get('nextPageToken')
                if not next_page_token or len(comments) >= max_results:
                    break
            
            return comments
            
        except HttpError as e:
            # Comments may be disabled for some videos
            if e.resp.status == 403:
                logger.warning(f"Comments are disabled for video {video_id}")
                return []
            else:
                logger.warning(f"Error fetching comments for video {video_id}: {e}")
                return []
        except Exception as e:
            logger.warning(f"Error fetching comments for video {video_id}: {e}")
            return []
