import re


def html_to_rtf(html_string):
    """Convert basic HTML to RTF format.

    Handles paragraphs, bold, italic, underline, line breaks, links, and font tags.

    Args:
        html_string: An HTML string to convert.

    Returns:
        A valid RTF string.
    """
    text = html_string

    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # Handle line breaks before removing tags
    text = re.sub(r'<br\s*/?>', r'\\line ', text, flags=re.IGNORECASE)

    # Handle bold
    text = re.sub(r'<b\b[^>]*>(.*?)</b>', r'\\b \1\\b0 ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<strong\b[^>]*>(.*?)</strong>', r'\\b \1\\b0 ', text, flags=re.DOTALL | re.IGNORECASE)

    # Handle italic
    text = re.sub(r'<i\b[^>]*>(.*?)</i>', r'\\i \1\\i0 ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<em\b[^>]*>(.*?)</em>', r'\\i \1\\i0 ', text, flags=re.DOTALL | re.IGNORECASE)

    # Handle underline
    text = re.sub(r'<u\b[^>]*>(.*?)</u>', r'\\ul \1\\ulnone ', text, flags=re.DOTALL | re.IGNORECASE)

    # Handle links: extract text, ignore href
    text = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\\ul \1\\ulnone ', text, flags=re.DOTALL | re.IGNORECASE)

    # Handle paragraphs
    text = re.sub(r'<p\b[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', r'\\par ', text, flags=re.IGNORECASE)

    # Handle divs as paragraphs
    text = re.sub(r'<div\b[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', r'\\par ', text, flags=re.IGNORECASE)

    # Handle table rows as paragraphs
    text = re.sub(r'</tr>', r'\\par ', text, flags=re.IGNORECASE)
    text = re.sub(r'</td>', ' ', text, flags=re.IGNORECASE)

    # Handle headings
    for level in range(1, 7):
        size = max(44 - (level * 4), 24)  # h1=40, h2=36, h3=32, etc.
        text = re.sub(
            rf'<h{level}\b[^>]*>(.*?)</h{level}>',
            rf'\\fs{size}\\b \1\\b0\\fs24\\par ',
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Handle &nbsp; and common entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&auml;', r'\'e4')
    text = text.replace('&ouml;', r'\'f6')
    text = text.replace('&uuml;', r'\'fc')
    text = text.replace('&Auml;', r'\'c4')
    text = text.replace('&Ouml;', r'\'d6')
    text = text.replace('&Uuml;', r'\'dc')
    text = text.replace('&szlig;', r'\'df')

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n', text)
    text = text.strip()

    # Escape special RTF characters in the content (but not our RTF commands)
    # We need to be careful not to escape the backslashes we already inserted
    # Instead, handle curly braces in the remaining text
    text = text.replace('{', r'\{')
    text = text.replace('}', r'\}')

    # Wrap in RTF document structure
    rtf = (
        r'{\rtf1\ansi\ansicpg1252\deff0'
        r'{\fonttbl{\f0\fswiss\fcharset0 Arial;}}'
        r'\viewkind4\uc1'
        r'\pard\f0\fs24 '
        + text
        + r'}'
    )

    return rtf


def render_rtf_template(template, variables):
    """Replace {{variables}} in an RTF template without breaking RTF codes.

    This function carefully replaces template placeholders while preserving
    the integrity of RTF control words and structures.

    Args:
        template: An RTF template string containing {{variable}} placeholders.
        variables: A dict mapping variable names to replacement values.

    Returns:
        The rendered RTF string with all placeholders replaced.
    """
    result = template

    for var_name, var_value in variables.items():
        placeholder = '{{' + var_name + '}}'

        # Encode the value for RTF: escape special characters
        safe_value = _rtf_escape(str(var_value))

        result = result.replace(placeholder, safe_value)

    # Clean up any remaining unreplaced placeholders
    result = re.sub(r'\{\{[a-zA-Z_]+\}\}', '', result)

    return result


def _rtf_escape(text):
    """Escape a plain text string for safe inclusion in RTF.

    Args:
        text: Plain text string.

    Returns:
        RTF-safe string with special characters escaped.
    """
    # Escape backslashes first
    text = text.replace('\\', '\\\\')
    # Escape curly braces
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')

    # Handle German special characters (common in this context)
    replacements = {
        '\u00e4': r"\'e4",   # ae
        '\u00f6': r"\'f6",   # oe
        '\u00fc': r"\'fc",   # ue
        '\u00c4': r"\'c4",   # Ae
        '\u00d6': r"\'d6",   # Oe
        '\u00dc': r"\'dc",   # Ue
        '\u00df': r"\'df",   # ss
    }
    for char, rtf_code in replacements.items():
        text = text.replace(char, rtf_code)

    # Handle any remaining non-ASCII characters with Unicode escapes
    result = []
    for char in text:
        code_point = ord(char)
        if code_point > 127:
            result.append(f'\\u{code_point}?')
        else:
            result.append(char)

    return ''.join(result)
