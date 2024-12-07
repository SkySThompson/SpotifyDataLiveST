import sqlite3
from flask import Flask, jsonify, request, redirect, session, render_template, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

app = Flask(__name__, template_folder='templates')
app.secret_key = '123abc'  # Replace with your actual secret key

def get_db_connection():
    conn = sqlite3.connect('spotify_db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

sp_oauth = SpotifyOAuth(
    client_id='dd2e711b0a1f48be9aef94a683bae1db',
    client_secret='788689b2bfff4cd09f97dc01853ab1a9',
    redirect_uri='http://localhost:5000/callback',
    scope='user-library-read user-top-read'
)

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None
    now = int(time.time())
    is_token_expired = token_info['expires_at'] - now < 60
    if is_token_expired:
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    return token_info

@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    if not token_info:
        return "Error retrieving access token.", 400
    session['token_info'] = token_info
    return redirect('/dashboard-content')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'token_info' not in session:
        return redirect(sp_oauth.get_authorize_url())
    return redirect(url_for('dashboard_content'))

@app.route('/dashboard-content', methods=['GET'])
def dashboard_content():
    token_info = get_token()
    if token_info is None:
        return redirect(sp_oauth.get_authorize_url())
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    try:
        # Fetch saved tracks
        saved_tracks_results = sp.current_user_saved_tracks()
        saved_tracks = []
        for item in saved_tracks_results['items']:
            track = item['track']
            album_cover = track['album']['images'][0]['url'] if track['album']['images'] else None
            saved_tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'album_cover': album_cover,
                'preview_url': track['external_urls']['spotify']  # Add Spotify URL
            })
        
        # Fetch top tracks
        top_tracks_results = sp.current_user_top_tracks()
        top_tracks = []
        for item in top_tracks_results['items']:
            album_cover = item['album']['images'][0]['url'] if item['album']['images'] else None
            top_tracks.append({
                'track_name': item['name'],
                'artist_name': item['artists'][0]['name'],
                'album_name': item['album']['name'],
                'album_cover_url': album_cover,
                'play_count': item.get('play_count', 'N/A'),  # Adjust if play count is not available
                'preview_url': item['external_urls']['spotify']  # Add Spotify URL
            })

        return render_template('dashboard.html', saved_tracks=saved_tracks, top_tracks=top_tracks)
    except Exception as e:
        print("Error while fetching data:", e)
        return "An error occurred while fetching data."

if __name__ == '__main__':
    app.run(debug=True)
