# nltk_stance/stance_lexicon.py

STANCE_LEXICON = {
    "hedging": [
        "may", "might", "could", "seem", "appear", "suggest", "possible",
        "approximately", "generally", "likely", "perhaps", "indicate"
    ],
    "boosting": [
        "clearly", "definitely", "certainly", "undoubtedly", "it is clear that",
        "it is evident that", "show", "prove", "demonstrate"
    ],
    "attitude": [
        "unfortunately", "importantly", "surprisingly", "interestingly",
        "it is important to note", "it is surprising that"
    ],
    "self_mention": [
        "I", "we", "our", "my", "us", "the researcher", "the author"
    ]
}
