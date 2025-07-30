#!/usr/bin/env python3
import sys
import re

VERSION = "1.7.8"  # Added replacement of <center> tags
#VERSION = "1.7.7"  # Added removal of CDATA sections in style tags

def print_version():
    """Print version information."""
    print(f"HTML5 Converter version {VERSION}")
    print()

def clean_css_comments(css_content):
    """Clean problematic comment syntax in CSS."""
    css_content = re.sub(r'\s*\/\/\s*-->\s*', '', css_content)
    css_content = re.sub(r'\s*\/\*\s*XML\s+end\s*\]\]>\s*\*\/\s*', '', css_content)
    css_content = re.sub(r'\s*\]\]>\s*', '', css_content)
    return css_content

def merge_styles(old_style, new_styles):
    """Merge new CSS styles with existing style attribute."""
    if not new_styles:
        return old_style

    if not old_style:
        return '; '.join(s.strip() for s in new_styles.split(';') if s.strip()) + ';'

    # Remove any quotes around the style content
    old_style = old_style.strip('"\'')

    # Split and clean both old and new styles
    old_parts = [s.strip() for s in old_style.split(';') if s.strip()]
    new_parts = [s.strip() for s in new_styles.split(';') if s.strip()]

    # Combine and join with semicolons
    all_parts = old_parts + new_parts
    return '; '.join(all_parts) + ';'

def convert_alignment_and_width(match):
    """Convert both align and width attributes to CSS."""
    tag_start = match.group(1)
    attrs = match.group(2)
    tag_end = match.group(3)

    styles = []

    # Handle align attribute
    align_match = re.search(r'\balign=(["\'])(.*?)\1', attrs)
    if align_match:
        align_value = align_match.group(2)
        styles.append(f"text-align: {align_value};")
        # Remove align attribute
        attrs = re.sub(r'\balign=(["\'])[^"\']*["\']', '', attrs)

    # Handle width attribute
    width_match = re.search(r'\bwidth=(["\'])(\d+(?:\.\d+)?(?:%|em|px|rem|vw|vh)?)(["\'])', attrs)
    if width_match:
        value = width_match.group(2)
        # Add px if it's just a number
        if value.isdigit():
            value += 'px'
        styles.append(f"width: {value};")
        # Remove width attribute
        attrs = re.sub(r'\bwidth=(["\'])[^"\']*["\']', '', attrs)

    if styles:
        # Check for existing style attribute
        style_match = re.search(r'style=(["\'])(.*?)\1', attrs)
        if style_match:
            old_style = style_match.group(2)
            new_style = merge_styles(old_style, ' '.join(styles))
            attrs = re.sub(r'style=(["\']).*?\1', f'style="{new_style}"', attrs)
        else:
            attrs = f' style="{" ".join(styles)}"'

    # Add space after tag name if we have attributes
    if attrs.strip():
        return f"{tag_start} {attrs.strip()}{tag_end}"
    else:
        return f"{tag_start}{tag_end}"

def convert_table_attributes(match):
    """Convert obsolete table attributes to CSS styles."""
    tag_start = match.group(1)
    attrs = match.group(2)
    tag_end = match.group(3)

    styles = []
    new_attrs = []

    # Extract existing style attribute if present
    style_match = re.search(r'style=(["\'])(.*?)\1', attrs)
    existing_style = style_match.group(2) if style_match else ""

    # Process attributes
    for attr in re.finditer(r'(\w+)=(["\'])(.*?)\2', attrs):
        name, _, value = attr.groups()
        if name == 'cellpadding':
            styles.append(f"padding: {value}px;")
        elif name == 'cellspacing':
            styles.append(f"border-spacing: {value}px;")
        elif name == 'border':
            if value == '0':
                styles.append("border: none;")
            else:
                styles.append(f"border: {value}px solid;")
        elif name == 'summary':
            # summary attribute is obsolete, skip it
            continue
        elif name == 'style':
            # Skip style attribute as we'll handle it separately
            continue
        else:
            # Keep other attributes
            new_attrs.append(f'{name}="{value}"')

    # Merge existing styles with new styles
    all_styles = merge_styles(existing_style, ' '.join(styles))

    if all_styles:
        new_attrs.append(f'style="{all_styles}"')

    # Add space after tag name if we have attributes
    if new_attrs:
        return f"{tag_start} {' '.join(new_attrs)}{tag_end}"
    else:
        return f"{tag_start}{tag_end}"

