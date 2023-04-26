import openai
import tiktoken
from secrets import api_key
from helpers import preprocess_text
from money_stuff import scrape_money_stuff
from the_economist import scrape_the_economist
import ast
import uuid
from embeddings import Embeddings
import csv
from datetime import date

openai.api_key = api_key


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
def generate_html_page(articles):
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
        <img class="logo" src="{logo_url}" alt="Source logo" />
        <div class="header">
            <div class="title-date">
                <h2>{title}</h2>
                <span class="date">{date}</span>
            </div>
        </div>
        <p>{summary}</p>
        <p><span style="color: #E3120B;">Opinion:</span> {opinion}</p>
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
        opinion = article["opinion"]

        if source == "The Economist":
            logo_path = "https://www.economist.com/engassets/google-search-logo.f1ea908894.png"
        elif source == "Bloomberg":
            logo_path = "https://pbs.twimg.com/profile_images/1016326195221352450/KCcdUN0v_400x400.jpg"

        formatted_date = date.strftime("%d %B %Y")
        articles_html += article_template.format(title=title, summary=summary, url=url, logo_url=logo_url, date=formatted_date, opinion=opinion)

    return html_template.format(articles_html=articles_html)


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

    return summary, opinion


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
            article_text = article_data["article_text"]
            article_source = article_data["source"]

            print(f"    • Generating summary and opinion")
            article_summary, article_opinion = preprocessing_for_gpt(article_data)
            articles[url]["summary"] = article_summary
            articles[url]["opinion"] = article_opinion

            writer.writerow([article_uuid, url, article_title, article_date, article_source, article_text, article_summary, article_opinion])
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
            chunks = embedder.create_chunks(article_text, words_per_chunk=500, step=30)

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
