import requests
from bs4 import BeautifulSoup
from datetime import datetime
from secrets import username, password
import csv
from readability import Document


def login_to_economist(username, password):
    login_url = "https://myaccount.economist.com/s/login"
    payload = {"username": username, "password": password}
    session = requests.Session()
    session.post(login_url, data=payload)
    return session


def scrape_homepage(session, homepage_url) -> BeautifulSoup:
    response = session.get(homepage_url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup


def get_articles(soup, session, homepage_url) -> dict:
    # Extract article URLs and titles
    articles = {}
    # current_time = datetime.now()

    # Get URLs already in database
    with open("database/articles.csv", "r", newline="") as f:
        reader = csv.reader(f)
        existing_urls = {row[1] for row in reader}

    for a in soup.find_all("a", attrs={"data-analytics": True}):
        url = homepage_url + a["href"]

        # Strip query parameters from URL
        url = url.split("?")[0]

        # If the article is from an unwanted section, skip it
        if "podcast" in url:
            print(f"    ⏭ Skipping {url} (podcast)")
            continue
        elif "the-economist-reads" in url:
            print(f"    ⏭ Skipping {url} (book review)")
            continue

        title = a.text

        # Check if URL is already in database
        if url in existing_urls:
            print(f"    ⏭ Skipping {url} (already in database)")
            continue

        # Fetch the article content
        article_response = session.get(url)
        article_soup = BeautifulSoup(article_response.text, "html.parser")

        # Extract the article's publication date
        try:
            article_datetime_str = article_soup.find("time", class_="css-j5ehde e1fl1tsy0")["datetime"]
            article_datetime = datetime.strptime(article_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        except:
            article_datetime = None
            print(f"    ⏭ Skipping {url} (no date found)")
            continue

        print(f"    • Scraping '{title}' ({article_datetime}, {url})")

        # Get the article text/HTML for reader view
        html_content = article_response.text
        doc = Document(html_content)
        article_text = doc.summary()
        article_text = BeautifulSoup(article_text, "html.parser").get_text()  # Remove HTML tags from text

        if article_datetime is not None and article_text is not None:  # if current_time - article_datetime < timedelta(hours=48):
            # Save to dictionary
            articles[url] = {
                "title": title,
                "date": article_datetime,
                "article_text": article_text,
                "source": "The Economist"
            }

    return articles


def scrape_the_economist():
    session = login_to_economist(username, password)

    homepage_url = "https://www.economist.com"
    soup = scrape_homepage(session, homepage_url)
    articles = get_articles(soup, session, homepage_url)

    return articles
