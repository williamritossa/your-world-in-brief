import openai
from openai.embeddings_utils import cosine_similarity
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_not_exception_type
import pandas as pd
import numpy as np
from itertools import islice
from secrets import api_key
import tiktoken
from typing import List, Dict, Optional, Tuple
import json

# Authenticate with the OpenAI API
openai.api_key = api_key


class Embeddings:
    def __init__(self, model: str = 'text-embedding-ada-002', ctx_length: int = 200, encoding: str = 'cl100k_base'):
        self.embedding_model = model
        self.ctx_length = ctx_length  # The number of words per chunk
        self.encoding = encoding
        self.df_embeddings = pd.DataFrame()

    # Function to get the embedding for a given text
    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6), retry=retry_if_not_exception_type(openai.InvalidRequestError))
    def get_embedding(self, text_or_tokens, model=None) -> List[float]:
        if model is None:
            model = self.embedding_model
        return openai.Embedding.create(input=text_or_tokens, model=model)["data"][0]["embedding"]

    # Function to batch data into tuples of length n
    def batched(self, iterable: List, n: int) -> Tuple:
        """Batch data into tuples of length n. The last batch may be shorter."""
        # batched('ABCDEFG', 3) --> ABC DEF G
        if n < 1:
            raise ValueError('n must be at least one')
        it = iter(iterable)
        while (batch := tuple(islice(it, n))):
            yield batch

    # Function to break a text into chunks of a given length
    def chunked_tokens(self, text: str, encoding_name: str, chunk_length: int) -> Tuple:
        """Encodes a string into tokens and breaks them into chunks"""
        # May make sense to split chunks on paragraph/sentence boundaries to help preserve the meaning of the text
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)
        chunks_iterator = self.batched(tokens, chunk_length)
        yield from chunks_iterator

    def create_chunks(self, text: str, words_per_chunk: int, step: int) -> List[List[str]]:
        """Breaks a text into chunks of a given length, overlapping by a given step"""
        if step >= words_per_chunk:
            raise ValueError("Step should be smaller than words_per_chunk")

        # Split the text into words
        words = text.split()
        num_words = len(words)
        chunks = []

        # Iterate through the words, creating chunks with overlap defined by step
        for i in range(0, num_words - step, words_per_chunk - step):
            # Calculate the start and end indices for the current chunk
            start = i
            end = start + words_per_chunk

            # Create the chunk and add it to the list of chunks
            chunk = words[start:end]
            chunks.append(chunk)

            # Break the end index exceeds the number of words
            if end >= num_words:
                break

        return chunks

    # Function to get the embedding for a given text, chunking it if necessary
    def len_safe_get_embedding(self, text, average=True):
        """Get embedding for a text, chunking it if necessary"""
        chunk_embeddings = []
        chunk_lens = []
        for chunk in self.chunked_tokens(text, encoding_name=self.encoding, chunk_length=self.ctx_length):
            chunk_embeddings.append(self.get_embedding(chunk, model=self.embedding_model))
            chunk_lens.append(len(chunk))

        # If true, return the weighted average of the chunk embeddings
        # If false, return the unmodified list of chunk embeddings
        if average:
            chunk_embeddings = np.average(chunk_embeddings, axis=0, weights=chunk_lens)
            chunk_embeddings = chunk_embeddings / np.linalg.norm(chunk_embeddings)  # normalizes length to 1
            chunk_embeddings = chunk_embeddings.tolist()
        return chunk_embeddings

    # Returns pandas dataframe with embeddings
    @staticmethod
    def load_embeddings_from_database(embeddings_model_manager, text_column_name) -> pd.DataFrame:
        embeddings = embeddings_model_manager.all().values(text_column_name, 'embeddings')  # Retrieve data from the Django model
        df_embeddings = pd.DataFrame(embeddings)
        df_embeddings = df_embeddings.rename(
            columns={'embeddings': 'embedding'})  # Rename columns to match existing code

        # Convert string embeddings to numpy arrays
        if not df_embeddings.empty:
            df_embeddings['embedding'] = df_embeddings['embedding'].apply(eval).apply(np.array)

        df_embeddings = df_embeddings.dropna(subset=['embedding'])  # Drop rows with missing embeddings
        return df_embeddings


    """
    embeddings = EmbeddingsModel.objects.all().values('text', 'embeddings')  # Retrieve data from the Django model
    self.df_embeddings = pd.DataFrame(embeddings)  # Convert to pandas DataFrame
    self.df_embeddings = self.df_embeddings.rename(columns={'embeddings': 'embedding'})  # Rename columns to match existing code

    # Convert string embeddings to numpy arrays
    if not self.df_embeddings.empty:
        self.df_embeddings['embedding'] = self.df_embeddings['embedding'].apply(eval).apply(np.array)

    self.df_embeddings = self.df_embeddings.dropna(subset=['embedding'])  # Drop rows with missing embeddings
    """

    # Function to return the embedding for a given text
    def get_embedding_for_text(self, text: str) -> Optional[str]:
        try:
            embedding = self.get_embedding(text)
            embedding = json.dumps(embedding)  # convert from list to string
            return ''.join(embedding)
        except Exception as e:
            print("An error occurred while loading embeddings:", e)
            return None

    # Function to search for a given search term
    def search(self, search_term: str, embeddings_model_manager, text_column_name: str, n: int = None) -> List[str]:
        search_term_vector = self.get_embedding(search_term)
        self.df_embeddings = self.load_embeddings_from_database(embeddings_model_manager, text_column_name)

        # Set n to the number of rows in the dataframe if it is not provided
        if n is None:
            n = self.df_embeddings.shape[0]

        # If n is greater than the number of rows in the dataframe, set n to the number of rows
        if n > self.df_embeddings.shape[0]:
            n = self.df_embeddings.shape[0]

        # Get top n most similar texts
        if self.df_embeddings.empty:
            return ["No context was found in the knowledge base."]

        self.df_embeddings["similarity"] = self.df_embeddings['embedding'].apply(lambda x: cosine_similarity(x, search_term_vector))
        self.df_embeddings = self.df_embeddings.sort_values(by='similarity', ascending=False)

        top_n = self.df_embeddings.nlargest(n, 'similarity')

        return top_n[text_column_name].to_list()

#long_text = 'AGI ' * 5000
#try:
#    get_embedding(long_text)
#except openai.InvalidRequestError as e:
#    print(e)

#average_embedding_vector = len_safe_get_embedding(long_text, average=True)
#chunks_embedding_vectors = len_safe_get_embedding(long_text, average=False)

#print(f"Setting average=True gives us a single {len(average_embedding_vector)}-dimensional embedding vector for our long text.")
#print(f"Setting average=False gives us {len(chunks_embedding_vectors)} embedding vectors, one for each of the chunks.")
