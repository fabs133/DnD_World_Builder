# Setting Up Ollama for Full AI

## What is Ollama?

Ollama runs AI models locally on your computer. With Ollama, NPCs can:
- Generate creative tactical decisions
- React dynamically to combat situations
- Have unique voice lines

Without Ollama, the game uses "Smart Bot" mode -- still fun, just more predictable!

## Installation

### Windows

1. Download from [ollama.ai](https://ollama.ai)
2. Run the installer
3. Open Command Prompt and run:
   ```
   ollama pull phi3
   ```
4. Wait for the download (~2GB)

### Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi3
```

## Verify It Works

1. Run `ollama serve` in a terminal (keep it open)
2. Launch D&D World Builder
3. Go to **Settings > AI**
4. Select **Full AI** mode
5. Status should show "Connected"

## Recommended Models

| Your Hardware | Recommended Model | Command |
|---------------|-------------------|---------|
| RTX 3060+ | Mistral 7B | `ollama pull mistral` |
| GTX 1060+ | Phi-3 | `ollama pull phi3` |
| CPU only, 16GB+ RAM | Gemma 2B | `ollama pull gemma:2b` |
| CPU only, 8GB RAM | Use Smart Bot mode | -- |

## Troubleshooting

**"Connection refused"**
Make sure `ollama serve` is running.

**"Model not found"**
Run `ollama pull phi3` first.

**AI is slow (>10 seconds)**
Try a smaller model or use Smart Bot mode.
