# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import pytz
import re

# 환경 변수 로드
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

BASE_URL = 'https://www.mk.co.kr'
URL = 'https://www.mk.co.kr/mirakleai'

def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    cutoff = now - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0 Safari/537.36",
        "Accept-Language": "ko,en-US;q=0.7,en;q=0.3",
        "Referer": URL
    }

    session = requests.Session()
    session.headers.update(headers)
    session.get(BASE_URL, timeout=10)

    resp = session.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    articles = []

    for li in soup.select('ul.latest_news_list > li.news_node')[:20]:
        a = li.select_one('a')
        date_tag = li.select_one('.time_area span')

        if not a or not date_tag:
            continue

        link_raw = a['href']
        link = link_raw if link_raw.startswith('http') else BASE_URL + link_raw
        title = a.get_text(strip=True)
        date_str = date_tag.get_text(strip=True)

        # 날짜 추출 (07.18 처럼 보이는 부분만 파싱)
        match = re.search(r'(\d{2})\.(\d{2})', date_str)
        if not match:
            print(f"[오류] 날짜 추출 실패: {date_str}")
            continue

        month, day = map(int, match.groups())
        try:
            article_date = tz.localize(datetime(now.year, month, day))
        except ValueError as e:
            print(f"[오류] 날짜 파싱 실패: {date_str}, 오류: {e}")
            continue

        if article_date < cutoff:
            continue

        summary_tag = li.select_one('.desc')
        summary = summary_tag.get_text(strip=True) if summary_tag else ''

        articles.append({
            'title': title,
            'link': link,
            'summary': summary,
            'date': article_date.strftime('%Y-%m-%d %H:%M')
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
        html += f'<div><h2><a href="{a["link"]}">{a["title"]}</a></h2>'
        html += f'<p>{a["summary"]}</p><small>{a["date"]}</small></div><hr>'
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
        print(f"❌ Email send error: {e}")


if __name__ == '__main__':
    articles = crawl_mirakleai()
    send_email(articles)
