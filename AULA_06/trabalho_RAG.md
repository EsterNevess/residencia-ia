# Projeto e Arquitetura de uma Aplicação RAG

---

# PARTE 1 — IDENTIFICAÇÃO DOS PROBLEMAS

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

### 1.1 Descrição do problema
* **Problema:** Gargalo na análise minuciosa de contratos no fluxo diário (revisão de minutas e fornecedores) e lentidão extrema na auditoria massiva (*Due Diligence*) durante operações de M&A ou reestruturações, onde centenas de documentos precisam ser auditados para identificação de riscos, penalidades, regras de rescisão e passivos ocultos.
* **Usuário:** Advogados corporativos e analistas jurídicos de nível técnico pleno/sênior. O contexto de uso varia entre análises pontuais urgentes durante negociações e auditorias em lote sob pressão de prazos.
* **Informações consultadas:** Cláusulas de vigência, rescisão antecipada, multa rescisória, responsabilidade civil, alteração de controle societário (*change of control*), não-cumulatividade, foro, LGPD e anexos operacionais.
* **Origem das informações:** Contratos sociais, instrumentos particulares de prestação de serviços, NDAs, aditivos, anexos técnicos e termos de quitação armazenados no repositório corporativo/Drive.
* **Por que LLM sozinho não é suficiente:** O LLM pré-treinado não possui acesso aos contratos privados da empresa. Além disso, LLMs tendem a inventar ("alucinar") obrigações ou valores se não forem estritamente ancorados no texto exato do contrato em análise.
* **Interface do sistema:** Aplicação Web com painel lateral (*split-screen*): de um lado o chat/análise RAG, do outro o visualizador de PDF destacando a cláusula exata recuperada.
* **Perguntas reais de usuários:**
  1. *"Qual é a multa em caso de rescisão imotivada antes do prazo de 12 meses no contrato da Fornecedora X?"*
  2. *"Existe alguma cláusula de exclusividade ou limitação de responsabilidade nos contratos firmados com a Empresa Y?"*
  3. *"Quais contratos de prestação de serviços possuem cláusula de mudança de controle societário (change of control) vigente?"*

### 1.2 Por que RAG?
* **Adequação:** RAG permite extrair trechos exatos de minutas contratuais privadas sem a necessidade de retreinar o modelo, garantindo rastreabilidade (*citation*) de cada afirmação.
* **Conhecimento necessário:** O texto integral dos instrumentos contratuais vigentes e passados do acervo privado da empresa/cliente.
* **Frequência de atualização:** Diária (no fluxo de novos contratos aprovados) e pontual em lotes (upload sob demanda para Due Diligence).

#### Existe necessidade de utilizar documentos privados ou específicos da organização?
Sim, é absolutamente indispensável. Os contratos de prestação de serviços, acordos de confidencialidade (NDAs), aditivos e minutas societárias são documentos estritamente privados, confidenciais e específicos da organização (ou das empresas sob auditoria). Eles contêm regras negociais exclusivas, prazos, preços, cláusulas de exclusividade e penalidades que jamais existiram em bases de dados públicas ou na internet aberta. Sem injetar essa base privada, a aplicação não tem sobre o que operar.

#### Que problemas poderiam ocorrer se o LLM respondesse apenas com seu conhecimento pré-treinado? Dê um exemplo concreto de resposta errada que ele daria no seu cenário.
* **Problemas operacionais e jurídicos:** O modelo não saberia as regras específicas firmadas entre as partes, resultando em respostas genéricas, desatualizadas ou baseadas apenas no senso comum jurídico do Código Civil, o que invalidaria a due diligence.
* **Exemplo concreto de erro sem RAG:**
  * *Pergunta do analista:* "Qual é o valor da multa rescisória e o prazo de aviso prévio previstos no contrato de TI com a TechSolutions?"
  * *Resposta errada do LLM puro (conhecimento genérico):* "A multa contratual rescisória por encerramento imotivado é geralmente fixada em 10% do valor restante do contrato conforme os costumes de mercado, e o aviso prévio padrão é de 30 dias."
  * *A realidade do contrato privado:* O contrato real da TechSolutions estipulava uma multa fixa de **3 mensalidades integrais** somadas a perdas e danos apurados, com aviso prévio de **90 dias**. O uso do conhecimento pré-treinado geraria uma premissa financeira totalmente falsa, induzindo a equipe a um prejuízo grave na negociação.

### 1.3 Limitações — Quando RAG não é a resposta
#### Situacões em que RAG não seria a melhor solução isolada: O RAG puro falha quando a dúvida exige **exatidão numérica, agregação global sobre toda a base de dados ou buscas por termos exatos/códigos alfanuméricos**. 
Para esses casos, outras abordagens são superiores:
* **Busca tradicional por palavra-chave (BM25/Lexical):** Superior para encontrar o contrato pelo CNPJ, número exato do contrato ou razão social exata da parte, onde a busca vetorial por significado pode falhar se o nome for um acrônimo genérico.
* **Banco de dados estruturado + SQL:** Ideal para controle de metadados operacionais: datas de vencimento, valores totais pagáveis, status de assinatura e indexadores de reajuste (ex: IPCA, IGPM).
* **Regras determinísticas:** Para disparar alertas automáticos de renovação (ex: `se data_atual >= data_vencimento - 60 dias → disparar notificação de não-renovação`).
* **Uso direto de API:** Consulta em APIs de órgãos públicos (ex: Receita Federal para validar se o CNPJ da contratada está ativo).
* **Combinação ideal:** **Busca Híbrida (BM25 + Vetorial)** para encontrar o trecho, integrada a um **Banco SQL** que gerencia o ciclo de vida e vigência do contrato.
* **Pergunta mal respondida por RAG e bem respondida por SQL:** *"Qual é a soma total do valor mensal de todos os contratos de TI ativos em 2026?"*
  * *Por quê?* **RAG** recuperaria trechos com valores de diversos contratos, mas o LLM falha em somar de forma determinística grandes listas e corre o risco de omitir contratos por limite de contexto. O **SQL** executa `SELECT SUM(valor_mensal) FROM contratos WHERE categoria = 'TI' AND status = 'ativo'` em milissegundos com precisão exata.
* **Agregação em múltiplos documentos (contar/somar/ordenar):** *"O que aconteceria se a pergunta do usuário exigisse contar, somar ou ordenar informação espalhada por muitos documentos?"* 
  * *Por quê?* RAG performa mal em contagens ou ordenações globais. O retriever busca apenas os top-K chunks mais semelhantes, ignorando os demais 90% dos contratos da base.

---

## CENÁRIO 2: Assistente de Jurisprudência Interna e Peças Processuais

### 1.1 Descrição do problema
* **Problema:** Desperdício de tempo de advogados refazendo pesquisas do zero ou redigindo fundamentações jurídicas para teses repetitivas que o próprio escritório já defendeu com sucesso em processos anteriores.
* **Usuário:** Advogados associados e estagiários (nível técnico jurídico alto, vocabulário formal). O contexto de uso é a elaboração de petições iniciais, contestações e recursos sob prazos processuais fatais.
* **Informações consultadas:** Modelos de peças vencedoras, fundamentações doutrinárias e jurisprudenciais adotadas pelo escritório, pareceres internos e precedentes judiciais específicos de tribunais estaduais e superiores.
* **Origem das informações:** Sistema de gestão processual do escritório (ERP Jurídico) onde as peças finalizadas são protocoladas.
* **Por que LLM sozinho não é suficiente:** O LLM genérico traz doutrina e jurisprudência pública, mas não conhece a "linha jurídica", o tom de escrita, os argumentos específicos e as estratégias bem-sucedidas construídas historicamente pelo escritório.
* **Interface do sistema:** Integração web com editor de texto embutido e extensão/plugin para o Microsoft Word/Google Docs.
* **Perguntas reais de usuários:**
  1. *"Qual fundamentação utilizamos no recurso de apelação da ação de indenização contra a Seguradora X sobre a validade da cláusula de sinistro?"*
  2. *"Encontre petições do escritório que sustentaram com sucesso a impenhorabilidade do bem de família para fiador de contrato comercial."*
  3. *"Quais julgados do TJSP nós citamos para combater a tese de prescrição intercorrente na execução fiscal do Cliente Y?"*

### 1.2 Por que RAG?
* **Adequação:** Permite recuperar trechos inteiros de peças bem estruturadas (teses, jurisprudências citadas, pedidos) para servirem de base na redação de novas peças.
* **Conhecimento necessário:** O acervo histórico interno de milhares de peças defensivas e pareceres produzidos pelos advogados do escritório.
* **Frequência de atualização:** Diária e contínua (ingestão automática a cada novo protocolo efetuado).

