# Entrega Aula 04 — Grupo 02

**Disciplina:** Cloud & Cognitive Environments — FIAP MBA AI Engineering & Multi-Agents
**Turma:** 1AIER
**Data de entrega:** 19/07/2026

## Grupo

| # | Nome completo | GitHub | E-mail FIAP |
|---|---------------|--------|-------------|
| 1 | Filipe Borges de Figueiredo Chicre da Costa |  | rm371390@fiap.com.br |
| 2 | Lucas de Assis Fialho | https://github.com/lucasdafialho | rm370676@fiap.com.br |
| 3 | Rafael Peinado da Silva | https://github.com/rafaelpeinado | rm373803@fiap.com.br |

**Organization do grupo:** https://github.com/fiap-1aier-grupo-02


## Distribuição do trabalho
| Membro | Nível assumido | Item específico |
|--------|----------------|-----------------|
| Rafael Peinado | 🟢 N1 | Exercícios 1.1, 1.2, 1.3, 1.4 |
| Filipe Borges | 🟡 N2 | Exercício 2.1 |
| Lucas de Assis | 🟡 N2 | Exercício 2.2, 2.3 |
| Rafael Peinado | 🔴 N3 (bônus) | Exercício 3.1, 3.2, 3.3 |

> Regra: cada membro deve ter pelo menos uma contribuição. O **rodízio entre aulas** (quem fez N1 antes faz N2 depois) é incentivado e vale o ponto do Critério 4 (ver [rubrica.md](rubrica.md)).

---

## 🟢 Nível 1 — Básico: Consolidando os Fundamentos

### Exercício 1.1 — Pronto vs Custom vs LLM

| Caso de uso | Pronta | Custom | LLM | Justificativa |
|-------------|:------:|:------:|:---:|---------------|
| Detectar idioma de uma review | x | | | O Azure AI Language possui uma funcionalidade específica de detecção de idioma, já treinada para textos em diversos idiomas. Não há necessidade de treinamento próprio ou de usar um LLM. |
| Classificar produtos em 5 categorias da QC (jargão próprio) | | x | | As categorias utilizam uma taxonomia específica da Quantum Commerce. Um modelo customizado, como Custom Text Classification ou CLU, permite treinar diretamente com os termos e exemplos do negócio. |
| Gerar descrição de produto a partir da foto + specs | | | x | A tarefa exige combinar informações visuais e textuais e produzir uma descrição coerente, comercial e não determinística. Um modelo multimodal pode interpretar a imagem e gerar o texto final. |
| Transcrever áudio de atendimento em PT-BR | x | | | O Azure AI Speech já possui modelos de Speech-to-Text treinados para pt-BR, com suporte a pontuação, transcrição em tempo real e processamento batch. |
| Extrair CPF, e-mail, telefone de chat (LGPD) | x | | | O recurso PII Detection do Azure AI Language foi desenvolvido especificamente para identificar e redigir dados pessoais, sendo mais previsível para controles relacionados à LGPD. |
| Responder pergunta aberta do cliente sobre política de troca | | | x | A resposta exige interpretação da pergunta, recuperação de trechos da política e geração de uma resposta contextualizada. A melhor abordagem é um LLM com RAG sobre os documentos oficiais da empresa. |
| OCR de etiqueta nutricional | x | | | O OCR/Read API foi otimizado para localizar e extrair texto de imagens. Um LLM poderia interpretar os dados posteriormente, mas não é necessário para a extração inicial. |
| Identificar peças industriais da empresa em foto de estoque | | x | | As peças pertencem a um vocabulário visual próprio, que provavelmente não é reconhecido adequadamente por um modelo genérico. O Custom Vision pode ser treinado com imagens rotuladas de cada peça. |

---

### Exercício 1.2 — Calcule o custo mensal

A Quantum Commerce processa por mês:

- **2M de reviews** para análise de sentimento (média 200 chars cada → 400M chars)
- **50.000 horas de atendimento** transcritas (Speech)
- **500k imagens de produto** analisadas (Vision)

