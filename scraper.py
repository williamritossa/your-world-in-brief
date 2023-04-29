import openai
import os
import secrets
import tiktoken
from helpers import preprocess_text
from money_stuff import scrape_money_stuff
from the_economist import scrape_the_economist
import ast
import uuid
from embeddings import Embeddings
import csv
import json
from datetime import date, timedelta, datetime

openai.api_key = os.environ.get("OPENAI_API_KEY")


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


def summarise_article(title, text, sentences) -> str:
    messages = [
        {"role": "system",
         "content": "You are part of a system that constructs the President's Daily Briefing. You help produce a summary of articles and offer your professional opinion, as an expert advisor. You output a Python dictionary."},
        {"role": "user",
         "content": f"Summarise the following article in {sentences} long and detailed sentences. "
                    f"Include what is about, what the main points are, and what the conclusion is. "
                    f"The goal is to provide a summary that is accurate and concise and helps the reader decide if "
                    f"they want to read the full article.\n\nThen, act as an expert advisor to the president. "
                    f"Provide 2-3 sentences which will serve as a note from an expert. Your goal is to add extra "
                    f"context, draw connections to historical events, policies, trends, etc.\n\n"
                    f"Title: {title}\nArticle body: {text}\n\n\n\n\n\nYour output takes the form of a Python "
                    'dictionary:\n\n{"summary": "your summary...", "advisor": "expert advisors comments..."}\n\nOnly output '
                    f"the Python dictionary. Stop words, such as 'a', 'an', 'the', and other common words that do not "
                    f"carry significant meaning, may have been removed from the original text. Remember, the president "
                    f"is an expert and it can be assumed they have a high degree of background knowledge on the topic."},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=500,
    )

    summary_string = response['choices'][0]['message']['content']
    result_dict = ast.literal_eval(summary_string)
    summary = result_dict['summary']
    advisor = result_dict['advisor']
    return summary, advisor


