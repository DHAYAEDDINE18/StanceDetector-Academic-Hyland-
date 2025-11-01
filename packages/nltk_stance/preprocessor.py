# nltk_stance/preprocessor.py
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag

class TextPreprocessor:
    def __init__(self, text):
        self.text = text
    
    def clean_text(self):
        # Remove unwanted spaces/newlines
        return " ".join(self.text.split())
    
    def tokenize_sentences(self):
        return sent_tokenize(self.clean_text())
    
    def tokenize_words(self, sentence):
        return word_tokenize(sentence)
    
    def pos_tag_sentence(self, sentence):
        words = self.tokenize_words(sentence)
        return pos_tag(words)