#### Existe necessidade de utilizar documentos privados ou específicos da organização?
Sim, com total prioridade. O acervo de petições anteriores, contestações vencedoras, modelos de peças, pareceres técnicos e teses jurídicas desenvolvidas pela banca ou pelo departamento jurídico da empresa constitui o patrimônio intelectual privado e o "know-how" estratégico da organização. Nenhum modelo de linguagem pré-treinado possui acesso a essas peças internas customizadas para as teses do escritório.

#### Que problemas poderiam ocorrer se o LLM respondesse apenas com seu conhecimento pré-treinado? Dê um exemplo concreto de resposta errada que ele daria no seu cenário.
* **Perda de padronização e eficácia processual:** O LLM geraria peças genéricas, desconsiderando a linha argumentativa específica, a jurisprudência interna já validada pelos tribunais locais e a identidade de redação do escritório.
* **Exemplo concreto de erro sem RAG:**
  * *Pergunta do advogado:* "Quais argumentos específicos e Súmulas internas nossa banca costuma utilizar para afastar pedidos de horas extras por cargo de confiança em ações trabalhistas de gerentes?"
  * *Resposta errada do LLM puro (conhecimento genérico):* *"Para afastar horas extras de gerentes, recomenda-se citar de forma genérica o artigo 62, inciso II, da CLT, argumentando que o empregado possuía poderes de mando e gestão."*
  * *A realidade do acervo privado:* O LLM ignoraria completamente as petições de sucesso anteriores do escritório que continham a tese refinada detalhando a **fórmula exata de cálculo de gratificação de função (superior a 40%)** alinhada ao entendimento específico da 2ª Região do TRT. A resposta genérica desconsideraria o padrão técnico de excelência da banca, aumentando o risco de sucumbência no processo.

### 1.3 Limitações — Quando RAG não é a resposta
#### Situações em que o RAG puro falha nas Peças Processuais e Jurisprudência: O RAG baseado apenas em vetores semânticos falha quando a consulta exige **contagem em lote, auditoria estatística de êxito de teses, cruzamento temporal de prazos processuais ou recuperação exata por chaves numéricas**.
Nestes casos, ferramentas determinísticas são obrigatórias:
* **Busca por palavra-chave (BM25):** Essencial para localizar o arquivo pelo número do processo (ex: CNJ `0000000-00.2026.8.26.0100`) ou pelo nome exato das partes/relator.
* **Banco SQL:** Essencial para controle de prazos processuais (fatal/interno), status da ação, comarca, vara e distribuição de tarefas da equipe.
* **Regras determinísticas:** Para contagem automática de prazos processuais em dias úteis de acordo com o Código de Processo Civil e calendários dos tribunais.
* **Uso de API direta:** Integração com a API do DataJud (CNJ) ou dos tribunais para puxar o andamento em tempo real do processo.
* **Combinação ideal:** RAG para a busca semântica de teses + BM25 para termos jurídicos exatos + Banco SQL para metadados processuais.
* **Pergunta mal respondida por RAG e bem respondida por SQL:** *"Quantas contestações do setor Trabalhista foram protocoladas no mês passado e qual advogado produziu mais peças?"*
  * *Por quê?* **RAG** buscaria textos semânticos de contestações, sem conseguir agrupar, contar ou relacionar com a produtividade do autor de forma confiável. O **SQL** faz isso diretamente com agregações simples (`COUNT` e `GROUP BY`).
* **Agregação em múltiplos documentos (contar/somar/ordenar):** *"O que aconteceria se a pergunta do usuário exigisse contar, somar ou ordenar informação espalhada por muitos documentos?"* 
  * *Por quê?* Pedidos como *"Faça um levantamento estatístico de qual tese teve mais êxito no tribunal nos últimos 5 anos"* não funcionam em RAG padrão sem uma camada de análise analítica prévia sobre dados estruturados.

---
---

# PARTE 2 — ORGANIZAÇÃO DOS DOCUMENTOS

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

### 2.1 Tipos, Volume e Atualização
* **Tipos de arquivo:** Predominantemente PDF nativo (gerados via Word/DocuSign), com pequeno percentual de PDFs escaneados (contratos antigos) e anexos em DOCX.
* **Volume aproximado:** ~15.000 documentos na base fixa corporativa + lotes temporários de até 2.000 documentos por projeto de Due Diligence.
* **Tamanho típico:** 10 a 45 páginas por contrato (aprox. 500 KB a 5 MB por arquivo).
* **Frequência de entrada:** 20 a 50 novos contratos/aditivos por semana.
* **Comportamento de atualização:** Contratos antigos raramente são editados; novos aditivos são anexados ao contrato original, alterando cláusulas vigentes.

### 2.2 Estrutura de Pastas Proposta
```text
documentos_contratuais/
├── fornecedores/
│   ├── tecnologia/
│   ├── logistica/
│   └── servicos_gerais/
├── clientes_corporativos/
├── societario_e_ma/
├── recursos_humanos/
└── aditivos_e_anexos/
```

---

**Justificativa da estrutura:** Escolheu-se a divisão por Área Negocial / Categoria de Contrato porque é exatamente assim que o analista de Due Diligence delimita o escopo da auditoria. Quando o usuário investiga passivos de tecnologia, ele não quer buscar em contratos de RH. Essa estrutura permite aplicar filtros de metadados por diretório (folder_path) no retriever do RAG, reduzindo o espaço de busca, evitando falsos positivos de outras áreas e acelerando a resposta.

### 2.3 Exclusões, Segurança e Versionamento
* **Documentos excluídos:** Comprovantes de pagamento, notas fiscais isoladas, rascunhos de minutas sem assinatura, extratos bancários e documentos com dados sensíveis de cartão de crédito (PCI-DSS) ou dados pessoais excessivos (LGPD).

* **Mecanismo de bloqueio:** Pipeline de triagem na ingestão contendo:
    1. Filtro por extensão e formato: Rejeição automática de imagens puras sem camada de texto e planilhas de pagamento.
    2. Regex e NER (Reconhecimento de Entidades): Validação de padrões de cartão de crédito e CPF/dados sensíveis antes do armazenamento no Vector DB.
    3. Verificação de Assinatura: Apenas arquivos com tag de conclusão no DocuSign/ERP ou com marcador OCR de assinatura entram no fluxo.

* **Gestão de versões e temporalidade:** Contratos possuem aditivos que alteram cláusulas antigas. Para impedir que o RAG recupere uma regra revogada:
    1. Cada família de contratos recebe um contract_family_id.
    2. O contrato original e seus aditivos são vinculados. O sistema atualiza o metadado is_latest_version = False nas cláusulas do contrato original que foram substituídas pelo aditivo mais recente.
    3. No momento da consulta, a busca vetorial aplica um filtro obrigatório (is_latest_version = True), garantindo que apenas a redação vigente da cláusula seja enviada ao contexto do LLM.

---

## CENÁRIO 2: Assistente de Jurisprudência Interna e Peças Processuais

### 2.1 Tipos, Volume e Atualização
* **Tipos de arquivo:** Documentos em PDF (petições protocoladas e acórdãos) e arquivos DOCX (modelos e pareceres internos extraídos do ERP jurídico).
* **Volume aproximado:** ~45.000 peças e pareceres históricos no acervo.
* **Tamanho típico:** 5 a 25 páginas por peça (aprox. 200 KB a 2 MB por arquivo).
* **Frequência de entrada:** Entrada contínua e automática de ~150 a 300 novas peças por semana logo após o protocolo no tribunal.
* **Comportamento de atualização:** Peças protocoladas são imutáveis (documentos históricos de arquivo definitivo). O que muda é a validade da tese jurídica ao longo do tempo.

### 2.2 Estrutura de Pastas Proposta
```text
pecas_processuais/
├── civel/
│   ├── contratos/
│   ├── responsabilidade_civil/
│   └── consumidor/
├── trabalhista/
│   ├── peticoes_iniciais/
│   └── contestacoes/
├── tributario/
└── pareceres_e_consultoria/
```

---

**Justificativa da estrutura:** A organização foi desenhada por Ramo do Direito e Tipo de Peça porque os advogados do escritório trabalham agrupados por bancas especializadas (equipe Trabalhista, equipe Tributária). Ao redigir uma Contestação Trabalhista, o advogado pensa a informação dentro do rito trabalhista. Essa divisão permite filtrar as buscas vetoriais por ramo_direito e tipo_peca, impedindo que teses de Direito Civil contaminem consultas de Direito Tributário.