Use a [calculadora Azure](https://azure.microsoft.com/pricing/calculator) e preencha:

| Serviço | Volume | Preço unit. (S0) | Total mensal |
|---------|--------|-----------------|--------------|
| Language (sentiment + entities) | 400M chars | ~$2/1M chars | US$ 800,00 |
| Speech batch (PT-BR) | 50.000h | ~$1/h | US$ 50.000,00 |
| Vision Read + Tags | 500.000 chamadas | ~$1.50/1k | US$ 750,00 |
| **Total** | | | US$ 51.550,00/mês |

**Análise:**

****a)** Qual serviço pesa mais no orçamento mensal?**
- O Azure AI Speech representa o maior custo, com aproximadamente US$ 50.000 mensais, correspondendo a cerca de 97% do orçamento total estimado.
- O principal motivo é o elevado volume de 50 mil horas de atendimento transcritas mensalmente.

**b) Se substituir Sentiment pela Azure OpenAI (GPT-4o-mini @ ~$0.15/1M input + $0.60/1M output), quanto custaria? (Considere ~50 input tokens + 10 output tokens por review)**


**Tokens de Entrada**
```
2.000.000 reviews × 50 tokens
= 100.000.000 tokens de entrada

100 milhões ÷ 1 milhão × US$ 0,15
= US$ 15
```

**Tokens de Saída**
```
2.000.000 reviews × 10 tokens
= 20.000.000 tokens de saída

20 milhões ÷ 1 milhão × US$ 0,60
= US$ 12
```

**Total Estimado**
```
US$ 15 + US$ 12
= US$ 27 por mês
```

Portanto, considerando estritamente as premissas do exercício, a análise de sentimento com GPT-4o-mini custaria aproximadamente US$ 27 mensais.


**c) Em que cenário vale a pena trocar API pronta por LLM mesmo sendo mais caro?**
A troca pode ser justificada quando a aplicação precisar:
- interpretar contexto complexo ou ambiguidades;
- produzir explicações em linguagem natural;
- combinar sentimento, intenção, causa e recomendação;
- gerar uma saída estruturada própria do negócio;
- analisar relações entre várias reviews;
- realizar uma tarefa ainda não coberta por uma API especializada.

Para classificação simples de sentimento em alto volume, uma API pronta continua sendo arquiteturalmente mais previsível. Para produzir uma análise como principais reclamações, impactos e ações recomendadas, o LLM agrega mais valor.


### Exercício 1.3 — Segurança: como sua Function autentica no AI Services?
Marque a estratégia recomendada para produção e justifique:

| Estratégia | Recomendado? | Razão |
|-----------|--------------|-------|
| API Key hardcoded em `function_app.py` | Não | A chave pode ser exposta em commits, logs, branches, forks ou ferramentas de análise de código. Também dificulta a rotação do segredo. |
| API Key como Application Setting da Function | Não | É melhor que colocar a chave no código, mas ela continua sendo um segredo persistente e pode ser visualizada por usuários com acesso à configuração da Function. |
| API Key no Key Vault, lida pela Function via MI no Vault | Aceitável | Elimina o segredo do código e centraliza sua proteção e rotação. Porém, a aplicação ainda precisa recuperar e utilizar uma chave de API. |
| Token AAD via Managed Identity diretamente no AI Services | Sim | É o padrão recomendado para produção. A Function obtém um token temporário do Microsoft Entra ID, sem armazenar ou manipular uma API Key. |

**Pergunta extra:** Para o último caso (MI direta), quais são os 2 pré-requisitos no recurso AI Services para que funcione? (Dica: subdomínio + role)
- Para utilizar Managed Identity diretamente no Azure AI Services, o recurso deve possuir um subdomínio personalizado habilitado e a identidade gerenciada da Azure Function deve receber a role Cognitive Services User. Dessa forma, a aplicação obtém tokens temporários do Microsoft Entra ID, eliminando a necessidade de armazenar ou recuperar chaves de API.



### Exercício 1.4 — Vision capabilities map

