import streamlit as st
import random
import tempfile
import tempfile
import os
from docx import Document
from io import BytesIO
from supabase import create_client

# Configuração do Supabase usando secrets
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]  # sb_secret_...
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# === Inicialização do estado ===
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
        if i+1 < len(linhas):
            pergunta = linhas[i]
            resposta = linhas[i+1].upper()
            pares.append((pergunta, resposta))
    return pares


def salvar_no_supabase(arquivo):
    # cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(arquivo.read())
        tmp_path = tmp.name

    try:
        # upload usando caminho do arquivo
        resp = supabase.storage.from_("forca").upload(
            "arquivo_compartilhado.docx",
            tmp_path
        )
        print(resp)
    finally:
        # remove o arquivo temporário
        os.remove(tmp_path)




def carregar_do_supabase():
    response = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
    return BytesIO(response)

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

# === Fluxo de entrada do jogador ===
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    st.markdown("<h1 style='color:orange;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    if st.session_state.jogador.lower() == "pratti":
        arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])
        if arquivo:
            salvar_no_supabase(arquivo)
            pares = extrair_perguntas_respostas(arquivo)
            st.session_state.pares = pares
        else:
            try:
                arquivo_padrao = carregar_do_supabase()
                pares = extrair_perguntas_respostas(arquivo_padrao)
                st.session_state.pares = pares
            except Exception:
                st.error("Nenhum arquivo disponível no Supabase ainda.")
    else:
        if not st.session_state.pares:
            try:
                arquivo_padrao = carregar_do_supabase()
                pares = extrair_perguntas_respostas(arquivo_padrao)
                st.session_state.pares = pares
            except Exception:
                st.error("Nenhum arquivo disponível no Supabase ainda.")


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

    with col_jogo:
        if st.session_state.pergunta:
            st.markdown(
                f"<div style='background-color:#444; color:white; padding:15px; border-radius:5px; font-size:18px;'>"
                f"{st.session_state.pergunta}</div>",
                unsafe_allow_html=True
            )

            exibicao = " ".join([letra if letra in st.session_state.letras_corretas else "_" 
                                 for letra in st.session_state.palavra])
            st.subheader(exibicao)

            letras = ["A","Á","Â","Ã","À","B","C","Ç","D","E","É","Ê","Ë","F","G","H","I","Í","Î","Ï",
                      "J","K","L","M","N","Ñ","O","Ó","Ô","Õ","Ö","P","Q","R","S","T","U","Ú","Û","Ü","V","W","X","Y","Z"]

            st.markdown("<h3 style='background-color:blue; color:white; padding:5px;'>ESCOLHER UMA LETRA ABAIXO</h3>", unsafe_allow_html=True)

            jogo_ativo = (
                st.session_state.erros < st.session_state.max_erros and
                not all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra)
            )

            cols = st.columns(8, gap="small")
            for i, letra in enumerate(letras):
                with cols[i % 8]:
                    if st.button(letra, key=f"btn_{letra}"):
                        if not jogo_ativo or st.session_state.rodada_encerrada:
                            st.warning("A rodada terminou! Clique em PRÓXIMO para continuar.")
                        else:
                            if letra in st.session_state.palavra:
                                if letra not in st.session_state.letras_corretas:
                                    st.session_state.letras_corretas.append(letra)
                                    st.success(f"Acertou a letra {letra}!")
                                    st.rerun()
                            else:
                                if letra not in st.session_state.letras_erradas:
                                    st.session_state.letras_erradas.append(letra)
                                    st.session_state.erros += 1
                                    st.error(f"A letra {letra} não está na palavra.")
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



# O Streamlit busca os valores que você salvou no painel 'Secrets' automaticamente
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]

URL_SUPABASE = "https://lfgqxphittdatzknwkqw.supabase.co"
KEY_SUPABASE = "sb_publishable_zLiarara0IVVcwQm6oR2IQ_Sb0YOWTe"

