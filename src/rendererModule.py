from mistune.plugins.formatting import mark
from mistune.plugins.math import math
import mistune
from src.img_plugin import img

renderer = mistune.HTMLRenderer()
markdown = mistune.Markdown(renderer, plugins=[mark, math, img])
