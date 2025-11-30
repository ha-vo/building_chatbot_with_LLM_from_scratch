from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import csv
import re

targets = []
driver = webdriver.Chrome()

titles = [
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-12-chan-troi-sang-tao',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-12-ket-noi-tri-thuc',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-12-canh-dieu',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-11-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-11-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-11-canh-dieu.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-10-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-10-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-10-canh-dieu.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-9-ket-noi-tri-thuc',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-9-chan-troi-sang-tao',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-9-canh-dieu',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-8-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-8-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-8-canh-dieu.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-7-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-7-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-7-canh-dieu.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-6-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-6-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-6-canh-dieu.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-5-ket-noi-tri-thuc',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-5-chan-troi-sang-tao',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-5-canh-dieu',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-4-ket-noi-tri-thuc.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-4-chan-troi-sang-tao.html',
    'https://tech12h.com/cong-nghe/trac-nghiem-lich-su-va-dia-li-4-canh-dieu.html',
    
]

def clean_question(text):
    text = re.sub(r'^(Câu|Bài)\s?\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^[:.\-,\s"\'?]+', '', text)

    return text.strip().strip('"\'')

def clean_answer(text):
    if not text: return ""
    text = text.strip()
    text = re.sub(
        r'^(Chọn|Đáp án( đúng là)?|Phương án)\s+[A-D][\s.:,]*', 
        '', 
        text, 
        flags=re.IGNORECASE
    )
    text = re.sub(r'^[A-D][.:)\-]\s*', '', text)
    text = re.sub(r'^[:.\-,\s"\'?]+', '', text)
    text = text.strip().strip('"\'')
    if text:
        text = text[0].upper() + text[1:]
        
    return text

def is_valid_qa(question, answer):
    q_lower = question.lower()
    a_lower = answer.lower()

    bad_keywords = [
        "sau đây", "dưới đây", "câu nào", "ý nào", "phương án nào", 
        "nhận định nào", "nhận xét nào", "mệnh đề nào", "khẳng định nào",
        "hình bên", "hình vẽ", "sơ đồ", "biểu đồ", "bảng số liệu", 
        "đoạn văn trên", "trong các", "hãy chọn", "cặp nào", 'hãy'
    ]

    for kw in bad_keywords:
        if kw in q_lower:
            return False
        
    bad_answers = [
        "cả a", "cả b", "cả c", "cả 3", "cả ba", "cả 4", "cả bốn",
        "tất cả", "đáp án khác", "các phương án", "đều đúng", "đều sai"
    ]

    for kw in bad_answers:
        if kw in a_lower:
            return False
    
    return True

def getListLesson(title):
    linkLessons = []
    driver.get(title)
    try:
        content = driver.find_element(By.CLASS_NAME, "my_set")
        ps = content.find_elements(By.TAG_NAME, "p")
        for p in ps:
            tagAs = p.find_elements(By.TAG_NAME, "a")
            for a in tagAs:
                linkLessons.append(a.get_attribute("href"))
    except Exception as e:
        print("Error", e)

    return linkLessons
f = open('questionAnswer.csv', 'w', encoding='utf8')
writer = csv.writer(f)
writer.writerow(['question','answer'])
def getQA(link):
    driver.get(link)
    elements = driver.find_element(By.CLASS_NAME, "tex2jax")
    questions = []
    answers = []
    xpath_query = "//p[following-sibling::*[1][self::ul]]"
    pQuestions = elements.find_elements(By.XPATH, xpath_query)
    for p in pQuestions:
        question = p.text
        
        try:
            ul_options = p.find_element(By.XPATH, "following-sibling::ul[1]")
            try:
                solution_element = ul_options.find_element(By.XPATH, ".//*[h6]")
                answer = solution_element.text
            except: continue
        except: continue
        answer = clean_answer(answer)
        question = clean_question(question)
        if is_valid_qa(question, answer) == False: continue
        questions.append(question)
        answers.append(answer)
        writer.writerow([questions[-1],answers[-1]])



for t in titles:
    l = getListLesson(t)
    print("----------------------------------------")
    for i in l:
        getQA(i)



f.close()

driver.quit()