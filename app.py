import streamlit as st
import unicodedata
import random
import time
import os
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO E CONFIGURAÇÃO (APENAS UMA VEZ)
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
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt: texto_bruto.append(txt)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto: texto_bruto.append(txt)
        lista_final = []
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        st.error(f"Erro ao ler o documento Word: {e}")
        return []

# ==================================================
# 2. LOGIN E ESTADO (VERSÃO COM TRAVA DE ADMIN)
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    nome = st.text_input("Digite seu nome para entrar na Arena:", key="input_nome")
    if st.button("ENTRAR NA ARENA"):
        if nome:
            nome_upper = nome.strip().upper()
            st.session_state.jogador = nome_upper
            
            # --- ALTERAÇÃO AQUI ---
            # Só registra no banco de dados se o nome NÃO for o seu
            if nome_upper != "PRATTI":
                supabase.table("forca_disputa_ranking").upsert(
                    {"jogador": nome_upper, "pontos": 0}, 
                    on_conflict="jogador"
                ).execute()
            # ----------------------
            
            st.rerun()
        else:
            st.warning("Por favor, digite um nome.")
    st.stop()


# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def registrar_jogada(letra, jogo_atual):
    lista_antiga = jogo_atual['letras_tentadas']
    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    
    # Se a letra não está na palavra, incrementa erro
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # Atualiza a mesa global com a nova letra e o autor da jogada
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

def reiniciar_arena_completa():
    if "baloes_disparados" in st.session_state:
        del st.session_state.baloes_disparados
    supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
    supabase.table("forca_disputa_arena").update({
        "pergunta": "Aguardando nova pergunta...", "palavra": "ARENA",
        "letras_tentadas": "", "erros": 0, "restantes": 0, "ultimo_jogador": "SISTEMA"
    }).eq("id", 1).execute()
    st.rerun()

# ==================================================
# 4. INTERFACE DA ARENA (CHAMADA ÚNICA)
# ==================================================
@st.fragment(run_every=2)
def arena_viva():
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Mestre Pratti iniciar...")
        return

    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo.get('erros', 0)
        ultimo_player = jogo.get('ultimo_jogador', "SISTEMA")
        
        with c_img:
            nome_img = f"erro{erros_atuais}.png"
            if os.path.exists(nome_img):
                st.image(nome_img, width=180)
            else:
                st.metric("Erros da Equipe", f"{erros_atuais}/6")

        with c_txt:
            contagem = jogo.get('restantes', 0)
            tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
            palavra_alvo = jogo['palavra']
            
            # Verifica se a palavra foi toda descoberta
            vitoria = all((letra == " " or letra in tentadas) for letra in palavra_alvo)

            # --- LÓGICA DE PONTUAÇÃO ÚNICA POR VITÓRIA ---
            if vitoria and erros_atuais < 6:
                # Usamos uma variável de estado local para garantir que o ponto só suba UMA VEZ por palavra
                id_palavra_atual = f"vitoria_{palavra_alvo}_{contagem}"
                if id_palavra_atual not in st.session_state:
                    # Se o jogador atual é quem deu o último palpite certeiro
                    if st.session_state.jogador == ultimo_player:
                        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
                        pts = res_p.data['pontos'] if res_p.data else 0
                        supabase.table("forca_disputa_ranking").update({"pontos": pts + 10}).eq("jogador", st.session_state.jogador).execute()
                        st.toast(f"🏆 +10 pontos por vencer o desafio!")
                    st.session_state[id_palavra_atual] = True

            # --- MENSAGENS DE INTERFACE ---
            if vitoria and contagem == 0:
                st.subheader("🏆 ARENA CONQUISTADA!")
                st.success(f"🌟 **{ultimo_player}** venceu o desafio final!")
                st.balloons()
            elif erros_atuais >= 6 and contagem == 0:
                st.subheader("💀 FIM DA LINHA")
                st.error("A arena caiu no último desafio!")
            else:
                prefixo = f"📝 Pergunta {contagem}" if contagem > 0 else "🔥 PERGUNTA FINAL"
                st.subheader(prefixo)
                st.info(f"❓ **DICA:** {jogo['pergunta']}")

            # Renderização da palavra
            texto_visual = "".join([f"{l} " if (l == " " or l in tentadas or erros_atuais >= 6) else "_ " for l in palavra_alvo])
            st.markdown(f"## `{texto_visual}`")
            st.caption(f"Última jogada por: **{ultimo_player}**")

        # --- BALÕES ---
        if contagem == 0 and (vitoria or erros_atuais >= 6):
            if "baloes_fim" not in st.session_state:
                st.balloons()
                st.session_state.baloes_fim = True

        # Teclado (só aparece se o jogo estiver ativo)
        if not vitoria and erros_atuais < 6:
            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                if cols_tec[i % 9].button(letra, key=f"bt_{letra}", disabled=ja_foi, use_container_width=True):
                    registrar_jogada(letra, jogo)
                    st.rerun()
        elif not (contagem == 0) and vitoria:
             st.info("✅ Palavra correta! Aguardando o Mestre.")

    with col_rank:
        st.markdown("### 🏆 Ranking")
        # Busca todos os jogadores
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).execute()
        
        # Filtra para não mostrar o "PRATTI" na lista visual
        jogadores_faciais = [r for r in res_rank.data if r['jogador'] != "PRATTI"]

        for i, r in enumerate(jogadores_faciais):
            # Cria colunas para colocar o botão de excluir ao lado do nome (só para o admin)
            if st.session_state.jogador == "PRATTI":
                c_nome, c_del = st.columns([4, 1])
                c_nome.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")
                if c_del.button("❌", key=f"del_{r['jogador']}", help=f"Excluir {r['jogador']}"):
                    supabase.table("forca_disputa_ranking").delete().eq("jogador", r['jogador']).execute()
                    st.rerun()
            else:
                # Visualização normal para os outros jogadores (apenas os 10 primeiros)
                if i < 10:
                    st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")

        st.divider()
        
        # CONTROLES EXCLUSIVOS DO ADMINISTRADOR (PRATTI)
        if st.session_state.jogador == "PRATTI":
            st.subheader("🛠️ Gestão da Arena")
            
            # Botão Reiniciar Arena (Acessível apenas ao Pratti)
            if st.button("🔄 REINICIAR ARENA", use_container_width=True):
                reiniciar_arena_completa()
            
            # Botão Excluir Todos
            if st.button("🗑️ EXCLUIR TODOS OS JOGADORES", use_container_width=True, type="primary"):
                # Remove todos da tabela de ranking
                supabase.table("forca_disputa_ranking").delete().neq("jogador", "").execute()
                st.success("Ranking resetado!")
                st.rerun()



