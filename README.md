# Sentinela

Auditor de variações de criativos (VSLs) para operações de marketing direto.
Verifica se mudanças combinadas em **fala, preço, formato de produto e imagem** foram
realmente aplicadas no vídeo novo — sem precisar assistir a hora inteira.

Quando você roda `/sentinela` no Claude Code, ele te pergunta o que mudou,
analisa **apenas a janela da oferta** (geralmente min 40-60), e te entrega
um relatório do tipo:

```
✅ Preço alterado: "$57" detectado em 47:23
❌ ATENÇÃO: produto continua aparecendo em gotas (frame 48:10)
⚠️  Fala "lose weight fast" não foi alterada conforme briefing
```

---

## Instalação (uma vez só por máquina)

**Requisitos:** Claude Code já instalado. Windows 10/11, macOS 12+ ou Linux.

### 1. Clone o repositório

```bash
git clone https://github.com/bbismaq/Sentinela.git
cd Sentinela
```

### 2. Rode o instalador da sua plataforma

| Sistema | Como instalar (escolha um) |
|---|---|
| **Windows (fácil)** | Duplo-clique em **`Install.bat`** |
| **Windows (terminal)** | `.\install.ps1` no PowerShell |
| **macOS (fácil)** | Duplo-clique em **`install.command`** |
| **macOS / Linux (terminal)** | `chmod +x install.sh && ./install.sh` |

O instalador faz tudo sozinho:
- Instala Python e ffmpeg (via `winget` no Windows ou `brew` no Mac) se faltarem
- Cria um ambiente isolado em `~/.claude/skills/sentinela/.venv`
- Instala `faster-whisper` (transcritor)
- Baixa o modelo `medium` (~1.5GB, uma vez só)
- Copia a skill para `~/.claude/skills/sentinela/`

### 3. Teste

Abra um terminal novo, entre no Claude Code e digite:

```
/sentinela
```

---

## Atualizando depois

Quando o autor publicar melhorias:

```bash
git pull
```

Depois rode o updater da sua plataforma:

| Sistema | Comando |
|---|---|
| Windows | `.\update.ps1` |
| macOS / Linux | `./update.sh` |

O updater não reinstala dependências — só copia os arquivos novos da skill.

---

## Como usar

Dentro do Claude Code, basta digitar:

```
/sentinela
```

A skill vai te guiar com perguntas. Você pode entregar:

| Tipo de input | Quando usar |
|---|---|
| **Vídeo novo + briefing** | Tenho o MP4 e quero validar |
| **Vídeo novo + script marcado com `[]` `<>`** | Já tenho o script que mandei pro editor, com as marcações |
| **Só transcrição em texto + briefing** | Não preciso analisar imagens, só fala/preço |
| **Vídeo antigo + vídeo novo** | Quero comparação A/B direta |

### Formato do script marcado

Quando você manda o script pro editor com marcações, o Sentinela sabe ler:

```
Buy now for just [$67] <$57> and get [2 bottles] <3 bottles>
of our [Weight Loss Drops] <Weight Loss Capsules>.
```

- `[texto]` = **o que devia sair** (versão antiga)
- `<texto>` = **o que devia entrar** (versão nova)

A skill extrai cada par e valida automaticamente no vídeo/texto novo.

---

## Suporte

Problemas no install? Abra uma issue neste repositório.
