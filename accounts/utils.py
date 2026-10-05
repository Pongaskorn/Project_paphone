import re


def normalize_phone(value):
    """เก็บเฉพาะตัวเลข เช่น 081-234-5678 -> 0812345678"""
    return re.sub(r"\D", "", value or "")
