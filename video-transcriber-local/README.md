# Video Transcriber Local

Servidor local de transcrição de vídeo. Recebe um arquivo de vídeo por HTTP, extrai o áudio com **FFmpeg**
e transcreve com **faster-whisper** (modelo Whisper), devolvendo o texto e os trechos com tempo.
Tudo roda no seu computador: o vídeo e a transcrição não saem da máquina.

Foi feito para servir uma extensão de Chrome de estudo (transcrição de aulas em vídeo), mas funciona com
qualquer cliente que consiga fazer um `POST`.

## Como funciona

```
cliente  ──POST /transcribe (vídeo)──▶  servidor (127.0.0.1:8765)
                                          │ 1. grava o vídeo em disco, em pedaços de 1 MB
                                          │ 2. FFmpeg extrai o áudio (WAV, mono, 16 kHz)
                                          │ 3. confere a duração do áudio com a esperada
                                          │ 4. faster-whisper transcreve (CPU, int8, filtro de silêncio)
cliente  ◀──JSON (texto + trechos)──────┘
```

A conferência de duração evita aceitar uma transcrição parcial: se o áudio extraído tiver duração diferente
da informada pelo cliente (tolerância de 2 s ou 1%), a requisição falha.

## Requisitos

- Windows 10/11 (os scripts `.cmd` são para Windows; o `.py` roda em qualquer sistema)
- Python 3.10 a 3.12 (recomendado; versões muito novas podem não ter pacotes compatíveis)
- FFmpeg: o `setup.cmd` baixa sozinho para dentro da pasta (build "essentials" do gyan.dev). Se você já tem FFmpeg no PATH ou uma pasta `ffmpeg*` ao lado do script, ele usa essa

## Instalação e uso

1. Execute `setup.cmd`: cria o ambiente virtual `.venv`, instala as dependências e baixa o FFmpeg para a pasta, se necessário.
2. Execute `start.cmd` e **deixe a janela aberta**. Na primeira vez o modelo Whisper é baixado.
3. Quando aparecer `Transcritor pronto em http://127.0.0.1:8765`, o servidor está no ar.

Sem Windows:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python video-transcriber.py
```

## Configuração (variáveis de ambiente)

| Variável | Padrão | Descrição |
|---|---|---|
| `WHISPER_MODEL` | `small` | `tiny`, `base`, `small`, `medium`, `large-v3`. Maiores são mais precisos e bem mais lentos. |
| `WHISPER_LANGUAGE` | `pt` | Idioma da fala (`en`, `es`...). Vazio detecta automaticamente. |
| `TRANSCRIBER_PORT` | `8765` | Porta do servidor. |

## API

### `GET /health`
Retorna `{"ok": true, "status": "ready"}`.

### `POST /transcribe`
Corpo: o arquivo de vídeo em binário.

- Cabeçalho `Content-Type: application/octet-stream`
- Cabeçalho `X-Expected-Duration`: duração do vídeo em segundos (ativa a conferência de duração)

```bash
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/octet-stream" \
  -H "X-Expected-Duration: 154" \
  --data-binary @aula.mp4
```

Resposta:

```json
{
  "ok": true,
  "text": "texto completo...",
  "segments": [{ "start": 0.0, "end": 4.2, "text": "..." }],
  "audio_duration": 154.1,
  "duration_verified": true
}
```

Em caso de erro: `{"ok": false, "error": "mensagem"}` com status 500.

O formato antigo (JSON com `video_base64`) continua aceito, mas só serve para vídeos pequenos: em vídeos
grandes a string base64 estoura o limite do navegador.

## Problemas comuns

- **`open() got an unexpected keyword argument 'metadata_errors'`**: versão do PyAV (`av`) nova demais para o
  faster-whisper. Rode `.venv\Scripts\python.exe -m pip install "av<17"` (o `requirements.txt` já faz isso).
- **`Não encontrei o FFmpeg`**: rode `setup.cmd` de novo, instale com `winget install Gyan.FFmpeg` ou extraia uma pasta `ffmpeg*` ao lado do script.
- **Erro de conexão no cliente**: confira se a janela do `start.cmd` está aberta e reinicie-a após editar o `.py`.
- **Lento**: o modelo roda na CPU. Use `WHISPER_MODEL=base` para ganhar velocidade, com menos precisão.

## Limitações e segurança

- Transcreve **apenas o áudio**. Textos e números que só aparecem na imagem não entram na transcrição.
- O servidor escuta só em `127.0.0.1`, mas responde com `Access-Control-Allow-Origin: *` para que uma extensão ou
  página possa chamá-lo. Isso significa que qualquer site aberto no seu navegador consegue enviar vídeo para ele.
  Use apenas em máquina pessoal e feche o servidor quando não estiver usando.

## Licença

MIT. Veja [LICENSE](LICENSE).

O FFmpeg não faz parte deste repositório; é baixado separadamente e tem sua própria licença (veja ffmpeg.org/legal.html).
