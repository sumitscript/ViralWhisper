# 🐦 ViralWhisper — Let Your Project Speak!

**AI-powered social engagement tool for solo builders and indie hackers.**

---

## 📌 Tagline

> *"AI’s gentle touch, engaging mind — appreciating voices, promoting dreams."*

---

##  🚀 About the Project

**ViralWhisper** is an AI-powered assistant built for indie devs, solo founders, and product builders who are deeply involved in development but don’t have time to engage on platforms like **Twitter/X** and **Reddit**.

It automatically:
- Finds relevant posts in your niche
- Understands the context using local LLMs (Ollama, etc.)
- Generates meaningful replies
- Adds a subtle promotional line about your product or upcoming launch

With **ViralWhisper**, your presence grows — even when you're heads-down building 🚧

---

## 🧩 Problem It Solves

Building in public is powerful, but:

- It's time-consuming to engage daily on Reddit/X
- Context-aware replies are hard to automate
- Promoting your product can feel spammy

**ViralWhisper** solves all of this by:
- Using keywords and niches to track relevant content
- Parsing posts using AI (locally run LLMs like `DeepSeek-r1`, `mistral`)
- Replying with human-like, value-adding messages
- Appending soft promotional CTAs based on your config

All while you **focus on shipping** 🚢

---

## ⚙️ How It Works

1. **Input**: You define your:
   - Keywords (e.g., `AI`, `startup`, `web3`)
   - Product description, promo lines, CTA

2. **Fetch**: Bot scrapes relevant posts from **Reddit** and **Twitter (coming soon)**

3. **Process**: Uses **Ollama LLM** locally to understand post context

4. **Generate**: Crafts a thoughtful reply + soft plug for your product

5. **Engage**: Posts response via Reddit API (Twitter support coming)

---

## 🧪 Features

- ✅ Reddit integration with keyword-based filtering
- ✅ Local AI response generation (Ollama, no OpenAI keys needed)
- ✅ Auto-logging of interactions
- ✅ Configurable promotional CTA
- 🚧 Twitter/X support (Coming Soon)
- 🚧 Frontend for easier config (Planned)

---

## 🔧 Tech Stack

`Python`, `Reddit API (PRAW)`, `Ollama (LLMs)`, `CSV`, `ConfigParser`, `Logging`

---

## 🧱 Project Structure

```bash
reddit-bot/
├── reddit_promo_bot.py       # Main bot logic
├── config.ini                # Config: keywords, promo text, etc.
├── reddit_interactions.csv  # Logs for posts replied to
├── bot-1.py                  # Extra bot logic/testing
├── reddit_bot.log            # Logging
└── README.md
-----
