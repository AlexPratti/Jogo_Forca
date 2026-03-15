from supabase import create_client

URL = "https://SEU-PROJETO.supabase.co"   # substitua pelo seu URL
KEY = "sb_secret_..."                     # substitua pela sua service role key

supabase = create_client(URL, KEY)

# Teste simples: subir um arquivo de texto
resp = supabase.storage.from_("forca").upload(
    "teste.txt",                # nome do arquivo dentro do bucket
    b"conteudo de teste"        # conteúdo em bytes
)

print(resp)
