# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, date
import pytz
import os

# 환경 변수
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

BASE_URL = 'https://www.mk.co.kr/mirakleai'
URL = BASE_URL

def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Referer": BASE_URL,
    }

    session = requests.Session()
    session.headers.update(headers)
    resp = session.get(URL, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []

    for li in soup.select('.latest_news_wrap li.news_node'):
        a = li.select_one('a.news_item')
        title_tag = li.select_one('.news_ttl')
        desc_tag = li.select_one('.news_desc')
        date_tag = li.select_one('.time_area span')

        if not (a and title_tag and date_tag):
            continue

        # 날짜 파싱: ['07.18', '2025']
        parts = list(date_tag.stripped_strings)
        if len(parts) != 2:
            continue

        month_day, year = parts
        try:
            date_str = f"{year}-{month_day.replace('.', '-')}"
            pub_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            print(f"[날짜 파싱 실패]: {date_str}, 오류: {e}")
            continue

        if pub_date not in [today, yesterday]:
            continue

        link = a['href'] if a['href'].startswith('http') else 'https://www.mk.co.kr' + a['href']
        title = title_tag.get_text(strip=True)
        summary = desc_tag.get_text(strip=True) if desc_tag else ""

        articles.append({
            'title': title,
            'link': link,
            'summary': summary,
            'date': str(pub_date)
        })

    return articles

def send_email(articles):
    if not articles:
        print("No new articles today.")
        return

    tz = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(tz).strftime('%Y년 %m월 %d일')

    html = f"<html><body><h2>[{today_str}] 신규 미라클AI 기사</h2>"
    for a in articles:
        html += f'<h3><a href="{a["link"]}">{a["title"]}</a></h3>'
        html += f'<p>{a["summary"]}</p><p><small>{a["date"]}</small></p><hr>'
    html += "</body></html>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{today_str}] 미라클AI 신규 기사"
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
        print("✅ Email sent.")
    except Exception as e:
        print("❌ Email send error:", e)

if __name__ == '__main__':
    arts = crawl_mirakleai()
    send_email(arts)
