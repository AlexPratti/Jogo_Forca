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
        # 1. Extrai absolutamente todo o texto de parágrafos e tabelas
        texto_bruto = []
        
        # Pega textos de parágrafos
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                texto_bruto.append(txt)
        
        # Pega textos de tabelas (caso existam)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto:
                        texto_bruto.append(txt)
        
        lista_final = []
        # 2. Agrupa em pares (Pergunta -> Próxima linha disponível)
        # O range pula de 2 em 2, garantindo o par pergunta/resposta
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                # Limpa a resposta: remove acentos e caracteres especiais de espaço
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                
                lista_final.append({
                    "pergunta": pergunta, 
                    "resposta": resposta
                })
        
        if not lista_final:
            st.warning("Nenhum par de Pergunta/Resposta foi detectado no arquivo.")
            
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

        # --- LÓGICA DE FIM DE JOGO E TECLADO ---
        if vitoria and erros_atuais < 6:
            st.success("🎉 VITÓRIA COLETIVA!")
            st.balloons()
        elif erros_atuais >= 6:
            st.error(f"💀 DERROTA! A resposta era: {palavra_alvo}")
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
        col_adm1, col_adm2 = st.columns(2)
        
        with col_adm1:
            st.markdown("#### 📝 Carregar Desafio")
            arquivo = st.file_uploader("Arquivo .docx", type=["docx"])
            if st.button("🚀 LANÇAR NOVA PALAVRA") and arquivo:
                lista_q = extrair_dados_do_docx(arquivo)
                if lista_q:
                    esc = random.choice(lista_q)
                    supabase.table("forca_disputa_arena").update({
                        "pergunta": esc['pergunta'], 
                        "palavra": esc['resposta'],
                        "letras_tentadas": "", 
                        "erros": 0, 
                        "ultimo_jogador": "Mestre Pratti"
                    }).eq("id", 1).execute()
                    st.success(f"Nova rodada lançada: {len(lista_q)} questões carregadas!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("O arquivo Word parece estar vazio ou fora do padrão.")

        with col_adm2:
            st.markdown("#### 🛡️ Gestão da Arena")
            
            if st.button("🧹 ZERAR APENAS RANKING", use_container_width=True):
                supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
                st.toast("Ranking zerado!")
                time.sleep(1)
                st.rerun()

            # Botão de Reset Total para emergências ou nova aula
            if st.button("💥 RESET TOTAL DA ARENA", type="primary", use_container_width=True):
                # Limpa a Arena
                supabase.table("forca_disputa_arena").update({
                    "pergunta": "AGUARDANDO MESTRE...", 
                    "palavra": "",
                    "letras_tentadas": "", 
                    "erros": 0, 
                    "ultimo_jogador": "SISTEMA"
                }).eq("id", 1).execute()
                
                # Zera o Ranking
                supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
                
                st.warning("Tudo foi resetado!")
                time.sleep(1.5)
                st.rerun()

    # Log de segurança para você ver o que está no banco (opcional)
    st.caption(f"Conectado ao Supabase: {URL_SUPABASE}")
