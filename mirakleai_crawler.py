# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import pytz

# 환경 변수 (GitHub Actions 또는 로컬에서 설정 필요)
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

BASE_URL = 'https://www.mk.co.kr'
URL = 'https://www.mk.co.kr/mirakleai'

def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    today = now.date()
    yesterday = today - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": URL,
        "Connection": "keep-alive"
    }

    session = requests.Session()
    session.headers.update(headers)
    session.get(URL, timeout=10)  # 사전 요청

    resp = session.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    articles = []
    news_list = soup.select('.latest_news_list li.news_node')

    for li in news_list:
        a = li.select_one('a')
        title_tag = li.select_one('.txt_area .tit')
        summary_tag = li.select_one('.txt_area .desc')
        date_tag = li.select_one('.time_area span')

        if not (a and title_tag and date_tag):
            continue

        title = title_tag.get_text(strip=True)
        summary = summary_tag.get_text(strip=True) if summary_tag else ''
        link = a['href'] if a['href'].startswith('http') else BASE_URL + a['href']
        date_str = date_tag.get_text(strip=True)

        try:
            parsed_date = datetime.strptime(f"{now.year}.{date_str}", '%Y.%m.%d').date()
        except Exception as e:
            print(f"[오류] 날짜 파싱 실패: {date_str}, 오류: {e}")
            continue

        if parsed_date not in (today, yesterday):
            continue

        articles.append({
            'title': title,
            'summary': summary,
            'link': link,
            'date': parsed_date.strftime('%Y-%m-%d')
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
        html += f"<h3><a href='{a['link']}'>{a['title']}</a></h3>"
        html += f"<p>{a['summary']}</p>"
        html += f"<small>{a['date']}</small><hr>"
    html += "</body></html>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{today_str}] 미라클AI 신규 기사"
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print("❌ Email send error:", e)

if __name__ == '__main__':
    articles = crawl_mirakleai()
    send_email(articles)
