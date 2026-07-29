import json
import unicodedata
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from docx import Document

def remover_acentos(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(conteudo_arquivo):
    try:
        doc = Document(BytesIO(conteudo_arquivo))
        texto_bruto = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt: texto_bruto.append(txt)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto: texto_bruto.append(txt)
        
        lista_final = []
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        return []

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        questoes = extrair_dados_do_docx(post_data)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"success": True, "questoes": questoes}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
