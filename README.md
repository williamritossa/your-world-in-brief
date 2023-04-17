# Your world in brief

Inspired by The Economist's 'The world in brief,' this project is a Python script that scrapes and summarizes the latest articles from The Economist website, generating a simple HTML page with the summaries and links to the original articles. The script automatically logs in to your Economist account and handles articles behind the paywall.

## Installation

1. Install the required packages:
  ```
  pip install -r requirements.txt
  ```

2. Create an OpenAI API key at [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)

3. Enter your API key and login details for The Economist in `secrets.py`
   ```py
   api_key = 'ENTER YOUR API'
   username = 'your_the_economist_username'
   password = 'your_the_economist_password'
   ```
