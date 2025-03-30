from mistune.plugins.formatting import mark
import mistune
from .img_plugin import img
from .mathjax_plugin import mathjax

renderer = mistune.HTMLRenderer()
markdown = mistune.Markdown(renderer, plugins=[mark, mathjax, img])
