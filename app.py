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
    st.session_state.indice = -1
    st.session_state.acertos = 0
    st.session_state.derrotas = 0
    st.session_state.pergunta = None
    st.session_state.palavra = None
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0
    st.session_state.max_erros = 6
    st.session_state.fim_de_jogo = False
    st.session_state.novo_arquivo_carregado = False

# ================================
# Funções
# ================================
import unicodedata

def remover_acentos(texto):
    # Transforma 'Á' em 'A', 'Ç' em 'C', etc.
    return "".join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')

def extrair_perguntas_respostas(docx_file):
    try:
        doc = Document(docx_file)
        # Pega apenas linhas que possuem texto real, ignorando as linhas em branco da sua imagem
        linhas =
        
        pares = []
        # Itera de 2 em 2 (Pergunta na linha i, Resposta na linha i+1)
        for i in range(0, len(linhas) - 1, 2):
            pergunta = linhas[i]
            # Limpa a resposta: maiúsculas, sem espaços extras e sem acentos
            resposta_suja = linhas[i+1].upper().strip()
            resposta_limpa = remover_acentos(resposta_suja)
            
            pares.append((pergunta, resposta_limpa))
        
        if not pares:
            st.error("O arquivo parece estar vazio ou fora do padrão (Pergunta na linha 1, Resposta na linha 2).")
            return []
            
        random.shuffle(pares)
        return pares
    except Exception as e:
        st.error(f"Erro ao processar o documento Word: {e}")
        return []


def salvar_no_supabase(arquivo):
    try:
        # Tenta deletar se existir, mas o upsert=True resolve a maioria dos casos
        try:
            supabase.storage.from_("forca").remove(["arquivo_compartilhado.docx"])
        except:
            pass
            
        supabase.storage.from_("forca").upload(
            path="arquivo_compartilhado.docx",
            file=arquivo.getvalue(),
            upsert=True
        )
        # Limpa o estado atual para forçar o recarregamento do novo arquivo
        st.session_state.pares = []
        st.session_state.indice = -1
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.session_state.novo_arquivo_carregado = True
        st.success("Arquivo enviado e carregado com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao enviar arquivo: {e}")

def carregar_do_supabase():
    try:
        response = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
        return BytesIO(response)
    except Exception:
        return None

def carregar_perguntas():
    """Garante que as perguntas sejam baixadas se a lista estiver vazia ou houver novo upload"""
    if st.session_state.novo_arquivo_carregado or not st.session_state.pares:
        arquivo = carregar_do_supabase()
        if arquivo:
            try:
                novos_pares = extrair_perguntas_respostas(arquivo)
                if novos_pares:
                    st.session_state.pares = novos_pares
                    st.session_state.novo_arquivo_carregado = False
            except Exception as e:
                st.error(f"Erro ao ler DOCX: {e}")

def iniciar_nova_pergunta():
    carregar_perguntas()
    if not st.session_state.pares:
        st.warning("Nenhuma pergunta carregada no sistema.")
        return
    
    st.session_state.indice += 1
    if st.session_state.indice < len(st.session_state.pares):
        pergunta, resposta = st.session_state.pares[st.session_state.indice]
        st.session_state.pergunta = pergunta
        st.session_state.palavra = resposta
        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.erros = 0
        st.session_state.fim_de_jogo = False
    else:
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.session_state.fim_de_jogo = True
        st.info("Fim das perguntas disponíveis!")

# ================================
# Fluxo Principal
# ================================
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    st.markdown("<h1 style='color:black;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # ADMIN
    if st.session_state.jogador.lower() == "pratti":
        with st.expander("⚙️ Painel do Administrador"):
            arq = st.file_uploader("Subir novo arquivo de perguntas (.docx)", type=["docx"])
            if st.button("Confirmar e Atualizar Jogo"):
                if arq:
                    salvar_no_supabase(arq)
                else:
                    st.warning("Selecione um arquivo .docx primeiro.")

    # Tenta carregar se a lista estiver vazia
    carregar_perguntas()

    if not st.session_state.pares:
        st.warning("Aguardando o administrador enviar o arquivo de perguntas...")
    else:
        # PLACAR
        st.markdown(
            f"<div style='background-color:#222; color:white; padding:10px; border-radius:5px; margin-bottom:20px;'>"
            f"Jogador: {st.session_state.jogador}<br>"
            f"Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}<br>"
            f"Erros atuais: {st.session_state.erros}/{st.session_state.max_erros}"
            f"</div>", unsafe_allow_html=True
        )

        col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

        with col_forca:
            nome_imagem = f"erro{st.session_state.erros}.png"
            if os.path.exists(nome_imagem):
                st.image(nome_imagem)

        with col_controles:
            if st.button("JOGAR / PRÓXIMA", use_container_width=True):
                iniciar_nova_pergunta()
                st.rerun()
            if st.button("RESETAR GERAL", use_container_width=True):
                # Limpa tudo exceto o nome do jogador
                jogador_atual = st.session_state.jogador
                st.session_state.clear()
                st.session_state.jogador = jogador_atual
                st.rerun()
            if st.button("SAIR", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        with col_jogo:
            if st.session_state.pergunta:
                st.subheader(f"Dica: {st.session_state.pergunta}")
                
                # Monta a visualização da palavra
                exibicao = ""
                for letra in st.session_state.palavra:
                    if letra == " ":
                        exibicao += "  "
                    elif letra in st.session_state.letras_corretas:
                        exibicao += f"{letra} "
                    else:
                        exibicao += "_ "
                
                st.markdown(f"## `{exibicao}`")

                # Teclado Virtual
                letras = [
                    "A","Á","Ã","Â","B","C","Ç","D","E","É","Ê","F","G","H","I","J","K","L","M",
                    "N","O","Ó","Õ","Ô","P","Q","R","S","T","U","Ú","V","W","X","Y","Z"
                ]
                
                venceu = all((l in st.session_state.letras_corretas or l == " ") for l in st.session_state.palavra)
                perdeu = st.session_state.erros >= st.session_state.max_erros
                bloqueado = venceu or perdeu

                cols = st.columns(10)
                for i, l in enumerate(letras):
                    ja_tentou = l in st.session_state.letras_corretas or l in st.session_state.letras_erradas
                    if cols[i%10].button(l, key=f"btn_{l}", disabled=bloqueado or ja_tentou):
                        if l in st.session_state.palavra:
                            st.session_state.letras_corretas.append(l)
                        else:
                            st.session_state.letras_erradas.append(l)
                            st.session_state.erros += 1
                        st.rerun()

                if perdeu:
                    st.error(f"💀 Você perdeu! A palavra era: {st.session_state.palavra}")
                    if not st.session_state.fim_de_jogo:
                        st.session_state.derrotas += 1
                        st.session_state.fim_de_jogo = True
                elif venceu:
                    st.success("🎉 Você venceu!")
                    if not st.session_state.fim_de_jogo:
                        st.session_state.acertos += 1
                        st.session_state.fim_de_jogo = True
            else:
                st.info("Clique em JOGAR para carregar a primeira pergunta.")