| Cenário | Capacidade | Justificativa |
|---|---|---|
| Auto-categorizar produto novo enviado pelo vendedor | Tags | Identifica conceitos genéricos presentes na imagem, como móvel, cadeira, eletrônico ou alimento, permitindo uma categorização inicial do produto. |
| Encontrar produtos visualmente similares ao da busca | Image Embedding | Converte a imagem em vetor para comparação por similaridade com as imagens do catálogo no Azure AI Search. |
| Detectar quantos produtos estão na prateleira de uma loja física | Object Detection | Localiza cada produto por meio de bounding boxes, permitindo identificar e contar os objetos detectados. |
| Extrair preço da etiqueta de um produto fotografado | OCR/Read | Extrai caracteres e valores monetários presentes na etiqueta. |
| Gerar texto alternativo para acessibilidade | Caption | Produz uma descrição textual da imagem que pode ser utilizada como alt-text. |
| Identificar se a foto tem uma ou mais pessoas | Object Detection | Localiza as ocorrências da classe pessoa e permite contar ou encaminhar a imagem para anonimização. |
| Classificar entre os 12 modelos próprios da linha QC Premium | Custom Vision | Aprende as classes visuais específicas da Quantum Commerce a partir de imagens rotuladas. |

---
## 🟡 Nível 2 — Intermediário: Pipeline e Decisões

### Exercício 2.1 — Pipeline robusto de reviews QC
- [Código Atualizado](./scripts/function_app.py)
- [Reviews](./jsons/reviews-processadas.json)

---

### Exercício 2.2 — Casos de uso de Speech na QC

#### Caso 1: Transcrição pós-atendimento
- **Qual o problema de negócio:** A Quantum Commerce possui milhares de horas de atendimento que hoje são avaliadas apenas por amostragem. Isso dificulta identificar reclamações recorrentes, falhas de processo e atendimentos que exigem acompanhamento.
- **STT ou TTS? Real-time ou batch?**
  - Speech-to-Text. Processamento Batch.

- **Arquitetura proposta:**
```
Plataforma de atendimento
        ↓
Azure Blob Storage
        ↓
Event Grid / Queue
        ↓
Azure Function
        ↓
Azure Speech Batch
        ↓
Language: PII + sentimento + entidades
        ↓
MongoDB / Cosmos DB
        ↓
Dashboard de qualidade
```

- **Estimativa de volume mensal + custo:**
```
Premissas:
10.000 horas de atendimento/mês
US$ 1 por hora

Cáculo: 10.000 × US$ 1 = US$ 10.000/mês
```

- **Riscos:**
  - ruído e sobreposição de falantes;
  - variação de sotaques em português;
  - exposição de dados pessoais;
  - retenção desnecessária dos áudios;
  - erros em nomes de produtos ou termos próprios da QC.
- **Métricas de sucesso:**
  - Word Error Rate inferior a 15% no conjunto de validação;
  - 95% dos áudios processados em até 30 minutos;
  - percentual de chamadas avaliadas automaticamente;
  - redução de reclamações recorrentes;
  - evolução de NPS e First Contact Resolution.


#### Caso 2: Busca de produtos por voz
- **Qual o problema de negócio:** Clientes em dispositivos móveis podem ter dificuldade para digitar descrições completas, nomes de produtos ou características específicas.
- **STT ou TTS? Real-time ou batch?**
  - Speech-to-Text. Processamento em tempo real.

- **Arquitetura proposta:**
```
App ou site Angular
        ↓
Captura de áudio
        ↓
API Management
        ↓
Azure Function
        ↓
Azure Speech real-time
        ↓
Texto da consulta
        ↓
Azure AI Search
        ↓
Produtos encontrados
```

- **Estimativa de volume mensal + custo:**
```
Premissas:
200.000 buscas por mês
8 segundos por busca
US$ 1 por hora de áudio

Cáculo:
200.000 × 8 segundos = 1.600.000 segundos

1.600.000 ÷ 3.600 = 444,44 horas

444,44 × US$ 1 = US$ 444,44/mês
```

- **Riscos:**
  - latência percebida pelo cliente;
  - reconhecimento incorreto de marcas e SKUs;
  - áudio capturado em ambientes ruidosos;
  - envio involuntário de informações pessoais;
  - baixa precisão para termos próprios do catálogo.
- **Métricas de sucesso:**
  - latência p95 inferior a 1,5 segundo;
  - Word Error Rate para termos do catálogo;
  - taxa de buscas sem resultado;
  - taxa de clique após busca por voz;
  - conversão de busca por voz versus busca digitada.



