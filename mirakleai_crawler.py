# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import pytz

# 환경 변수 로드
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

BASE_URL = 'https://www.mk.co.kr/mirakleai'
URL = BASE_URL  # 메인 페이지 기준

def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    cutoff = now - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0 (...) Chrome/115.0 Safari/537.36",
        "Accept-Language": "ko,en-US;q=0.7,en;q=0.3",
        "Referer": BASE_URL
    }
    session = requests.Session()
    session.headers.update(headers)
    session.get(BASE_URL, timeout=10)

    resp = session.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    articles = []
    # 선택자 예시: .list-area .article-unit (실제 구조 확인 필요)
    for li in soup.select('.list-area .article-unit')[:20]:
        a = li.select_one('a')
        date_tag = li.select_one('.date')  # 예시
        if not a or not date_tag: continue
        link = BASE_URL + a['href']
        title = a.get_text(strip=True)
        date_str = date_tag.get_text(strip=True)
        dt = tz.localize(datetime.strptime(f"{now.year}-{date_str}", '%Y-%m-%d %H:%M'))
        if dt < cutoff: continue

        summary = li.select_one('.desc').get_text(strip=True) if li.select_one('.desc') else ''
        articles.append({'title': title, 'link': link, 'summary': summary, 'date': dt.strftime('%Y-%m-%d %H:%M')})

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

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
    print("Email sent.")

if __name__ == '__main__':
    arts = crawl_mirakleai()
    send_email(arts)
