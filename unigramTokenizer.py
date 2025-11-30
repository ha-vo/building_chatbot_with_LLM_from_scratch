import argparse
import math
import json
import unicodedata
from collections import defaultdict, Counter


# this special character is rarely found in text (replacement for " ")
WS_MARK = "\u2581" 

# avoiding the difference between decomposed and precomposed forms
def normalizeText(s):
    s = unicodedata.normalize("NFC",s)
    return " ".join(s.split())

# replacing " " to special character
def add_ws_marker(s):
    if not s: return ""
    return WS_MARK + s.replace(" ", WS_MARK)

NEG_INF = -float('inf')
def log_add(a, b):
    if a == NEG_INF or a == NEG_INF:
        return b
    if b == NEG_INF or b == NEG_INF:
        return a
    if a < b:
        a, b = b, a
    return a + math.log1p(math.exp(b - a))



#split corpus into [s[i:i+1], s[i:i+2],...s[i:i+maxSubWord]]
# return len(dictionary) <= maxCandidates, with the number of appearances of each token >= 2 
def generate_seed_candidates(corpus, maxSubword = 16, minCount = 2,
                             maxCandidates = 200000):
    counts = Counter()
    for line in corpus:
        line = normalizeText(line)
        if not line: continue
        marked = add_ws_marker(line)
        n = len(marked)

        for i in range(n):
            isStartOfWord = (marked[i] == WS_MARK)
            maxL = min(maxSubword, n-i)
            
            for l in range(1, maxL + 1):
                sub = marked[i:i+l]
                if isStartOfWord:
                    counts[sub] += 1
                else:
                    if WS_MARK not in sub: counts[sub] += 1

    if counts.get(WS_MARK,0) == 0: counts[WS_MARK] = 1

    # filtering >= minCount
    candidates = [(t,c) for t,c in counts.items() if c >= minCount]
    candidates.sort(key=lambda x: -x[1])
    candidates = candidates[:maxCandidates]
    return dict(candidates)
    
def probability(counts):
    s = sum(counts.values())
    if s == 0: return {k: 1.0/len(counts) for k in counts}
    return {k: max(v/s, 1e-12) for k,v in counts.items()}

def forward_backward(markedText, vocab, maxTokenLen):
    s = markedText
    n = len(s)
    edges = [[] for _ in range(n)]
    for i in range(n):
        for l in range(1, min(maxTokenLen, n-i)+1):
            tok = s[i:i+l]
            if tok in vocab:
                edges[i].append((tok, l))
    
    # Counting the probability of all possible ways to reach position i
    forward = [NEG_INF] * (n+1)
    forward[0] = 0.0   # log(1)
    for i in range(n):
        if forward[i] == NEG_INF:
            continue
        for tok, l in edges[i]:
            score = forward[i] + math.log(vocab[tok])
            forward[i+l] = log_add(forward[i+l], score)


    Z = forward[n]
    if Z == NEG_INF:
        return {}, NEG_INF

    # Counting the probability of all ways that can go from i.
    backward = [NEG_INF] * (n+1)
    backward[n] = 0.0  # log(1)

    for i in range(n-1,-1,-1):
        for tok, l in edges[i]:
            score = math.log(vocab[tok]) + backward[i+l]
            backward[i] = log_add(backward[i], score)


    expected = defaultdict(float)
    for i in range(n):
        if forward[i] == NEG_INF:continue    
        for tok, l in edges[i]:
            contrib  = forward[i] + math.log(vocab[tok]) + backward[i+l] - Z            
            expected[tok] += math.exp(contrib)
    
    return expected, Z

