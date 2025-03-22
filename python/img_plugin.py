'''
module defining a mistune plugin for inline images
'''

# inline image pattern
INLINE_IMG_PATTERN = r"!\[\[(?P<img_src>[\w\s\.]+)\]\]"

# inline image parsing function
def parse_inline_img(inline, m, state):
    img_src = m.group('img_src')
    state.append_token({'type': 'inline_img', 'raw': img_src})
    
    # return end position of parsed text
    return m.end()

# inline image rendering function
def render_inline_img(renderer, text):
    return f"<img src=\"{text}\">"

# image plugin
def img(md):
    md.inline.register('inline_img', INLINE_IMG_PATTERN, parse_inline_img, before='link')
    
    if md.renderer and md.renderer.NAME == 'html':
        md.renderer.register('inline_img', render_inline_img)
        