import streamlit as st
import unicodedata
import random
import time
import os  # Adicionado para verificar os arquivos de imagem
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO E CONFIGURAÇÃO
# ==================================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Arena da Forca", page_icon="⚔️", layout="wide")

# --- FUNÇÕES DE APOIO ---
def remover_acentos(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        texto_bruto = []
        
        # Mantém sua lógica original de parágrafos
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt: texto_bruto.append(txt)
        
        # Mantém sua lógica original de tabelas
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto: texto_bruto.append(txt)
        
        lista_final = []
        # Agrupa em pares (Pergunta -> Resposta)
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                # Mantém sua limpeza rigorosa de resposta
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                
                lista_final.append({
                    "pergunta": pergunta, 
                    "resposta": resposta
                })
        
        if not lista_final:
            st.warning("Nenhum par de Pergunta/Resposta detectado.")
        return lista_final
    except Exception as e:
        st.error(f"Erro ao ler o documento Word: {e}")
        return []



# ==================================================
# 2. INICIALIZAÇÃO DE ESTADO E LOGIN
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    nome = st.text_input("Digite seu nome para entrar na Arena:", key="input_nome")
    if st.button("ENTRAR NA ARENA"):
        if nome:
            st.session_state.jogador = nome.strip().upper()
            # Registra no ranking se não existir
            supabase.table("forca_disputa_ranking").upsert({"jogador": st.session_state.jogador, "pontos": 0}, on_conflict="jogador").execute()
            st.rerun()
        else:
            st.warning("Por favor, digite um nome.")
    st.stop() # Interrompe a execução aqui até o login ser feito


# ==================================================
# 3. LÓGICA DE JOGO (GLOBAL)
# ==================================================
def registrar_jogada(letra, jogo_atual):
    lista_antiga = jogo_atual['letras_tentadas']
    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # Atualiza mesa global
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

    # Ranking individual
    if letra in jogo_atual['palavra']:
        res = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        pts = res.data['pontos'] if res.data else 0
        supabase.table("forca_disputa_ranking").update({"pontos": pts + 1}).eq("jogador", st.session_state.jogador).execute()

# ==================================================
# 4. INTERFACE DA ARENA (COM IMAGENS)
# ==================================================
st.markdown(f"### 🕹️ Competidor: `{st.session_state.jogador}`")

@st.fragment(run_every=2)
def arena_viva():
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Mestre Pratti iniciar...")
        return

    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        # --- BLOCO DA IMAGEM E PALAVRA ---
        c_img, c_txt = st.columns([1, 2])
        
        erros_atuais = jogo['erros']
        
        with c_img:
            # Busca a imagem baseada nos erros globais do banco
            nome_img = f"erro{erros_atuais}.png"
            if os.path.exists(nome_img):
                st.image(nome_img, width=180)
            else:
                st.metric("Erros da Equipe", f"{erros_atuais}/6")

         with c_txt:
            # --- LÓGICA DE CONTAGEM DE PERGUNTAS ---
            # Busca o valor da coluna 'restantes' que você acabou de criar
            contagem = jogo.get('restantes', 0)

            if contagem > 0:
                st.subheader(f"📝 Esta é a pergunta de número {contagem}")
            else:
                st.subheader("🔥 ESTA É A PERGUNTA FINAL!")

            st.info(f"❓ **DICA:** {jogo['pergunta']}")
            
            tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
            palavra_alvo = jogo['palavra']
            
            vitoria = True
            texto_visual = ""
            for letra in palavra_alvo:
                if letra == " ": texto_visual += "  "
                elif letra in tentadas or erros_atuais >= 6: texto_visual += letra + " "
                else:
                    texto_visual += "_ "
                    vitoria = False
            
            st.markdown(f"## `{texto_visual}`")
            st.caption(f"Última jogada por: **{jogo['ultimo_jogador']}**")

        # --- LÓGICA DE FIM DE JOGO ---
        if vitoria and erros_atuais < 6:
            if contagem == 0:
                st.success("🎉 VITÓRIA FINAL DA EQUIPE!")
                # st.balloons()  <-- Desativado
            else:
                st.info(f"✅ Palavra correta! Aguardando o Mestre lançar a próxima.")
        
        elif erros_atuais >= 6:
            st.error(f"💀 DERROTA! A resposta era: {palavra_alvo}")
            if contagem == 0:
                st.error("Fim de jogo. A arena caiu no último desafio!")
                # st.snow()
                # st.balloons() <-- Desativado
       
        else:
            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                if cols_tec[i % 9].button(letra, key=f"bt_{letra}", disabled=ja_foi, use_container_width=True):
                    registrar_jogada(letra, jogo)
                    st.rerun()

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
        for i, r in enumerate(res_rank.data):
            st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")

arena_viva()


# ==================================================
# 5. PAINEL DO ADMIN (PRATTI)
# ==================================================
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE"):
        if "fila_perguntas" not in st.session_state:
            st.session_state.fila_perguntas = []

        col_adm1, col_adm2 = st.columns(2)
        
        with col_adm1:
            st.markdown("#### 📝 Carregar Desafio")
            arquivo = st.file_uploader("Arquivo .docx", type=["docx"], key="mestre_upload")
            
            if st.button("📥 PROCESSAR ARQUIVO"):
                if arquivo:
                    st.session_state.fila_perguntas = extrair_dados_do_docx(arquivo)
                    st.success(f"{len(st.session_state.fila_perguntas)} questões carregadas!")
                else:
                    st.error("Selecione um arquivo primeiro.")

            if st.button("🚀 LANÇAR PRÓXIMA PERGUNTA"):
                if st.session_state.fila_perguntas:
                    # Pega o total na fila antes de remover
                    total_antes_de_tirar = len(st.session_state.fila_perguntas)
                    proxima = st.session_state.fila_perguntas.pop(0)
                    
                    # Se restar algo na fila após tirar esta, manda o número atual.
                    # Se não restar nada, manda 0 para indicar que é a Pergunta Final.
                    valor_para_banco = total_antes_de_tirar if len(st.session_state.fila_perguntas) > 0 else 0

                    supabase.table("forca_disputa_arena").update({
                        "pergunta": proxima['pergunta'],
                        "palavra": proxima['resposta'],
                        "letras_tentadas": "",
                        "erros": 0,
                        "restantes": valor_para_banco, # Atualizando sua nova coluna
                        "ultimo_jogador": "SISTEMA"
                    }).eq("id", 1).execute()
                    st.rerun()
                else:
                    st.warning("A fila de perguntas está vazia!")

