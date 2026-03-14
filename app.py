import streamlit as st
import random
from docx import Document
from supabase import create_client

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# Conexão com Supabase
url = "https://SEU-PROJETO.supabase.co"
key = "CHAVE-API"
supabase = create_client(url, key)

# CSS para fundo escuro e título laranja
st.markdown(
    """
    <style>
    body { background-color: #111; color: white; }
    .stButton>button {
        background-color: #333; color: white; border-radius: 5px; padding: 8px 16px;
    }
    .stButton>button:hover { background-color: #555; color: orange; }
    </style>
    """,
    unsafe_allow_html=True
)

def extrair_perguntas_respostas(docx_file):
    doc = Document(docx_file)
    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    pares = []
    for i in range(0, len(linhas), 2):
        if i+1 < len(linhas):
            pergunta = linhas[i]
            resposta = linhas[i+1].upper()
            pares.append((pergunta, resposta))
    return pares

# Inicialização do estado
if 'pares' not in st.session_state:
    st.session_state.pares = []
    st.session_state.indice = None
    st.session_state.acertos = 0
    st.session_state.derrotas = 0
    st.session_state.pergunta = None
    st.session_state.palavra = None
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0
    st.session_state.max_erros = 6
    st.session_state.fim_de_jogo = False
    st.session_state.rodada_encerrada = False

def iniciar_nova_pergunta():
    if st.session_state.indice is None:
        st.session_state.indice = 0
    else:
        st.session_state.indice += 1

    if st.session_state.indice < len(st.session_state.pares):
        pergunta, resposta = st.session_state.pares[st.session_state.indice]
        st.session_state.pergunta = pergunta
        st.session_state.palavra = resposta
        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.erros = 0
        st.session_state.fim_de_jogo = False
        st.session_state.rodada_encerrada = False
    else:
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.session_state.fim_de_jogo = True
# === Fluxo de entrada do nome do jogador ===
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    st.markdown("<h1 style='color:orange;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # Upload só aparece se jogador for Pratti
    if st.session_state.jogador.lower() == "pratti":
        arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])
        if arquivo:
            # Salva no Supabase
            supabase.storage.from_("forca").upload("perguntas.docx", arquivo.read(), {"upsert": True})
            pares = extrair_perguntas_respostas(arquivo)
            st.session_state.pares = pares
        else:
            st.info("Nenhum arquivo carregado ainda.")
    else:
        # Se não for Pratti, tenta baixar do Supabase
        try:
            dados = supabase.storage.from_("forca").download("perguntas.docx")
            if dados:
                with open("temp.docx", "wb") as f:
                    f.write(dados)
                pares = extrair_perguntas_respostas("temp.docx")
                st.session_state.pares = pares
            else:
                st.session_state.fim_de_jogo = True
        except:
            st.session_state.fim_de_jogo = True
    # Placar fixo no topo
    st.markdown(
        f"""
        <div style='background-color:#222; color:white; padding:10px; border-radius:5px;'>
        Jogador: {st.session_state.jogador}<br>
        Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}<br>
        Erros atuais: {st.session_state.erros}/{st.session_state.max_erros}
        </div>
        """,
        unsafe_allow_html=True
    )

    col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

    with col_forca:
        nome_imagem = f"erro{st.session_state.erros}.png"
        try:
            st.image(nome_imagem, caption="Forca")
        except:
            st.warning(f"Imagem {nome_imagem} não encontrada.")

    with col_controles:
        st.markdown("### Controles")

        label_btn = "JOGAR" if st.session_state.indice is None else "PRÓXIMO"
        if st.button(label_btn):
            iniciar_nova_pergunta()
            st.rerun()

        if st.button("RESETAR"):
            st.session_state.indice = 0
            if st.session_state.pares:
                pergunta, resposta = st.session_state.pares[0]
                st.session_state.pergunta = pergunta
                st.session_state.palavra = resposta
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.session_state.erros = 0
            st.session_state.acertos = 0
            st.session_state.derrotas = 0
            st.session_state.fim_de_jogo = False
            st.session_state.rodada_encerrada = False
            st.rerun()

        if st.button("SAIR DO JOGO"):
            del st.session_state["jogador"]
            st.session_state.indice = None
            st.session_state.acertos = 0
            st.session_state.derrotas = 0
            st.session_state.pergunta = None
            st.session_state.palavra = None
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.session_state.erros = 0
            st.session_state.fim_de_jogo = False
            st.session_state.rodada_encerrada = False
            st.rerun()
            # Condições de vitória ou derrota
            if st.session_state.erros >= st.session_state.max_erros and not st.session_state.rodada_encerrada:
                st.error("💀 Você foi enforcado! Game Over!")
                st.error(f"A resposta era: {st.session_state.palavra}")
                st.session_state.derrotas += 1
                st.session_state.rodada_encerrada = True
                st.snow()

            elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra) and not st.session_state.rodada_encerrada:
                st.balloons()
                st.success("Parabéns! Você acertou a resposta!")
                st.session_state.acertos += 1
                st.session_state.rodada_encerrada = True

            # Informações da rodada
            st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
            st.write(f"Tentativas restantes: {st.session_state.max_erros - st.session_state.erros}")
        else:
            if st.session_state.fim_de_jogo:
                st.markdown("<h2 style='color:red;'>🏁 FIM DE JOGO</h2>", unsafe_allow_html=True)
                st.write(f"Placar final → Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}")
            else:
                st.info("Clique em **JOGAR** para começar.")
