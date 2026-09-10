# EducaChat — Fase 1 (entrega 02/09/2026)

Texto único para copiar. Seções 1.1 a 1.10.

---

## 1.1 Resumo

O avanço das ferramentas de inteligência artificial generativa ampliou o acesso de estudantes a respostas imediatas, mas evidenciou um risco pedagógico: o uso desses sistemas como atalho para obter o resultado pronto, muitas vezes inadequado à série do aluno. Nesse contexto, o projeto EducaChat propõe um protótipo de assistente virtual escolar gratuito para apoiar estudantes a partir do 6º ano do Ensino Fundamental em Matemática, Português, Ciências e conhecimentos gerais. O objetivo geral é desenvolver um chatbot que conduza o aluno à compreensão pelo método socrático, restringindo o material à etapa escolar informada no cadastro, em vez de entregar trabalhos ou soluções acabadas. O público, nesta fase, são estudantes do 6º ano em diante, e o local de realização é o ambiente acadêmico do curso de Análise e Desenvolvimento de Sistemas da ETEP, em São José dos Campos, como prototipação voltada à futura aplicação em escolas, ainda sem instituição parceira formalizada. A metodologia articula o artigo extensionista, o desenvolvimento ágil com quadro Kanban e a construção incremental de um sistema em Vue, com autenticação, seleção de série e recuperação de conteúdos curriculares. As atividades previstas incluem diagnóstico da demanda, fundamentação teórica, prototipação do assistente, versionamento em Git e produção de documentação e apresentação. Espera-se um protótipo funcional mínimo capaz de filtrar conteúdos por série e de estimular o raciocínio do estudante, contribuindo para a formação dos discentes de ADS e de Ciência da Computação e, potencialmente, para o reforço escolar acessível quando o produto for ofertado a instituições de ensino.

Palavras-chave: educação básica. inteligência artificial. tutoria socrática. prototipagem de software. extensão universitária.

## 1.2 Introdução

A popularização de assistentes de inteligência artificial generativa alterou o modo como muitos estudantes buscam apoio para tarefas escolares. Em poucos segundos, é possível obter uma redação, a resolução de uma equação ou um resumo de conteúdo histórico. Esse acesso imediato, contudo, convive com um problema pedagógico: quando a ferramenta entrega a resposta pronta, o aluno tende a copiar o resultado sem percorrer o raciocínio exigido pela etapa escolar em que se encontra. Além disso, modelos de uso geral frequentemente produzem explicações acima ou abaixo da série do estudante, misturando competências de anos distintos.

No Brasil, a Base Nacional Comum Curricular organiza aprendizagens por etapa e por componente, o que torna inadequado um “chat único” para todas as idades. Um aluno do 6º ano do Ensino Fundamental e um estudante do Ensino Médio não devem receber o mesmo recorte de Matemática, Português ou Ciências. O EducaChat parte dessa premissa: o cadastro registra a série, e o sistema restringe o material àquela etapa, com ênfase em Matemática, Português, Ciências e conhecimentos gerais.

A situação-problema que fundamenta o projeto é, portanto, dupla. De um lado, há desigualdade de acesso a reforço escolar presencial e gratuito. De outro, o uso irrestrito de IAs generativas pode aprofundar a dependência de respostas prontas e desalinhar o conteúdo da série. A relevância social aproxima-se do Objetivo de Desenvolvimento Sustentável 4, relativo à educação de qualidade, inclusiva e equitativa. A relevância acadêmica dialoga com o curso de Análise e Desenvolvimento de Sistemas e com a Ciência da Computação, ao exigir análise de requisitos, prototipação, persistência de dados, integração com modelo de linguagem e gestão ágil.

A ação insere-se nas Diretrizes para a Extensão na Educação Superior Brasileira, que vinculam a formação estudantil à interação com demandas da sociedade. Nesta Fase 1, o diálogo com a sociedade ocorre como planejamento: o protótipo é concebido para uso escolar futuro, embora ainda não exista instituição parceira formalizada. O local de elaboração é o ambiente acadêmico da ETEP, em São José dos Campos.

