# app/blacklist.py
blacklisted_tokens = set()

def is_token_blacklisted(token: str) -> bool:
    return token in blacklisted_tokens

def blacklist_token(token: str):
    blacklisted_tokens.add(token)
