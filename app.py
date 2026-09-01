import os
import asyncio
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

def get_db_connection():
    if not HAS_POSTGRES or not DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("Skipping DB initialization (No active connection or driver).")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    user_email VARCHAR(255),
                    title VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("✅ Supabase PostgreSQL Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing DB tables: {e}")
    finally:
        conn.close()

# Auto-initialize DB tables
init_db()

try:
    from google.antigravity import Agent, LocalAgentConfig
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False

def create_agent():
    if HAS_ANTIGRAVITY:
        try:
            config = LocalAgentConfig(
                api_key=os.getenv("GOOGLE_API_KEY"),
                system_prompt="""
                You are CloudBot, a professional customer support assistant for a cloud computing company.
                - Keep responses short, clear, and professional.
                - If asked about pricing, say 'Please check our pricing page.'
                - If you don't know, say 'Let me connect you to a human agent.'
                """
            )
            return Agent(config=config)
        except Exception:
            return None
    return None

agent = create_agent()

@app.route('/')
def home():
    return send_file('login.html')

@app.route('/index.html')
def index():
    return send_file('index.html')

@app.route('/login.html')
def login():
    return send_file('login.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        user_msg = data.get('message', '').strip()
        if not user_msg:
            return jsonify({'reply': 'Please type a message.', 'status': 'error'}), 400

        if agent:
            async def get_reply():
                response = await agent.chat(user_msg)
                return response.text
            reply = asyncio.run(get_reply())
        else:
            reply = "Hello! CloudBot API is active."

        return jsonify({'reply': reply, 'status': 'success'})

    except Exception as e:
        return jsonify({'reply': f'Error: {str(e)}', 'status': 'error'}), 500

@app.route('/api/db-status', methods=['GET'])
def db_status():
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'database': 'Supabase PostgreSQL', 'connected': True, 'status': 'online'}), 200
    return jsonify({'database': 'Supabase PostgreSQL', 'connected': False, 'status': 'offline'}), 500

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return send_file('login.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
