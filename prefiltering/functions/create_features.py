import re
import nltk

def count_boolean_operators(input_string):
    boolean_operators = ['AND', 'OR', 'NOT']
    count_total = 0 
    for operator in boolean_operators:
        count = sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(operator), input_string))
        count_total += count
    return count_total

def count_tokens(input_string):
    tokens = len(nltk.word_tokenize(input_string))
    return tokens


# Not tested yet! 
def count_nouns(input_string):
    nltk.download('averaged_perceptron_tagger_eng')

    is_noun = lambda pos: pos[:2] == 'NN'
    tokenized = nltk.word_tokenize(input_string)
    nouns = [word for (word, pos) in nltk.pos_tag(tokenized) if is_noun(pos)] 
    count_nouns = len(nouns)

    return count_nouns
