# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

BASE_URL = 'https://www.mk.co.kr/mirakleai'
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')


def crawl_mirakleai():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    cutoff = now - timedelta(days=1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Referer": BASE_URL,
        "Accept-Language": "ko-KR,ko;q=0.9"
    }

    session = requests.Session()
    session.headers.update(headers)
    session.get(BASE_URL, timeout=10)
    resp = session.get(BASE_URL, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    article_blocks = soup.select('ul.latest_news_list > li.news_node')

    articles = []

    for li in article_blocks:
        a_tag = li.select_one('a.news_item')
        if not a_tag:
            continue

        link = a_tag['href']
        if not link.startswith("http"):
            link = 'https://www.mk.co.kr' + link

        title = li.select_one('.txt_area .tit').get_text(strip=True)
        summary = li.select_one('.txt_area .desc').get_text(strip=True) if li.select_one('.desc') else ''

        try:
            date_parts = li.select('div.time_area span')
            if len(date_parts) == 2:
                date_str = f"{date_parts[1].text.strip()}-{date_parts[0].text.strip()}"
                dt = tz.localize(datetime.strptime(date_str, "%Y-%m.%d"))
            else:
                continue
        except Exception as e:
            print(f"[오류] 날짜 파싱 실패: {e}")
            continue

        if dt >= cutoff:
            articles.append({
                'title': title,
                'summary': summary,
                'link': link,
                'date': dt.strftime('%Y-%m-%d %H:%M')
            })

    return articles


def send_email(articles):
    if not articles:
        print("No new articles today.")
        return

    tz = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(tz).strftime('%Y년 %m월 %d일')

    html = f"""<html>
    <head>
    <style>
    body {{ font-family: sans-serif; }}
    h1 {{ font-size: 20px; }}
    .article {{ border-bottom: 1px solid #ccc; padding-bottom: 15px; margin-bottom: 15px; }}
    h2 a {{ color: #0000cc; text-decoration: none; }}
    h2 a:hover {{ text-decoration: underline; }}
    p {{ color: #333; }}
    small {{ color: #999; }}
    </style>
    </head>
    <body>
    <h1>[{today_str}] 신규 미라클AI 기사</h1>
    """

    for a in articles:
        html += f"""
        <div class="article">
            <h2><a href="{a['link']}">{a['title']}</a></h2>
            <p>{a['summary']}</p>
            <small>{a['date']}</small>
        </div>
        """

    html += "</body></html>"

    print("--- 이메일 본문 미리보기 ---")
    print(html)
    print("--------------------------")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{today_str}] 미라클AI 신규 기사"
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html', 'utf-8'))

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