### 2.3 Exclusões, Segurança e Versionamento
* **Documentos excluídos:** Minutas em rascunho não protocoladas, e-mails de desalinhamento interno com o cliente, guias de arrecadação/custas pagas, procurações puramente formais e substabelecimentos sem conteúdo tese.

* **Mecanismo de bloqueio:** O script de ingestão é integrado diretamente ao ERP Jurídico e só consome arquivos que cumpram dois requisitos simultâneos:
    1. status == "PROTOCOLADO" (garante que não entram rascunhos).
    2. categoria_documento IN ["PETICAO_INICIAL", "CONTESTACAO", "RECURSO", "PARECER"] (filtra e bloqueia automaticamente guias de custas e procurações).

* **Gestão de versões e temporalidade:** Como peças judiciais não são reeditadas após o protocolo, o problema de "versão obsoleta" ocorre quando a legislação ou o entendimento do tribunal muda (ex: uma tese usada em 2024 baseada em lei alterada em 2026). Para resolver isso:
    1. Cada peça é indexada com os metadados protocol_date (data do protocolo) e tese_status (ativa ou obsoleta).
    2. Quando uma tese é superada por nova Súmula ou mudança legislativa, o administrador atualiza o metadado das peças antigas para tese_status = obsoleta.
    3. Por padrão, a busca RAG filtra apenas tese_status = ativa. Se o usuário quiser consultar o histórico antigo, precisa marcar explicitamente a opção "Incluir teses históricas/superadas" na interface.

---
---

# PARTE 3 — PIPELINE DE INGESTÃO

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

### 3.1 Extração
* Como o texto seria extraído?
A extração combina leitores de PDF vetoriais (pdfplumber / pypdf) para contratos digitais recentes e pipelines de OCR (Tesseract / EasyOCR) para contratos antigos ou digitalizados em imagem.

* Como você trataria PDFs com texto selecionável (nativos)?
Extração direta com pdfplumber, aplicando regras de corte por coordenadas de layout para ignorar e remover timbres de fornecedores, cabeçalhos repetitivos e marcas d'água de "RASCUNHO" que poluiriam os embeddings.

* E PDFs digitalizados (imagem escaneada, sem camada de texto)?
Conversão das páginas em imagens via pdf2image, pré-processamento no OpenCV (ajuste de contraste e binarização para papeis amarelados/antigos) e OCR com Tesseract. O resultado passa por validação via Regex para garantir a integridade de valores monetários.

* Como trataria tabelas? É importante mantê-las?
**Tratamento:** Detectadas via pdfplumber (por detecção de grades) e convertidas integralmente para Markdown Table. O formato preserva o vínculo entre o cabeçalho das colunas e os valores das linhas dentro de um único chunk indivisível.
**Importância:** É vital mantê-las intactas. Uma tabela contém dados financeiros e jurídicos altamente sensíveis (cronogramas de pagamento, tabelas de preço por item, índices de reajuste como IPCA e multas por rescisão).

* Como trataria imagens? Posso descartar? Quais informações elas têm?
**O que descartar:** Logotipos de empresas/fornecedores, assinaturas manuscritas e marcas d'água decorativas.
**O que preservar:** Organogramas societários, fluxogramas de processos e diagramas de infraestrutura anexados aos contratos de prestação de serviços.
**Tratamento:** As imagens operacionais preservadas passam por um modelo de visão multimodal (ex: GPT-4o / Gemini Flash) para gerar uma descrição técnica detalhada (captioning) em texto, que é indexada junto ao documento.

* Como trataria documentos multimodais (texto + imagem, áudio + vídeo)?
**Texto + Imagem:** Processados no fluxo unificado de extração de PDF + descrição descritiva de diagramas via LLM de Visão.
**Áudio + Vídeo (Reuniões de Negociação / M&A):** O áudio é transcrito via OpenAI Whisper utilizando Diarização de Locutores (Speaker Diarization) para identificar e registrar quem fez cada promessa verbal pré-contratual ([Comprador]: ... / [Vendedor]: ...).

* Explique quais problemas podem surgir durante a extração e cite um caso concreto.
**Problema Geral:** Inversão da ordem de leitura em minutas de contrato formatadas em duas colunas paralelas (o extrator junta linhas de colunas diferentes).
**Caso Concreto Enfrentado:** Em um contrato antigo escaneado, o OCR interpretou o valor de uma multa "R$ 50.000,00" como "R$ 50.000OO" (trocando os zeros decimais pelas letras "O" maiúsculas). Isso inviabilizou as buscas por valores exatos até ser aplicada uma regra de normalização de moedas via Regex no pipeline de limpeza.

### 3.2 Limpeza e Normalização
#### O que precisa ser removido?
* **Cabeçalhos e rodapés repetidos:** Timbres corporativos, nomes de escritórios de advocacia contratados, CNPJs repetidos no topo de todas as páginas e números de cláusulas gerados automaticamente pelo editor de texto.
* **Numeração de página:** Expressões como "Página X de Y" ou "Fls. XX" que aparecem isoladas e poluem semanticamente o espaço vetorial.
* **Marcas d'água:** Textos diagonais recorrentes como "CONFIDENCIAL", "MINUTA" ou "RASCUNHO".
* **Elementos estruturais de navegação:** Sumários, índices remissivos e páginas de controle de versionamento puramente burocráticas que não agregam valor à análise de obrigações.

#### O que precisa ser padronizado?
* **Codificação:** Conversão forçada de todo o texto para UTF-8 padrão para evitar caracteres corrompidos.
* **Quebras de linha e espaçamento:** Remoção de quebras de linha artificiais inseridas no meio de parágrafos devido à quebra de layout do PDF, além da normalização de múltiplos espaços em branco para apenas um espaço simples.
* **Acentuação e pontuação:** Padronização de aspas tipográficas (curvas) para aspas retas e normalização de hífens e travessões utilizados em obrigações contratuais.
* **Formatação de termos monetários e datas:** Conversão de variações de moedas e datas para um padrão único (ex: formato `DD/MM/AAAA` e representação monetária limpa) para facilitar o casamento com buscas exatas.

#### Que informação você corre o risco de perder ao limpar demais?
* **Referências cruzadas internas:** Ao remover "elementos repetitivos", corre-se o risco de apagar remissões fundamentais como *"conforme a Cláusula 14.2 supra"* ou menções a anexos essenciais.
* **Contexto de rodapés explicativos:** Notas de rodapé jurídicas ou financeiras que contêm ressalvas importantes sobre uma cláusula de exclusão de responsabilidade (*disclaimer*) podem ser suprimidas se o filtro de rodapé for agressivo demais.
* **Identificadores numéricos e tabelas pequenas:** Excesso de limpeza de caracteres especiais pode corromper referências a anexos, leis citadas (ex: Lei nº 8.666/93 ou 14.133/21) e percentuais de juros e multas.

### 3.3 Frequência de Ingestão
#### O pipeline roda uma vez, sob demanda, ou de forma agendada? Com que frequência chegam novos documentos?
* **Frequência de novos documentos:** Os contratos chegam de forma **contínua e sob demanda**, de acordo com o fechamento de novas negociações, renovações ou aditivos gerados pelo departamento jurídico e comercial.
* **Modelo de execução do pipeline:** O pipeline opera de forma **híbrida**: 
  1. *Sob demanda* por meio de *Webhooks* disparados pelo sistema de assinatura eletrônica (ex: DocuSign/ClickSign) ou do repositório corporativo (SharePoint/Google Drive) assim que um novo contrato é assinado.
  2. *Agendada* (via rotinas noturnas/batch de *Cron jobs*) para varreduras de consistência e captura de lotes retroativos de documentos digitalizados pelo setor de arquivos.

#### Quando um documento é atualizado, você reprocessa só ele ou a base inteira? Como sabe qual reprocessar?
* **Estratégia de reprocessamento:** **Reprocessa-se apenas o documento alterado (e seu respectivo aditivo/família)**, jamais a base inteira. Reprocessar milhares de contratos por causa de uma alteração pontual seria computacionalmente inviável e financeiramente custoso.
* **Como o sistema sabe qual reprocessar:** 
  * Cada documento possui um `document_id` único e um carimbo temporal de versão (`updated_at` / `is_latest_version`). 
  * Quando um aditivo contratual modifica um contrato pré-existente, o sistema atualiza o metadado `contract_family_id`. 
  * Na ingestão do novo arquivo, o pipeline identifica o `document_id` correspondente, **deleta vetores antigos** associados a ele no banco vetorial via chave estrangeira, e insere os novos *chunks* atualizados, alternando a flag `is_latest_version` para falso na versão anterior.