# Function to generate the HTML page
def generate_html_page(articles, styles_file="styles.css", scripts_file="scripts.js") -> str:
    with open(styles_file, "r") as f:
        styles = f.read()

    with open(scripts_file, "r") as f:
        scripts = f.read()

    html_template = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css">
        <title>Your Daily Briefing</title>
        <style>
            {styles}
        </style>
    </head>
    <body>
        <h1>Your world in brief</h1>
        {articles_html}
        
        <div class="chatbot-container">
            <button id="chatbot-button" class="btn btn-primary rounded-circle">
                <i class="bi bi-chat-dots-fill"></i>
            </button>
            <div id="chatbot-box" class="card d-none">
                <div class="card-body">


                    <div class="chat">
                        <div id="chatbot-messages" class="messages"></div>
                    </div>


                    <div id="chatbot-messages" class="mb-3"></div>
                    <div class="input-group chatbot-input-container">
                        <input type="text" id="chatbot-input" class="form-control" placeholder="Type your message...">
                        <div class="input-group-append">
                            <button id="chatbot-send" class="btn"><i class="bi bi-arrow-right-circle"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    <script>
        const OPENAI_API_KEY = "{openai_api_key}";
        const embeddingsData = {embeddings_data}; // in JSON format
        {scripts}
    </script>
    </html>
    """

    article_template = """
        <div class="article">
            <img class="logo fade-in fade-in-logo" src="{logo_url}" alt="Source logo" />
            <div class="header">
                <div class="title-date fade-in fade-in-title-date">
                    <a href="{url}" target="_blank"><h2>{title}</h2></a>
                    <span class="date">{date}</span>
                </div>
            </div>
            <p class="fade-in fade-in-summary">{summary}</p>
            <p class="fade-in fade-in-opinion"><span style="color: #E3120B;">Opinion:</span> {opinion}</p>
            </div>
        </div>
    """

    # Get list of categories from today's articles
    categories = {}
    for url, article in articles.items():
        category = article["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append({"url": url, **article})

    articles_html = ""

    for category, articles_in_category in categories.items():
        articles_html += f"""<div class='category fade-in fade-in-category'>
            <h2>{category}</h2>
        <hr>"""
        for article in articles_in_category:
            title = article["title"]
            date = article["date"]
            summary = article["summary"]
            source = article["source"]
            opinion = article["opinion"]
            url = article["url"]

            if source == "The Economist":
                logo_path = "https://www.economist.com/engassets/google-search-logo.f1ea908894.png"
            elif source == "Bloomberg":
                logo_path = "https://pbs.twimg.com/profile_images/1016326195221352450/KCcdUN0v_400x400.jpg"
            else:
                logo_path = "http://brentapac.com/wp-content/uploads/2017/03/transparent-square.png"

            formatted_date = date.strftime("%d %B %Y")
            articles_html += article_template.format(title=title, summary=summary, url=url, logo_url=logo_path, date=formatted_date, opinion=opinion)

    # Get embeddings data to save as JSON and use in JS
    embeddings_data = []
    with open("database/article_embeddings.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            embeddings_data.append(row)

    n_days = 1  # Set the number of days you want to filter
    article_added_dates = get_publication_dates()
    filtered_embeddings_data = filter_embeddings_by_days(embeddings_data, article_added_dates, n_days)

    return html_template.format(styles=styles, scripts=scripts, embeddings_data=filtered_embeddings_data, articles_html=articles_html, openai_api_key=os.environ.get("OPENAI_API_KEY"))


def get_publication_dates():
    """Returns a dictionary of article UUIDs and the date and time they were added to the database"""
    article_added_dates = {}
    with open("database/articles.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                uuid = row['UUID']
                date_added = datetime.strptime(row['date_added'], '%Y-%m-%d %H:%M:%S')  # Adjust the date format accordingly
                article_added_dates[uuid] = date_added
            except ValueError:
                print(f"Article UUID {uuid} has an invalid date: {row['date_added']}")
                pass

    return article_added_dates


def filter_embeddings_by_days(embeddings_data, article_added_dates, days):
    """Filters the embeddings data so that only articles saved within the last n days are included"""
    filtered_embeddings = []
    threshold_date = datetime.now() - timedelta(days=days)

    for embedding in embeddings_data:
        article_uuid = embedding['article_uuid']
        date_added = article_added_dates[article_uuid]

        try:
            if date_added >= threshold_date:
                filtered_embeddings.append(embedding)
        except KeyError:
            print(f"Article UUID {article_uuid} not found in article publication dates dictionary")
            pass

    return filtered_embeddings


def summarise_section(text):
    messages = [
        {"role": "system",
         "content": "You are an article summariser. Your goal is to reduce the text so it is about half the length."},
        {"role": "user",
         "content": f"Summarise the following article so it is half the length. Make sure to include detail.\n\nArticle body: {text}\n\n\n\n\n\nOnly output the summary. Stop words, such as 'a', 'an', 'the', and other common words that do not carry significant meaning, may have been removed from the original text."},
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


def categorise_article(text: str, allowed_categories: dict) -> str:
    topics = "\n".join(allowed_categories.keys())
    messages = [
        {"role": "system",
         "content": "You are a news article categoriser. Your output which category an article belongs to based on "
                    "the text of the article and a list of topics. You only output the topic exactly as it is written "
                    "in the list of topics."},
        {"role": "user", "content": f"Here are a list of topics:\n{topics}\n\n\n\nHere is the article: {text}\n\n\n\n\n\nOutput the category the article belongs to"},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=10,
    )

    category = response['choices'][0]['message']['content']
    return category

def preprocessing_for_gpt(article):
    title = article["title"]
    text = article["article_text"]

    # Reduce token length of text
    text = preprocess_text(text, stem=False, remove_stopwords=True, keep_newlines=True)

    # Remove apostrophes from the text to avoid errors with dictionary syntax
    text = text.replace("'", "\'")
    text = text.replace('"', '\"')

    # Check article isn't too many tokens
    text = [{"role": "user", "content": text}]
    num_tokens = num_tokens_from_messages(text)
    if num_tokens > 3500:
        # Run code to split and summarize
        text = recursive_summarize(text)
        text = [{"role": "user", "content": text}]

    if article["source"] == "Bloomberg":
        sentences = 5
    else:
        sentences = 3

    max_attempts = 5
    success = False

    for attempt in range(max_attempts):
        try:
            text = text[0]["content"]
            summary, opinion = summarise_article(title, text, sentences)
            success = True
            break  # If the call is successful, exit the loop
        except Exception as e:
            print(f"Error summarising {text[:50]} (attempt {attempt + 1}): {e}")

    if not success:
        summary = "Error summarising article."
        opinion = "Error generating opinion."

    # Categorise the article
    max_attempts = 5
    success = False
    allowed_categories = {
        "Business and Economics": "covering topics related to companies, markets, investments, and finance.",
        "Politics and Government": "covering topics related to national and international politics, government policy, and diplomacy.",
        "Technology and Innovation": "covering topics related to new and emerging technologies, digital culture, and scientific research.",
        "Environment and Sustainability": "covering topics related to climate change, energy, conservation, and the natural world.",
        "Culture and Society": "covering topics related to art, literature, music, film, social trends, and identity.",
        "Science and Health": "covering topics related to scientific research, health policy, medicine, and public health.",
        "Education and Learning": "covering topics related to education policy, pedagogy, and innovations in teaching and learning.",
        "International Relations and Diplomacy": "covering topics related to global politics, international organizations, and diplomacy.",
        "Sports and Entertainment": "covering topics related to sports, entertainment, and popular culture.",
        "History and Philosophy": "covering topics related to history, philosophy, and ideas."
    }

    for attempt in range(max_attempts):
        try:
            category = categorise_article(text, allowed_categories)
            # Check category is in list of allowed categories, if not, set success to False
            if category not in allowed_categories:
                success = False
                raise Exception(f"Category {category} not in list of allowed categories.")
            success = True
            break  # If the call is successful, exit the loop
        except Exception as e:
            print(f"Error categorising {text[:50]} (attempt {attempt + 1}): {e}")

    if not success:
        category = "Other"

    return summary, opinion, category


if __name__ == "__main__":
    articles = {}

    print("Scraping articles")
    # Get The Economist articles
    try:
        print("  • Scraping The Economist...")
        economist_articles = scrape_the_economist()
        articles.update(economist_articles)
    except Exception as e:
        print(f"  ✗ Error scraping The Economist: {e}")

    # Get Money Stuff articles
    try:
        print("  • Scraping Money Stuff by Matt Levine...")
        latest_newsletter_text = scrape_money_stuff()
        articles.update(latest_newsletter_text)
    except Exception as e:
        print(f"  ✗ Error scraping Money Stuff: {e}")

    print()
    print("Saving articles to database")
    # Open the CSV file in read mode to check for duplicates
    with open("database/articles.csv", "r", newline="") as f:
        reader = csv.reader(f)
        existing_urls = {row[1] for row in reader}

    # Add new articles to the database
    new_articles = {}
    with open("database/articles.csv", "a", newline="") as f:
        writer = csv.writer(f)

        # Loop through the articles and write each one to a new row in the CSV
        for url, article_data in articles.items():
            print(f"  • {url}:")
            if url in existing_urls:
                print(f"    ⏭ Skipping as it already exists in the CSV")
                continue

            article_uuid = uuid.uuid4()
            articles[url]["uuid"] = article_uuid
            article_title = article_data["title"]
            article_date = article_data["date"].strftime("%Y-%m-%d %H:%M:%S")
            article_date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            article_text = article_data["article_text"]
            article_source = article_data["source"]

            print(f"    • Generating summary and opinion")
            article_summary, article_opinion, article_category = preprocessing_for_gpt(article_data)

            articles[url]["summary"] = article_summary
            articles[url]["opinion"] = article_opinion
            articles[url]["category"] = article_category

            writer.writerow([article_uuid, url, article_title, article_date, article_date_added, article_category, article_source, article_text, article_summary, article_opinion])
            new_articles[url] = article_data
            print(f"    ✓ Added to the CSV with UUID {article_uuid}")

    print()
    print("Generating semantic embeddings")

    embedder = Embeddings()

    # Create and open the embeddings CSV file
    with open("database/article_embeddings.csv", "a", newline="") as f:
        writer_article = csv.writer(f)

        # Write the header row if the file is empty
        if f.tell() == 0:
            writer_article.writerow(["article_uuid", "embedding_uuid", "text", "embedding"])

        # Iterate through the new_articles dictionary
        for url, article_data in new_articles.items():
            article_uuid = article_data["uuid"]
            article_text = article_data["article_text"]

            # Split the article_text into chunks
            chunks = embedder.create_chunks(article_text, words_per_chunk=100, step=10)

            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                embeddings_uuid = f"{article_uuid}_embedding-{i}"
                chunk_text = " ".join(chunk)
                chunk_embedding = embedder.len_safe_get_embedding(chunk_text, average=True)

                # Save the embeddings in the CSV file
                writer_article.writerow([article_uuid, embeddings_uuid, chunk_text, chunk_embedding])

            # Embed the summary
            summary = article_data["summary"]
            summary_embedding = embedder.len_safe_get_embedding(summary, average=True)
            summary_uuid = f"{article_uuid}_embedding-summary"

            # Open the summary embeddings CSV file in append mode
            with open("database/summary_embeddings.csv", "a", newline="") as s:
                writer_summary = csv.writer(s)

                # Write the header row if the file is empty
                if s.tell() == 0:
                    writer_summary.writerow(["article_uuid", "embedding_uuid", "text", "embedding"])

                # Save the summary embeddings in the CSV file
                writer_summary.writerow([article_uuid, summary_uuid, summary, summary_embedding])

            print(f"  ✓ Generated embeddings for {url} and saved to the CSV")

    print()
    print("Generating HTML page")
    # Save the HTML page to a file
    today = date.today().strftime("%Y-%m-%d")
    with open(f"briefings/your_world_in_brief_{today}.html", "w") as file:
        html_page = generate_html_page(new_articles)
        file.write(html_page)