O objetivo geral é prototipar um assistente virtual escolar gratuito que oriente o estudante pelo método socrático e utilize apenas conteúdos compatíveis com a série informada. Os objetivos específicos são: (a) prever autenticação com indicação de série a partir do 6º ano; (b) filtrar materiais curriculares (BNCC) por etapa e componente; (c) oferecer três modos de uso — dúvida, estruturação de trabalho e exercício com correção comentada; (d) documentar o processo em artigo, repositório Git e quadro Kanban; (e) preparar apresentação e devolutiva quando houver espaço de aplicação.

## 1.3 Diagnóstico da Demanda

O diagnóstico que orienta o EducaChat é, nesta fase, documental, e não resulta de pesquisa de campo já concluída em uma escola específica. Essa escolha é explícita: ainda não há instituição parceira formalizada, e inventar entrevistas ou quantitativos de alunos comprometeria a integridade do relato extensionista. Os instrumentos utilizados foram a leitura da BNCC, a análise de diretrizes de extensão e a definição de requisitos da disciplina de projetos (interface em Vue, autenticação com série, versionamento Git e gestão em Trello). Não há, nesta Fase 1, observação sistematizada do uso de IAs generativas por estudantes: não se registrou método, período, amostra nem fonte empírica. A percepção de uso cotidiano dessas ferramentas entra apenas como hipótese de trabalho da equipe, a ser verificada quando houver escuta com escola.

O território de referência é São José dos Campos, no estado de São Paulo, onde se situa a ETEP. O público beneficiário pretendido são estudantes da educação básica a partir do 6º ano do Ensino Fundamental, em Matemática, Português, Ciências e conhecimentos gerais. O público executor é a dupla de graduandos Thiago Reis, do curso de Análise e Desenvolvimento de Sistemas, e Marcus Paulo Pereira de Oliveira, de Ciência da Computação.

A demanda que o projeto assume pode ser sintetizada em três hipóteses de trabalho, e não em achados observacionais. Primeiro, ferramentas de IA de uso geral não distinguiriam adequadamente a série do aluno e, por isso, tenderiam a oferecer conteúdos deslocados da etapa. Segundo, o formato “resposta pronta” favoreceria a entrega de trabalhos escolares sem mediação pedagógica, o que conflitaria com a formação de competências previstas na BNCC. Terceiro, o reforço escolar presencial nem sempre seria acessível de forma contínua e gratuita, o que abriria espaço para um protótipo digital que oriente em vez de substituir o estudo.

Parte-se ainda da hipótese de que parte dos estudantes recorre a IAs no celular, sem mediação de professor e sem indicação de série. Isso reforça a tese de desenho de que um protótipo acadêmico só se justifica se incorporar, no próprio desenho, o filtro curricular e a recusa de tarefas prontas. A sustentabilidade educacional, neste diagnóstico, significa ampliar o acesso a um apoio gratuito e alinhado à etapa, e não substituir a escola.

A prioridade definida pela equipe, até que haja escuta com uma escola, é construir um produto mínimo viável com login, seleção de série, chat em três modos e base de conteúdos da etapa, usando materiais oficiais (BNCC) e um recorte de sustentabilidade educacional. A validação com professores e estudantes da educação básica fica registrada como etapa seguinte do plano de articulação, e não como resultado já obtido.

## 1.4 Referencial Teórico

A extensão universitária, no Brasil, não se reduz à prestação unilateral de serviço nem à produção exclusiva de artigo científico. A Resolução CNE/CES nº 7, de 18 de dezembro de 2018, estabelece as Diretrizes para a Extensão na Educação Superior Brasileira e afirma a extensão como atividade que integra a formação do estudante à interlocução com a sociedade (BRASIL, 2018). O EducaChat adota esse marco: o software é o meio de uma ação que pretende, quando aplicada, devolver à comunidade escolar um instrumento de apoio ao estudo, e não apenas um exercício interno de programação.

