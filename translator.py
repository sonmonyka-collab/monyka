import urllib.request
import urllib.parse
import json

class Translator:
    def translate(self, text, dest='km'):
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={dest}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                translated_text = "".join([sentence[0] for sentence in data[0]])
                return type('obj', (object,), {'text': translated_text})()
        except:
            return type('obj', (object,), {'text': text})()
