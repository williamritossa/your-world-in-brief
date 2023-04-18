import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import SnowballStemmer

# Uncomment the following lines if you haven't downloaded the nltk data
# nltk.download('stopwords')
# nltk.download('punkt')

def preprocess_text(text, stem=True, remove_stopwords=True, keep_newlines=True):
    # Check if text is over 10 words long
    if len(word_tokenize(text)) < 10:
        return text

    if keep_newlines:
        sentences = text.split('\n')  # Split text into sentences
    else:
        sentences = nltk.sent_tokenize(text)  # Tokenize text into sentences

    processed_sentences = []
    for sentence in sentences:
        words = word_tokenize(sentence)  # Tokenize sentence into words

        if remove_stopwords:
            # Do not remove the phrase "[NEW SECTION]"
            stop_words = set(stopwords.words('english'))
            words = [word for word in words if word.casefold() not in stop_words]

        if stem:
            stemmer = SnowballStemmer('english')
            words = [stemmer.stem(word) for word in words]

        processed_sentence = ' '.join(words)  # Join words back into a string
        processed_sentences.append(processed_sentence)

    if keep_newlines:
        processed_text = '\n'.join(processed_sentences)  # Join sentences back together with newlines
    else:
        processed_text = ' '.join(processed_sentences)  # Join sentences back together with spaces
    return processed_text