---

## CENÁRIO 2: Assistente de Jurisprudência Interna e Peças Processuais

* Como o texto seria extraído?
O texto é extraído diretamente de PDFs nativos baixados dos sistemas dos tribunais (PJe/e-SAJ) via pdfplumber, preservando a ordem de leitura dos parágrafos, e via OCR para cópias físicas de processos antigos juntados aos autos.

* Como você trataria PDFs com texto selecionável (nativos)?
Extração direta com pdfplumber, aplicando limpeza automatizada por coordenadas para remover tarjas de protocolo eletrônico nas margens, cabeçalhos de escritórios e numerações de páginas geradas pelo tribunal.

* E PDFs digitalizados (imagem escaneada, sem camada de texto)?
Conversão via pdf2image, binarização no OpenCV para remoção de ruídos provocados por carimbos físicos ou assinaturas manuais sobre o texto, e processamento via OCR (Tesseract / EasyOCR) focado em preservar a estrutura dos parágrafos da tese.

* Como trataria tabelas? É importante mantê-las?
**Tratamento:** Extraídas via pdfplumber e convertidas para Markdown Table. Isso impede que os valores percam a relação com o período correspondente (ex: mês/ano) e garante que o contexto chegue intacto à LLM.
**Importância:** É vital mantê-las. Tabelas em peças processuais contêm planilhas de atualização de débitos, cálculos de liquidação de sentença e demonstrativos de horas extras.

* Como trataria imagens? Posso descartar? Quais informações elas têm?
**O que descartar:** Timbres de advogados, selos de cartório judicial e ícones de validação de assinatura digital.
**O que preservar:** Print screens de conversas do WhatsApp (usados como prova probatória), fotos de acidentes e croquis de sinistros anexados às peças.
**Tratamento:** Enviadas a um modelo de visão multimodal para gerar um resumo do conteúdo probatório em texto, permitindo que a busca semântica encontre fotos de provas a partir do seu significado.

* Como trataria documentos multimodais (texto + imagem, áudio + vídeo)?
**Texto + Imagem:** Processados no fluxo unificado de PDF/OCR + transcrição probatória de imagens via LLM de Visão.
**Áudio + Vídeo (Gravações de Audiências Judiciais e Depoimentos):** Transcritos via OpenAI Whisper com Diarização de Locutores, rotulando a fala de cada agente processual ([Juiz]: ..., [Advogado]: ..., [Testemunha]: ...).

* Explique quais problemas podem surgir durante a extração e cite um caso concreto.
**Problema Geral:** Tarjas e carimbos verticais de protocolo eletrônico do PJe/e-SAJ sendo lidos no meio das frases do corpo da petição.
**Caso Concreto Enfrentado:** O extrator nativo fundiu o texto do cabeçalho de uma petição (contendo a comarca e o número do processo) ao primeiro parágrafo do texto principal, fazendo o retriever confundir a localização da vara cível com os argumentos da tese jurídica. O problema foi corrigido configurando a extração por caixas delimitadoras (bounding boxes) com pdfplumber.

### 3.2 Limpeza e Normalização
#### O que precisa ser removido?
* **Cabeçalhos e rodapés repetidos:** Timbres de tribunais, numeração de processo repetida automaticamente no topo de cada folha dos autos eletrônicos e nomes de magistrados ou servidores impressos por padrão no rodapé.
* **Numeração de página:** Indicações de folhas do processo (ex: "Fl. 145" ou "ID. 8934712") inseridas pelos sistemas dos tribunais (PJe/e-SAJ).
* **Marcas d'água e carimbos de protocolo:** Selos digitais de autenticidade, carimbos eletrônicos de "JUNTADO EM..." e avisos de sigilo processual automatizados.
* **Elementos estruturais redundantes:** Sumários de petições extensas e índices de documentos juntados que apenas repetem informações já contidas no corpo do processo.

#### O que precisa ser padronizado?
* **Codificação:** Garantia estrita de codificação UTF-8 para evitar perdas de acentuação em termos jurídicos fundamentais (ex: *habeas corpus*, *acórdão*, *ônus*, *magistrado*).
* **Quebras de linha e espaçamento:** Eliminação de quebras de linha forçadas geradas pela digitalização ou exportação de petições em PDF, unificando os parágrafos da tese jurídica para leitura contínua pela LLM.
* **Acentuação e pontuação:** Padronização de abreviações forenses comuns (ex: *fls.*, *art.*, *v.g.*, *STF*, *STJ*) e eliminação de caracteres gráficos espúrios resultantes de falhas de formatação de fontes nos sistemas dos tribunais.
* **Formatação de ementas e citações:** Padronização de blocos de citação de jurisprudência (destacando tribunais e relatores) para facilitar a recuperação vetorial e o reconhecimento de padrões pela IA.

#### Que informação você corre o risco de perder ao limpar demais?
* **Cabeçalhos com dados de autoria e classe processual:** Se o filtro for excessivamente amplo, pode remover o cabeçalho que identifica a vara de origem, o número do processo ou o nome das partes, elementos cruciais para a filtragem por metadados.
* **Citações de leis e artigos específicos:** A remoção descuidada de números e símbolos especiais (como parágrafos e artigos, ex: § 1º do art. 5º) pode apagar a base normativa exata sobre a qual a tese jurídica foi construída.
* **Notas de rodapé com precedentes:** Em petições e acórdãos, notas de rodapé frequentemente contêm indicações de julgados secundários e doutrinas que fundamentam o argumento principal; eliminá-las empobrece o contexto jurisprudencial recuperado.

### 3.3 Frequência de Ingestão
#### O pipeline roda uma vez, sob demanda, ou de forma agendada? Com que frequência chegam novos documentos?
* **Frequência de novos documentos:** O acervo de petições, contestações, pareceres e acórdãos cresce **diariamente e de forma automatizada** com o protocolo de novas peças pelo escritório.
* **Modelo de execução do pipeline:** Funciona primariamente de forma **agendada em lotes (batch noturno)** e **sob demanda**. Todas as noites, um robô de integração varre o banco de dados do ERP jurídico do escritório e captura as peças protocoladas no dia. Opcionalmente, o advogado pode acionar a ingestão *sob demanda* de um precedente externo importante diretamente pela interface do assistente.

#### Quando um documento é atualizado, você reprocessa só ele ou a base inteira? Como sabe qual reprocessar?
* **Estratégia de reprocessamento:** **Reprocessamento cirúrgico apenas da peça específica modificada ou substituída.**
* **Como o sistema sabe qual reprocessar:** 
  * Cada peça processual é indexada vinculada ao seu número de controle interno no ERP e ao número do processo no CNJ (`processo_cnj`).
  * Caso uma peça seja retificada nos autos (ex: petição de emenda à inicial ou substituição de peça por erro material), o ERP gera um novo hash de arquivo ou um identificador de revisão atualizado (`version_number`).
  * O pipeline compara o hash do documento recebido com o hash armazenado no metadado do banco vetorial. Se houver divergência, o sistema executa o *upsert* (atualização ou exclusão dos vetores antigos e inserção da nova versão), garantindo que a IA nunca consulte teses processuais desatualizadas.

---
---

# PARTE 4 — METADADOS

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

### 4.1 Metadados do Documento
```json
{
  "document_id": "doc_contract_8841",
  "contract_family_id": "fam_tech_2025_01",
  "title": "Contrato de Prestação de Serviços de TI - TechSolutions",
  "category": "Tecnologia",
  "partes_envolvidas": ["Empresa X S/A", "TechSolutions Ltda"],
  "created_at": "2025-03-10",
  "data_vencimento": "2027-03-10",
  "valor_total": 450000.00,
  "is_latest_version": true,
  "folder_path": "documentos_contratuais/fornecedores/tecnologia/"
}
```

**Justificativa dos campos:**
1. document_id: Identificador único no banco para exclusões ou atualizações incrementais.
2. contract_family_id: Agrupa o contrato principal e seus aditivos em um mesmo cluster lógico.
3. title: Nome legível exibido na interface do usuário.
4. category: Permite que o analista restrinja a busca a uma área específica (ex: apenas contratos de TI).
5. partes_envolvidas: Permite buscas filtradas pelo nome ou CNPJ exato do fornecedor.
6. created_at e data_vencimento: Fundamentais para auditorias de vigência e cálculo de temporalidade.
7. valor_total: Permite filtros numéricos (ex: auditar apenas contratos acima de R$ 100.000).
8. is_latest_version: Evita a leitura de cláusulas revogadas por aditivos posteriores.
9. folder_path: Aplica controle de acesso baseado no diretório corporativo de origem.

