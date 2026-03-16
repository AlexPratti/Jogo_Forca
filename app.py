import streamlit as st
import os
import time
from docx import Document
from io import BytesIO
from supabase import create_client

# ================================
# CONFIG
# ================================

st.set_page_config(
    page_title="Jogo da Forca",
    page_icon="🎮",
    layout="wide"
)

URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]

supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

# ================================
# ESTILO
# ================================

st.markdown("""
<style>

body {
    background-color:#f5f5f5;
}

button[kind="secondary"] {
    background-color:#111;
    color:white;
}

div.stButton > button {
    font-size:18px;
    font-weight:bold;
    border-radius:8px;
}

.teclado button {
    height:60px;
    width:60px;
}

</style>
""", unsafe_allow_html=True)

# ================================
# SESSION STATE
# ================================

defaults = {
"pares": [],
"indice": None,
"acertos": 0,
"derrotas": 0,
"pergunta": None,
"palavra": None,
"letras_corretas": [],
"letras_erradas": [],
"erros": 0,
"max_erros": 6
}

for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================================
# DOCX
# ================================

def extrair_perguntas_respostas(docx_file):

    doc = Document(docx_file)

    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    pares=[]

    for i in range(0,len(linhas),2):

        if i+1 < len(linhas):

            pergunta = linhas[i]
            resposta = linhas[i+1].upper()

            pares.append((pergunta,resposta))

    return pares

# ================================
# SUPABASE STORAGE
# ================================

def salvar_no_supabase(arquivo):

    supabase.storage.from_("forca").upload(
        "arquivo_compartilhado.docx",
        arquivo.getvalue(),
        {"x-upsert":"true"}
    )

    atualizar_versao()

def carregar_do_supabase():

    try:

        response = supabase.storage.from_("forca").download(
            "arquivo_compartilhado.docx"
        )

        return BytesIO(response)

    except:

        return None

# ================================
# VERSÃO (SINCRONIZAÇÃO)
# ================================

def atualizar_versao():

    versao = str(int(time.time()))

    supabase.storage.from_("forca").upload(
        "versao.txt",
        versao.encode(),
        {"x-upsert":"true"}
    )

def verificar_versao():

    try:

        response = supabase.storage.from_("forca").download("versao.txt")

        versao = response.decode()

        if "versao" not in st.session_state:

            st.session_state.versao = versao

        elif st.session_state.versao != versao:

            st.session_state.versao = versao

            st.session_state.pares=[]

            st.rerun()

    except:

        pass

# ================================
# RANKING
# ================================

def salvar_ranking(nome,pontos):

    try:

        supabase.table("ranking").insert({
            "nome":nome,
            "pontos":pontos
        }).execute()

    except:
        pass


def carregar_ranking():

    try:

        res = supabase.table("ranking") \
        .select("*") \
        .order("pontos",desc=True) \
        .limit(10) \
        .execute()

        return res.data

    except:

        return []

# ================================
# CARREGAR PERGUNTAS
# ================================

def carregar_perguntas():

    if not st.session_state.pares:

        arquivo = carregar_do_supabase()

        if arquivo:

            st.session_state.pares = extrair_perguntas_respostas(arquivo)

# ================================
# NOVA PERGUNTA
# ================================

def iniciar_nova_pergunta():

    if not st.session_state.pares:

        st.warning("Nenhuma pergunta carregada.")

        return

    if st.session_state.indice is None:
        st.session_state.indice = 0
    else:
        st.session_state.indice += 1

    if st.session_state.indice < len(st.session_state.pares):

        pergunta,resposta = st.session_state.pares[st.session_state.indice]

        st.session_state.pergunta = pergunta
        st.session_state.palavra = resposta

        st.session_state.letras_corretas=[]
        st.session_state.letras_erradas=[]
        st.session_state.erros=0

    else:

        st.session_state.pergunta=None
        st.session_state.palavra=None

        st.success("Fim das perguntas!")