A educação de qualidade e o acesso ao conhecimento aproximam o projeto do Objetivo de Desenvolvimento Sustentável 4 da Agenda 2030, que trata de assegurar educação inclusiva, equitativa e de qualidade (ONU, 2015). A “sustentabilidade educacional” aqui não substitui o debate ambiental, mas o complementa: tecnologia pode reduzir barreiras de acesso a um reforço mediado, desde que não reproduza a lógica de atalho. O módulo de Ciências e conhecimentos gerais poderá, em etapas posteriores, dialogar também com temas de meio ambiente, energia e mudanças climáticas, alinhados a habilidades da BNCC.

A Base Nacional Comum Curricular define direitos de aprendizagem e organiza competências por etapa e componente curricular (BRASIL, 2018a). Esse documento é o principal recorte de conteúdo do protótipo. Ao indexar trechos por série e disciplina, o sistema evita tratar o currículo como um bloco único. A opção por partir do 6º ano corresponde ao segundo segmento do Ensino Fundamental, em que se intensificam a abstração matemática, a produção textual e os conceitos de Ciências, sem abandonar o cuidado com a linguagem adequada à faixa etária.

No campo da inteligência artificial aplicada à educação, distingue-se a tutoria inteligente — que diagnostica dificuldades e conduz o aprendiz — do uso de modelos generativos como meros produtores de texto. A UNESCO tem alertado para a necessidade de orientação ética, proteção de dados e centralidade humana no uso de IA em contextos educativos (UNESCO, 2021). O EducaChat posiciona-se no primeiro polo: o método socrático, baseado em perguntas que levam o aluno a explicitar o que já sabe e a dar o próximo passo, opera como restrição de desenho. Em dúvida, o sistema pede identificação de dados e hipóteses; em trabalho escolar, oferece estrutura e perguntas de pesquisa, não o texto final; em exercício, gera questão da série, aguarda a resposta e comenta o erro.

A proteção de dados pessoais de crianças e adolescentes é condição de legitimidade. A Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais) exige finalidade, necessidade e segurança no tratamento de dados e, no caso de menores, o melhor interesse do titular (BRASIL, 2018b, art. 14). Antes de qualquer teste escolar, o projeto documenta e deve implementar os seguintes controles: (a) finalidade — tutoria socrática restrita à série cadastrada, sem perfilamento comercial; (b) hipótese legal — consentimento específico de pelo menos um responsável, nos termos do art. 14 da LGPD, e execução das atividades acadêmicas da extensão; (c) melhor interesse — o sistema recusa resposta pronta e conteúdo de outra série; (d) papéis — a equipe acadêmica (e, quando houver, a escola) atua como controladora do cadastro e da série; o Supabase e o OpenRouter atuam como operadores no limite do serviço contratado; (e) minimização — e-mail de teste, série e mensagens da conversa; sem nome civil, foto, geolocalização, dado de saúde ou identificador escolar; (f) retenção e exclusão — contas e histórico de teste são apagados ao fim da disciplina ou a pedido, o que ocorrer primeiro; (g) canal para direitos — pedido de acesso, correção ou exclusão pelo e-mail institucional da dupla, com prazo de resposta alinhado à LGPD; (h) bloqueio técnico de dados reais — enquanto não houver termo de responsável e parceiro, o protótipo opera só com contas fictícias; cadastro com dado de aluno real deve ser recusado.

No fluxo de envio ao OpenRouter, o texto da conversa constitui dado pessoal e segue para tratamento no exterior (Estados Unidos e, conforme o modelo roteado, outros países em que o provedor do modelo opere). Não há, até esta data, decisão de adequação da ANPD reconhecendo nível equivalente nesses destinos. O mecanismo aplicável, antes de teste com titulares reais, é a transferência internacional amparada no art. 33, II, “b”, da LGPD, mediante adesão integral às cláusulas-padrão contratuais do Anexo II da Resolução CD/ANPD nº 19/2024 (BRASIL, 2024), firmadas entre o exportador (equipe/instituição) e o importador (OpenRouter e, se houver subprocessamento, o provedor do modelo). Enquanto essas cláusulas e o aviso a responsáveis não existirem, o envio de conversa de aluno real permanece bloqueado. Essa ressalva será retomada no contato com o parceiro externo.