### 4.2 Metadados do Chunk
```json
{
  "chunk_id": "doc_contract_8841_chunk_12",
  "document_id": "doc_contract_8841",
  "page": 14,
  "section": "CLÁUSULA OITAVA — DA RESCISÃO E MULTA",
  "document_type": "contrato_prestacao_servicos",
  "text": "CLÁUSULA OITAVA — DA RESCISÃO E MULTA. Caso a CONTRATANTE rescinda o contrato imotivadamente antes de 12 meses, incidirá multa rescisória de 20% do valor restante."
}
```

**Justificativa dos campos:**
1. chunk_id: Chave primária do vetor no Vector DB.
2. document_id: Chave estrangeira relacionando o chunk ao documento pai.
3. page: Permite abrir o leitor de PDF exatamente na página de onde o trecho foi extraído.
4. section: Dá contexto imediato sobre o escopo jurídico da cláusula antes da geração.
5. document_type: Diferencia o texto principal de anexos e tabelas técnicas.
6. text: O conteúdo textual indexado.

#### Quais metadados você usaria para filtrar a busca? Dê um exemplo de pergunta em que o filtro é indispensável.

* **Cenário 1 (Due Diligence Contratual):**
  * **Metadados usados:** `partes_envolvidas`, `categoria`, `is_latest_version`.
  * **Exemplo de pergunta:** *"Qual é a multa por rescisão imotivada no contrato vigente da TechSolutions?"*
  * **Por que o filtro é indispensável:** Sem filtrar por `partes_envolvidas CONTAINS "TechSolutions"` e `is_latest_version == True`, o RAG recuperaria cláusulas de rescisão de outros fornecedores ou de versões antigas/revogadas do contrato que foram alteradas por aditivos recentes.

* **Cenário 2 (Peças Processuais e Jurisprudência):**
  * **Metadados usados:** `ramo_direito`, `tipo_peca`, `tese_status`.
  * **Exemplo de pergunta:** *"Quais teses ativas o escritório utiliza em Contestações Trabalhistas para combater horas extras por cargo de confiança?"*
  * **Por que o filtro é indispensável:** O filtro por `ramo_direito == "Trabalhista"`, `tipo_peca == "Contestação"` e `tese_status == "ativa"` garante que o sistema trará apenas defesas vigentes, bloqueando teses obsoletas que já foram superadas por mudanças em Súmulas do TST.

---

#### Quais metadados você usaria para citar a fonte ao usuário? O que exatamente apareceria na tela junto da resposta?

* **Cenário 1 (Due Diligence Contratual):**
  * **Metadados de citação:** `title`, `section`, `page`, `folder_path`.
  * **Exibição na tela:** Card no painel lateral de fontes:
    > **Fonte:** Contrato de Prestação de Serviços de TI — TechSolutions Ltda  
    > **Localização:** Página 14, *Cláusula 8ª (Da Rescisão e Multa)*  
    > **Ação:** [ Botão: Abrir PDF na Página 14 ]

* **Cenário 2 (Peças Processuais e Jurisprudência):**
  * **Metadados de citação:** `tipo_peca`, `processo_cnj`, `section`, `advogado_autor`, `page`.
  * **Exibição na tela:** Rodapé da resposta gerada:
    > **Fonte do Modelo:** Contestação (Proc. CNJ `1004589-12.2024.8.26.0100`) — *Seção "Do Mérito"* (Pág. 6)  
    > **Elaborado por:** Dra. Ester Nóbrega  
    > **Ação:** [ Botão: Copiar Trecho ] | [ Botão: Ver Peça Completa ]

---

#### Que metadado seria caríssimo de acrescentar depois que a base já estivesse indexada? Por quê?

* **Cenário 1 (Due Diligence Contratual):**
  * **Metadados mais caros:** `is_latest_version` e `contract_family_id`.
  * **Por que é caríssimo:** Exige submeter dezenas de milhares de contratos legados a um LLM avançado para reanalisar todo o histórico, mapear quais aditivos alteraram quais cláusulas originais e reescrever o *payload* de todos os vetores no banco de dados, interrompendo o serviço ou exigindo reindexação total.

* **Cenário 2 (Peças Processuais e Jurisprudência):**
  * **Metadado mais caro:** `tese_status`.
  * **Por que é caríssimo:** Se a base de 45.000 peças estiver indexada sem essa marcação, será necessário reanalisar todo o acervo histórico para verificar se a lei ou Súmula citada na petição antiga continua ativa ou foi superada, gerando um custo massivo de API e tempo de curadoria especializada.

---

#### Como você vai extrair esses metadados?

* **Cenário 1 (Due Diligence Contratual):**
  * *Metadados Determinísticos (`title`, `page`, `created_at`, `cnpj_contratada`):* Extraídos automaticamente via leitores de PDF (`pdfplumber`) e APIs corporativas dos sistemas de assinatura eletrônica (ex: DocuSign) no momento do upload.
  * *Metadados Complexos de Negócio (`is_latest_version`, `contract_family_id`, `valor_total`, `category`):* Extraídos na fase de ingestão via chamada de LLM configurada com **Outputs Estruturados (Pydantic / JSON Schema)**. A LLM lê a minuta e devolve um JSON com as chaves e tipos de dados estritamente validados.

* **Cenário 2 (Peças Processuais e Jurisprudência):**
  * *Metadados Determinísticos (`processo_cnj`, `vara_origem`, `data_protocolo`, `nome_advogado`):* Extraídos de forma programática lendo os metadados estruturados dos PDFs nativos do PJe/e-SAJ e cruzando com o banco de dados do ERP jurídico do escritório.
  * *Metadados Complexos Jurídicos (`tese_status`, `ramo_direito`, `artigos_violados`, `jurisprudencia_dominante`):* Extraídos por **LLM com Output Estruturado (Pydantic / JSON Schema)**, onde a inteligência analisa o corpo da petição ou acórdão e classifica a tese jurídica de acordo com a taxonomia interna da banca.

---
---

# PARTE 5 — CHUNKING / SPLITTING

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

* **Estratégia de Splitting:** **Divisão Semântica / Estrutural baseada em Cláusulas**, utilizando um *RecursiveCharacterTextSplitter* ajustado com separadores customizados por Regex.
* **Tamanho dos Chunks e Overlap:** **800 tokens** (aprox. 3.500 caracteres) com **150 tokens de overlap** (aprox. 15%).
* **Unidade de Divisão:** Por **Seções/Cláusulas** (nível primário) com *fallback* recursivo para parágrafos e sentenças.
* **Uso de Splitter Recursivo:** Sim. A prioridade de divisão segue a ordem: `["\nCLÁUSULA ", "\n\n", "\n", ". ", " ", ""]`. Isso garante que a cláusula seja mantida junta até o limite do tamanho do chunk; se ultrapassar, divide nos parágrafos internos.
* **Estratégia Específica por Documento:** **Sim, indispensável.** Um contrato possui estrutura formal rígida e lógica declarativa; uma transcrição de call center é um fluxo conversacional desestruturado. Tratar ambos da mesma forma destruiria a recuperação.

---
### Comparativo de Estratégia de Documentos (Contrato vs. Call Center)
| Critério | Contrato (Estruturado) | Transcrição de Call Center (Não-Estruturado) |
| :--- | :--- | :--- |
| **Ponto de corte natural** | Limites formais (Cláusulas, Parágrafos Únicos e Anexos). | Janelas de tempo (ex: a cada 2 minutos) ou turnos de fala (*Speaker Turns*). |
| **Janela de Overlap** | Pequena a média (mantém a coesão entre parágrafos da mesma cláusula). | Alta (garante que a troca de contexto entre cliente e atendente não seja cortada ao meio). |
| **Tratamento de ruído** | Remoção de cabeçalhos repetitivos e numeração de páginas. | Filtro de marcações de áudio (ex: `[risos]`, `[inaudível]`) e hesitações (*"ah"*, *"né"*). |

