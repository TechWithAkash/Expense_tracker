import logging
logging.basicConfig(level=logging.DEBUG)

import google.generativeai as genai

API_KEY = "AIzaSyBimFWYTtL4trfzyqWLyqiHaeP-zrTx8DU"
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro')
response = model.generate_content("What is 2+2?")
print(response.text)
