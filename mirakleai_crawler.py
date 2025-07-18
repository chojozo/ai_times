# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 이메일 정보 (환경변수에서 가져옴)
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

BASE_URL = 'https://www.mk.co.kr/mirakleai'

def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    today = now.date()
    yesterday = today - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko,en-US;q=0.7,en;q=0.3",
        "Referer": BASE_URL
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        resp = session.get(BASE_URL, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ 페이지 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []

    for li in soup.select('.latest_news_list > li.news_node')[:20]:
        a_tag = li.select_one('a')
        title_tag = li.select_one('.txt_area .tit')
        summary_tag = li.select_one('.txt_area .desc')
        date_tag = li.select_one('.time_area span')

        if not all([a_tag, title_tag, date_tag]):
            continue

        title = title_tag.get_text(strip=True)
        link = a_tag['href'] if a_tag['href'].startswith('http') else BASE_URL + a_tag['href']
        summary = summary_tag.get_text(strip=True) if summary_tag else ''
        date_str = date_tag.get_text(strip=True)  # 예: "07.18"

        try:
            month, day = map(int, date_str.split('.'))
            parsed_date = datetime(now.year, month, day).date()
        except Exception as e:
            print(f"[오류] 날짜 파싱 실패: {date_str}, 오류: {e}")
            continue

        if parsed_date not in (today, yesterday):
            continue

        articles.append({
            'title': title,
            'link': link,
            'summary': summary,
            'date': parsed_date.strftime('%Y-%m-%d')
        })

    return articles

def send_email(articles):
    if not articles:
        print("No new articles today.")
        return

    tz = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(tz).strftime('%Y년 %m월 %d일')

    html = f"<html><body><h1>[{today_str}] 신규 미라클AI 기사</h1>"
    for a in articles:
        html += f'<h2><a href="{a["link"]}">{a["title"]}</a></h2>'
        html += f'<p>{a["summary"]}</p><small>{a["date"]}</small><hr>'
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