* **O que pode acontecer se os chunks forem muito pequenos?**
  * *Perda de Contexto (Fragmentação):* Um trecho de 50 tokens pode isolar a frase *"A multa será de 50%"* e perder a condição contida na frase anterior (*"Em caso de rescisão por falha grave da CONTRATADA..."*).
  * *Alucinação da LLM:* A IA responderá com base em informações incompletas, inventando premissas para preencher a lacuna.
* **O que pode acontecer se os chunks forem muito grandes?**
  * *Diluição da Similaridade:* O vetor gerado mistura múltiplos temas contratuais, reduzindo a precisão da busca.
  * *Efeito "Lost in the Middle":* A LLM ignora detalhes importantes escondidos no meio de blocos gigantescos de minutas.

* **Como você trataria uma tabela na hora de dividir? Uma tabela cortada ao meio ainda significa alguma coisa? E uma imagem?**
  * *Tabelas:* Extraídas em bloco único no formato **Markdown Table** (ex: cronogramas de pagamento e tabelas de preço). Se muito extensas, aplica-se divisão por linha com repetição do cabeçalho.
  * *Imagens:* Organogramas societários e fluxogramas de processos passam por um modelo de visão multimodal no pipeline para gerar uma **descrição descritiva textual**, indexada junto ao metadado do contrato.

* **Como saber se a escolha de chunking foi boa? Que evidência você juntaria para provar isso?**
  * *Critério de Sucesso:* Garantir que as cláusulas contratuais, limites de responsabilidade e penalidades não sejam fragmentados e que o retriever traga a regra completa sem "gordura" desnecessária.
  * *Evidências Juntadas para Provar:*
    1. **Relatório de Métricas Automatizadas (RAGAS):** Demonstração de índices elevados de *Context Recall* (recuperação integral da cláusula) e *Context Precision* (ausência de ruído nos chunks de 800 tokens).
    2. **Matriz de Benchmark de Chunks:** Um gráfico comparativo testando tamanhos de 300, 800 e 1.500 tokens em um dataset de validação com 50 perguntas contratuais padrão, provando que a configuração de 800 tokens obteve o maior *Hit Rate@3* e menor taxa de alucinação da LLM.

---

## CENÁRIO 2: Assistente de Jurisprudência Interna e Peças Processuais

* **Estratégia de Splitting:** **Divisão Estruturada por Seção Jurídica (Markdown Header Splitter)**, complementada por *RecursiveCharacterTextSplitter*.
* **Tamanho dos Chunks e Overlap:** **1.200 tokens** (aprox. 5.000 caracteres) com **200 tokens de overlap** (aprox. 15%).
* **Unidade de Divisão:** Por **Tópicos/Capítulos da Peça Processual** (*"DOS FATOS"*, *"DO DIREITO"*, *"DOS PEDIDOS"*).
* **Uso de Splitter Recursivo:** Sim. A prioridade segue os marcadores da peça: `["\n# DOS ", "\n\n", "\n", ";\n", ". ", " "]`.
* **Estratégia Específica por Documento:** **Sim.** Peças jurídicas exigem janelas de contexto maiores do que contratos, pois uma tese jurídica demanda a apresentação da premissa de fato, a citação doutrinária/jurisprudencial e o pedido de forma encadeada.

---

## Comparativo de Estratégia de Documentos (Contrato vs. Call Center)

| Critério | Peça Inicial / Contestação | Acórdão / Jurisprudência |
| :--- | :--- | :--- |
| **Ponto de corte natural** | Blocos argumentativos (*"Dos Fatos"*, *"Do Direito"*, *"Dos Pedidos"*). | Estrutura de voto do relator e Ementa (*Relatório*, *Fundamentação*, *Dispositivo*). |
| **Janela de Overlap** | Moderada (para manter a tese jurídica conectada aos artigos de lei citados). | Baixa a moderada (foco em isolar a *ratio decidendi* / tese vencedora). |
| **Tratamento de ruído** | Remoção de rodapés de peticionamento e timbres de advogados. | Remoção de ementários longos repetidos e relatórios puramente processuais de andamento. |

---

* **O que pode acontecer se os chunks forem muito pequenos?**
  * *Fragmentação da Tese Jurídica:* A argumentação de uma apelação é dividida, separando a premissa legal da conclusão lógica do advogado, fazendo com que a LLM perca a força da tese defendida.

* **O que pode acontecer se os chunks forem muito grandes?**
  * *Poluição do Contexto Jurisprudencial:* O chunk engloba trechos de processos diferentes ou múltiplos argumentos não correlacionados, atrapalhando a busca precisa por precedentes específicos.

* **Como você trataria uma tabela na hora de dividir? Uma tabela cortada ao meio ainda significa alguma coisa? E uma imagem?**
  * *Tabelas:* Planilhas de cálculo de liquidação de sentença e demonstrativos de débitos são convertidas para **Markdown Table**, garantindo que o valor financeiro mantenha a relação direta com o período/mês de apuração.
  * *Imagens:* *Print screens* de conversas de WhatsApp (provas em ações trabalhistas/civis) ou fotos de acidentes anexadas passam por LLM multimodal para gerar um **resumo descritivo probatório em texto**.

* **Como saber se a escolha de chunking foi boa? Que evidência você juntaria para provar isso?**
  * *Critério de Sucesso:* Assegurar que a tese jurídica, os fundamentos de direito e os precedentes sejam recuperados com coesão, permitindo que o advogado redija a peça com base em argumentos íntegros e não fragmentados.
  * *Evidências Juntadas para Provar:*
    1. **Validação Humana (Curadoria de Advogados):** Relatório de testes com a equipe jurídica da banca respondendo a um conjunto de 50 consultas de teses recorrentes.
    2. **Métrica de Posicionamento (MRR - Mean Reciprocal Rank):** Evidência estatística de que os precedentes mais relevantes e vencedores apareceram consistentemente nas primeiras posições (*Top-3*) da recuperação vetorial utilizando blocos de 1.200 tokens orientados por seções.

---
---

# PARTE 6 — EMBEDDINGS

---

## Tabela Comparativa dos Modelos Escolhidos

