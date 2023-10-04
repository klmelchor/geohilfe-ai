#!pip install quantities
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

from quantities import units
from transformers import pipeline

import pandas as pd
import urllib3
import requests

def load_libraries():
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    nltk.download('words', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)

    # Create a custom PoolManager with increased timeout
    # http = urllib3.PoolManager(timeout=30.0)
    session = requests.Session()
    session.request = requests.Request()
    session.request.timeout = 20.0

    sw_nltk = stopwords.words('english')
    #qa_model = pipeline("question-answering", model='deepset/roberta-base-squad2', session=session)
    qa_model = None

    return sw_nltk, qa_model

def get_singular_form(word):
    lemmatizer = WordNetLemmatizer()
    singular = lemmatizer.lemmatize(word, pos='n')
    return singular

def remove_sw(text, sw_nltk):
    words = [word for word in text.split() if word.lower() not in sw_nltk]
    new_text = " ".join(words)
    return new_text

def extract_keywords_from_sentence(sentence, sw_nltk, qa_model=''):
    # Tokenize the sentence into individual words
    #tokens = nltk.word_tokenize(remove_sw(sentence, sw_nltk))
    tokens = nltk.word_tokenize(sentence)

    # Apply part-of-speech tagging
    tagged_words = nltk.pos_tag(tokens)

    # Extract noun phrases using chunking
    #NP: {<DT>?<JJ>*<NN.*>+}
    grammar = r""" 
      NP: {<JJ>*<NN.*>+}
    """
    chunk_parser = nltk.RegexpParser(grammar)
    parsed_tree = chunk_parser.parse(tagged_words)
    # Extract noun phrases from the parsed tree
    noun_phrases = []
    pronouns = ['PRP', 'PRP$', 'WP', 'WP$']

    for subtree in parsed_tree.subtrees():
        if subtree.label() == 'NP':
            noun_phrase = " ".join(word for word, pos in subtree.leaves() if pos not in pronouns)
            noun_phrases.append(noun_phrase)

    # Print the extracted noun phrases
    # print(noun_phrases)
    distance_units = list(units.length.__dict__.keys())
    
    pronouns = ['he', 'she', 'it', 'they', 'we', 'you', 'i', 'me', 'him', 'her', 'us', 'them', 'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves']
    possible_locations = [ploc for ploc in noun_phrases if get_singular_form(ploc) not in distance_units]
    possible_locations = [ploc for ploc in possible_locations if ploc not in pronouns]
    
    keywords = [] 
    [keywords.append(x) for x in possible_locations if x not in keywords] 
    
    return keywords
