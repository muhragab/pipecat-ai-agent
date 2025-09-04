# Realtime AI Interview Agent (Pipecat Cloud)

[![Docs](https://img.shields.io/badge/Documentation-blue)](https://docs.pipecat.daily.co) [![Discord](https://img.shields.io/discord/1217145424381743145)](https://discord.gg/dailyco)

A Realtime AI Interview Agent built on Pipecat Cloud, using **Daily WebRTC**, **GPT-4o Mini**, and **Whisper** for voice-only AI interviews.

---

## Features

- Conduct structured, voice-only AI interviews
- Real-time speech-to-text using Whisper
- AI-powered responses via GPT-4o Mini
- Text-to-speech (TTS) integration
- Dockerized for easy deployment
- Configurable environment variables for API keys

---

## Prerequisites

- Python 3.10+
- Linux, MacOS, or WSL
- [Docker](https://www.docker.com)
- [Pipecat Cloud](https://pipecat.daily.co) account
- API keys:
  - **OpenAI API Key**
  - **Daily API Key** (from Pipecat Cloud)
  - **Cartesia API Key** (optional)

---

## Setup & Run Locally

### 1. Clone repository
git clone https://github.com/muhragab/pipecat-ai-agent.git
cd pipecat-ai-agent
cd pipecat-ai-agent

2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt
pip install pipecatcloud

4. Set environment variables

export OPENAI_API_KEY="your_openai_key"
export DAILY_API_KEY="your_daily_key"
export CARTESIA_API_KEY="your_cartesia_key"  # optional

5. Run agent locally

LOCAL_RUN=1 python bot.py
Docker Deployment

1. Build and tag image

docker build --platform=linux/arm64 -t ai-interview-agent:latest .
docker tag ai-interview-agent:latest your-docker-username/ai-interview-agent:0.1

2. Push to Docker Hub
docker push your-docker-username/ai-interview-agent:0.1

4. Create secret set
cp env.example .env
# Edit .env with your API keys
pcc secrets set ai-interview-agent-secrets --file .env

4. Deploy to Pipecat Cloud
pcc deploy ai-interview-agent your-docker-username/ai-interview-agent:0.1 --secrets ai-interview-agent-secrets

5. Start agent session
pcc agent start ai-interview-agent --use-daily

Notes
Idle instances are terminated after 5 minutes (scale-to-zero)

Scale to keep warm instances:

pcc deploy ai-interview-agent your-docker-username/ai-interview-agent:0.1 --min-instances 1
pcc agent status ai-interview-agent
Keep .env and API keys secret. Do not commit them.

Documentation & Support
Pipecat Cloud Docs

Pipecat Community Discord

---
