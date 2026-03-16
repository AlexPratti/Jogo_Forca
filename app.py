import streamlit as st
import os
import random
import unicodedata
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONFIGURAÇÃO DO SUPABASE
# ==================================================
# Certifique-se que estas chaves estão no seu secrets do Streamlit
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# ==================================================
# 2. FUNÇÕES DE APOIO
# ==================================================

def remover_acentos(texto):
    """Remove acentos e cedilha para não quebrar o jogo"""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    """Lê o Word e ignora as linhas vazias (conforme sua imagem)"""
    try:
        doc = Document(arquivo_docx)
        textos_reais = []
        
        # Percorre o Word e pega apenas o que tem texto escrito
        for p in doc.paragraphs:
            texto_limpo = p.text.strip()
            if texto_limpo:
                textos_reais.append(texto_limpo)
        
        # Monta os pares: Pergunta (linha 1), Resposta (linha 2)...
        lista_final = []
        for i in range(0, len(textos_reais) - 1, 2):
            pergunta = textos_reais[i]
            # Resposta fica em maiúsculo e sem acentos
            resposta = remover_acentos(textos_reais[i+1].upper())
            lista_final.append({"pergunta": pergunta, "resposta": resposta})
        
        random.shuffle(lista_final)
        return lista_final
    except Exception as e:
        st.error(f"Erro ao processar o Word: {e}")
        return []

# ==================================================
# 3. INICIALIZAÇÃO DO ESTADO (SESSION STATE)
# ==================================================
if 'pares' not in st.session_state:
    st.session_state.pares = []
    st.session_state.indice = -1
    st.session_state.acertos = 0
    st.session_state.derrotas = 0
    st.session_state.pergunta = ""
    st.session_state.palavra = ""
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0
    st.session_state.max_erros = 6
    st.session_state.fim_da_rodada = False
    st.session_state.precisa_recarregar = False

# ==================================================
# 4. TELA DE LOGIN
# ==================================================
if "jogador" not in st.session_state:
    st.title("🎮 Bem-vindo ao Jogo da Forca")
    nome_digitado = st.text_input("Quem está jogando?")
    if st.button("Entrar no Jogo") and nome_digitado.strip():
        st.session_state.jogador = nome_digitado.strip().upper()
        st.rerun()
    st.stop()

# ==================================================
# 5. INTERFACE DO JOGO
# ==================================================
st.markdown(f"## JOGO DA FORCA - JOGADOR: {st.session_state.jogador}")

# PAINEL DO ADMINISTRADOR (PRATTI)
if st.session_state.jogador == "PRATTI":
    with st.expander("⚙️ PAINEL DO ADMIN (Upload de Perguntas)"):
        arquivo_subido = st.file_uploader("Suba o arquivo .docx", type=["docx"])
        if st.button("SALVAR E ATUALIZAR JOGO"):
            if arquivo_subido:
                try:
                    # Envia para o Supabase Storage
                    supabase.storage.from_("forca").upload(
                        path="arquivo_compartilhado.docx",
                        file=arquivo_subido.getvalue(),
                        file_options={"upsert": True}
                    )

                    
                    # Reseta o jogo para carregar as novas perguntas
                    st.session_state.pares = []
                    st.session_state.precisa_recarregar = True
                    st.success("Perguntas atualizadas com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro no Supabase: {e}")

# CARREGAR PERGUNTAS DO SERVIDOR
if not st.session_state.pares or st.session_state.precisa_recarregar:
    try:
        conteudo_download = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
        st.session_state.pares = extrair_dados_do_docx(BytesIO(conteudo_download))
        st.session_state.precisa_recarregar = False
    except:
        st.info("Aguardando o administrador subir o primeiro arquivo de perguntas.")

# SE JÁ TIVER PERGUNTAS CARREGADAS
if st.session_state.pares:
    
    col_placar, col_vazio = st.columns([2, 1])
    with col_placar:
        st.write(f"🏆 Acertos: **{st.session_state.acertos}** | 💀 Derrotas: **{st.session_state.derrotas}**")
        st.write(f"⚠️ Erros: **{st.session_state.erros} / {st.session_state.max_erros}**")

    st.divider()

    col_img, col_controles, col_teclado = st.columns([1, 1, 2])

    with col_img:
        # Tenta carregar a imagem da forca baseada no número de erros
        caminho_imagem = f"erro{st.session_state.erros}.png"
        if os.path.exists(caminho_imagem):
            st.image(caminho_imagem, width=180)
        else:
            st.write(f"Forca: {st.session_state.erros} erros")

    with col_controles:
        if st.button("🚀 JOGAR", use_container_width=True):
            st.session_state.indice += 1
            if st.session_state.indice < len(st.session_state.pares):
                item_atual = st.session_state.pares[st.session_state.indice]
                st.session_state.pergunta = item_atual["pergunta"]
                st.session_state.palavra = item_atual["resposta"]
                st.session_state.letras_corretas = []
                st.session_state.letras_erradas = []
                st.session_state.erros = 0
                st.session_state.fim_da_rodada = False
            else:
                st.warning("Todas as perguntas foram respondidas!")
            st.rerun()

    with col_teclado:
        if st.session_state.palavra:
            st.subheader(f"Dica: {st.session_state.pergunta}")
            
            # Desenha a palavra na tela (ex: _ _ A _ _)
            texto_exibicao = ""
            for letra in st.session_state.palavra:
                if letra == " ":
                    texto_exibicao += "  "
                elif letra in st.session_state.letras_corretas:
                    texto_exibicao += f"{letra} "
                else:
                    texto_exibicao += "_ "
            st.markdown(f"## `{texto_exibicao}`")

            # Teclado Virtual
            alfabeto_completo = "AÁÃÂBCÇDEÉÊFGHIÍJKLMNOÓÕÔPQRSTUÚVWXYZ-"
            venceu = all(l in st.session_state.letras_corretas or l == " " for l in st.session_state.palavra)
            perdeu = st.session_state.erros >= st.session_state.max_erros
            
            colunas_teclas = st.columns(9)
            for i, letra_tecla in enumerate(alfabeto_completo):
                ja_foi = letra_tecla in st.session_state.letras_corretas or letra_tecla in st.session_state.letras_erradas
                
                if colunas_teclas[i % 9].button(letra_tecla, key=f"t_{letra_tecla}", disabled=ja_foi or venceu or perdeu):
                    if letra_tecla in st.session_state.palavra:
                        st.session_state.letras_corretas.append(letra_tecla)
                    else:
                        st.session_state.letras_erradas.append(letra_tecla)
                        st.session_state.erros += 1
                    st.rerun()

            # Mensagens de Vitória/Derrota
            if venceu and not st.session_state.fim_da_rodada:
                st.success("🎉 Você acertou!")
                st.session_state.acertos += 1
                st.session_state.fim_da_rodada = True
            elif perdeu and not st.session_state.fim_da_rodada:
                st.error(f"💀 Você perdeu! A palavra era: {st.session_state.palavra}")
                st.session_state.derrotas += 1
                st.session_state.fim_da_rodada = True
        else:
            st.info("Clique no botão PRÓXIMA PERGUNTA para começar!")

# Botão de sair na lateral
if st.sidebar.button("Sair do Jogo"):
    st.session_state.clear()
    st.rerun()
