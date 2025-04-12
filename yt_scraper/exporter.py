import os
import json
import csv
import pandas as pd
import tempfile
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def export_data(channel_data, videos_data, export_format, timestamp):
    """Export data to the specified format."""
    try:
        logger.debug(f"Exporting data in {export_format} format")
        if export_format == 'csv':
            return export_to_csv(channel_data, videos_data, timestamp)
        elif export_format == 'json':
            return export_to_json(channel_data, videos_data, timestamp)
        elif export_format == 'excel':
            return export_to_excel(channel_data, videos_data, timestamp)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    except Exception as e:
        logger.error(f"Error during export: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def export_to_csv(channel_data, videos_data, timestamp):
    """Export data to CSV format."""
    logger.debug("Starting CSV export...")
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    
    try:
        # Open the file for writing
        with open(temp_file.name, 'w', newline='', encoding='utf-8') as csvfile:
            # Create CSV writer
            writer = csv.writer(csvfile)
            
            # Write channel section header
            writer.writerow(['CHANNEL DATA'])
            writer.writerow(['Field', 'Value'])
            
            # Write channel data
            for key, value in channel_data.items():
                if key == 'upload_frequency':
                    writer.writerow(['upload_frequency_per_day', value.get('per_day', 0)])
                    writer.writerow(['upload_frequency_per_week', value.get('per_week', 0)])
                    writer.writerow(['upload_frequency_per_month', value.get('per_month', 0)])
                elif isinstance(value, list):
                    writer.writerow([key, ', '.join(str(item) for item in value)])
                elif isinstance(value, dict):
                    writer.writerow([key, json.dumps(value)])
                else:
                    writer.writerow([key, value])
            
            # Add a blank row
            writer.writerow([])
            
            # Write videos section header
            writer.writerow(['VIDEOS DATA'])
            
            # Determine all possible video fields by combining fields from all videos
            video_fields = set()
            for video in videos_data:
                for key in video.keys():
                    if key != 'comments':  # Handle comments separately
                        video_fields.add(key)
            
            # Convert to ordered list and write header row
            video_fields = sorted(list(video_fields))
            writer.writerow(video_fields)
            
            # Write video data
            for video in videos_data:
                row = []
                for field in video_fields:
                    value = video.get(field, '')
                    if field in ['tags', 'description_urls'] and isinstance(value, list):
                        row.append(', '.join(str(item) for item in value))
                    elif isinstance(value, dict):
                        row.append(json.dumps(value))
                    else:
                        row.append(str(value))
                writer.writerow(row)
                
            # Add a blank row
            writer.writerow([])
            
            # Write comments section if available
            writer.writerow(['COMMENTS DATA'])
            writer.writerow(['video_id', 'video_title', 'author', 'text', 'like_count', 'published_at', 'updated_at'])
            
            for video in videos_data:
                video_id = video.get('id', '')
                video_title = video.get('title', '')
                
                for comment in video.get('comments', []):
                    writer.writerow([
                        video_id,
                        video_title,
                        comment.get('author', ''),
                        comment.get('text', '').replace('\n', ' '),
                        comment.get('like_count', 0),
                        comment.get('published_at', ''),
                        comment.get('updated_at', '')
                    ])
        
        logger.debug(f"CSV export completed to file: {temp_file.name}")
        return temp_file.name
    
    except Exception as e:
        # Ensure we clean up the temporary file in case of error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.error(f"Error exporting to CSV: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def export_to_json(channel_data, videos_data, timestamp):
    """Export data to JSON format."""
    logger.debug("Starting JSON export...")
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
    
    try:
        # Prepare the export data structure
        export_data = {
            'channel': channel_data,
            'videos': videos_data,
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'video_count': len(videos_data)
            }
        }
        
        # Write to the JSON file
        with open(temp_file.name, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.debug(f"JSON export completed to file: {temp_file.name}")
        return temp_file.name
    
    except Exception as e:
        # Ensure we clean up the temporary file in case of error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.error(f"Error exporting to JSON: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def export_to_excel(channel_data, videos_data, timestamp):
    """Export data to Excel format."""
    logger.debug("Starting Excel export...")
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    
    try:
        # Create Excel writer
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            # Prepare channel data for DataFrame
            channel_df_data = []
            for key, value in channel_data.items():
                if key == 'upload_frequency':
                    channel_df_data.append(['upload_frequency_per_day', value.get('per_day', 0)])
                    channel_df_data.append(['upload_frequency_per_week', value.get('per_week', 0)])
                    channel_df_data.append(['upload_frequency_per_month', value.get('per_month', 0)])
                elif isinstance(value, list):
                    channel_df_data.append([key, ', '.join(str(item) for item in value)])
                elif isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        channel_df_data.append([f"{key}_{subkey}", subvalue])
                else:
                    channel_df_data.append([key, value])
            
            # Create channel DataFrame and export to sheet
            channel_df = pd.DataFrame(channel_df_data, columns=['Field', 'Value'])
            channel_df.to_excel(writer, sheet_name='Channel Data', index=False)
            
            # Prepare video data for DataFrame
            # Handle nested fields and lists by converting them to strings
            videos_df_data = []
            for video in videos_data:
                video_copy = {}
                for key, value in video.items():
                    if key == 'comments':
                        video_copy['comment_count'] = len(value)  # Just store the count here
                    elif isinstance(value, list):
                        video_copy[key] = ', '.join(str(item) for item in value)
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            video_copy[f"{key}_{subkey}"] = subvalue
                    else:
                        video_copy[key] = value
                videos_df_data.append(video_copy)
            
            # Create videos DataFrame and export to sheet
            if videos_df_data:
                videos_df = pd.DataFrame(videos_df_data)
                videos_df.to_excel(writer, sheet_name='Videos Data', index=False)
            
            # Prepare comments data for DataFrame
            comments_data = []
            for video in videos_data:
                video_id = video.get('id', '')
                video_title = video.get('title', '')
                
                for comment in video.get('comments', []):
                    comments_data.append({
                        'video_id': video_id,
                        'video_title': video_title,
                        'author': comment.get('author', ''),
                        'text': comment.get('text', '').replace('\n', ' '),
                        'like_count': comment.get('like_count', 0),
                        'published_at': comment.get('published_at', ''),
                        'updated_at': comment.get('updated_at', '')
                    })
            
            # Create comments DataFrame and export to sheet
            if comments_data:
                comments_df = pd.DataFrame(comments_data)
                comments_df.to_excel(writer, sheet_name='Comments Data', index=False)
            
            # Add a summary sheet
            summary_data = [
                ['Channel Name', channel_data.get('title', '')],
                ['Channel ID', channel_data.get('id', '')],
                ['Subscribers', channel_data.get('subscriber_count', 0)],
                ['Total Videos', channel_data.get('video_count', 0)],
                ['Total Views', channel_data.get('view_count', 0)],
                ['Videos in Export', len(videos_data)],
                ['Date Range Start', timestamp],
                ['Date Range End', timestamp],
                ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]
            
            # Calculate some aggregated stats
            total_views = sum(video.get('view_count', 0) for video in videos_data)
            total_likes = sum(video.get('like_count', 0) for video in videos_data)
            total_comments = sum(video.get('comment_count', 0) for video in videos_data)
            avg_engagement = sum(video.get('engagement_rate', 0) for video in videos_data) / len(videos_data) if videos_data else 0
            
            summary_data.extend([
                ['Total Views (Export)', total_views],
                ['Total Likes (Export)', total_likes],
                ['Total Comments (Export)', total_comments],
                ['Average Engagement Rate', f"{avg_engagement:.2f}%"]
            ])
            
            summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        logger.debug(f"Excel export completed to file: {temp_file.name}")
        return temp_file.name
    
    except Exception as e:
        # Ensure we clean up the temporary file in case of error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.error(f"Error exporting to Excel: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
