import os
import pathlib

import math
import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

from dotenv import load_dotenv
load_dotenv()  
# hi hi``

app = Flask("Google Login App")
app.secret_key = os.environ.get("SECRET_KEY") # make sure this matches with that's in client_secret.json
print(app.secret_key)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = "341501985016-cneblrth1bp5gmda83jrvoaf1vn8cdkp.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID") 
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_SECRET_ID") 
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/spotify_callback"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/protected_area")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_area")
@login_is_required
def protected_area():
    user_name = session.get('name', 'Guest')  # Default to 'Guest' if name is not in session
    return render_template('welcome.html', user_name=user_name)


@app.route("/spotify_login")
def spotify_login():
    scope = "user-read-private playlist-modify-public playlist-modify-private"  # Add or modify scopes as needed
    auth_url = f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={SPOTIFY_CLIENT_ID}&scope={scope}&redirect_uri={SPOTIFY_REDIRECT_URI}"
    return redirect(auth_url)

# Add a new route for Spotify Callback
@app.route("/spotify_callback")
def spotify_callback():
    code = request.args.get('code')
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
    token_info = response.json()

    access_token = token_info.get('access_token')
    session["spotify_token"] = access_token

    # Get user profile information to retrieve Spotify user ID
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
        user_profile_info = user_profile_response.json()

        session["spotify_user_id"] = user_profile_info.get('id')


    # Store Spotify token in session or handle it as needed
    session["spotify_token"] = token_info.get('access_token')
    return redirect("/protected_area")

@app.route('/spotify_test', methods=['GET', 'POST'])
def spotify_test():
    if request.method == 'POST':
        # Extract the text input from the form
        text_input = request.form['text_input']
        # results = parse_sentence(text_input)    
        # for result in results:
        #     print(result['name'], " ", result['artists'][0]['name'])

        spotify_token = session.get("spotify_token")
        playlist = create_playlist("test", spotify_token)
        print(playlist)
        # add_songs(playlist, results)

        # Redirect or render a template after processing
        return redirect("/protected_area")  # Redirect to some other page or

    # If it's a GET request, just render the form page
    return render_template("/protected_area")

def create_playlist(playlist_name, spotify_token):
    # Spotify API endpoint for creating a playlist
    user_id = session["spotify_user_id"]
    url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    
    # Headers for the POST request, including the authorization token
    headers = {
        "Authorization": f"Bearer {spotify_token}",
        "Content-Type": "application/json"
    }

    # JSON data with the playlist name
    data = {
        "name": playlist_name,
        "description": "Created with Python",
        "public": False  # Set to True if you want the playlist to be public
    }

    # Sending POST request to the Spotify API
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    print(response.json())

    # Check if the request was successful
    if response.status_code == 201:
        return response.json()  # Returns the created playlist details as JSON
    else:
        return None  
    
def add_songs(playlist_id, results):
    """do stuff"""

def parse_sentence(input):
    sentence = input.split()
    spotify_token = session.get("spotify_token")
    print(sentence)
    results = []
    for word in sentence:
        search_result = search_spotify(word, spotify_token)

        if search_result['tracks'] and search_result['tracks']['items']:
            closest_result = search_result['tracks']['items'][0]
            closest_score = math.inf
            for track in search_result['tracks']['items']:
                track_string = track['name']
                similarity = compare_similarity(word, track_string)
                if similarity < closest_score:
                    closest_result = track
                    closest_score = similarity
                print(track_string, similarity)
                if similarity == 0:
                    break
            print()
            results.append(closest_result)
            
        else:
            continue
    return results

def compare_similarity(s1, s2):
    """compares the similarity of two strings (Levenshtein difference)"""
    # Code from https://www.educative.io/answers/the-levenshtein-distance-algorithm
    a = s1.lower()
    b = s2.lower()
    

    # Declaring array 'D' with rows = len(a) + 1 and columns = len(b) + 1:
    D = [[0 for i in range(len(b) + 1)] for j in range(len(a) + 1)]
    # Initialising first row:
    for i in range(len(a) + 1):
        D[i][0] = i
    # Initialising first column:
    for j in range(len(b) + 1):
        D[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                D[i][j] = D[i - 1][j - 1]
            else:
                # Adding 1 to account for the cost of operation
                insertion = 1 + D[i][j - 1]
                deletion = 1 + D[i - 1][j]
                replacement = 1 + D[i - 1][j - 1]

                # Choosing the best option:
                D[i][j] = min(insertion, deletion, replacement)

    return D[len(a)][len(b)]


def search_spotify(query, token):
    search_url = 'https://api.spotify.com/v1/search'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    refined_query = f'"{query}"'

    params = {
        'q': refined_query,
        'type': 'track',
        'limit': 50  # number of results to return
    }
    response = requests.get(search_url, headers=headers, params=params)
    return response.json()

if __name__ == '__main__':
    app.run()
