# YouTube Channel Analytics Scrapper

A web application that allows users to extract and analyze YouTube channel statistics and video data within a specified date range.

## Features

- Fetch YouTube channel metadata using the YouTube API
- Retrieve videos published within a specified date range
- Display comprehensive statistics for the channel and its videos
- Calculate engagement metrics
- Export data to CSV or Excel format
- Clean and modern user interface

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Data Processing**: Pandas
- **API Integration**: Google API Python Client
- **Deployment**: Heroku

## Getting Started

### Prerequisites

- Python 3.7+
- Google API Key with YouTube Data API v3 enabled

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/HassanAliMAli/youtube-data-scrapper.git
   cd youtube-data-scrapper
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

4. Access the application at `http://localhost:5000`

### Configuration

You'll need to obtain a Google API key with YouTube Data API v3 enabled:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to API & Services > Library
4. Search for "YouTube Data API v3" and enable it
5. Go to API & Services > Credentials
6. Create an API key
7. Use this API key in the application when prompted

## Deployment

This application is deployed on Heroku at https://youtube-scrapper-e28371549797.herokuapp.com/

For manual deployment:

1. Create a Heroku account and install the Heroku CLI
2. Log in to Heroku: `heroku login`
3. Create a new Heroku app: `heroku create`
4. Push to Heroku: `git push heroku main`
5. Ensure the web dyno is running: `heroku ps:scale web=1`

## Usage

1. Enter a YouTube channel URL (or video URL from the channel)
2. Provide your Google API key
3. Select a date range (optional)
4. Click "Analyze" to view the results
5. Export data as needed

## License

This project is licensed under the MIT License.

## Acknowledgements

- YouTube Data API v3
- Flask framework
- Open-source libraries used in this project
