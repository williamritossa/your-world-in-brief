import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import openai
import tiktoken
from secrets import api_key, username, password

openai.api_key = api_key


def login_to_economist(username, password):
    login_url = "https://myaccount.economist.com/s/login"
    payload = {"username": username, "password": password}
    session = requests.Session()
    session.post(login_url, data=payload)
    return session


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def get_previous_wdbs():
    if os.path.exists("previous_dbs.txt"):
        with open("previous_dbs.txt", "r") as f:
            previous_wdbs = f.read().splitlines()
    else:
        previous_wdbs = []
    return previous_wdbs


def save_url_to_previous_wdbs(url):
    with open("previous_dbs.txt", "a") as f:
        f.write(url + "\n")


def scrape_homepage(session, homepage_url) -> BeautifulSoup:
    response = session.get(homepage_url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup


def get_articles(soup) -> dict:
    # Extract article URLs and titles
    articles = {}
    # current_time = datetime.now()
    previous_wdbs = get_previous_wdbs()

    for a in soup.find_all("a", attrs={"data-analytics": True}):
        url = homepage_url + a["href"]
        title = a.text

        # Check if URL is already in previous_dbs.txt
        if url in previous_wdbs:
            print(f"{url} is already in previous_dbs.txt, skipping...")
            continue
        else:
            # Add URL to previous_dbs.txt
            with open("previous_dbs.txt", "a") as f:
                f.write(url + "\n")

        # Fetch the article content
        article_response = session.get(url)
        article_soup = BeautifulSoup(article_response.text, "html.parser")

        try:
            article_datetime_str = article_soup.find("time", class_="css-j5ehde e1fl1tsy0")["datetime"]
            article_datetime = datetime.strptime(article_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        except:
            article_datetime = None

        print(title, article_datetime)

        try:
            article_text = article_soup.find("div", class_="css-13gy2f5 e1prll3w0").text
        except:
            article_text = None

        if article_datetime is not None and article_text is not None:  # if current_time - article_datetime < timedelta(hours=48):
            # Save to dictionary
            articles[url] = {
                "title": title,
                "date": article_datetime,
                "article_text": article_text,
                "source": "The Economist"
            }
            print(f"    • Added {title} to dictionary")

    return articles


def summarise_article(title, text):
    messages = [
        {"role": "system",
         "content": "You are an assistant to the President who helps prepare the President's Daily Priefing (PDB), a daily summary of articles published in The Economist. The reading level should be aimed at an educated audience."},
        {"role": "user",
         "content": f"Summarise the following article in three sentences. Include what is about, what the main points are, and what the conclusion is. The goal is to provide a summary that is accurate and concise and helps the reader decide if they want to read the full article.\n\nTitle: {title}\n\nArticle body: {text}\n\n\n\n\n\nOnly output the summary. Do not output the title."},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=250,
    )

    summary = response['choices'][0]['message']['content']
    return summary


# Function to generate the HTML page
def generate_html_page(articles, logo_image="economist_logo.png"):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Daily Briefing</title>
        <style>
            @media (prefers-color-scheme: dark) {{
                /* Styles for dark mode */
                body {{
                    background-color: black;
                    color: white;
                }}
                .date {{
                    color: Silver;
                }}
            }}
            @media (prefers-color-scheme: light) {{
                /* Styles for light mode */
                body {{
                    background-color: white;
                    color: black;
                }}
                .date {{
                    color: DimGray;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px;
            }}
            h1 {{
                font-size: 28px;
            }}
            h2 {{
                font-size: 22px;
                display: inline;
            }}
            p {{
                font-size: 18px;
                margin-top: 15px;
                margin-bottom: 5px;
            }}
            a {{
                color: #E3120B;
                text-decoration: none;
            }}
            .date {{
                font-size: 18px;
                font-weight: normal;
                display: block;
            }}
            .article {{
                display: flex;
                flex-wrap: wrap;
                align-items: flex-start;
                margin-bottom: 40px;
            }}
            .header {{
                flex-grow: 1;
            }}
            .logo {{
                height: 50px;
                width: auto;
                margin-right: 20px;
            }}
            .title-date {{
                margin-top: 2px;
            }}
        </style>
    </head>
    <body>
        <h1>Your world in brief</h1>
        {articles_html}
    </body>
    </html>
    """

    article_template = """
    <div class="article">
        <img class="logo" src="{logo_image}" alt="Source logo" />
        <div class="header">
            <div class="title-date">
                <h2>{title}</h2>
                <span class="date">{date}</span>
            </div>
        </div>
        <p>{summary}</p>
        <a href="{url}" target="_blank">Read more</a>
        </div>
    </div>
    """

    articles_html = ""

    for url, article in articles.items():
        title = article["title"]
        date = article["date"]
        summary = article["summary"]
        source = article["source"]

        logo_path = "logos/"
        if source == "The Economist":
            logo_path += "the_economist.png"

        formatted_date = date.strftime("%d %B %Y")
        articles_html += article_template.format(title=title, summary=summary, url=url, logo_image=logo_path, date=formatted_date)

    return html_template.format(articles_html=articles_html)


def summarise_section(text):
    messages = [
        {"role": "system",
         "content": "You are an article summariser. Your goal is to reduce the text so it is about half the length."},
        {"role": "user",
         "content": f"Summarise the following article so it is half the length. Make sure to include detail.\n\nArticle body: {text}\n\n\n\n\n\nOnly output the summary."},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=1000,
    )

    summary = response['choices'][0]['message']['content']
    return summary


def recursive_summarize(text_ChatML, max_tokens=3500):
    num_tokens = num_tokens_from_messages(text_ChatML)
    text = text_ChatML[-1]["content"]

    if num_tokens <= max_tokens:
        return text

    # Split the text into two halves
    split_index = len(text) // 2
    first_half = text[:split_index]
    second_half = text[split_index:]

    # Summarize each half
    first_summary = summarise_section(first_half)
    second_summary = summarise_section(second_half)

    # Combine the summaries and check if the result is within the token limit
    combined_summary = first_summary + "\n\n" + second_summary
    messages = [{"role": "user", "content": combined_summary}]
    return recursive_summarize(messages, max_tokens)


if __name__ == "__main__":
    session = login_to_economist(username, password)

    homepage_url = "https://www.economist.com"
    soup = scrape_homepage(session, homepage_url)
    articles = get_articles(soup)

    for url, article in articles.items():
        title = article["title"]
        text = article["article_text"]

        # Check article isn't too many tokens
        text = [{"role": "user", "content": text}]
        num_tokens = num_tokens_from_messages(text)
        if num_tokens > 3500:
            # Run code to split and summarize
            text = recursive_summarize(text)

        try:
            summary = summarise_article(title, text)
        except Exception as e:
            print(f"Error summarising {text}")
            print(e)
            summary = "Error summarising article."

        articles[url]["summary"] = summary

    #print(articles)

    # Save the HTML page to a file
    with open("your_world_in_brief.html", "w") as file:
        html_page = generate_html_page(articles)
        file.write(html_page)