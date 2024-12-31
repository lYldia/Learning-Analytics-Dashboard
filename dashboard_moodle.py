import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3


# Carregar os dados CSV e salvar no SQLite
df_programacao_202101 = pd.read_csv('202101_anonimizado.csv')
df_programacao_202102 = pd.read_csv('202102_anonimizado.csv')
df_programacao_202201 = pd.read_csv('202201_anonimizado.csv')
df_programacao_202202 = pd.read_csv('202202_anonimizado.csv')
df_programacao_202301 = pd.read_csv('202301_anonimizado.csv')

# Dicionário para acesso aos dados por semestre
dfs = {
    '2021.1': df_programacao_202101,
    '2021.2': df_programacao_202102,
    '2022.1': df_programacao_202201,
    '2022.2': df_programacao_202202,
    '2023.1': df_programacao_202301
}

# Painel lateral para filtros
st.sidebar.header("Filtros de Visualização")

# 1. Filtro para selecionar se é Acesso ou Distribuição
opcao_tipo = st.sidebar.radio("Selecione o Tipo", ("Interação", "Distribuição"))

# 2. Exibir o selectbox de tipo de visualização apenas se o tipo for Acesso ou Distribuição
tipo_visualizacao = None
if opcao_tipo in ["Interação", "Distribuição"]:
    tipo_visualizacao = st.sidebar.selectbox("Selecione o Tipo de Visualização", ["Avaliação", "Conteúdo"])

