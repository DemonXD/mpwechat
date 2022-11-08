def text_length(text: str) -> int:
    """
    计算文本长度，unicode 算2个字符
    """
    try:
        str_len = len(str(text))
        unicode_len = len(text.encode("utf-8"))
        return (unicode_len - str_len) // 2 + str_len
    except Exception:
        return str_len
