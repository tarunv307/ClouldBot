import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig

load_dotenv()

app = Flask(__name__)
CORS(app)

def create_agent():
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

agent = create_agent()

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        if not user_msg:
            return jsonify({'reply': 'Please type a message.', 'status': 'error'}), 400

        async def get_reply():
            response = await agent.chat(user_msg)
            return response.text

        reply = asyncio.run(get_reply())
        return jsonify({'reply': reply, 'status': 'success'})

    except Exception as e:
        return jsonify({'reply': f'Error: {str(e)}', 'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
