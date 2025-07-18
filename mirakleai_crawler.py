# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def crawl_mirakleai():
    BASE_URL = 'https://www.mk.co.kr/mirakleai/'
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    }

    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    cutoff = now - timedelta(days=1)

    session = requests.Session()
    session.headers.update(HEADERS)

    res = session.get(BASE_URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')

    articles = []
    items = soup.select("ul#list_area li.news_node")

    for li in items:
        try:
            a_tag = li.select_one("a")
            if not a_tag:
                continue

            href = a_tag.get("href")
            title_tag = li.select_one(".txt_area .tit")
            summary_tag = li.select_one(".txt_area .desc")
            date_tag = li.select_one(".time_area span")

            if not title_tag or not date_tag:
                continue

            title = title_tag.get_text(strip=True)
            summary = summary_tag.get_text(strip=True) if summary_tag else ''
            raw_date = date_tag.get_text(strip=True).replace('.', '-')
            date_full = f"{now.year}-{raw_date}"

            try:
                article_date = datetime.strptime(date_full, "%Y-%m-%d")
            except ValueError:
                continue

            article_date = tz.localize(article_date)

            if article_date.date() >= cutoff.date():
                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": href if href.startswith("http") else f"https://www.mk.co.kr{href}",
                    "date": article_date.strftime("%Y-%m-%d")
                })
        except Exception as e:
            print("Error parsing article:", e)
            continue

    return articles

def send_email(articles):
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

    if not all([SMTP_USER, SMTP_PASSWORD, RECIPIENT_EMAIL]):
        print("❌ Missing email credentials.")
        return

    if not articles:
        print("No new articles today.")
        return

    tz = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(tz).strftime("%Y년 %m월 %d일")

    html = f"<html><body><h1>[{today_str}] 신규 미라클AI 기사</h1>"
    for a in articles:
        html += f'<div style="margin-bottom:25px;">'
        html += f'<h2><a href="{a["link"]}">{a["title"]}</a></h2>'
        html += f'<p>{a["summary"]}</p>'
        html += f'<small>발행일: {a["date"]}</small>'
        html += "</div>"
    html += "</body></html>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{today_str}] 미라클AI 신규 기사"
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent.")
    except Exception as e:
        print("❌ Email send error:", e)

if __name__ == "__main__":
    articles = crawl_mirakleai()
    send_email(articles)
