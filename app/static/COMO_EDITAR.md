# Guia de Edição: Relatórios em Markdown

Bem-vindo! Este guia explica como editar seu relatório estratégico em formato Markdown e fazer upload de volta para obter o PDF final.

---

## O que é Markdown?

Markdown é um formato de texto simples que pode ser editado em qualquer programa - Bloco de Notas, Word, Google Docs, ou editores especializados como Typora ou Obsidian.

**Vantagens:**
- ✅ Fácil de ler e editar
- ✅ Funciona em qualquer editor de texto
- ✅ Pode ser copiado/colado no ChatGPT para melhorias
- ✅ Converte automaticamente para PDF profissional

---

## Como Editar Seções

### Estrutura Básica

```markdown
# Título Principal (não editar - é o nome da sua empresa)

## Seção Grande (ex: Análise SWOT)

### Subseção (ex: Forças)

- Item de lista 1
- Item de lista 2

**Negrito:** Usado para rótulos e destaques
```

### Editando Texto

**Você pode:**
- ✅ Adicionar ou remover parágrafos
- ✅ Modificar listas (adicionar/remover itens)
- ✅ Mudar o texto dentro das seções
- ✅ Reorganizar seções inteiras (cortar e colar)
- ✅ Deletar seções que não precisa

**Evite:**
- ⚠️ Mudar os `---` no topo do arquivo (metadados importantes)
- ⚠️ Remover completamente o "Sumário Executivo" (necessário para o PDF)

### Exemplo de Edição

**Antes:**
```markdown
### 💪 Forças

- Equipe técnica experiente
- Tecnologia proprietária
```

**Depois (adicionando um item):**
```markdown
### 💪 Forças

- Equipe técnica experiente
- Tecnologia proprietária
- Forte relacionamento com clientes
```

---

## Usando com ChatGPT 🤖

Uma das melhores formas de melhorar seu relatório é usar IA!

### Passo a Passo:

1. **Copie a seção que quer melhorar**
   - Exemplo: Copie todo o "Sumário Executivo"

2. **Cole no ChatGPT com uma instrução**
   ```
   Aqui está o sumário executivo da minha empresa:

   [COLAR TEXTO AQUI]

   Por favor, reescreva isso de forma mais persuasiva e com dados mais específicos.
   Foque em resultados concretos que investidores gostariam de ver.
   ```

3. **Copie a resposta melhorada**

4. **Cole de volta no seu arquivo Markdown**
   - Substitua o texto original pelo novo

### Prompts Úteis:

**Para Sumário Executivo:**
```
Torne este sumário executivo mais convincente e focado em métricas de crescimento.
```

**Para Recomendações:**
```
Transforme estas recomendações em planos de ação específicos com prazos e KPIs.
```

**Para SWOT:**
```
Expanda esta análise SWOT com insights mais profundos sobre o mercado brasileiro.
```

**Para OKRs:**
```
Revise estes OKRs para serem mais mensuráveis e ambiciosos, focados em growth.
```

---

## Editando em Diferentes Programas

### Bloco de Notas / TextEdit
- Mais simples, sem formatação
- Salve como `.md` (não `.txt`)
- Use "Salvar Como" → Tipo: "Todos os arquivos" → Nome: `relatorio.md`

### Microsoft Word
- Abra o arquivo `.md` normalmente
- Edite como texto simples
- **Importante:** Ao salvar, escolha "Salvar Como" → Formato: "Texto Simples (.txt)"
- Depois renomeie de `.txt` para `.md`

### Google Docs
- Não recomendado (adiciona formatação extra)
- Se usar, copie tudo e cole no Bloco de Notas antes de salvar

### Editores Markdown (Recomendado)
- **Typora** (pago, mas excelente): https://typora.io
- **Obsidian** (gratuito): https://obsidian.md
- **VS Code** (gratuito, para técnicos): https://code.visualstudio.com

---

## Formatação Markdown

### Listas

```markdown
- Item simples
- Outro item
  - Sub-item (dois espaços de indentação)
```

### Tabelas

```markdown
| Coluna 1 | Coluna 2 |
|----------|----------|
| Valor A  | Valor B  |
| Valor C  | Valor D  |
```

**Dica:** Use sites como https://tableconvert.com para converter Excel para Markdown!

### Ênfase

```markdown
**Negrito** para destaques importantes
*Itálico* para ênfase leve
```

### Links

```markdown
[Texto do link](https://exemplo.com)
```

---

## Como Fazer Upload de Volta

1. **Salve suas edições** no arquivo `.md`

2. **Acesse o sistema web**

3. **Clique em "Upload Markdown & Get PDF"**

