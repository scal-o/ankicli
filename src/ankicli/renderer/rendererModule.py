import mistune
from mistune.plugins.formatting import mark

from ankicli.renderer.img_plugin import img
from ankicli.renderer.mathjax_plugin import mathjax

renderer = mistune.HTMLRenderer()
markdown = mistune.Markdown(renderer, plugins=[mark, mathjax, img])