Do ponto de vista da engenharia de software, o projeto apoia-se em métodos ágeis e no quadro Kanban para visualizar o fluxo de trabalho (Backlog, A Fazer, Em Desenvolvimento, Em Teste, Concluído). A abordagem incremental reduz o risco de construir um sistema completo sem validação e atende à exigência da disciplina de versionar o código e movimentar cards conforme o progresso. A arquitetura prevista separa interface (Vue), API (FastAPI), persistência de usuários (PostgreSQL via Supabase) e busca semântica do material da série (ChromaDB local), de modo que o modelo de linguagem não “invente matéria”, mas se apoie em trechos recuperados e filtrados.

A literatura sobre sistemas de tutoria inteligente reforça que o valor pedagógico está menos na velocidade da resposta e mais no encadeamento de pistas, na verificação do que o aprendiz já compreende e no retorno sobre o erro. Transposto para um modelo generativo, isso implica recusar o papel de “autor fantasma” de trabalhos escolares. O EducaChat, ao separar os modos dúvida, trabalho e exercício, operacionaliza essa recusa: cada modo tem um contrato distinto com o aluno. No modo trabalho, por exemplo, o sistema pode sugerir introdução, desenvolvimento e conclusão e formular perguntas de pesquisa, mas não deve produzir o texto a ser entregue ao professor. Essa distinção é central para que o protótipo não contradiga a finalidade extensionista de apoiar a aprendizagem.

Outro eixo é a governança do conteúdo. Sem uma base curricular filtrada, o modelo de linguagem completa lacunas com conhecimento paramétrico, o que pode misturar competências de anos diferentes ou introduzir imprecisões. A opção por ChromaDB local, com metadados de série e disciplina, materializa o princípio da BNCC de progressão das aprendizagens. A BNCC não é “treinada” como um modelo novo; ela é recuperada em trechos e injetada no contexto da conversa. O modelo do OpenRouter, em variante gratuita, funciona apenas como motor linguístico. Essa divisão de responsabilidades — currículo na base vetorial, diálogo no modelo, identidade e série no banco relacional — é também uma decisão ética: reduz a chance de o sistema inventar matéria.

Do ponto de vista formativo, o referencial dialoga com competências da Análise e Desenvolvimento de Sistemas (requisitos, prototipação, dados, qualidade) e da Ciência da Computação (algoritmos, arquitetura, inteligência artificial). A Resolução CNE/CES nº 7/2018 destaca que a extensão deve contribuir para a formação cidadã e profissional. Ao documentar limitações (ausência temporária de escola parceira, teto de requisições da API gratuita, protótipo ainda sem papéis de professor e administrador), o projeto evita o discurso de solução milagrosa e assume o caráter incremental próprio da extensão e da engenharia de software.

Assim, o referencial articula extensão, currículo, tutoria, proteção de dados e prototipação ágil. Sem essa articulação, o EducaChat se reduziria a mais um chatbot genérico; com ela, o produto pretende ser um artefato de formação profissional e, futuramente, de apoio escolar.

## 1.5 Metodologia

O projeto será desenvolvido em ciclo de planejamento, prototipação e, quando houver parceiro, aplicação com devolutiva. A Fase 1 corresponde ao planejamento e à fundamentação teórica. A Fase 2 descreverá a execução efetivamente realizada. A Fase 3 reunirá resultados, discussão, aprendizagens e referências.

As estratégias previstas são: (1) diagnóstico documental da demanda; (2) recorte de público (a partir do 6º ano) e de componentes (Matemática, Português, Ciências e conhecimentos gerais); (3) gestão ágil em Trello, com um card por vez; (4) versionamento em GitHub; (5) implementação incremental da stack — Vue 3 e Vite no front-end, FastAPI em Python no back-end, Supabase para autenticação e série, ChromaDB local para trechos da BNCC, OpenRouter com modelo gratuito como motor de linguagem; (6) testes internos do protótipo; (7) planejamento de contato com escola; (8) documentação e apresentação em Word.