def convert_to_html5(content, lang='en'):
    """Convert HTML content to HTML5."""
    # Remove forbidden control characters
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)

    # Remove XML declaration and any following blank lines
    content = re.sub(
        r'<\?xml[^>]*\?>[\r\n]*[\n\r]*',
        '',
        content
    )

    # First replace DOCTYPE
    content = re.sub(
        r'<!DOCTYPE[^>]*>',
        '<!DOCTYPE html>',
        content,
        flags=re.IGNORECASE
    )

    # Clean up html tag attributes and ensure single lang attribute
    def clean_html_tag(match):
        full_tag = match.group(0)
        # Remove xmlns and xml:lang attributes
        full_tag = re.sub(r'\s+xmlns="[^"]*"', '', full_tag)
        full_tag = re.sub(r'\s+xml:lang="[^"]*"', '', full_tag)
        # Remove duplicate lang attributes
        lang_matches = re.finditer(r'\s+lang="([^"]*)"', full_tag)
        langs = [m.group(1) for m in lang_matches]

        # Remove all lang attributes
        full_tag = re.sub(r'\s+lang="[^"]*"', '', full_tag)

        # Add back the appropriate lang attribute
        if langs:
            # Use the first lang value found if any exist
            final_lang = langs[0]
        else:
            final_lang = lang

        # Insert the lang attribute after the html tag
        full_tag = full_tag.replace('html', f'html lang="{final_lang}"', 1)
        return full_tag

    # Clean up the html tag
    content = re.sub(
        r'<html[^>]*>',
        clean_html_tag,
        content,
        flags=re.IGNORECASE
    )

    # Remove Content-Style-Type meta tag
    content = re.sub(
        r'[\s]*<meta[^>]*Content-Style-Type[^>]*/?>[\s]*\n?',
        '',
        content,
        flags=re.IGNORECASE
    )

    # Replace or add UTF-8 charset meta tag
    old_meta = re.search(
        r'<meta[^>]+charset=[^>]*>|<meta\s+http-equiv=["\']Content-Type["\'][^>]*>',
        content,
        flags=re.IGNORECASE
    )

    if old_meta:
        content = content.replace(old_meta.group(0), '<meta charset="utf-8">')
    else:
        content = re.sub(
            r'(<head[^>]*>)',
            r'\1\n    <meta charset="utf-8">',
            content,
            flags=re.IGNORECASE
        )

    # Remove xml:space attributes
    content = re.sub(
        r'\s+xml:space=["\'][^"\']*["\']',
        '',
        content,
        flags=re.IGNORECASE
    )

    # Remove type="text/css" from style tags
    content = re.sub(
        r'<style\s+type=["\']text/css["\']',
        '<style',
        content,
        flags=re.IGNORECASE
    )
    # Remove CDATA sections from style tags
    content = re.sub(
        r'(<style[^>]*>)\s*<!\[CDATA\[(.*?)\]\]>\s*(</style>)',
        r'\1\2\3',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    content = re.sub(
        r'(<style[^>]*>)\s*/\*<!\[CDATA\[\*/\s*(.*?)\s*/\*\]\]>\*/\s*(</style>)',
        r'\1\2\3',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Clean up CSS in style tags
    for style_match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE):
        css_content = style_match.group(1)
        cleaned_css = clean_css_comments(css_content)
        content = content.replace(css_content, cleaned_css)

    # Convert <tt> tags to span with monospace style
    content = re.sub(
        r'<tt([^>]*)>',
        r'<span\1 style="font-family: monospace;">',
        content,
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'</tt>',
        '</span>',
        content,
        flags=re.IGNORECASE
    )

    # Convert <big> tags to span with style
    content = re.sub(
        r'<big([^>]*)>',
        r'<span style="font-size: larger"\1>',
        content,
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'</big>',
        '</span>',
        content,
        flags=re.IGNORECASE
    )

    # Convert <center> tags to div with style
    content = re.sub(
        r'<center([^>]*)>',
        r'<div style="text-align: center"\1>',
        content,
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'</center>',
        '</div>',
        content,
        flags=re.IGNORECASE
    )

    # Handle name and id attributes in anchors
    content = re.sub(
        r'<a([^>]*?)\s+id=(["\'][^"\']*["\'])\s+name=\2([^>]*?)>',  # id first, then name
        r'<a\1 id=\2\3>',
        content,
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'<a([^>]*?)\s+name=(["\'][^"\']*["\'])\s+id=\2([^>]*?)>',  # name first, then id
        r'<a\1 id=\2\3>',
        content,
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'<a([^>]*?)\s+name=(["\'][^"\']*["\'])(?![^>]*?\s+id=)([^>]*?)>',  # only name exists
        r'<a\1 id=\2\3>',
        content,
        flags=re.IGNORECASE
    )

    # Convert width and align attributes to CSS for various elements
    content = re.sub(
        r'(<(?:hr|table|td|th|div|p|h[1-6]))((?:\s+[^>]*)?)(\s*>)',
        convert_alignment_and_width,
        content,
        flags=re.IGNORECASE
    )

    # Convert table attributes to CSS
    content = re.sub(
        r'(<table)((?:\s+[^>]*)?)(\s*>)',
        convert_table_attributes,
        content,
        flags=re.IGNORECASE
    )

    def convert_cell_attrs_to_style(match):
        tag_start = match.group(1)
        attrs = match.group(2)
        tag_end = match.group(3)

        styles = []

        # Handle align attribute
        align_match = re.search(r'\balign=(["\'])(.*?)\1', attrs)
        if align_match:
            align_value = align_match.group(2)
            styles.append(f"text-align: {align_value};")
            # Remove align attribute
            attrs = re.sub(r'\balign=(["\']).*?\1', '', attrs)

        # Handle valign attribute
        valign_match = re.search(r'\bvalign=(["\'])(.*?)\1', attrs)
        if valign_match:
            valign_value = valign_match.group(2)
            styles.append(f"vertical-align: {valign_value};")
            # Remove valign attribute
            attrs = re.sub(r'\bvalign=(["\']).*?\1', '', attrs)

        if styles:
            # Check for existing style attribute
            style_match = re.search(r'style=(["\'])(.*?)\1', attrs)
            if style_match:
                old_style = style_match.group(2)
                new_style = merge_styles(old_style, ' '.join(styles))
                attrs = re.sub(r'style=(["\']).*?\1', f'style="{new_style}"', attrs)
            else:
                attrs = f' style="{" ".join(styles)}"'

        # Add space after tag name if we have attributes
        if attrs.strip():
            return f"{tag_start} {attrs.strip()}{tag_end}"
        else:
            return f"{tag_start}{tag_end}"

    # Convert td/th align and valign attributes to CSS
    content = re.sub(
        r'(<(?:td|th))((?:\s+[^>]*)?)(\s*>)',
        convert_cell_attrs_to_style,
        content,
        flags=re.IGNORECASE
    )

    # Convert width/height with units on images to CSS
    def convert_img_sizes(match):
        full_tag = match.group(0)

        # Find width/height with unit values (%, em, px, etc) or plain numbers
        width_match = re.search(r'\bwidth=(["\'])(\d+(?:\.\d+)?(?:%|em|px|rem|vw|vh)?)(["\'])', full_tag)
        height_match = re.search(r'\bheight=(["\'])(\d+(?:\.\d+)?(?:%|em|px|rem|vw|vh)?)(["\'])', full_tag)
        border_match = re.search(r'\bborder=(["\'])(\d+)(["\'])', full_tag)

        # If we found any values, move them to style
        if width_match or height_match or border_match:
            styles = []
            # Remove width/height/border attributes and collect CSS
            if width_match:
                value = width_match.group(2)
                # Add px if it's just a number
                if value.isdigit():
                    value += 'px'
                full_tag = re.sub(r'\bwidth=(["\'])[^"\']*["\']', '', full_tag)
                styles.append(f"width: {value}")
            if height_match:
                value = height_match.group(2)
                # Add px if it's just a number
                if value.isdigit():
                    value += 'px'
                full_tag = re.sub(r'\bheight=(["\'])[^"\']*["\']', '', full_tag)
                styles.append(f"height: {value}")
            if border_match:
                value = border_match.group(2)
                full_tag = re.sub(r'\bborder=(["\'])[^"\']*["\']', '', full_tag)
                if value == '0':
                    styles.append("border: none")
                else:
                    styles.append(f"border: {value}px solid")

            # Clean up the tag before adding style
            full_tag = re.sub(r'\s*/\s*>', '>', full_tag)  # Remove self-closing slash
            full_tag = re.sub(r'\s+', ' ', full_tag)       # Clean up spaces
            full_tag = full_tag.rstrip('>')                # Remove closing bracket temporarily

            # Add or merge style attribute
            style_match = re.search(r'style=(["\'])(.*?)\1', full_tag)
            if style_match:
                old_style = style_match.group(2)
                new_style = merge_styles(old_style, '; '.join(styles))
                full_tag = re.sub(r'style=(["\']).*?\1', f'style="{new_style}"', full_tag)
            else:
                full_tag = f'{full_tag.strip()} style="{"; ".join(styles)}"'

            full_tag = f"{full_tag}>"  # Add back closing bracket
        else:
            # Just clean up self-closing slash if no width/height/border found
            full_tag = re.sub(r'\s*/\s*>', '>', full_tag)

        return full_tag

    content = re.sub(
        r'<img[^>]+>',
        convert_img_sizes,
        content,
        flags=re.IGNORECASE
    )

    # Convert self-closing tags
    content = re.sub(r'/>', '>', content)

    return content

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert HTML files to HTML5')
    parser.add_argument('input_file', help='Input HTML file to convert')
    parser.add_argument('--lang', default='en', help='Language code for html tag (default: en)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    print_version()

    try:
        # Try UTF-8 first
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try reading as iso-8859-1 and encode to UTF-8
            with open(args.input_file, 'r', encoding='iso-8859-1') as f:
                content = f.read()

        # Convert content
        new_content = convert_to_html5(content, lang=args.lang)

        # Always write as UTF-8
        with open('output.htm', 'w', encoding='utf-8') as f:
            f.write(new_content)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
