import streamlit as st
import os
from docx import Document
from supabase import create_client, Client

# Configuração do Supabase
url = "https://SEU_PROJECT.supabase.co"
key = "SEU_API_KEY"
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Jogo da Forca", layout="wide")

# Inicialização de variáveis de sessão
if "pares" not in st.session_state:
    st.session_state.pares = []
if "indice" not in st.session_state:
    st.session_state.indice = None
if "palavra" not in st.session_state:
    st.session_state.palavra = ""
if "letras_corretas" not in st.session_state:
    st.session_state.letras_corretas = []
if "letras_erradas" not in st.session_state:
    st.session_state.letras_erradas = []
if "erros" not in st.session_state:
    st.session_state.erros = 0
if "max_erros" not in st.session_state:
    st.session_state.max_erros = 6
if "acertos" not in st.session_state:
    st.session_state.acertos = 0
if "derrotas" not in st.session_state:
    st.session_state.derrotas = 0

def salvar_no_supabase(arquivo):
    supabase.storage.from_("jogo").upload("perguntas.docx", arquivo)

def carregar_do_supabase():
    try:
        dados = supabase.storage.from_("jogo").download("perguntas.docx")
        if dados:
            with open("perguntas.docx", "wb") as f:
                f.write(dados)
            return "perguntas.docx"
    except Exception:
        return None

def extrair_perguntas_respostas(caminho):
    doc = Document(caminho)
    pares = []
    for p in doc.paragraphs:
        if ":" in p.text:
            pergunta, resposta = p.text.split(":", 1)
            pares.append((pergunta.strip(), resposta.strip().upper()))
    return pares

st.title("🎮 Jogo da Forca")

# Entrada de nome
if "jogador" not in st.session_state:
    st.session_state.jogador = ""

st.session_state.jogador = st.text_input("Digite seu nome:")

# Só continua se o nome foi digitado
if st.session_state.jogador.strip() != "":
    if st.session_state.jogador.lower() == "pratti":
        arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])
        if arquivo:
            salvar_no_supabase(arquivo)
            pares = extrair_perguntas_respostas(arquivo)
            st.session_state.pares = pares
        else:
            arquivo_padrao = carregar_do_supabase()
            if arquivo_padrao:
                pares = extrair_perguntas_respostas(arquivo_padrao)
                st.session_state.pares = pares
            else:
                st.warning("Nenhum arquivo no Supabase ainda.")
    else:
        if not st.session_state.pares:
            arquivo_padrao = carregar_do_supabase()
            if arquivo_padrao:
                pares = extrair_perguntas_respostas(arquivo_padrao)
                st.session_state.pares = pares
            else:
                st.error("Nenhum arquivo disponível no Supabase.")
else:
    st.info("Digite seu nome para começar o jogo.")

def iniciar_nova_pergunta():
    if st.session_state.pares:
        import random
        st.session_state.indice = random.randint(0, len(st.session_state.pares)-1)
        pergunta, resposta = st.session_state.pares[st.session_state.indice]
        st.session_state.palavra = resposta
        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.erros = 0

col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

with col_forca:
    nome_imagem = f"erro{st.session_state.erros}.png"
    if os.path.exists(nome_imagem):
        st.image(nome_imagem)
    else:
        st.warning(f"Imagem {nome_imagem} não encontrada.")
with col_controles:
    st.markdown(
        """
        <style>
        div.stButton > button {
            font-size: 20px !important;
            font-weight: bold;
            height: 55px !important;
            width: 220px !important;
            margin: 6px 0;
            border-radius: 6px;
            white-space: nowrap;
            text-align: center;
            justify-content: center;
        }
        @media (max-width: 600px) {
            div.stButton > button {
                width: 90% !important;
                height: 50px !important;
                font-size: 18px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    cor_fundo = "#f97316" if st.session_state.indice is None else "#111"
    st.markdown(
        f"""
        <style>
        div.stButton > button {{
            background-color: {cor_fundo} !important;
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    label_btn = "JOGAR" if st.session_state.indice is None else "PRÓXIMO"
    if st.button(label_btn, key="btn_jogar"):
        iniciar_nova_pergunta()
        st.rerun()
    if st.button("RESETAR", key="btn_resetar"):
        st.session_state.clear()
        st.rerun()
    if st.button("SAIR DO JOGO", key="btn_sair"):
        st.session_state.clear()
        st.rerun()
with col_jogo:
    if st.session_state.indice is not None:
        pergunta, resposta = st.session_state.pares[st.session_state.indice]
        st.subheader(pergunta)

        exibicao = " ".join([l if l in st.session_state.letras_corretas else "_" for l in resposta])
        st.write(exibicao)

        st.markdown(
            """
            <style>
            div[data-testid="stHorizontalBlock"] div.stButton > button {
                background-color: #111 !important;
                color: white !important;
                font-size: 44px !important;
                font-weight: bold;
                height: 100px !important;
                width: 100px !important;
                margin: 4px;
                border-radius: 8px;
            }
            div[data-testid="stHorizontalBlock"] div.stButton > button:disabled {
                background-color: #444 !important;
                color: #aaa !important;
            }
            @media (max-width: 600px) {
                div[data-testid="stHorizontalBlock"] div.stButton > button {
                    width: 18% !important;
                    height: 60px !important;
                    font-size: 24px !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        letras = ["A","Á","Ã","Â","B","C","Ç","D","E","É","Ê","F","G","H","I","J","K","L","M",
                  "N","O","Ó","Õ","Ô","P","Q","R","S","T","U","Ú","V","W","X","Y","Z"]

        bloqueado = (
            st.session_state.erros >= st.session_state.max_erros or
            all(l in st.session_state.letras_corretas for l in resposta)
        )

        cols = st.columns(10)
        for i, l in enumerate(letras):
            disabled = bloqueado or l in st.session_state.letras_corretas or l in st.session_state.letras_erradas
            if cols[i % 10].button(l, key=f"btn_{l}", disabled=disabled):
                if l in resposta:
                    st.session_state.letras_corretas.append(l)
                else:
                    st.session_state.letras_erradas.append(l)
                    st.session_state.erros += 1
                st.rerun()

        # condição de derrota
        if st.session_state.erros >= st.session_state.max_erros:
            st.error("💀 Você perdeu!")
            st.write(f"A palavra era: {resposta}")
            st.session_state.derrotas += 1

        # condição de vitória
        elif resposta and all(l in st.session_state.letras_corretas for l in resposta):
            st.success("🎉 Você ganhou!")
            st.session_state.acertos += 1

    # placar geral
    st.markdown("---")
    st.write(f"✅ Vitórias: {st.session_state.acertos}")
    st.write(f"❌ Derrotas: {st.session_state.derrotas}")
