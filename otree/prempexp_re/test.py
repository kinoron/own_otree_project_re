import yaml
import pprint

with open('oTree/prempexp/test.yaml', encoding='utf-8') as f:
    document = yaml.safe_load(f)

pprint.pprint(document)

p1 = True
p2 = False
key1 = "round{}"
key2 = "({}, {})"
n=2
payoff = document[key1.format(n)][key2.format(p1, p2)]

pprint.pprint(payoff)