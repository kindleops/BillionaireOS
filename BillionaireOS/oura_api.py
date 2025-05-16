import os
import json
import time
import requests
import datetime
import openai
from flask import Flask, request

# ✅ Load Environment Variables
OURA_ACCESS_TOKEN = os.getenv("OURA_ACCESS_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Initialize OpenAI Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ Flask App for Real-Time Commands
app = Flask(__name__)

# ✅ Fetch Oura Data

def fetch_oura_data(endpoint, start_date, end_date):
    url = f"https://api.ouraring.com/v2/usercollection/{endpoint}?start_date={start_date}&end_date={end_date}"
    headers = {"Authorization": f"Bearer {OURA_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

# ✅ Collect Metrics

def get_oura_metrics():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sleep_data = fetch_oura_data("sleep", today, today)
    readiness_data = fetch_oura_data("readiness", today, today)
    activity_data = fetch_oura_data("daily_activity", today, today)
    if not sleep_data or not readiness_data or not activity_data:
        return None

    sleep = sleep_data["data"][0] if sleep_data["data"] else {}
    readiness = readiness_data["data"][0] if readiness_data["data"] else {}
    activity = activity_data["data"][0] if activity_data["data"] else {}

    metrics = {
        "Date": datetime.datetime.now().date().isoformat(),
        "Total Sleep (min)": sleep.get("total_sleep_duration", 0) // 60,
        "Sleep Score": readiness.get("score"),
        "REM Sleep (min)": sleep.get("rem_sleep_duration", 0) // 60,
        "Deep Sleep (min)": sleep.get("deep_sleep_duration", 0) // 60,
        "Light Sleep (min)": sleep.get("light_sleep_duration", 0) // 60,
        "Sleep Efficiency (%)": sleep.get("efficiency"),
        "Sleep Latency (min)": sleep.get("latency", 0) // 60,
        "Restfulness Score": sleep.get("restless_periods"),
        "Body Temperature (°C)": readiness.get("temperature_deviation"),
        "Resting Heart Rate (bpm)": readiness.get("resting_heart_rate"),
        "Respiratory Rate (rom)": sleep.get("average_breath"),
        "HRV (ms)": readiness.get("average_hrv"),
        "Readiness Score": readiness.get("score"),
        "Activity Score": activity.get("score"),
        "Total Steps": activity.get("steps"),
        "Active Calories Burned": activity.get("active_calories"),
        "Stressed Time (min)": activity.get("stress_duration", 0) // 60,
        "Restored Time (min)": activity.get("restoration_time", 0) // 60
    }
    return metrics

# ✅ AI Insight Generator

def generate_ai_insights(metrics):
    prompt = f"""
    You are a 24/7 AI optimization system. Analyze the following Oura data and optimize the user's day in real time, including sleep recovery, training suggestions, task prioritization, and habit scheduling.

    DATA:
    {json.dumps(metrics, indent=2)}

    Respond with a clear breakdown of:
    1. Morning Analysis
    2. Midday Optimization
    3. Evening Routine
    4. Key Adjustments & Suggestions
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ✅ Notion Uploader

def log_to_notion(metrics, insights):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Date": {"date": {"start": metrics["Date"]}},
            **{k: {"number": v} for k, v in metrics.items() if isinstance(v, (int, float))},
            "AI Performance Insights": {"rich_text": [{"text": {"content": insights}}]}
        }
    }
    return requests.post(url, headers=headers, json=payload).json()

# ✅ Telegram Messenger

def notify_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    return requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}).json()

# ✅ Master Function

def main():
    metrics = get_oura_metrics()
    if not metrics:
        print("❌ Oura data unavailable.")
        notify_telegram("⚠️ Oura data missing. Cannot optimize today.")
        return

    insights = generate_ai_insights(metrics)
    notion_response = log_to_notion(metrics, insights)
    notify_telegram(f"✅ AI Optimization Logged for {metrics['Date']}\n\n{insights}")
    print("✅ AI Optimization System Logged and Running")

# ✅ Loop Forever
if __name__ == "__main__":
    while True:
        main()
        time.sleep(43200)  # Run every 12 hours