Os recursos incluem ambiente de desenvolvimento (Cursor), quadro Trello, repositório GitHub, materiais oficiais da BNCC, plano gratuito do Supabase e modelos `:free` do OpenRouter. A participação do público externo, nesta fase, é potencial: o protótipo é desenhado para o aluno da educação básica, mas a interação direta ainda não ocorreu. A metodologia deixa isso explícito para não confundir planejamento com execução.

O critério pedagógico de aceite do produto mínimo é o seguinte: o aluno autentica-se, informa a série, escolhe um modo (dúvida, trabalho ou exercício) e recebe condução socrática baseada em material daquela etapa. Pedidos de resposta pronta ou de conteúdo de outra série devem ser recusados e redirecionados.

## 1.6 Planejamento e articulação com o parceiro externo

Ainda não houve contato formal com escola, secretaria ou outra instituição parceira, nem reunião com data, pauta e acordo registrados. Esta seção descreve o planejamento da articulação, e não um fato já consumado.

A abordagem prevista consiste em apresentar o EducaChat a uma escola da rede municipal ou estadual de São José dos Campos, ou a um núcleo de reforço vinculado à educação básica, por meio dos canais institucionais da ETEP e do professor orientador. A equipe executora — Thiago Reis (ADS) e Marcus Paulo Pereira de Oliveira (Ciência da Computação) — elaborará um convite objetivo, contendo: o que o protótipo faz e o que não faz; o recorte de série e de matérias; a garantia de que o sistema não redige trabalhos prontos; e os cuidados de LGPD (contas de teste, ausência de dados sensíveis, ciência de que a conversa transita por API de modelo de linguagem).

O que se pedirá ao parceiro, quando o contato ocorrer, é a possibilidade de teste supervisionado com estudantes a partir do 6º ano e a escuta de professores sobre dúvidas frequentes. O que se oferecerá em troca é o acesso ao protótipo, um relatório simples de uso e uma devolutiva presencial ou remota. As responsabilidades da equipe acadêmica incluem desenvolvimento, documentação e ética de dados; as da escola, quando houver aceite, incluirão autorização de responsáveis e mediação pedagógica.

Enquanto o parceiro não for formalizado, o desenvolvimento segue no ambiente da ETEP, com validação interna da dupla e do orientador. Qualquer alteração desse status será registrada nas Fases 2 e 3, sem retroagir como se a escola já tivesse participado desta Fase 1.

## 1.7 Público participante e local de realização

O público-alvo pretendido do EducaChat são estudantes da educação básica a partir do 6º ano do Ensino Fundamental, incluindo séries seguintes do Ensino Fundamental e, potencialmente, o Ensino Médio, desde que a série seja informada no cadastro. Os componentes priorizados no produto mínimo são Matemática, Português, Ciências e conhecimentos gerais. Não há número de participantes definido, porque ainda não existe turma parceira nem lista de inscritos.

O critério de participação no software é o cadastro com e-mail de teste e a escolha da série. A partir desse dado, o sistema filtra o material. Não se prevê, no primeiro protótipo, os papéis de professor e administrador, embora esses perfis permaneçam no backlog como evolução.

O local de realização desta Fase 1 é o ambiente acadêmico da ETEP, na Avenida Barão do Rio Branco, 882, Jardim Esplanada, São José dos Campos (SP). A aplicação em escola é perspectiva futura, condicionada à articulação descrita no item 1.6. A equipe executora é multidisciplinar: Thiago Reis, do curso de Análise e Desenvolvimento de Sistemas, e Marcus Paulo Pereira de Oliveira, de Ciência da Computação.

## 1.8 Plano de ação / intervenção

Etapa 1 — Planejamento (Fase 1): elaboração do artigo (itens 1.1 a 1.10), recorte de público e de stack, organização do Trello e criação do repositório GitHub. Responsáveis: Thiago Reis e Marcus Paulo Pereira de Oliveira. Produto: texto da Fase 1 e quadro de tarefas.

Etapa 2 — Prototipação técnica: scaffold em Vue (login e chat), API FastAPI, projeto Supabase com campo de série, ingestão da BNCC da série no ChromaDB e, depois, ligação da API OpenRouter com prompt socrático. Responsáveis: a definir na divisão interna da dupla. Produto: protótipo navegável.

