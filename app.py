import streamlit as st
import os
from docx import Document
from io import BytesIO
from supabase import create_client

URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

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

def extrair_perguntas_respostas(docx_file):
    doc = Document(docx_file)
    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    pares = []
    for i in range(0, len(linhas), 2):
        if i + 1 < len(linhas):
            pergunta = linhas[i]
            resposta = linhas[i+1].upper()
            pares.append((pergunta, resposta))
    return pares

def salvar_no_supabase(arquivo):
    try:
        supabase.storage.from_("forca").upload(
            "arquivo_compartilhado.docx",
            arquivo.getvalue(),
            {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "upsert": "true"}
        )
        st.success("Arquivo enviado para o Supabase!")
    except Exception as e:
        st.error(f"Erro ao enviar arquivo: {e}")

def carregar_do_supabase():
    try:
        response = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
        return BytesIO(response)
    except Exception:
        return None

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

if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    st.markdown("<h1 style='color:black;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

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

    # cria as colunas
    col_forca, col_controles, col_jogo = st.columns([1,0.8,2])
    
    # coluna da forca
    with col_forca:
        nome_imagem = f"erro{st.session_state.erros}.png"
        if os.path.exists(nome_imagem):
            st.image(nome_imagem)
        else:
            st.warning(f"Imagem {nome_imagem} não encontrada.")
    
    # coluna dos controles
    with col_controles:
        st.markdown(
            """
            <style>
            div.stButton > button {
                font-size: 20px !important;
                font-weight: bold;
                height: 55px !important;      /* altura fixa */
                width: 220px !important;      /* largura fixa */
                margin: 6px 0;
                border-radius: 6px;
                white-space: nowrap;          /* impede quebra de linha */
                text-align: center;
                justify-content: center;
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
        if st.button("SAIR", key="btn_sair"):
            st.session_state.clear()
            st.rerun()

# coluna do jogo
    with col_jogo:
        if st.session_state.pergunta:
            st.subheader(st.session_state.pergunta)

            exibicao = " ".join(
                letra if letra in st.session_state.letras_corretas else "_"
                for letra in st.session_state.palavra
            )
            st.markdown(f"## {exibicao}")

            st.markdown(
                """
                <style>
                div[data-testid="stHorizontalBlock"] div.stButton > button {
                    background-color: #111 !important;
                    color: white !important;
                    font-size: 100px !important;
                    font-weight: bold;
                    height: 80px !important;
                    width: 80px !important;
                    margin: 4px;
                    border-radius: 8px;
                }
                div[data-testid="stHorizontalBlock"] div.stButton > button:disabled {
                    background-color: #888 !important;
                    color: #aaa !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

              # teclado de letras em português
            letras = [
                "A","Á","Ã","Â","B","C","Ç","D","E","É","Ê","F","G","H","I","J","K","L","M",
                "N","O","Ó","Õ","Ô","P","Q","R","S","T","U","Ú","V","W","X","Y","Z"
            ]
            
            # condição de bloqueio: se perdeu ou ganhou
            bloqueado = (
                st.session_state.erros >= st.session_state.max_erros or
                (st.session_state.palavra and all(
                    l in st.session_state.letras_corretas for l in st.session_state.palavra
                ))
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
