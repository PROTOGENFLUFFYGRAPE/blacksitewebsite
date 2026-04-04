from flask import Flask, redirect, request, session, jsonify
import requests
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('secret_key', 'your-secret-key-change-this')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

DISCORD_CLIENT_ID = os.environ.get('discord_client_id')
DISCORD_CLIENT_SECRET = os.environ.get('discord_client_secret')
DISCORD_REDIRECT_URI = os.environ.get('discord_redirect_uri')
DISCORD_API_BASE_URL = 'https://discordapp.com/api'

@app.route('/')
def index():
    return jsonify({"message": "Discord OAuth Backend Running"})

@app.route('/login')
def login():
    discord_login_url = f'{DISCORD_API_BASE_URL}/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds'
    return redirect(discord_login_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        token_response = requests.post(
            f'{DISCORD_API_BASE_URL}/oauth2/token',
            data={
                'client_id': DISCORD_CLIENT_ID,
                'client_secret': DISCORD_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': DISCORD_REDIRECT_URI
            }
        )
        
        if token_response.status_code != 200:
            return jsonify({"error": "Failed to get token"}), 400
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        user_response = requests.get(
            f'{DISCORD_API_BASE_URL}/users/@me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if user_response.status_code != 200:
            return jsonify({"error": "Failed to get user"}), 400
        
        user_data = user_response.json()
        user_id = user_data.get('id')
        username = user_data.get('username')
        avatar = user_data.get('avatar')
        
        guild_id = '1405701060793860147'
        member_response = requests.get(
            f'{DISCORD_API_BASE_URL}/users/@me/guilds/{guild_id}/member',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        user_roles = []
        if member_response.status_code == 200:
            member_data = member_response.json()
            user_roles = member_data.get('roles', [])
            print(f"✓ Got roles for {username}: {user_roles}")
        else:
            print(f"✗ Failed to get member. Status: {member_response.status_code}")
        
        session.permanent = True
        session['user_id'] = user_id
        session['username'] = username
        session['avatar'] = avatar
        session['roles'] = user_roles
        
        roles_str = ','.join(user_roles) if user_roles else 'none'
        redirect_url = f"{os.environ.get('website_url', 'http://localhost:5000')}?token={access_token}&user_id={user_id}&username={username}&avatar={avatar}&roles={roles_str}"
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    return jsonify({
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "avatar": session.get('avatar'),
        "roles": session.get('roles', [])
    })

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