def viterbi_segment(markedText, vocab, maxTokenLen):
    s = markedText
    n = len(s)
    bestScore = [-1e300] * (n+1)
    bestPrev = [-1] * (n+1)
    bestScore[0] = 0.0

    for i in range(n):
        if bestScore[i] < -1e300: continue #  ~ log(0)
        for l in range(1, min(maxTokenLen, n-i) + 1):
            tok = s[i:i+l]
            if tok in vocab:
                score = bestScore[i] + math.log(vocab[tok])
                if score > bestScore[i+l]:
                    bestScore[i+l] = score
                    bestPrev[i+l] = i

    if bestPrev[n] == -1: return [c for c in markedText]

    tokens = []
    cur = n
    while cur > 0:
        prev = bestPrev[cur]
        tokens.append(s[prev:cur])
        cur = prev
    tokens.reverse()
    return tokens

class Trainer:
    def __init__(self, targetVocabSize = 8000,
                 maxTokenLen = 24,
                 seedMinCount = 2
                 ):
        self.targetVocabSize = targetVocabSize
        self.maxTokenLen = maxTokenLen
        self.seedMinCount = seedMinCount
        self.vocab = {}

    def caculateProb(self, corpusLines, candidates = 200000):
        seed = generate_seed_candidates(corpusLines, self.maxTokenLen, self.seedMinCount, candidates)
        self.vocab = probability(seed)
        if WS_MARK not in self.vocab:
            self.vocab[WS_MARK] = 1e-12
        self.vocab = probability(self.vocab)
        
    
    def train(self, corpusLines, maxIters = 20):
        corpus = []
        for l in corpusLines:
            norm = normalizeText(l)
            if norm: corpus.append(add_ws_marker(norm))

        print(f"Length of corpus: {len(corpus)} sentences")

        for i in range(1, maxIters+1):
            print(f"i = {i} | vocabulary size = {len(self.vocab)}")
            expected = defaultdict(float)
            logLikelihood = 0.0

            for line in corpus:
                e, ll = forward_backward(line, self.vocab, self.maxTokenLen)
                logLikelihood += ll
                for k,v in e.items():
                    expected[k] += v

            print(f"log likelihood: {logLikelihood:.2f}")

            newCount = {}
            for tok, val in expected.items():
                newCount[tok] = val + 1e-5

            self.vocab = probability(newCount)

            if len(self.vocab) > self.targetVocabSize:
                self.prune()

            if len(self.vocab) <= self.targetVocabSize and i > 5: break

        self.vocab = probability(self.vocab)

    def prune(self):
        n = len(self.vocab)
        removeN = max(int(n*0.2), n- self.targetVocabSize)
        if removeN <= 0: return

        items = sorted(self.vocab.items(), key = lambda x: x[1])

        removes = []
        for t, _ in items:
            if t != WS_MARK:
                removes.append(t)
            if len(removes) >= removeN: break

        for tok in removes:
            del self.vocab[tok]
        self.vocab = probability(self.vocab)

class UnigramTokenizer:
    def __init__(self, vocab, maxTokenLen = 24, unk =  "<unk>"):
        self.vocab = vocab.copy()
        self.maxTokenLen = maxTokenLen
        self.unk = unk

        if unk not in self.vocab: self.vocab[unk] = 1e-12

    def encode(self, text):
        text = normalizeText(text)
        marked = add_ws_marker(text)
        tokens = viterbi_segment(marked, self.vocab, self.maxTokenLen)

        encoding = []
        for t in tokens:
            if t in self.vocab: encoding.append(t)
            else: encoding.append(self.unk)
        return encoding
    
    def decode(self, tokens):
        s = "".join(tokens)
        return s.replace(WS_MARK, " ").strip()
    
def saveModel(modelName, vocab, maxTokenLen):
    modelPath = f"{modelName}.json"
    encoding = {}
    decoding = {}
    for i,j in enumerate(vocab.keys()):
        encoding[j] = i + 1
        decoding[i+1] = j

    with open(modelPath, "w", encoding="utf8") as f:
        json.dump({
            "vocab": vocab,
            "maxTokenLen": maxTokenLen,
            "encoding": encoding,
            "decoding": decoding
        },f, ensure_ascii=False, indent=2)
    print(f"Saved model to {modelName}.json")

def loadModel(modelPath):
    with open(modelPath, "r", encoding="utf8") as f:
        data = json.load(f)
    return data



                

        

        




    


    