# ================================
# SINCRONIZAÇÃO
# ================================

verificar_versao()

# ================================
# LOGIN
# ================================

if "jogador" not in st.session_state:

    st.title("🎮 Jogo da Forca")

    nome = st.text_input("Digite seu nome")

    if st.button("Entrar") and nome.strip():

        st.session_state.jogador = nome.strip().upper()

        carregar_perguntas()

        st.rerun()

else:

    st.title("🎮 Jogo da Forca")

# ================================
# ADMIN
# ================================

    if st.session_state.jogador.lower() == "pratti":
    
        arquivo = st.file_uploader("Carregar perguntas (.docx)", type=["docx"])
    
        if arquivo and "arquivo_enviado" not in st.session_state:
    
            salvar_no_supabase(arquivo)
    
            # extrai perguntas imediatamente
            st.session_state.pares = extrair_perguntas_respostas(arquivo)
    
            st.session_state.arquivo_enviado = True
    
            st.success("Perguntas carregadas!")

# ================================
# CARREGAR PERGUNTAS
# ================================

    carregar_perguntas()
    
    if not st.session_state.pares:
        
        st.warning("Nenhuma pergunta encontrada. O administrador precisa enviar um arquivo.")
        
    else:



# ================================
# PLACAR
# ================================

    st.markdown(f"""
**Jogador:** {st.session_state.jogador}  
**Acertos:** {st.session_state.acertos}  
**Derrotas:** {st.session_state.derrotas}  
**Erros:** {st.session_state.erros}/{st.session_state.max_erros}
""")

    col_forca,col_controles,col_jogo = st.columns([1,1,2])

# ================================
# FORCA
# ================================

    with col_forca:

        img=f"erro{st.session_state.erros}.png"

        if os.path.exists(img):

            st.image(img)

# ================================
# CONTROLES
# ================================

    with col_controles:

        label="JOGAR" if st.session_state.indice is None else "PRÓXIMO"

        if st.button(label):

            iniciar_nova_pergunta()

            st.rerun()

        if st.button("RESETAR"):

            for k in list(st.session_state.keys()):

                if k!="pares":

                    del st.session_state[k]

            st.rerun()

# ================================
# JOGO
# ================================

    with col_jogo:

        if st.session_state.pergunta:

            st.subheader(st.session_state.pergunta)

            exibicao=" ".join(
                l if l in st.session_state.letras_corretas else "_"
                for l in st.session_state.palavra
            )

            st.markdown(f"## {exibicao}")

            linhas_teclado = [
            list("ABCDEFGHI"),
            list("JKLMNOPQR"),
            list("STUVWXYZ")
            ]

            for linha in linhas_teclado:

                cols = st.columns(len(linha))

                for i,l in enumerate(linha):

                    disabled = l in st.session_state.letras_corretas or l in st.session_state.letras_erradas

                    if cols[i].button(l,key=l,disabled=disabled):

                        if l in st.session_state.palavra:

                            st.session_state.letras_corretas.append(l)

                        else:

                            st.session_state.letras_erradas.append(l)

                            st.session_state.erros+=1

                        st.rerun()

# ================================
# RESULTADO
# ================================

            if st.session_state.erros>=st.session_state.max_erros:

                st.error("💀 Você perdeu!")

                st.write("Palavra:",st.session_state.palavra)

                st.session_state.derrotas+=1

            elif all(l in st.session_state.letras_corretas for l in st.session_state.palavra):

                st.success("🎉 Você venceu!")

                st.session_state.acertos+=1

                salvar_ranking(
                    st.session_state.jogador,
                    st.session_state.acertos
                )

        else:

            st.info("Clique em JOGAR")

# ================================
# RANKING
# ================================

    st.divider()

    st.subheader("🏆 Ranking")

    ranking=carregar_ranking()

    for r in ranking:

        st.write(f"{r['nome']} — {r['pontos']}")
