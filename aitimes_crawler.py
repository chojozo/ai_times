# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import pytz

# --- 환경 변수 로드 ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
URL = 'https://www.aitimes.com/news/articleList.html?view_type=sm'

def crawl_aitimes():
    """AITimes 기사 목록을 크롤링하고 디버깅 정보를 출력합니다."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko,en-US;q=0.7,en;q=0.3",
            "Connection": "keep-alive",
            "Referer": "https://www.aitimes.com/",
            "Upgrade-Insecure-Requests": "1"
        }

        session = requests.Session()
        session.headers.update(headers)

        # 첫 페이지 요청 → 쿠키 및 세션 정보 확보
        session.get("https://www.aitimes.com/", timeout=10)

        articles = []
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        one_day_ago = now - timedelta(days=1)

        for page in range(1, 3):  # ✅ 1~2 페이지 순회
            response = session.get(URL, params={'view_type': 'sm', 'page': page}, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            li_elements = soup.select('ul.altlist-webzine > li.altlist-webzine-item')

            print(f"\n== {page}페이지: {len(li_elements)}개의 기사 블록 탐색 ==")

            for i, li_item in enumerate(li_elements):
                print(f"\n[li 블록 #{i+1} 분석 시작]")

                date_tag = li_item.select_one('div.altlist-info-item:last-child')
                if not date_tag:
                    print("  -> 날짜 태그를 찾지 못했습니다. (건너뜀)")
                    continue

                date_str = date_tag.get_text(strip=True)
                print(f"  -> 추출된 날짜 문자열: '{date_str}'")

                try:
                    article_date_naive = datetime.strptime(f"{now.year}-{date_str}", '%Y-%m-%d %H:%M')
                    article_date = kst.localize(article_date_naive)

                    if article_date > now and (now.month == 1 and article_date.month == 12):
                        article_date = article_date.replace(year=now.year - 1)

                    print(f"  -> 파싱된 날짜 객체: {article_date}")

                    if article_date > one_day_ago:
                        print("  -> 결과: [포함] 24시간 이내의 새 기사입니다.")
                        title_tag = li_item.select_one('h2.altlist-subject a')
                        lead_tag = li_item.select_one('p.altlist-summary')

                        if title_tag and lead_tag:
                            link_raw = title_tag['href']
                            link = link_raw if link_raw.startswith('http') else 'https://www.aitimes.com' + link_raw

                            articles.append({
                                'title': title_tag.get_text(strip=True),
                                'link': link,
                                'summary': lead_tag.get_text(strip=True),
                                'date': article_date.strftime('%Y-%m-%d %H:%M')
                            })
                    else:
                        print("  -> 결과: [제외] 오래된 기사입니다.")
                except ValueError:
                    print(f"  -> 날짜 파싱 실패: '{date_str}'")
                    continue

        print("\n--- 디버깅 종료 ---")
        articles.sort(key=lambda x: x['date'], reverse=True)
        print(f"최종적으로 {len(articles)}개의 새 기사를 이메일로 보냅니다.")
        return articles

    except Exception as e:
        print(f"크롤링 중 심각한 오류 발생: {e}")
        return None


def send_email(articles):
    if not articles:
        print("No new articles to send.")
        return

    kst = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(kst).strftime('%Y년 %m월 %d일')

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; }}
            .article {{
                border-bottom: 1px solid #eee;
                padding-bottom: 15px;
                margin-bottom: 15px;
            }}
            .article:last-child {{
                border-bottom: none;
            }}
            h2 a {{ color: #0066cc; text-decoration: none; }}
            h2 a:hover {{ text-decoration: underline; }}
            p {{ color: #333; }}
            small {{ color: #888; }}
        </style>
    </head>
    <body>
        <h1>[{today_str}] AITimes 신규 기사</h1>
    """

    for article in articles:
        html_body += f"""
        <div class="article">
            <h2><a href="{article['link']}">{article['title']}</a></h2>
            <p>{article['summary']}</p>
            <small>발행일: {article['date']}</small>
        </div>
        """

    html_body += """
    </body>
    </html>
    """

    print("--- 이메일 본문 미리보기 ---")
    print(html_body)
    print("--------------------------")

    if not all([SMTP_USER, SMTP_PASSWORD, RECIPIENT_EMAIL]):
        print("Email environment variables are not set. Skipping email sending.")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{today_str}] AITimes 신규 기사 알림"
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    crawled_articles = crawl_aitimes()
    if crawled_articles is not None:
        send_email(crawled_articles)