# EXECUÇÃO DA ARENA
arena_viva()

# ==================================================
# 5. PAINEL DO ADMIN (PRATTI) - COMPLETO E SEM SIMPLIFICAÇÕES
# ==================================================
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE"):
        # Garante que a fila exista na sessão do Mestre
        if "fila_perguntas" not in st.session_state:
            st.session_state.fila_perguntas = []

        col_adm1, col_adm2 = st.columns(2)
        
        with col_adm1:
            st.markdown("#### 📝 Carregar Desafio")
            # Widget de upload original
            arquivo = st.file_uploader("Arquivo .docx", type=["docx"], key="mestre_upload")
            
            # 1. PROCESSAR ARQUIVO: Mantém sua lógica de extração original
            if st.button("📥 PROCESSAR ARQUIVO"):
                if arquivo:
                    # Chama a função que percorre parágrafos e tabelas do DOCX
                    st.session_state.fila_perguntas = extrair_dados_do_docx(arquivo)
                    st.success(f"{len(st.session_state.fila_perguntas)} questões carregadas!")
                else:
                    st.error("Selecione um arquivo primeiro.")

            # 2. LANÇAR PRÓXIMA: Gerencia a fila e a nova contagem de 'restantes'
            if st.button("🚀 LANÇAR PRÓXIMA PERGUNTA"):
                if st.session_state.fila_perguntas:
                    # Captura o total antes de remover da lista para a contagem visual
                    total_antes_de_tirar = len(st.session_state.fila_perguntas)
                    
                    # Remove a primeira pergunta da fila (Lógica FIFO)
                    proxima = st.session_state.fila_perguntas.pop(0)
                    
                    # Define o valor que vai para a coluna 'restantes' no Supabase:
                    # Se após o pop ainda houver perguntas, manda o número atual.
                    # Se a fila esvaziou, manda 0 (ativando o texto 'PERGUNTA FINAL')
                    valor_para_banco = total_antes_de_tirar if len(st.session_state.fila_perguntas) > 0 else 0

                    # Atualização ATÔMICA no Supabase
                    supabase.table("forca_disputa_arena").update({
                        "pergunta": proxima['pergunta'],
                        "palavra": proxima['resposta'],
                        "letras_tentadas": "",
                        "erros": 0,
                        "restantes": valor_para_banco,
                        "ultimo_jogador": "SISTEMA"
                    }).eq("id", 1).execute()
                    
                    # Força o app a atualizar para o Mestre ver que a fila diminuiu
                    st.rerun()
                else:
                    st.warning("A fila de perguntas está vazia!")
        
        with col_adm2:
            # Informação útil para o mestre controlar a fila
            st.markdown("#### 📊 Status da Fila")
            st.metric("Perguntas na Fila", len(st.session_state.fila_perguntas))
            if st.session_state.fila_perguntas:
                st.write("Próxima pergunta será lançada ao clicar no foguete.")