semestres_selecionados = st.multiselect("Selecione o(s) Semestre(s)", list(dfs.keys()))
if semestres_selecionados:
    # Adicionar a coluna 'Semestre' para identificar o semestre de cada evento
    for semestre in semestres_selecionados:
        dfs[semestre]['Semestre'] = semestre  # Adiciona a coluna 'Semestre' aos dados

    # Combinar os DataFrames dos semestres selecionados
    df_completo = pd.concat([dfs[semestre] for semestre in semestres_selecionados])

    # Função para gerar gráficos comparativos por semestre
    def gerar_grafico_comparativo(df, coluna_tipo, titulo, unico=False):
        # Contagem das strings únicas por semestre e tipo
        df_tipo = df.groupby(['Semestre', coluna_tipo])['Contexto do Evento'].nunique().reset_index(name='Strings Únicas')

        # Agora, somamos as ocorrências únicas de todos os meses dentro do semestre (para o tipo)
        df_tipo_semestre = df_tipo.groupby(['Semestre', coluna_tipo])['Strings Únicas'].sum().reset_index()

        # Exibir a tabela com a contagem de strings únicas por semestre e tipo
        st.write(f"Tabela de Contagem de Strings Únicas por Semestre e {coluna_tipo}:")
        st.dataframe(df_tipo_semestre)

        # Gerar o gráfico de barras comparando os semestres
        fig = go.bar(df_tipo_semestre,
                     x='Semestre',  # Apenas os semestres aparecem no eixo X
                     y='Strings Únicas',
                     color=coluna_tipo,
                     title=titulo)
        
        # Modificando a configuração do gráfico para garantir que apenas os rótulos de semestre apareçam no eixo X
        fig.update_layout(xaxis_tickmode='array', 
                          xaxis_tickvals=semestres_selecionados,
                          xaxis_tickangle=90
                          )
        st.plotly_chart(fig)

    # 4. Lógica para escolher os tipos de gráficos dependendo da opção selecionada
    if opcao_tipo == "Interação":
        if tipo_visualizacao == "Avaliação":
            avaliacao_interesse = ['Fórum', 'Laboratório', 'Tarefa', 'Questionário', 'Trabalho', 'Atividade', 'Exercício', 'Projeto']
            
            # Filtra o tipo de avaliação de interesse
            df_completo['Tipo de Avaliação'] = df_completo['Contexto do Evento'].apply(lambda x: next((tipo for tipo in avaliacao_interesse if tipo.lower() in x.lower()), None))

            # Filtra os dados para os conteúdos de interesse
            df_avaliacao_ocorrencias = df_completo[df_completo['Tipo de Avaliação'].notna()]

            # Classificar os alunos como aprovados ou reprovados com base na nota
            df_avaliacao_ocorrencias['Status'] = df_avaliacao_ocorrencias['Total do curso (Real)'].apply(lambda x: 'Aprv' if x >= 6.0 else 'Reprv')

            # Filtro de semestre (sem alterações no comportamento do filtro)
            if len(semestres_selecionados) > 1:
                # Criar uma matriz de subgráficos empilhados verticalmente
                fig = make_subplots(
                    rows=len(semestres_selecionados), cols=1,  # Um gráfico por linha
                    subplot_titles=semestres_selecionados,
                    shared_xaxes=True,  # Eixo X compartilhado
                    vertical_spacing=0.1
                )

                # Para cada semestre selecionado, criar um gráfico de barras verticais
                for i, semestre in enumerate(semestres_selecionados):
                    # Filtra os dados para o semestre específico
                    df_semestre = df_avaliacao_ocorrencias[df_avaliacao_ocorrencias['Semestre'] == semestre]
                    
                    # Contagem das ocorrências únicas por tipo de avaliação e status (Aprovado/Reprovado)
                    df_avaliacao_unicos = df_semestre.groupby(['Tipo de Avaliação', 'Status'])['Nome completo'].nunique().reset_index(name='Acessos')

                    # Criação de barras verticais para o gráfico
                    for status in ['Aprv', 'Reprv']:
                        df_status = df_avaliacao_unicos[df_avaliacao_unicos['Status'] == status]

                        # Adiciona o gráfico de barras verticais para o subgráfico correspondente
                        fig.add_trace(
                            go.Bar(
                                x=df_status['Tipo de Avaliação'],  # Tipos de avaliação
                                y=df_status['Acessos'],  # Contagem de acessos
                                name=status,  # Nome da barra (Aprovado/Reprovado)
                                orientation='v',  # Barra vertical
                                marker_color='green' if status == 'Aprv' else 'red',  # Cor das barras
                                opacity=0.7,
                                showlegend=(i == 0)  # Mostrar legenda apenas no primeiro gráfico
                            ),
                            row=i + 1, col=1  # Alterado para empilhar verticalmente
                        )

                fig.update_layout(
                    title="Proporção de Acessos por Avaliação ao Longo dos Semestres",
                    barmode='group',  # Para agrupar as barras de Aprovado e Reprovado
                    showlegend=True,
                    width=1000,
                    height=400 * len(semestres_selecionados),  # Aumentar a altura com base no número de semestres
                    yaxis_title="Acessos",
                    xaxis_title="Tipo de Avaliação"
                )

                # Garantir que o eixo X apareça em todos os gráficos
                for i in range(len(semestres_selecionados)):
                    fig.update_yaxes(title_text="Acessos", row=i+1, col=1)
                    fig.update_xaxes(title_text="Tipo de Avaliação", row=i+1, col=1, showticklabels=True)  # Aqui garantimos que o eixo X será visível em todos

                st.plotly_chart(fig)

            else:
                # Se apenas um semestre for selecionado, mostra o gráfico de barras verticais
                semestre = semestres_selecionados[0]

                # Filtra os dados para o semestre selecionado
                df_semestre = df_avaliacao_ocorrencias[df_avaliacao_ocorrencias['Semestre'] == semestre]

                # Contagem das ocorrências únicas por tipo de avaliação e status (Aprovado/Reprovado)
                df_avaliacao_unicos = df_semestre.groupby(['Tipo de Avaliação', 'Status'])['Nome completo'].nunique().reset_index(name='Acessos')

                fig = go.Figure()

                # Adiciona as barras para Aprovado e Reprovado
                for status in ['Aprv', 'Reprv']:
                    df_status = df_avaliacao_unicos[df_avaliacao_unicos['Status'] == status]
                    fig.add_trace(
                        go.Bar(
                            x=df_status['Tipo de Avaliação'],  # Tipos de avaliação
                            y=df_status['Acessos'],  # Contagem de acessos
                            name=status,  # Nome da barra (Aprovado/Reprovado)
                            orientation='v',  # Barra vertical
                            marker_color='green' if status == 'Aprv' else 'red',  # Cor das barras
                            opacity=0.7
                        )
                    )

                fig.update_layout(
                    title=f"Proporção de Acessos por Avaliação no Semestre {semestre}",
                    barmode='group',  # Para agrupar as barras de Aprovado e Reprovado
                    yaxis_title="Acessos",
                    xaxis_title="Tipo de Avaliação",
                    xaxis_tickangle=0,
                    showlegend=True
                )

                st.plotly_chart(fig)

        elif tipo_visualizacao == "Conteúdo":
            conteudo_interesse = ['POO', 'Comandos', 'Entrada de dados', 'Operadores', 'Classe', 'Encapsulamento', 'Herança', 'Polimorfismo', 'Vetores', 'ArrayList', 'Composição', 'Agregação']
            
            # Filtra o tipo de avaliação de interesse
            df_completo['Tipo de Conteúdo'] = df_completo['Contexto do Evento'].apply(lambda x: next((tipo for tipo in conteudo_interesse if tipo.lower() in x.lower()), None))

            # Filtra os dados para os conteúdos de interesse
            df_conteudo_ocorrencias = df_completo[df_completo['Tipo de Conteúdo'].notna()]

            # Classificar os alunos como aprovados ou reprovados com base na nota
            df_conteudo_ocorrencias['Status'] = df_conteudo_ocorrencias['Total do curso (Real)'].apply(lambda x: 'Aprv' if x >= 6.0 else 'Reprv')

            # Filtro de semestre (sem alterações no comportamento do filtro)
            if len(semestres_selecionados) > 1:
                # Criar uma matriz de subgráficos empilhados verticalmente
                fig1 = make_subplots(
                    rows=len(semestres_selecionados), cols=1,  # Um gráfico por linha
                    subplot_titles=semestres_selecionados,
                    shared_xaxes=True,  # Eixo X compartilhado
                    vertical_spacing=0.1
                )

                # Para cada semestre selecionado, criar um gráfico de barras verticais
                for i, semestre in enumerate(semestres_selecionados):
                    # Filtra os dados para o semestre específico
                    df_semestre = df_conteudo_ocorrencias[df_conteudo_ocorrencias['Semestre'] == semestre]
                    
                    # Contagem das ocorrências únicas por tipo de conteúdo e status (Aprovado/Reprovado)
                    df_conteudo_unicos = df_semestre.groupby(['Tipo de Conteúdo', 'Status'])['Nome completo'].nunique().reset_index(name='Acessos')

                    # Criação de barras verticais para o gráfico
                    for status in ['Aprv', 'Reprv']:
                        df_status = df_conteudo_unicos[df_conteudo_unicos['Status'] == status]

                        # Adiciona o gráfico de barras verticais para o subgráfico correspondente
                        fig1.add_trace(
                            go.Bar(
                                x=df_status['Tipo de Conteúdo'],  # Tipos de conteúdo
                                y=df_status['Acessos'],  # Contagem de acessos
                                name=status,  # Nome da barra (Aprovado/Reprovado)
                                orientation='v',  # Barra vertical
                                marker_color='green' if status == 'Aprv' else 'red',  # Cor das barras
                                opacity=0.7,
                                showlegend=(i == 0)  # Mostrar legenda apenas no primeiro gráfico
                            ),
                            row=i + 1, col=1  # Alterado para empilhar verticalmente
                        )

                fig1.update_layout(
                    title="Proporção de Acessos por Conteúdo ao Longo dos Semestres",
                    barmode='group',  # Para agrupar as barras de Aprovado e Reprovado
                    showlegend=True,
                    width=1000,
                    height=400 * len(semestres_selecionados),  # Aumentar a altura com base no número de semestres
                    yaxis_title="Acessos",
                    xaxis_title="Tipo de Conteúdo"
                )

                # Garantir que o eixo X apareça em todos os gráficos
                for i in range(len(semestres_selecionados)):
                    fig1.update_yaxes(title_text="Acessos", row=i+1, col=1)
                    fig1.update_xaxes(title_text="Tipo de Conteúdo", row=i+1, col=1, showticklabels=True)  # Aqui garantimos que o eixo X será visível em todos

                st.plotly_chart(fig1)
                
    elif opcao_tipo == "Distribuição":
        if tipo_visualizacao == "Avaliação":
            tipo_avaliacao = ['Fórum', 'Laboratório', 'Tarefa', 'Questionário', 'Trabalho', 'Atividade', 'Exercício', 'Projeto']
            df_completo['Tipo de Avaliação'] = df_completo['Contexto do Evento'].apply(lambda x: next((tipo for tipo in tipo_avaliacao if tipo.lower() in x.lower()), None))

            # Filtra os dados para os conteúdos de interesse
            df_avaliacao_frequencia = df_completo[df_completo['Tipo de Avaliação'].notna()] 

            # Se mais de um semestre for selecionado, mostra uma matriz de gráficos de barras empilhadas
            if len(semestres_selecionados) > 1:
                fig3 = make_subplots(
                    rows=len(semestres_selecionados), cols=1,  # Alteração: agora são várias linhas
                    subplot_titles=semestres_selecionados,
                    vertical_spacing=0.1
                )

                # Para cada semestre selecionado, calcular as ocorrências únicas e criar um gráfico de barras empilhadas
                for i, semestre in enumerate(semestres_selecionados):
                    # Filtra os dados para o semestre específico
                    df_semestre = df_avaliacao_frequencia[df_avaliacao_frequencia['Semestre'] == semestre]
                    
                    # Contagem das ocorrências únicas por semestre e tipo de conteúdo
                    freq_unica_avaliacao = df_semestre.groupby(['Tipo de Avaliação', 'Semestre'])['Contexto do Evento'].nunique().reset_index(name='Quantidade')

                    # Gerar a distribuição de ocorrências únicas de conteúdo para esse semestre
                    freq_unica_avaliacao = freq_unica_avaliacao.groupby(['Tipo de Avaliação'])['Quantidade'].sum().reset_index()

                    # Adiciona o gráfico de barras empilhadas para o semestre correspondente
                    fig3.add_trace(
                        go.Bar(
                            y=freq_unica_avaliacao['Tipo de Avaliação'],
                            x=freq_unica_avaliacao['Quantidade'],
                            name=semestre,
                            orientation='h'
                        ),
                        row=i + 1, col=1  # Ajuste para os gráficos estarem na coluna única
                    )

                    # Atualiza o eixo X de cada gráfico para garantir que ele mostre os rótulos
                    fig3.update_xaxes(
                        tickangle=0,
                        row=i + 1, col=1
                    )

                fig3.update_layout(
                    title="Distribuição de Avaliação ao Longo dos Semestres",
                    barmode='stack',
                    showlegend=False,
                    width=600,
                    height=400 * len(semestres_selecionados),  # Ajusta a altura total com base na quantidade de semestres
                )

                st.plotly_chart(fig3)

            else:
                # Caso apenas um semestre seja selecionado, mostra o gráfico de barras empilhadas
                semestre = semestres_selecionados[0]
                df_semestre = df_avaliacao_frequencia[df_avaliacao_frequencia['Semestre'] == semestre]
                
                # Contagem das ocorrências únicas por semestre e tipo de conteúdo
                freq_unica_avaliacao = df_semestre.groupby(['Tipo de Avaliação', 'Semestre'])['Contexto do Evento'].nunique().reset_index(name='Quantidade')

                # Gerar a distribuição de ocorrências únicas de conteúdo para esse semestre
                freq_unica_avaliacao = freq_unica_avaliacao.groupby(['Tipo de Avaliação'])['Quantidade'].sum().reset_index()

                fig3 = go.Figure(data=go.Bar(
                    y=freq_unica_avaliacao['Tipo de Avaliação'],
                    x=freq_unica_avaliacao['Quantidade'],
                    name=semestre,
                    orientation='h'
                ))

                fig3.update_layout(
                    title=f"Distribuição de Avaliações no Semestre {semestre}",
                    barmode='stack',
                    xaxis_title=None,
                    yaxis_title=None,
                    width=600,
                    height=400,
                )

                # Atualiza o eixo X para garantir que os rótulos sejam mostrados
                fig3.update_xaxes(tickangle=0)

                st.plotly_chart(fig3)

        elif tipo_visualizacao == "Conteúdo":
            conteudos_interesse = ['POO', 'Comandos', 'Entrada de dados', 'Operadores', 'Classe', 'Encapsulamento', 'Herança', 'Polimorfismo', 'Vetores', 'ArrayList', 'Composição', 'Agregação']
            df_completo['Tipo de Conteúdo'] = df_completo['Contexto do Evento'].apply(lambda x: next((tipo for tipo in conteudos_interesse if tipo.lower() in x.lower()), None))

            # Filtra os dados para os conteúdos de interesse
            df_conteudo_ocorrencias = df_completo[df_completo['Tipo de Conteúdo'].notna()]

            # Se mais de um semestre for selecionado, mostra uma matriz de gráficos de barras empilhadas
            if len(semestres_selecionados) > 1:
                fig4 = make_subplots(
                    rows=len(semestres_selecionados), cols=1,  # Alteração: agora são várias linhas
                    subplot_titles=semestres_selecionados,
                    vertical_spacing=0.1
                )

                # Para cada semestre selecionado, calcular as ocorrências únicas e criar um gráfico de barras empilhadas
                for i, semestre in enumerate(semestres_selecionados):

                    # Filtra os dados para o semestre específico
                    df_semestre = df_conteudo_ocorrencias[df_conteudo_ocorrencias['Semestre'] == semestre]
                    
                    # Contagem das ocorrências únicas por semestre e tipo de conteúdo
                    df_conteudo_unicos = df_semestre.groupby(['Tipo de Conteúdo', 'Semestre'])['Contexto do Evento'].nunique().reset_index(name='Quantidade')

                    # Gerar a distribuição de ocorrências únicas de conteúdo para esse semestre
                    df_conteudo_unicos = df_conteudo_unicos.groupby(['Tipo de Conteúdo'])['Quantidade'].sum().reset_index()

                    # Adiciona o gráfico de barras empilhadas para o semestre correspondente
                    fig4.add_trace(
                        go.Bar(
                            y=df_conteudo_unicos['Tipo de Conteúdo'],
                            x=df_conteudo_unicos['Quantidade'],
                            name=semestre,
                            orientation='h'
                        ),
                        row=i + 1, col=1  # Ajuste para os gráficos estarem na coluna única
                    )

                    # Atualiza o eixo X de cada gráfico para garantir que ele mostre os rótulos
                    fig4.update_xaxes(
                        tickangle=0,
                        row=i + 1, col=1
                    )

                fig4.update_layout(
                    title="Distribuição de Conteúdo ao Longo dos Semestres",
                    barmode='stack',
                    showlegend=False,
                    width=600,
                    height=400 * len(semestres_selecionados),  # Ajusta a altura total com base na quantidade de semestres
                )

                st.plotly_chart(fig4)

            else:
                # Caso apenas um semestre seja selecionado, mostra o gráfico de barras empilhadas
                semestre = semestres_selecionados[0]
                df_semestre = df_conteudo_ocorrencias[df_conteudo_ocorrencias['Semestre'] == semestre]
                
                # Contagem das ocorrências únicas por semestre e tipo de conteúdo
                df_conteudo_unicos = df_semestre.groupby(['Tipo de Conteúdo', 'Semestre'])['Contexto do Evento'].nunique().reset_index(name='Quantidade')

                # Gerar a distribuição de ocorrências únicas de conteúdo para esse semestre
                df_conteudo_unicos = df_conteudo_unicos.groupby(['Tipo de Conteúdo'])['Quantidade'].sum().reset_index()

                fig4 = go.Figure(data=go.Bar(
                    y=df_conteudo_unicos['Tipo de Conteúdo'],
                    x=df_conteudo_unicos['Quantidade'],
                    name=semestre,
                    orientation='h'
                ))

                fig4.update_layout(
                    title=f"Distribuição de Conteúdo no Semestre {semestre}",
                    barmode='stack',
                    yaxis_title="Tipo de Conteúdo",
                    xaxis_title="Quantidade",
                    width=600,
                    height=400
                )

                # Atualiza o eixo X para garantir que os rótulos sejam mostrados
                fig4.update_xaxes(tickangle=0)

                st.plotly_chart(fig4)
