from unigramTokenizer import *
import pandas as pd

df = pd.read_csv('questionAnswer.csv', encoding="utf8")
corpusLines = []
for i,d in df.iterrows():
    line = f"[Q]{d['question']}[A]{d['answer']}"
    corpusLines.append(line)

uniTrain = Trainer()
uniTrain.caculateProb(corpusLines)
uniTrain.train(corpusLines)
saveModel('tokenizer', uniTrain.vocab)
drawLoglikelihood(uniTrain.logll)