#### Caso 3: Áudio das descrições para acessibilidade
- **Qual o problema de negócio:** Clientes com deficiência visual ou dificuldade de leitura precisam acessar descrições, especificações e orientações dos produtos.
- **STT ou TTS? Real-time ou batch?**
  - Text-to-Speech. Geração batch, com cache do áudio no Blob Storage.

- **Arquitetura proposta:**
```
Cadastro ou alteração de produto
        ↓
Evento de catálogo
        ↓
Azure Function
        ↓
Azure Speech TTS
        ↓
Arquivo MP3/WAV
        ↓
Blob Storage + CDN
        ↓
Player acessível no site/app
```

- **Estimativa de volume mensal + custo:**
```
Premissas:
100.000 descrições geradas por mês
400 caracteres por descrição
40 milhões de caracteres
US$ 16 por 1 milhão de caracteres

Cáculo:
100.000 × 400 = 40.000.000 de caracteres

40 × US$ 16 = US$ 640/mês
```

- **Riscos:**
  - pronúncia incorreta de marcas;
  - custo elevado caso o áudio seja recriado a cada acesso;
  - voz pouco natural em textos técnicos;
  - falta de sincronização após alteração do produto;
  - inadequação de pausas, números e unidades.
- **Métricas de sucesso:**
  - quantidade de usuários que ativam o recurso;
  - percentual de áudios reutilizados pelo cache;
  - avaliações de naturalidade da voz;
  - redução de abandono em páginas acessíveis;
  - conformidade com testes de acessibilidade.

---

### Exercício 2.3 — Quando treinar modelo próprio?

A Quantum Commerce está decidindo entre Vision pronto vs Custom Vision para classificar imagens de produtos.

**Dados:**

- 5M de SKUs, organizados em 150 categorias específicas da QC (ex: "sofá-3-lugares-modular", "tapete-shaggy-redondo")
- 90% das imagens são em fundo branco padronizado
- Para cada categoria existem ~30-50 imagens rotuladas internamente
- Volume de classificação: 50k imagens/mês

**Sua tarefa:**

a) Calcule o custo mensal das 2 abordagens:
   - **Vision pronto + LLM para mapear tags genéricas → categoria QC:** Vision $0.0015 × 50k + GPT-4o-mini $X
   - **Custom Vision treinado:** treino inicial + storage + predição

---

- **Vision pronto + LLM para mapear tags genéricas**
```
Azure Vision
50.000 imagens × US$ 0,0015 = US$ 75/mês


GPT-4o-mini
Entrada:
50.000 × 1.000 = 50.000.000 tokens
50 × US$ 0,15 = US$ 7,50

Saída:
50.000 × 10 = 500.000 tokens
0,5 × US$ 0,60 = US$ 0,30


Total: US$ 82,80/mês
```


- **Custom Vision**
```
Quantidade de imagens armazenadas:
150 categorias × 40 imagens = 6.000 imagens

Predições:
50.000 ÷ 1.000 × US$ 2 = US$ 100/mês

Armazenamento:
6.000 ÷ 1.000 × US$ 0,70 = US$ 4,20/mês


Treinamento inicial:
1 hora × US$ 10 = US$ 10


Total inicial: US$ 114,20

Obs: Retrainings futuros acrescentam novamente o custo de treinamento.
```

---

b) Compare em termos de **qualidade esperada** — qual cobre melhor o vocabulário específico?

- **Vision pronto + LLM**
  - **Vantagens**
    - não exige treinamento inicial;
    - permite incluir categorias novas rapidamente;
    - possui maior flexibilidade para interpretar combinações de tags;
    - funciona bem como MVP ou fallback.
  - **Limitações**
    - as tags do Vision são genéricas;
    - o LLM não consegue recuperar detalhes visuais que não foram detectados;
    - categorias parecidas podem receber as mesmas tags;
    - a saída pode variar para a mesma entrada;
    - a classificação depende da qualidade do prompt.
