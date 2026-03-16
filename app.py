import streamlit as st
import os
from docx import Document
from io import BytesIO
from supabase import create_client
import random

# ================================
# Configuração Supabase
# ================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# ================================
# Inicialização do estado
# ================================
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

# ================================
# Funções
# ================================
def extrair_perguntas_respostas(docx_file):
    """Extrai pares (pergunta, resposta) do arquivo docx"""
    doc = Document(docx_file)
    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    pares = []
    for i in range(0, len(linhas)-1, 2):
        pergunta = linhas[i]
        resposta = linhas[i+1].upper()
        pares.append((pergunta, resposta))
    random.shuffle(pares)  # embaralha perguntas
    return pares

def salvar_no_supabase(arquivo):
    """Salva arquivo no Supabase"""
    try:
        try:
            supabase.storage.from_("forca").remove(["arquivo_compartilhado.docx"])
        except:
            pass
        supabase.storage.from_("forca").upload(
            path="arquivo_compartilhado.docx",
            file=arquivo.getvalue()
        )
        st.success("Arquivo enviado para o Supabase!")
    except Exception as e:
        st.error(f"Erro ao enviar arquivo: {e}")

def carregar_do_supabase():
    """Carrega arquivo do Supabase"""
    try:
        response = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
        return BytesIO(response)
    except Exception:
        return None

def carregar_perguntas():
    """Carrega perguntas do Supabase se ainda não carregadas"""
    if st.session_state.pares:
        return
    arquivo = carregar_do_supabase()
    if arquivo:
        st.session_state.pares = extrair_perguntas_respostas(arquivo)

def iniciar_nova_pergunta():
    """Inicia próxima pergunta"""
    carregar_perguntas()  # garante que pares estejam carregados
    if not st.session_state.pares:
        st.warning("Nenhuma pergunta carregada.")
        return

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

# ================================
# Entrada do jogador
# ================================
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()

else:
    st.markdown("<h1 style='color:black;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # ================================
    # ADMIN
    # ================================
    if st.session_state.jogador.lower() == "pratti":
        arquivo = st.file_uploader("Carregar perguntas (.docx)", type=["docx"])
        if arquivo:
            salvar_no_supabase(arquivo)
            st.session_state.pares = extrair_perguntas_respostas(arquivo)
            st.session_state.indice = None
            st.session_state.pergunta = None
            st.session_state.palavra = None
            st.success("Novo arquivo carregado!")

    # ================================
    # JOGADOR NORMAL
    # ================================
    carregar_perguntas()

    if not st.session_state.pares:
        st.warning("Nenhuma pergunta encontrada. O administrador precisa enviar um arquivo.")

    # ================================
    # PLACAR
    # ================================
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

    # ================================
    # Layout
    # ================================
    col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

    # ================================
    # IMAGEM DA FORCA
    # ================================
    with col_forca:
        nome_imagem = f"erro{st.session_state.erros}.png"
        if os.path.exists(nome_imagem):
            st.image(nome_imagem)
        else:
            st.warning(f"Imagem {nome_imagem} não encontrada.")

    # ================================
    # CONTROLES
    # ================================
    with col_controles:
        label_btn = "JOGAR" if st.session_state.indice is None else "PRÓXIMO"
        if st.button(label_btn, key="btn_jogar"):
            iniciar_nova_pergunta()
            st.rerun()
        if st.button("RESETAR", key="btn_resetar"):
            st.session_state.clear()
            st.rerun()
        if st.button("SAIR", key="btn_sair"):
            st.session_state.clear()
            st.rerun()

    # ================================
    # JOGO
    # ================================
    with col_jogo:
        if st.session_state.pergunta:
            st.subheader(st.session_state.pergunta)
            exibicao = " ".join(
                letra if letra in st.session_state.letras_corretas else "_"
                for letra in st.session_state.palavra
            )
            st.markdown(f"## {exibicao}")

            # teclado de letras
            letras = [
                "A","Á","Ã","Â","B","C","Ç","D","E","É","Ê","F","G","H","I","J","K","L","M",
                "N","O","Ó","Õ","Ô","P","Q","R","S","T","U","Ú","V","W","X","Y","Z"
            ]

            bloqueado = (
                st.session_state.erros >= st.session_state.max_erros or
                (st.session_state.palavra and all(l in st.session_state.letras_corretas for l in st.session_state.palavra))
            )

            cols = st.columns(10)
            for i, l in enumerate(letras):
                disabled = bloqueado or l in st.session_state.letras_corretas or l in st.session_state.letras_erradas
                if cols[i % 10].button(l, key=f"btn_{l}", disabled=disabled):
                    if l in st.session_state.palavra:
                        st.session_state.letras_corretas.append(l)
                    else:
                        st.session_state.letras_erradas.append(l)
                        st.session_state.erros += 1
                    st.rerun()

            # condição de derrota
            if st.session_state.erros >= st.session_state.max_erros:
                st.error("💀 Você perdeu!")
                st.write(f"A palavra era: {st.session_state.palavra}")
                st.session_state.derrotas += 1

            # condição de vitória
            elif st.session_state.palavra and all(
                l in st.session_state.letras_corretas for l in st.session_state.palavra
            ):
                st.success("🎉 Você venceu!")
                st.session_state.acertos += 1

        else:
            st.info("Clique em JOGAR para começar.")
