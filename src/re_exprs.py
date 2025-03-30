import yaml

with open("src/config/parse_config.yaml", "r") as f:
    configs = yaml.safe_load(f)


q = configs.get("question_identifiers")
a = configs.get("answer_identifiers")
i = configs.get("inline_identifiers")

id_re = r"(((?P<nid><!--ID: )|(?P<sid>\^))(?P<id>\d+)(?(nid)-->|))"

q_s = q.get("start", "")
q_e = q.get("end", "")
q_re = rf"^({q_s}[ \t]*)(?P<question_text>.*?)([ \t]*{q_e})[ \t\n]*?$"

a_s = a.get("start", "")
a_e = a.get("end", "")
a_re = rf"^({a_s}[ \t]*)(?P<answer_text>.*?)([ \t]*{a_e})[ \t\n]*?$"

i_s = i.get("start", "")
i_e = i.get("end", "")
i_b = i.get("basic", "::")
i_r = i.get("reversed", ":::")
i_b_re = rf"^({i_s}[ \t]*)(?P<question_text>.*?)([ \t]*{i_b}[ \t]*)(?P<answer_text>.*?)[ \t]*{id_re}?\n?$"
i_r_re = rf"^({i_s}[ \t]*)(?P<question_text>.*?)([ \t]*{i_r}[ \t]*)(?P<answer_text>.*?)[ \t]*{id_re}?\n?$"

precompiled = dict(
    properties="^---$|^...$",
    question=q_re,
    answer=a_re,
    id=id_re,
    empty_line=r"^(\s+)?\n",
    inline_card=i_b_re,
    inline_reverse_card=i_r_re,
)