- **Custom Vision**
  - **Vantagens**
    - aprende diretamente as 150 categorias da QC;
    - tende a distinguir melhor características próprias do catálogo;
    - oferece uma saída mais previsível;
    - o fundo branco padronizado reduz variações visuais irrelevantes.
  - **Limitações**
    - categorias visualmente semelhantes podem gerar confusão;
    - 30 a 50 imagens por categoria podem ser insuficientes para alguns casos;
    - exige avaliação de precision, recall e matriz de confusão;
    - sofre com mudanças de iluminação, ângulo ou padrão fotográfico.


- **Conclusão de qualidade**
  - O Custom Vision possui maior potencial de qualidade para o vocabulário específico, desde que os dados representem adequadamente as variações de cada categoria. O Vision pronto com LLM possui maior flexibilidade, mas depende de informações genéricas que podem não conter os atributos necessários para separar classes próximas.


c) Compare em **manutenção:** como cada um se comporta quando a QC adiciona 20 novas categorias por trimestre?

- **Vision pronto + LLM**
  - A inclusão pode ocorrer por alteração da taxonomia ou do prompt, sem novo treinamento. Entretanto:
    - o prompt fica progressivamente maior;
    - o custo de tokens pode crescer;
    - categorias semelhantes aumentam a ambiguidade;
    - é necessário manter testes de regressão de prompts;
    - a saída continua não determinística.
- **Custom Vision**
  - Para 20 categorias novas, seriam necessárias aproximadamente:
```
20 categorias × 30 a 50 imagens = 600 a 1.000 novas imagens
```
  - Depois seria necessário:
    - rotular as imagens;
    - incluir as novas classes;
    - treinar uma nova versão;
    - avaliar precision, recall e confusões;
    - publicar o novo modelo;
    - monitorar regressões nas classes antigas.

- O esforço de manutenção é maior, porém o modelo permanece diretamente alinhado à taxonomia da empresa.


d) Faça uma **recomendação justificada** considerando custo + qualidade + manutenção. Se possível, proponha uma arquitetura **híbrida** (ex: Custom para os 20 top vendedores + Pronto para o resto).

```
Imagem do produto
        ↓
Custom Vision
        ↓
Confiança ≥ 0,80?
        ├── Sim → aceitar categoria
        │
        └── Não
             ↓
        Vision pronto
             ↓
        Tags genéricas
             ↓
        GPT-4o-mini
             ↓
        Categoria candidata
             ↓
        Confiança suficiente?
             ├── Sim → aceitar
             └── Não → revisão humana
```

**Distribuição proposta**
- **Custom Vision:** categorias estáveis, estratégicas e de maior volume;
- **Vision + LLM:** categorias novas, cauda longa e fallback;
- **Revisão humana:** casos de baixa confiança ou divergência;
- **Active learning:** imagens corrigidas são adicionadas ao próximo treinamento.

**Justificativa final**
Embora o Vision pronto com LLM seja mais barato na estimativa inicial, o custo não deve ser o único critério. O Custom Vision tende a cobrir melhor a taxonomia própria da QC, enquanto o pipeline com LLM reduz o esforço para categorias novas. A combinação permite equilibrar qualidade, manutenção e velocidade de evolução.

---

## Reflexão coletiva
O grupo concluiu que APIs prontas, modelos customizados e LLMs atendem a necessidades diferentes. Serviços prontos são mais adequados para tarefas genéricas e bem definidas, modelos customizados para domínios específicos da Quantum Commerce, e LLMs para atividades abertas, interpretativas ou generativas.

No MVP, as APIs prontas aceleram a implementação e reduzem a complexidade. Com a evolução da solução e o aumento de dados rotulados, modelos customizados podem melhorar a precisão em categorias estratégicas. Os LLMs devem ser usados quando a flexibilidade justificar maior custo, latência e necessidade de governança.

O pipeline de reviews também evidenciou a importância da segurança e da ordem de processamento. A detecção de PII antes das demais análises reduz a exposição de dados pessoais, enquanto Managed Identity evita chaves no código. Assim, a abordagem mais adequada para a Quantum Commerce é híbrida, equilibrando qualidade, custo, manutenção e escalabilidade.


---

## Artefatos do ZIP

* Documento principal: `entrega-grupo-02-aula04.md`
* 3 Reviews em JSON: `jsons/reviews-processadas.json`
* Scripts Python usados nos exercícios avançados:
  * `scripts/function_app.py`
