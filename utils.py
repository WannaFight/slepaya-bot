from typing import List

from fuzzywuzzy import process, fuzz


def searcher(q: str, full_text: List[str], cutoff=85) -> List[str]:
    def custom_ratio(s1, s2):
        fratio = fuzz.UWRatio(s1, s2)
        if s1[0].lower() != s2[0].lower():
            fratio -= 25
        else:
            fratio += 10
        return fratio

    quotes_indices = []
    for i, sent in enumerate(full_text):
        try:
            if process.extractBests(q, filter(lambda x: len(q)/len(x) < 1.5 and len(x) > 1, sent.split()),
                                    score_cutoff=cutoff, scorer=custom_ratio):
                quotes_indices.append(i)
        except IndexError:
            continue

    return quotes_indices


def ending_decider(l: int, word_no_ending: str) -> str:
    ten_reminder = l % 10
    if ten_reminder == 1 and l != 11:
        return word_no_ending + 'у'
    elif ten_reminder in {2, 3, 4} and l not in {12, 13, 14}:
        return word_no_ending + 'ы'
    else:
        return word_no_ending