4. **Selecione qual relatório você está atualizando**
   - Lista mostra: "Relatório #123: Nome da Empresa (Setor)"
   - Escolha o correto!

5. **Selecione o arquivo `.md` editado**

6. **Clique em "Upload"**

7. **O sistema vai:**
   - Validar o markdown
   - Salvar suas alterações no banco de dados
   - Gerar o PDF automaticamente
   - Baixar o PDF para seu computador

8. **Pronto!** Você tem seu PDF atualizado.

---

## Solução de Problemas

### "Erro ao fazer parse do markdown"

**Possíveis causas:**
- Metadados no topo (entre `---`) foram alterados ou removidos
- Estrutura de seções quebrada (ex: faltam os `##` nos títulos)

**Solução:**
- Compare com o arquivo original
- Certifique-se de que manteve os cabeçalhos principais:
  - `## Sumário Executivo`
  - `## Análise SWOT`
  - etc.

### "Seção X não foi encontrada"

- Não é erro grave! O sistema continua processando
- Significa que uma seção opcional estava vazia ou foi removida
- O PDF será gerado normalmente sem essa seção

### PDF ficou estranho?

**Verifique:**
- Caracteres especiais (`, ~, {, }) podem quebrar o formato
- Tabelas muito largas (simplifique ou quebre em múltiplas linhas)
- Textos muito longos sem parágrafos (adicione quebras de linha)

### Upload não funciona?

- Certifique-se de que o arquivo termina com `.md`
- Tamanho máximo: 5 MB
- Se colou do Word, pode ter formatação invisível → cole primeiro no Bloco de Notas, depois salve como `.md`

---

## Dicas Profissionais

### 1. Trabalhe em Iterações
- Baixe markdown → Edite → Upload → Veja o PDF
- Repita até ficar perfeito
- Cada upload salva suas mudanças no sistema

### 2. Use IA Estrategicamente
- ChatGPT para reescrever texto
- Claude para análises mais profundas
- Gemini para pesquisas de mercado adicionais

### 3. Adicione Dados Locais
Se você tem dados específicos da sua empresa:
```markdown
### 💪 Forças

- Revenue: R$ 2.4M ARR (crescimento de 180% YoY)
- Customer base: 340 empresas (churn <3%)
- Team: 15 pessoas (70% técnico)
```

### 4. Reorganize para Seu Público
- Para investidores: Foque em métricas de tração e potencial de mercado
- Para board: Foque em riscos e plano de mitigação
- Para equipe: Foque em ações táticas e roadmap

### 5. Versione Seus Arquivos
Salve com nomes diferentes:
- `analise-acme-v1.md` (original)
- `analise-acme-v2-investidores.md` (customizado)
- `analise-acme-v3-final.md` (versão final)

---

## Suporte Técnico

**Problemas ou dúvidas?**

1. Releia este guia (geralmente a resposta está aqui!)
2. Tente fazer upload do arquivo **original** sem edições (para testar se o sistema está funcionando)
3. Se o erro persistir, entre em contato com o suporte técnico

---

## Exemplos de Uso Real

### Caso 1: Melhorando com ChatGPT

**Original:**
```markdown
## Sumário Executivo

Nossa empresa atua no setor de SaaS B2B. Temos um bom produto e clientes satisfeitos.
```

**Prompt usado:**
```
Reescreva este sumário executivo com métricas concretas e posicionamento estratégico:
[texto original]
```

**Resultado (colado de volta):**
```markdown
## Sumário Executivo

Acme Corp é uma plataforma SaaS B2B de automação de vendas que atende 340 empresas
no Brasil, com R$ 2.4M em ARR e crescimento de 180% YoY. Nossa solução reduz o
ciclo de vendas em 60% através de IA preditiva, posicionando-nos como líderes no
segmento de PMEs tecnológicas. Com CAC de R$ 850 e LTV de R$ 12.000, demonstramos
unit economics sólidos e caminho claro para profitabilidade em 18 meses.
```

### Caso 2: Adicionando Seção Personalizada

Você pode adicionar seções próprias:

```markdown
## Análise de Competidores (Adicionado Manualmente)

### Concorrente A
- **Posicionamento:** Enterprise-only, foco em Fortune 500
- **Fraqueza:** Onboarding de 6+ meses, não atende PMEs
- **Nossa vantagem:** Time-to-value de 48h, preço 70% menor

### Concorrente B
- **Posicionamento:** Self-service, DIY
- **Fraqueza:** Requer integração técnica complexa
- **Nossa vantagem:** White-glove implementation, suporte em PT-BR
```

---

**Última atualização:** 2025-01-29

**Versão do guia:** 1.0

---

*Criado por Strategy AI - Seu parceiro em análise estratégica orientada por IA*
