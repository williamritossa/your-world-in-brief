import requests
from bs4 import BeautifulSoup
from datetime import datetime


def extract_text_from_newsletter_soup(html):
    """
    Extracts the text contained in an iframe
    """
    # Locate the iframe element
    iframe = html.find("iframe")

    # Extract the srcdoc attribute content
    srcdoc_content = iframe["srcdoc"]

    # Parse the srcdoc content with BeautifulSoup
    srcdoc_soup = BeautifulSoup(srcdoc_content, "html.parser")

    # Remove all newline characters from the text
    for elem in srcdoc_soup(text=lambda text: text == '\n'):
        elem.extract()

    # Add a newline character before h1 and h2 elements
    for tag in srcdoc_soup.find_all(['h1', 'h2']):
        tag.insert_before('\n\n')
        tag.insert_before('[NEW SECTION] \n')
        tag.insert_after('\n')

    # Extract the text from the srcdoc_soup
    text = srcdoc_soup.get_text(separator=" ", strip=False)

    # Remove everything after "Follow Us" (including follow us)
    text = text.split("Follow Us")[0]

    return text


def extract_title_and_date(newsletter_soup):
    # Find all h2 elements containing "Money Stuff"
    h2_elements = newsletter_soup.find_all("h2", string=lambda string: "Money Stuff" in string)

    # Find the first h2 element's parent div containing a datetime
    div_with_h2 = None
    for h2 in h2_elements:
        parent_div = h2.find_parent("div")
        if parent_div.find("time") is not None:
            div_with_h2 = parent_div
            break

    # Extract the title from the h2 element
    title = div_with_h2.find("h2").get_text(strip=True)

    # Extract the datetime from the time element
    time_element = div_with_h2.find("time")
    datetime_str = time_element["datetime"]
    datetime_obj = datetime.fromisoformat(datetime_str)
    return title, datetime_obj


def scrape_money_stuff():
    base_url = "https://newsletterhunt.com"
    search_url = f"{base_url}/newsletters/money-stuff-by-matt-levine"

    # Get the newsletter hunt page content
    search_response = requests.get(search_url)
    search_soup = BeautifulSoup(search_response.content, "html.parser")

    # Find the latest newsletter URL
    latest_newsletter_a = search_soup.find("ul", role="list").find("a", href=True)
    latest_newsletter_url = base_url + latest_newsletter_a["href"]

    # Get the latest newsletter content
    newsletter_response = requests.get(latest_newsletter_url)
    newsletter_soup = BeautifulSoup(newsletter_response.content, "html.parser")

    # Scrape the text from the latest newsletter
    text = extract_text_from_newsletter_soup(newsletter_soup)

    # Get title and date from the newsletter
    title, date = extract_title_and_date(newsletter_soup)

    dict_to_return = {latest_newsletter_url: {
        "title": title,
        "date": date,
        "article_text": text,
        "source": "Bloomberg"
    }}

    return dict_to_return