Etapa 3 — Articulação externa: convite a escola ou núcleo de reforço, com termo de ciência sobre dados. Produto: registro de contato (quando houver).

Etapa 4 — Teste e ajuste: uso interno e, se autorizado, uso supervisionado por estudantes a partir do 6º ano. Produto: lista de falhas e melhorias.

Etapa 5 — Devolutiva e apresentação: documentação técnica, artigo (Fases 2 e 3) e apresentação em Word. Recursos: computador, Cursor, Trello, GitHub, Supabase free, ChromaDB local, OpenRouter free, PDFs oficiais da BNCC. Cronograma: alinhado às datas da disciplina; a Fase 1 concentra-se em 02/09/2026.

## 1.9 Participação dos estudantes e integração curricular

Os estudantes responsáveis pelo projeto são Thiago Reis, do curso de Análise e Desenvolvimento de Sistemas, e Marcus Paulo Pereira de Oliveira, de Ciência da Computação, ambos no contexto da ETEP. A composição é multidisciplinar: o ADS contribui com análise de requisitos, prototipação de sistemas, modelagem de dados e gestão de projeto; a Ciência da Computação contribui com fundamentos de algoritmos, arquitetura, inteligência artificial e persistência.

Os conhecimentos aplicados incluem levantamento de requisitos, arquitetura em camadas, interface web, API REST, banco relacional, busca vetorial, engenharia de prompt e versionamento. A divisão detalhada de papéis (front, back, artigo, apresentação) será combinada entre a dupla e registrada no Trello, evitando sobrecarga de uma única pessoa. O professor da disciplina de projetos orienta o recorte, cobra as entregas por fase e acompanha o quadro Kanban.

A integração curricular ocorre ao transformar uma demanda social — reforço escolar mediado e alinhado à série — em produto de software e em artigo extensionista, articulando ensino (conteúdos da graduação), pesquisa (referencial e diagnóstico documental) e extensão (planejamento de devolutiva à escola).

## 1.10 Instrumentos de acompanhamento e avaliação

O acompanhamento do projeto utilizará: quadro Trello (movimentação de cards como evidência de progresso); repositório GitHub (commits e histórico); arquivos do artigo por seção; registros de reunião da dupla; e, quando houver teste, lista de presença ou autorização de responsáveis, questionário breve de satisfação e prints do protótipo.

Indicadores quantitativos previstos: número de cards concluídos, número de commits, quantidade de matérias e séries efetivamente indexadas, e, após testes, número de sessões de uso. Indicadores qualitativos: clareza das respostas socráticas, adequação à série, recusa correta de pedidos de trabalho pronto e avaliação do orientador.

A devolutiva interna ocorrerá ao final de cada sprint (validação do card). A devolutiva externa dependerá da formalização do parceiro. Não se utilizarão, nesta Fase 1, dados de alunos reais de escola.

## Referências (rascunho para 3.5 — obras citadas nesta Fase 1)

BRASIL. Conselho Nacional de Educação. Câmara de Educação Superior. Resolução CNE/CES nº 7, de 18 de dezembro de 2018. Estabelece as Diretrizes para a Extensão na Educação Superior Brasileira. Diário Oficial da União: seção 1, Brasília, DF, 19 dez. 2018.

BRASIL. Ministério da Educação. Base Nacional Comum Curricular. Brasília: MEC, 2018a.

BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD). Diário Oficial da União: seção 1, Brasília, DF, 15 ago. 2018b.

BRASIL. Autoridade Nacional de Proteção de Dados. Resolução CD/ANPD nº 19, de 23 de agosto de 2024. Aprova o Regulamento de Transferência Internacional de Dados e o conteúdo das cláusulas-padrão contratuais. Diário Oficial da União: seção 1, Brasília, DF, 23 ago. 2024.

ORGANIZAÇÃO DAS NAÇÕES UNIDAS. Transformando nosso mundo: a Agenda 2030 para o Desenvolvimento Sustentável. Nova York: ONU, 2015.

UNESCO. Recomendação sobre a Ética da Inteligência Artificial. Paris: Unesco, 2021.