| Item | Cenário 1: Due Diligence Contratual (Auditoria de Riscos) | Cenário 2: Peças e Jurisprudência |
| :--- | :--- | :--- |
| **Modelo escolhido** | **bge-m3** (BAAI) | **text-embedding-3-large** (OpenAI) |
| **Dimensão do embedding** | 1024 dimensões | 3072 dimensões (ajustável até 256) |
| **Suporta português?** | Sim (Excelente suporte) | Sim (Excelente suporte) |
| **É multilíngue?** | Sim (+100 idiomas) | Sim (Multilíngue nativo) |
| **Tamanho máximo de entrada** | 8.192 tokens | 8.191 tokens |
| **É open source?** | **Sim** (Licença MIT) | **Não** (Proprietário) |
| **Pode ser executado localmente?** | **Sim** (Docker / Ollama / HuggingFace) | **Não** (Apenas Nuvem/API) |
| **Possui API?** | Sim (SaaS via Together AI / HuggingFace Inference API) | Sim (API Oficial OpenAI) |
| **Custo aproximado** | **R$ 0,00** (Infra própria) ou ~$0,000005/1k tokens (API) | $0.00013 / 1.000 tokens |
| **Fonte da informação** | [BAAI bge-m3 Repository](https://huggingface.co/BAAI/bge-m3) | [OpenAI Embeddings Documentation](https://platform.openai.com/docs/guides/embeddings) |

---

## Justificativa de Adequação por Cenário

### Por que o bge-m3 é adequado ao Cenário 1 (Due Diligence Contratual)?
O modelo **bge-m3** (BAAI) foi escolhido para o Copiloto de Due Diligence por três razões centrais:
1. **Soberania e Privacidade Absoluta dos Dados:** Contratos de Due Diligence envolvem segredos industriais, dados financeiros estratégicos e cláusulas confidenciais. Por ser *Open Source*, o `bge-m3` permite execução **100% On-Premise (Local)** em servidores internos da empresa, garantindo que nenhum texto contratual sensível navegue por APIs externas ou nuvens terceirizadas.
2. **Busca Híbrida Nativa (Dense + Sparse + Multi-Vector):** O `bge-m3` é um dos raros modelos que gera embeddings denso (similaridade semântica) e esparso (estilo BM25/palavra-chave) simultaneamente. Em auditorias contratuais, é fundamental combinar a busca semântica (*"qual a penalidade por quebra?"*) com a busca exata por códigos, CNPJs ou números de cláusula.

### Por que o text-embedding-3-large é adequado ao Cenário 2 (Jurisprudência e Peças)?
O modelo **text-embedding-3-large** da OpenAI foi escolhido para o Assistente de Jurisprudência por sua alta capacidade semântica e escalabilidade:
1. **Alta Representação Semântica e Nuances Jurídicas:** O domínio de peças processuais e jurisprudência exige captar a sutileza das teses de direito. Com 3.072 dimensões, o modelo possui uma das maiores capacidades de separação vetorial do mercado, permitindo diferenciar teses jurídicas parecidas em petições extensas.
2. **Infraestrutura Escalável em Nuvem:** O acervo de peças e pareceres internos exige velocidade para indexar centenas de novos documentos semanalmente. A API gerenciada da OpenAI oferece altíssimo throughput e integração direta sem a necessidade de manter clusters locais de GPUs dedicadas para embedding no escritório.

---

#### Considerou algum modelo alternativo e descartou? Qual, e por quê?
* **Modelo Alternativo Considerado:** `text-embedding-3-small` (OpenAI) e `all-MiniLM-L6-v2` (Sentence-Transformers).
* **Motivo do Descarte:**
  * O `all-MiniLM-L6-v2` foi descartado por ter uma janela de contexto extremamente curta (apenas 256 tokens) e por apresentar desempenho fraco no processamento de textos complexos em português.
  * O `text-embedding-3-small` foi testado para o Cenário 2, mas descartado em favor da versão `large`. Embora seja mais barato, o modelo `small` apresentou menor precisão para distinguir nuances entre teses jurídicas correlatas (ex: diferenciar *responsabilidade civil objetiva* de *subjetiva* em petições do Cível).

#### Se o cenário envolve documentos sigilosos, isso muda sua escolha entre modelo local e API? Como?
* **Sim, muda radicalmente.** 
* **Impacto no Cenário 1 (Contratos):** Como operações de M&A e Due Diligence envolvem alto risco de vazamento e obrigações contratuais de sigilo (NDAs severos), a escolha por um **modelo local (Open Source como o `bge-m3`)** é um requisito de segurança obrigatório. O uso de APIs públicas de terceiros poderia violar políticas de compliance da organização.
* **Mitigação no Cenário 2 (Jurisprudência):** Para utilizar a API no Cenário 2, exige-se a contratação do plano *Enterprise* da OpenAI ou via **Azure OpenAI Service**, com cláusula contratual explícita de *Zero Data Retention* (ZDR), onde os dados enviados via API não são armazenados nem utilizados para treinamento de novos modelos.

#### O tamanho máximo de entrada do modelo tem relação com a sua decisão de chunking da Parte 5? Explique.
* **Sim, o limite de entrada do modelo é o teto máximo absoluto para o tamanho do chunk.**
* Ambos os modelos escolhidos suportam até **8.192 tokens de contexto de entrada**.
* **Relação Prática com o Chunking escolhido:**
  * Na Parte 5, definimos chunks de **800 tokens** (Cenário 1) e **1.200 tokens** (Cenário 2).
  * O tamanho dos nossos chunks utiliza apenas cerca de 10% a 15% da capacidade máxima de entrada do embedding. Isso é uma decisão deliberada: o fato de o modelo aceitar 8.000 tokens **não significa** que devamos criar chunks desse tamanho. 
  * Chunks muito extensos (próximos de 8k) sofrem com o fenômeno de **diluição do vetor semântico**, onde múltiplos tópicos são misturados em um único ponto no espaço vetorial, reduzindo drasticamente a precisão da recuperação (*Context Precision*). O limite amplo de 8.192 tokens nos garante margem para concatenar os metadados e o contexto ao chunk antes de vetorizar, sem perigo de truncamento do texto.

---
---

# ARQUITETURA FINAL DO SISTEMA RAG

---

## CENÁRIO 1: Copiloto de Análise Contratual e Due Diligence (Auditoria de Riscos)

### Diagrama do Sistema Completo (ASCII)

```text
[ Documento Original (PDF / Contrato Escaneado / Anexo) ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 1. PIPELINE DE INGESTÃO E EXTRAÇÃO                     │
│  - Leitura vetorial (pdfplumber) ou OCR (Tesseract)     │
│  - Conversão de Tabelas em Markdown Table              │
│  - LLM de Visão (GPT-4o) para Captioning de Imagens    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. LIMPEZA E NORMALIZAÇÃO                              │
│  - Remoção de cabeçalhos repetidos, rodapés e marcas     │
│  - Padronização de codificação UTF-8, datas e moedas   │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. ESTRATÉGIA DE CHUNKING                              │
│  - RecursiveCharacterTextSplitter por Cláusulas        │
│  - Chunks de 800 tokens com 150 tokens de overlap      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. ENRIQUECIMENTO E METADADOS                          │
│  - Extração determinística (title, created_at)         │
│  - Extração via LLM (Pydantic/JSON): is_latest_version │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. EMBEDDING E ARMAZENAMENTO VETORIAL                  │
│  - Modelo Open Source: bge-m3 (Local / 1024 dimensões) │
│  - Banco Vetorial com suporte a Busca Híbrida          │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 6. RECUPERAÇÃO E GERAÇÃO (RAG LOOP)                    │
│  - Consulta do Usuário (Analista de M&A)               │
│  - Retriever Híbrido (BM25 + Vetorial) + Reranker      │
│  - Geração de Resposta pela LLM + Contexto Contratual  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
              [ Resposta ao Usuário ]
```
### Tabela de Decisões

| Etapa | Decisão | Justificativa em uma linha |
| :--- | :--- | :--- |
| **Extração** | `pdfplumber` + `Tesseract OCR` + LLM de Visão | Garante o processamento de PDFs digitais, digitalizados antigos e conversão de diagramas/organogramas corporativos. |
| **Limpeza** | Remoção de rodapés/timbres + Regex de Moedas | Elimina ruídos textuais repetitivos e padroniza termos financeiros para evitar distorções na busca. |
| **Chunking** | Baseado em Cláusulas (800 tokens / 150 overlap) | Preserva a integridade da regra contratual sem fragmentar o contexto jurídico ou estourar a similaridade. |
| **Metadados** | Determinísticos + LLM Estruturado (Pydantic) | Captura dados estruturais do arquivo e infere relações complexas de negócio (`is_latest_version`). |
| **Embeddings** | `bge-m3` (Open Source / Execução Local) | Assegura soberania e sigilo absoluto de dados contratuais confidenciais com suporte a busca híbrida nativa. |

---

#### Quais são os riscos e limitações da sua própria proposta? O que você sabe que essa arquitetura não resolve bem?

* **Limitação em Agregações Contábeis e Numéricas Globais:** A arquitetura baseada em RAG é excelente para recuperar cláusulas específicas, mas falha em perguntas que exigem operações matemáticas ou contábeis em larga escala sobre toda a base (ex: *"Qual é a soma total de todas as multas de rescisão previstas em nossa carteira ativa de contratos?"*). Como o modelo processa apenas os chunks recuperados, ele não consegue varrer e somar dados dispersos em centenas de documentos sem um acoplamento direto com um banco de dados relacional estruturado (SQL).
* **Risco de Dependência de Versionamento:** Se um aditivo contratual for injetado na base sem o vínculo correto do metadado `contract_family_id` ou sem atualizar a flag `is_latest_version`, a arquitetura poderá resgatar o texto de uma cláusula antiga que já foi revogada, induzindo o analista de Due Diligence a tomar decisões baseadas em obrigações contratuais desatualizadas.
* **Complexidade em Referências Cruzadas Complexas:** Contratos extensos costumam fazer remissões distantes (ex: *"Conforme o disposto no Anexo IV, item 3.2, alínea 'b', combinado com a Cláusula 18..."*). Se os blocos de texto estiverem em partes muito distantes do documento, o recuperador vetorial pode trazer apenas um dos trechos, deixando o contexto incompleto para a LLM.

## CENÁRIO 2: Assistente de Jurisprudência Interna e Peças Processuais

### Tabela de Decisões

| Etapa | Decisão | Justificativa em uma linha |
| :--- | :--- | :--- |
| **Extração** | `pdfplumber` focado em caixas delimitadoras | Evita a junção indevida de textos em petições de layout complexo ou com tarjas laterais de tribunais. |
| **Limpeza** | Supressão de carimbos de protocolo e rodapés PJe | Limpa o corpo textual de informações processuais puramente burocráticas que prejudicam o foco argumentativo. |
| **Chunking** | Baseado em Parágrafos/Seções (1.200 tokens / 200 overlap)| Mantém a coesão da tese jurídica e dos fundamentos do voto intactos dentro do mesmo bloco de recuperação. |
| **Metadados** | Cruzamento ERP Jurídico + LLM com Pydantic | Associa metadados processuais exatos (`processo_cnj`) e classifica o status atualizado da tese jurídica. |
| **Embeddings** | `text-embedding-3-large` (OpenAI API / Nuvem) | Oferece a mais alta resolução semântica para distinguir nuances e sutilezas entre teses jurídicas complexas. |

---

#### Quais são os riscos e limitações da sua própria proposta? O que você sabe que essa arquitetura não resolve bem?

* **Risco de Mudança Superveniente de Jurisprudência (*Overruling*):** O RAG busca com base na similaridade semântica do texto, o que significa que ele pode resgatar com alto score de relevância uma petição ou acórdão antigo muito bem fundamentado, mas que se baseia em uma lei que foi revogada ou em uma Súmula que já foi superada pelos tribunais superiores. Se o metadado `tese_status` não estiver rigorosamente atualizado, a IA recomendará um precedente obsoleto.
* **Limitação em Buscas Estritas por Chaves Numéricas (Ex: Número CNJ):** A busca estritamente vetorial e semântica lida mal com strings alfanuméricas exatas. Perguntas que exigem localizar um processo pelo número do CNJ ou por artigos de lei específicos (ex: *Art. 486 da CLT*) podem falhar ou trazer precedentes errados se o sistema não contar com uma camada complementar de busca léxica (BM25) ou filtro relacional em banco SQL.
* **Complexidade no Cálculo de Prazos Processuais:** O RAG não resolve o cálculo exato de prazos fatais e contagem de dias úteis em feriados forenses locais. Como o LLM opera por probabilidade estatística de texto, ele jamais deve ser utilizado para calcular datas-limite de protocolo sem o suporte de um motor determinístico de regras de prazos.

---
---

# COMPARAÇÃO ENTRE OS DOIS CENÁRIOS

---

#### 1. Em que pontos as decisões foram diferentes? Por quê?
As decisões divergiram principalmente nas etapas de **chunking, metadados e modelo de embedding**, refletindo diretamente a natureza distinta de cada domínio:
* **Estratégia de Chunking:** O Cenário 1 (Contratos) utilizou blocos menores (**800 tokens**) focados em **cláusulas e parágrafos**, pois minutas contratuais exigem precisão cirúrgica na recuperação de regras e penalidades específicas. Já o Cenário 2 (Jurisprudência) adotou blocos maiores (**1.200 tokens**) orientados por **blocos argumentativos e seções de tese**, pois petições e acórdãos dependem da preservação integral do raciocínio lógico e da fundamentação jurídica (*ratio decidendi*).
* **Modelo de Embedding e Infraestrutura:** O Cenário 1 escolheu o **bge-m3 (Open Source e execução local)** para garantir sigilo absoluto e soberania sobre dados estratégicos e financeiros confidenciais de M&A. O Cenário 2 optou pelo **text-embedding-3-large (API proprietária da OpenAI)** devido à necessidade de altíssima resolução semântica para distinguir nuances complexas entre teses jurídicas e à facilidade de escalabilidade em nuvem.
* **Metadados de Negócio:** No Cenário 1, focou-se no versionamento temporal e familiar (`contract_family_id` e `is_latest_version`) para evitar conflitos entre aditivos. No Cenário 2, o foco foi a validação processual e o mérito (`processo_cnj` e `tese_status`) para cruzar com o ERP jurídico e checar a vigência de precedentes.

---

#### 2. Em que pontos foram iguais? Isso é sinal de boa prática geral ou de você ter repetido a decisão sem pensar?
As decisões convergiram nas etapas estruturais de **pipeline de ingestão (com extração híbrida de PDF + OCR + Visão), limpeza de ruídos e uso de recuperação híbrida com Reranker**. 
* **É sinal de boa prática geral.** A adoção de uma fundação técnica padronizada é um princípio essencial de engenharia de software e arquitetura de dados (*pipeline robusto, separação de texto e imagens, limpeza de lixo textual e busca mista semântica/lexical*). Diferentes tipos de documentos exigem tratamentos de ponta distintos na camada de negócio (chunking e embeddings), mas compartilham das mesmas dores fundamentais de engenharia na hora de extrair e limpar dados brutos de arquivos PDF de baixa qualidade.

---

#### 3. Se você tivesse que construir apenas um dos dois, qual escolheria, e por quê?
Escolheria construir o **Cenário 1 (Copiloto de Análise Contratual / Due Diligence)**.
* **Justificativa de Impacto de Negócio:** Processos de Due Diligence em M&A e auditorias contratuais corporativas lidam com volumes massivos de documentos altamente complexos, variados e exaustivos para a revisão humana em prazos apertados. Um erro de leitura ou perda de uma cláusula de restrição/multa pode custar milhões de reais à empresa. Além disso, o desafio técnico de implementar uma arquitetura 100% *on-premise* com modelos open source (`bge-m3`) para proteger dados confidenciais de clientes entrega um ganho arquitetural e de segurança corporativa muito mais desafiador e de altíssimo valor de mercado.

---
---

# METODOLOGIA DE USO DE IA E REFERÊNCIAS BIBLIOGRÁFICAS

---

#### Como você usou IA para te apoiar nessa atividade? Quais ferramentas? Como você avaliou e verificou a resposta dela?

* **Ferramentas Utilizadas:** O projeto foi desenvolvido com o apoio de um Assistente de IA de última geração (baseado em modelos de grande porte como o Gemini), utilizado como coautor técnico, estruturador de texto e revisor de arquitetura de RAG.
* **Forma de Utilização:** A IA foi acionada iterativamente por meio de prompts direcionados para:
  1. *Elaboração e contrraste de cenários jurídicos e contratuais* (definindo o trade-off entre rigor contratuais e teses processuais).
  2. *Desenho de arquitetura de dados e engenharia de software* (estruturação de diagramas em ASCII, escolha de estratégias de *chunking* recursivo e dimensionamento de janelas de *overlap*).
  3. *Pesquisa comparativa de modelos de embeddings* (`bge-m3` vs. `text-embedding-3-large`), mapeando dimensões, janelas de contexto, custos e viabilidade de execução local (*on-premise*).
* **Avaliação e Verificação das Respostas:** A validação e o controle de qualidade do conteúdo gerado pela IA seguiram três pilares de checagem técnica:
  1. **Consistência Teórica de RAG:** Verificação rigorosa para garantir que os conceitos aplicados (como densidade de vetores, *Context Precision*, *Context Recall* e limitações de agregações contábeis globais) estivessem alinhados com o estado da arte da engenharia de dados em 2026.
  2. **Viabilidade Jurídico-Técnica:** Checagem para assegurar que a separação entre dados determinísticos (como metadados de ERP e números CNJ) e dados probabilísticos (gerados via LLM) fizesse sentido prático no dia a dia de escritórios de advocacia e departamentos de M&A.
  3. **Mitigação de Alucinações:** Revisão manual de todas as tabelas de decisão, parâmetros de tokens (ex: 800 vs. 1.200 tokens) e links de referência técnica para garantir precisão absoluta antes da consolidação do documento.

---

## Seção de Referências e Links de Pesquisa

* **Modelos de Embeddings e Bibliotecas:**
  * [Repositório Oficial BAAI bge-m3 no Hugging Face](https://huggingface.co/BAAI/bge-m3) — Especificações técnicas do modelo multivetorial e suporte a busca densa/esparsa.
  * [Documentação Oficial de Embeddings da OpenAI](https://platform.openai.com/docs/guides/embeddings) — Métricas, janelas de entrada e custos do modelo *text-embedding-3-large*.
  * [LangChain Documentation - Text Splitters](https://python.langchain.com/docs/concepts/text_splitters/) — Fundamentação teórica para o uso de *RecursiveCharacterTextSplitter* e controle de *overlap*.

* **Frameworks de Avaliação de RAG:**
  * [RAGAS (Retrieval Augmented Generation Assessment)](https://docs.ragas.io/) — Padrão de mercado para métricas automatizadas de *Context Recall* e *Context Precision*.

* **Ferramentas de Extração e Processamento:**
  * [pdfplumber Python Library](https://github.com/jsvine/pdfplumber) — Extração estruturada de texto e caixas delimitadoras de PDFs.
  * [Tesseract OCR Engine](https://github.com/tesseract-ocr/tesseract) — Motor de reconhecimento óptico de caracteres para documentos digitalizados legados.

