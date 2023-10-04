#import geo_database as gb
from ast import literal_eval
import spacy
import warnings
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity as cs
import subprocess
import jellyfish
from nltk.util import ngrams

warnings.filterwarnings("ignore", category=FutureWarning)

def sm_init():
    try:
        nlp = spacy.load('en_core_web_lg')
    except:
        print("en_core_web_lg not found, downloading spacy model...")
        subprocess.call(['python', '-m', "spacy", "download", "en_core_web_lg"])
        nlp = spacy.load('en_core_web_lg')

    # This line is used for prototyping on Google Maps data, geo_database is also commented-out above
    #sample_database = gb.create_dataset()

    # make sure that there are no nans in the csv
    filename = 'app/geohilfe_data_aws_v2.csv'
    sample_database = pd.read_csv(filename, sep='\t', converters={"northeast": literal_eval, "southwest": literal_eval, 
                                                        "raw_data": literal_eval, "keywords": literal_eval, "addresses": literal_eval,
                                                        "landmarks": literal_eval, "subregion": literal_eval, "streets": literal_eval,}).iloc[:, 1:]

    return nlp, sample_database

def kw_vectorizer(kd, kir, nlp):
    kd_v = [nlp(word).vector for word in kd]
    kir_v = [nlp(word).vector for word in kir]
    return kd_v, kir_v

def jaccard_similarity(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def keyword_similarity(keywords_detected, keywords_in_row, nlp):
    # if row has no entries, then return similarity score of 0
    if keywords_in_row == []:
        return 0
    
    kd_v, kir_v = kw_vectorizer(keywords_detected, keywords_in_row, nlp)
    
    # what is returned is a (x, y) matrix --> (x, 300) * (300, y), find the max value of each row
    res = cs(kd_v, kir_v).max(axis=1)

    # eliminate all zeros that were due to OOVs, convert it to NaNs, return the mean
    res[res == 0] = np.nan
    similarity_score_mean = np.nanmean(res, axis=0)

    #res.mean()
    return similarity_score_mean

### ----- Similarity computation for proper nouns ----- ###

def compute_ngram_similarity(str1, str2, n=2):
    str1_ngrams = set(ngrams(str1, n))
    str2_ngrams = set(ngrams(str2, n))
    intersection = str1_ngrams & str2_ngrams

    return len(intersection) / max(len(str1_ngrams), len(str2_ngrams))

def combined_similarity(str1, str2, n=2, weight_jw=0.5, weight_ng=0.5):
    jaro_winkler_sim = jellyfish.jaro_winkler(str1, str2)
    ngram_sim = compute_ngram_similarity(str1, str2, n)
    
    # TODO: this is a crude brute force approach, need a better way for this...
    if ngram_sim <= 0.25:
        weight_jw = 0.15
        weight_ng = 0.85
    
    if jaro_winkler_sim >= 0.85:
        weight_jw = 0.85
        weight_ng = 0.15

    # Combined score
    combined_score = weight_jw * jaro_winkler_sim + weight_ng * ngram_sim
    return combined_score

def calculate_eq_weights(values, sigma=0.35):
    # calculate the distance from 1 for each value
    distances = np.abs(1 - np.array(values))
    
    # calculate weights using a Gaussian function
    weights = np.exp(-distances**2 / (2 * sigma**2))
    
    # normalize weights so they sum to 1
    weights = weights / np.sum(weights)
    
    return weights.tolist()

def compute_weighted_mean(values, weights):
    return sum(v*w for v, w in zip(values, weights))

# this function is also used for landmarks similarity scoring
def prop_noun_sim(keywords, streets):
    # if streets/landmarks is empty, return 0.0
    if streets == []:
        return 0.0
    else:
        similarities = []
        for keyword in keywords:
            for street in streets:
                similarity_score = combined_similarity(keyword, street, n=2, weight_jw=0.65, weight_ng=0.35)
                similarities.append(similarity_score)

        weights = calculate_eq_weights(similarities)
        cwm = compute_weighted_mean(similarities, weights)
        
        return cwm

### ---------------------------------------------------- ###

def user_keyword_handler(keywords, nlp, database):

    sample_database = database.reset_index().iloc[:, 1:]
    grid_no = []
    grid_coors = []
    similarity_score_list = [] 
    for grid in range(len(sample_database)):
        try:
            keywords_in_row = sample_database.loc[grid]['keywords']
            streets_info = sample_database.loc[grid]['streets']
            landmarks_info = sample_database.loc[grid]['landmarks']

            if keywords_in_row == []:
                similarity_score_keywords = 0
            else:
                similarity_score_keywords = keyword_similarity(keywords, keywords_in_row, nlp)

            if streets_info == []:
                similarity_score_streets = 0
            else:
                similarity_score_streets = prop_noun_sim(keywords, streets_info)

            if landmarks_info == []:
                similarity_score_landmarks = 0
            else:
                similarity_score_landmarks = prop_noun_sim(keywords, landmarks_info)

            # TODO: At some point, if there are too many keywords, then the similarity scores across all categories degrade
            # make logic that removes the keyword if there is a high match?
            similarity_score = 0.5*similarity_score_streets + 0.3* similarity_score_landmarks + 0.2*similarity_score_keywords
            
            grid_no.append(str(sample_database.loc[grid]['grid_num']))
            
            center = ((sample_database.loc[grid]['northeast'][1] + sample_database.loc[grid]['southwest'][1])/2, 
                      (sample_database.loc[grid]['northeast'][0] + sample_database.loc[grid]['southwest'][0])/2)
            
            grid_coors.append(center)
            similarity_score_list.append(similarity_score)
            
        except Exception as e:
            print(e)
        
    grid_no = [x for _, x in sorted(zip(similarity_score_list, grid_no), reverse=True)]
    grid_coors = [x for _, x in sorted(zip(similarity_score_list, grid_coors), reverse=True)]
    similarity_score_list = sorted(similarity_score_list, reverse=True)
    
    return grid_no, grid_coors, similarity_score_list
    