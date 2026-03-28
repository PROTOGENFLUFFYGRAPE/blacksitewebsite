from flask import Flask, redirect, request, session, url_for, jsonify
import requests
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('secret_key', 'your-secret-key-change-this')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Discord OAuth config
DISCORD_CLIENT_ID = os.environ.get('discord_client_id')
DISCORD_CLIENT_SECRET = os.environ.get('discord_client_secret')
DISCORD_REDIRECT_URI = os.environ.get('discord_redirect_uri')
DISCORD_API_BASE_URL = 'https://discordapp.com/api'

@app.route('/')
def index():
    return jsonify({"message": "Discord OAuth Backend Running"})

@app.route('/login')
def login():
    """Redirect to Discord OAuth"""
    discord_login_url = f'{DISCORD_API_BASE_URL}/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds'
    return redirect(discord_login_url)

@app.route('/callback')
def callback():
    """Handle Discord OAuth callback"""
    code = request.args.get('code')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        # Exchange code for access token
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
        
        # Get user info
        user_response = requests.get(
            f'{DISCORD_API_BASE_URL}/users/@me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if user_response.status_code != 200:
            return jsonify({"error": "Failed to get user"}), 400
        
        user_data = user_response.json()
        user_id = user_data.get('id')
        username = user_data.get('username')
        discriminator = user_data.get('discriminator')
        avatar = user_data.get('avatar')
        
        # Get user guilds
        guilds_response = requests.get(
            f'{DISCORD_API_BASE_URL}/users/@me/guilds',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        guilds = guilds_response.json() if guilds_response.status_code == 200 else []
        
        # Store in session
        session.permanent = True
        session['user_id'] = user_id
        session['username'] = username
        session['discriminator'] = discriminator
        session['avatar'] = avatar
        session['access_token'] = access_token
        session['guilds'] = guilds
        
        # Redirect back to website with token
        redirect_url = f"{os.environ.get('website_url', 'http://localhost:5000')}?token={access_token}&user_id={user_id}&username={username}"
        return redirect(redirect_url)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user')
def get_user():
    """Get logged in user info"""
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    return jsonify({
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "discriminator": session.get('discriminator'),
        "avatar": session.get('avatar'),
        "guilds": session.get('guilds', [])
    })

@app.route('/api/logout')
def logout():
    """Logout user"""
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route('/api/check-role/<int:guild_id>/<int:role_id>')
def check_role(guild_id, role_id):
    """Check if user has a role in a guild"""
    if 'user_id' not in session:
        return jsonify({"has_role": False}), 401
    
    access_token = session.get('access_token')
    user_id = session.get('user_id')
    
    try:
        # Get user's roles in guild
        response = requests.get(
            f'{DISCORD_API_BASE_URL}/users/@me/guilds/{guild_id}/member',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code != 200:
            return jsonify({"has_role": False}), 400
        
        member_data = response.json()
        roles = member_data.get('roles', [])
        
        has_role = str(role_id) in roles
        return jsonify({"has_role": has_role})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
