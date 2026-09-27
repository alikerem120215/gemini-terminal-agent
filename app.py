import os
import sys
import subprocess
import json
import traceback
from flask import Flask, request, jsonify, render_template_string, g
import google.generativeai as genai

# Flask uygulamasını başlat
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Varsayılan Çalışma Dizini (Süreç başladığı dizin)
DEFAULT_CWD = os.getcwd()

def run_terminal_command(command: str) -> str:
    """Terminal üzerinde shell komutu çalıştırır. Proje dizininde veya seçilen hedef dizinde yürütülür.
    
    Args:
        command: Çalıştırılacak terminal komutu (örn: 'ls -la', 'python3 -v')
        
    Returns:
        JSON formatında komutun çıktısı (stdout, stderr, returncode)
    """
    # Aktif istek dizinini (g.cwd) veya varsayılan çalışma dizinini kullan
    cwd = DEFAULT_CWD
    if hasattr(g, 'cwd') and g.cwd:
        cwd = g.cwd
        
    try:
        # Komutu çalıştır
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=45,
            cwd=cwd
        )
        
        output = {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "status": "success",
            "cwd": cwd
        }
    except subprocess.TimeoutExpired:
        output = {
            "command": command,
            "stdout": "",
            "stderr": "HATA: Komut 45 saniye zaman aşımına uğradı.",
            "returncode": -1,
            "status": "timeout",
            "cwd": cwd
        }
    except Exception as e:
        output = {
            "command": command,
            "stdout": "",
            "stderr": f"HATA: {str(e)}",
            "returncode": -1,
            "status": "error",
            "cwd": cwd
        }
        
    # İstek bazlı log listemize (g.command_logs) ekleyelim
    if not hasattr(g, 'command_logs'):
        g.command_logs = []
    g.command_logs.append(output)
    
    return json.dumps(output)

# HTML ve CSS şablonu (Tek Python dosyası içinde gömülü olacak şekilde)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 2.5 Flash Terminal Ajanı</title>
    
    <!-- Google Fonts: Outfit (Arayüz) & Fira Code (Kod / Terminal) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- FontAwesome İkon Seti -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Markdown Parser: marked.js -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <style>
        /* CSS Reset & Genel Ayarlar */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        :root {
            --bg-primary: #080612;
            --bg-secondary: #0e0a22;
            --accent-primary: #8b5cf6; /* Canlı Mor */
            --accent-secondary: #c084fc; /* Açık Mor */
            --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6, #d946ef);
            --glass-bg: rgba(17, 12, 34, 0.55);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --terminal-bg: #05040a;
            --color-success: #10b981;
            --color-error: #ef4444;
            --color-warn: #f59e0b;
            --color-info: #06b6d4;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(217, 70, 239, 0.12) 0%, transparent 40%);
            background-attachment: fixed;
        }

        /* Üst Header Alanı */
        header {
            background: rgba(8, 6, 18, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--glass-border);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }

        .header-title-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            background: var(--accent-gradient);
            width: 42px;
            height: 42px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.3rem;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
            animation: pulse-glow 3s infinite;
        }

        h1 {
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(to right, #ffffff, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--color-success);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--color-success);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--color-success);
        }

        .status-dot.thinking {
            background-color: var(--color-info);
            box-shadow: 0 0 8px var(--color-info);
            animation: pulse-thinking 1.2s infinite;
        }

        /* Ayarlar & Konfigürasyon Çubuğu */
        .config-panel {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .input-group {
            position: relative;
            display: flex;
            align-items: center;
        }

        .input-group i {
            position: absolute;
            left: 12px;
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .config-input {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            padding: 8px 12px 8px 35px;
            border-radius: 10px;
            font-size: 0.85rem;
            outline: none;
            width: 260px;
            transition: all 0.3s ease;
        }

        .config-input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.2);
            background: rgba(255, 255, 255, 0.08);
        }

        .config-input-dir {
            width: 320px;
        }

        .toggle-key-btn {
            position: absolute;
            right: 10px;
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            outline: none;
        }

        .toggle-key-btn:hover {
            color: var(--text-main);
        }

        /* Ana İçerik Bölümü */
        main {
            flex: 1;
            display: flex;
            overflow: hidden;
            padding: 20px;
            gap: 20px;
        }

        /* Sol Panel - Sohbet Ekranı */
        .chat-container {
            flex: 1.1;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        .panel-header {
            padding: 15px 20px;
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.02);
        }

        .panel-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .panel-title i {
            color: var(--accent-primary);
        }

        .clear-chat-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: color 0.2s ease;
        }

        .clear-chat-btn:hover {
            color: var(--color-error);
        }

        .messages-list {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            scroll-behavior: smooth;
        }

        /* Mesaj Baloncukları */
        .message {
            max-width: 85%;
            display: flex;
            flex-direction: column;
            gap: 6px;
            animation: fadeInUp 0.3s ease forwards;
        }

        .message.user {
            align-self: flex-end;
        }

        .message.agent {
            align-self: flex-start;
        }

        .message-sender {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-left: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .message.user .message-sender {
            align-self: flex-end;
            margin-left: 0;
            margin-right: 12px;
        }

        .message-bubble {
            padding: 14px 18px;
            border-radius: 18px;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .message.user .message-bubble {
            background: var(--accent-gradient);
            color: white;
            border-bottom-right-radius: 4px;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2);
        }

        .message.agent .message-bubble {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            border-bottom-left-radius: 4px;
        }

        /* Markdown Stilleri (Ajan Cevapları İçin) */
        .message-bubble h1, .message-bubble h2, .message-bubble h3 {
            margin: 10px 0 6px 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: white;
        }
        .message-bubble p {
            margin-bottom: 8px;
        }
        .message-bubble p:last-child {
            margin-bottom: 0;
        }
        .message-bubble ul, .message-bubble ol {
            margin-left: 20px;
            margin-bottom: 8px;
        }
        .message-bubble li {
            margin-bottom: 4px;
        }
        .message-bubble code {
            font-family: 'Fira Code', monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--accent-secondary);
        }
        .message-bubble pre {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }
        .message-bubble pre code {
            background: none;
            padding: 0;
            font-size: 0.85rem;
            color: #e5e7eb;
        }

        /* Ajan Sohbet İçi Terminal Logları */
        .tool-log-container {
            margin-top: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.2);
        }

        .tool-log-header {
            background: rgba(255, 255, 255, 0.03);
            padding: 8px 12px;
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
            transition: background 0.2s ease;
        }

        .tool-log-header:hover {
            background: rgba(255, 255, 255, 0.06);
        }

        .tool-log-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: 'Fira Code', monospace;
            color: var(--color-info);
        }

        .tool-log-title.success {
            color: var(--color-success);
        }

        .tool-log-title.error {
            color: var(--color-error);
        }

        .tool-log-body {
            padding: 12px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            background: #040308;
            border-top: 1px solid rgba(255, 255, 255, 0.03);
            display: none; /* Varsayılan kapalı */
        }

        .tool-log-body.open {
            display: block;
        }

        .tool-command {
            color: var(--color-warn);
            margin-bottom: 8px;
            word-break: break-all;
        }

        .tool-output {
            color: #d1d5db;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 250px;
            overflow-y: auto;
        }

        /* Hızlı Şablonlar / Öneri Soruları */
        .suggestions-container {
            display: flex;
            gap: 10px;
            padding: 10px 20px;
            overflow-x: auto;
            background: rgba(0, 0, 0, 0.1);
            border-top: 1px solid var(--glass-border);
            scrollbar-width: none;
        }

        .suggestions-container::-webkit-scrollbar {
            display: none;
        }

        .suggestion-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 0.8rem;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
        }

        .suggestion-chip:hover {
            background: rgba(139, 92, 246, 0.1);
            border-color: var(--accent-primary);
            color: white;
            transform: translateY(-1px);
        }

        /* Sohbet Giriş Alanı */
        .chat-input-container {
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.01);
            border-top: 1px solid var(--glass-border);
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .chat-input-wrapper {
            flex: 1;
            position: relative;
            display: flex;
            align-items: center;
        }

        .chat-input {
            width: 100%;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 0.9rem;
            outline: none;
            transition: all 0.3s ease;
        }

        .chat-input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.15);
            background: rgba(255, 255, 255, 0.06);
        }

        .send-btn {
            background: var(--accent-gradient);
            border: none;
            color: white;
            width: 44px;
            height: 44px;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            transition: all 0.2s ease;
        }

        .send-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(139, 92, 246, 0.4);
        }

        .send-btn:active {
            transform: translateY(0);
        }

        .send-btn:disabled {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-muted);
            box-shadow: none;
            cursor: not-allowed;
            transform: none;
        }

        /* Sağ Panel - Terminal Simülatörü */
        .terminal-container {
            flex: 0.9;
            background: var(--terminal-bg);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5);
            position: relative;
        }

        .terminal-header {
            background: #110e1a;
            padding: 12px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .terminal-actions {
            display: flex;
            gap: 8px;
        }

        .terminal-action-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .dot-close { background-color: #ff5f56; }
        .dot-minimize { background-color: #ffbd2e; }
        .dot-maximize { background-color: #27c93f; }

        .terminal-title {
            font-family: 'Fira Code', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .terminal-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            line-height: 1.6;
            color: #e5e7eb;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .terminal-log-entry {
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.2s ease forwards;
        }

        .terminal-prompt-line {
            display: flex;
            gap: 8px;
            align-items: flex-start;
        }

        .terminal-user {
            color: var(--accent-secondary);
            font-weight: 600;
        }

        .terminal-cmd {
            color: white;
            font-weight: 500;
            word-break: break-all;
        }

        .terminal-res {
            margin-top: 6px;
            white-space: pre-wrap;
            word-break: break-all;
            padding-left: 15px;
            border-left: 2px solid rgba(255, 255, 255, 0.1);
        }

        .terminal-res.success {
            color: #a7f3d0;
        }

        .terminal-res.error {
            color: #fca5a5;
        }

        .terminal-input-simulator {
            display: flex;
            gap: 8px;
            align-items: center;
            color: var(--accent-secondary);
            margin-top: auto;
        }

        .cursor {
            display: inline-block;
            width: 8px;
            height: 15px;
            background-color: var(--accent-secondary);
            animation: blink 1s step-end infinite;
            vertical-align: middle;
        }

        /* Sistem Yönergeleri Düzenleme Çekmecesi */
        .system-instruction-toggle {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: color 0.2s ease;
        }

        .system-instruction-toggle:hover {
            color: var(--accent-primary);
        }

        .instruction-drawer {
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--glass-border);
            padding: 15px 20px;
            display: none;
            flex-direction: column;
            gap: 10px;
            animation: slideDown 0.3s ease forwards;
        }

        .instruction-drawer.open {
            display: flex;
        }

        .instruction-textarea {
            width: 100%;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            color: var(--text-main);
            padding: 10px;
            font-size: 0.8rem;
            line-height: 1.4;
            height: 80px;
            resize: none;
            outline: none;
        }

        .instruction-textarea:focus {
            border-color: var(--accent-primary);
        }

        /* Animasyonlar */
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 15px rgba(139, 92, 246, 0.4); }
            50% { box-shadow: 0 0 25px rgba(139, 92, 246, 0.7); }
        }

        @keyframes pulse-thinking {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.6; }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes blink {
            from, to { background-color: transparent }
            50% { background-color: var(--accent-secondary) }
        }

        /* Scrollbar Tasarımı */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.1);
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>

    <!-- Üst Header -->
    <header>
        <div class="header-title-container">
            <div class="logo-icon">
                <i class="fa-solid fa-terminal"></i>
            </div>
            <div>
                <h1>Gemini Terminal Ajanı</h1>
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">Gemini 2.5 Flash / 2.0 Flash Entegrasyonu</div>
            </div>
        </div>

        <!-- Ajan Durum Badge'i -->
        <div class="status-badge">
            <div id="status-dot" class="status-dot"></div>
            <span id="status-text">Ajan Çevrimiçi</span>
        </div>

        <!-- Konfigürasyon Ayarları -->
        <div class="config-panel">
            <div class="input-group">
                <i class="fa-solid fa-key"></i>
                <input type="password" id="api-key-input" class="config-input" placeholder="Gemini API Anahtarı Girin...">
                <button class="toggle-key-btn" id="toggle-key-visibility">
                    <i class="fa-regular fa-eye"></i>
                </button>
            </div>
            
            <div class="input-group">
                <i class="fa-solid fa-folder-open"></i>
                <input type="text" id="cwd-input" class="config-input config-input-dir" placeholder="Çalışma Dizini...">
            </div>
        </div>
    </header>

    <!-- Ana Çalışma Alanı -->
    <main>
        <!-- Sol Panel: Sohbet Paneli -->
        <div class="chat-container">
            <div class="panel-header">
                <div class="panel-title">
                    <i class="fa-regular fa-comment-dots"></i> Sohbet Arayüzü
                </div>
                <div style="display: flex; gap: 15px; align-items: center;">
                    <button class="system-instruction-toggle" id="instruction-toggle-btn">
                        <i class="fa-solid fa-sliders"></i> Sistem Talimatları
                    </button>
                    <button class="clear-chat-btn" id="clear-chat-btn">
                        <i class="fa-regular fa-trash-can"></i> Sohbeti Temizle
                    </button>
                </div>
            </div>

            <!-- Sistem Talimatları Drawer -->
            <div class="instruction-drawer" id="instruction-drawer">
                <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted);">Sistem Talimatı (System Instruction):</div>
                <textarea id="system-instruction-textarea" class="instruction-textarea">Sen yetenekli ve son derece yardımcı bir terminal asistanısın. Kullanıcının bilgisayarı üzerinde terminal komutları çalıştırarak ona kod yazımında, test yapmada, paket yüklemede, dosya oluşturma ve yönetmede yardımcı olursun.
İşlemleri yaparken önce analiz et, ardından uygun komutu çalıştır. Komutların çıktılarına göre sonraki adımını belirle.</textarea>
            </div>

            <!-- Mesaj Listesi -->
            <div class="messages-list" id="messages-list">
                <!-- Karşılama Mesajı -->
                <div class="message agent">
                    <div class="message-sender">
                        <i class="fa-solid fa-robot"></i> Gemini Ajanı
                    </div>
                    <div class="message-bubble">
                        Merhaba! Ben <b>Gemini 2.5 Flash</b> tabanlı terminal asistanınızım. 
                        Arayüzün sağ tarafında canlı bir terminal konsolu görebilirsiniz. Bana sunucuda/bilgisayarınızda çalıştırmak istediğiniz herhangi bir şeyi yazabilirsiniz. 
                        Örneğin: <i>"Mevcut klasördeki dosyaları listele"</i> ya da <i>"Bana rastgele sayı üreten bir python dosyası yarat ve çalıştır."</i>
                        <br><br>
                        Geliştirmeyi başlatmak için lütfen yukarıya <b>Gemini API Anahtarınızı</b> girin. (Anahtarınız yerel tarayıcınızda LocalStorage üzerinde güvenle saklanır).
                    </div>
                </div>
            </div>

            <!-- Önerilen Şablonlar -->
            <div class="suggestions-container">
                <div class="suggestion-chip" data-prompt="Mevcut klasördeki dosyaları ve dizin yapısını listeler misin?">📂 Dizin Listele</div>
                <div class="suggestion-chip" data-prompt="Python versiyonunu kontrol et ve kurulu pip paketlerini listele.">🐍 Python Durumu</div>
                <div class="suggestion-chip" data-prompt="Mevcut çalışma dizininde 'hello.py' adında bir dosya oluştur, içine basit bir ekrana yazdırma kodu ekle ve çalıştır.">📝 Hello.py Yarat ve Çalıştır</div>
                <div class="suggestion-chip" data-prompt="Sistem donanım bilgilerini, işletim sistemini ve disk durumunu raporla.">⚙️ Sistem Durumu</div>
            </div>

            <!-- Sohbet Girişi -->
            <div class="chat-input-container">
                <div class="chat-input-wrapper">
                    <input type="text" id="chat-input-field" class="chat-input" placeholder="Ajana bir talimat yazın (Örn: 'Uygulamayı build et ve testleri çalıştır')...">
                </div>
                <button class="send-btn" id="send-btn">
                    <i class="fa-regular fa-paper-plane"></i>
                </button>
            </div>
        </div>

        <!-- Sağ Panel: Terminal Simülatörü -->
        <div class="terminal-container">
            <div class="terminal-header">
                <div class="terminal-actions">
                    <div class="terminal-action-dot dot-close"></div>
                    <div class="terminal-action-dot dot-minimize"></div>
                    <div class="terminal-action-dot dot-maximize"></div>
                </div>
                <div class="terminal-title">
                    <i class="fa-solid fa-terminal"></i> gemini-terminal-agent - console
                </div>
                <div>
                    <button class="clear-chat-btn" id="clear-terminal-btn" style="font-size: 0.75rem;">
                        <i class="fa-solid fa-eraser"></i> Temizle
                    </button>
                </div>
            </div>

            <!-- Terminal İçeriği -->
            <div class="terminal-content" id="terminal-content">
                <div class="terminal-log-entry">
                    <div class="terminal-prompt-line">
                        <span class="terminal-user">agent@local:~$</span>
                        <span class="terminal-cmd">echo "Terminal Simülatörü Hazır. Ajanın komutları burada canlı akacak..."</span>
                    </div>
                    <div class="terminal-res success">Terminal Simülatörü Hazır. Ajanın komutları burada canlı akacak...</div>
                </div>
                
                <!-- Terminal Aktif Satırı -->
                <div class="terminal-input-simulator" id="terminal-cursor-line">
                    <span class="terminal-user">agent@local:~$</span>
                    <span class="cursor"></span>
                </div>
            </div>
        </div>
    </main>

    <script>
        // DOM Elementleri
        const apiKeyInput = document.getElementById('api-key-input');
        const toggleKeyVisibility = document.getElementById('toggle-key-visibility');
        const cwdInput = document.getElementById('cwd-input');
        
        const chatInputField = document.getElementById('chat-input-field');
        const sendBtn = document.getElementById('send-btn');
        const messagesList = document.getElementById('messages-list');
        const clearChatBtn = document.getElementById('clear-chat-btn');
        
        const instructionToggleBtn = document.getElementById('instruction-toggle-btn');
        const instructionDrawer = document.getElementById('instruction-drawer');
        const systemInstructionTextarea = document.getElementById('system-instruction-textarea');
        
        const terminalContent = document.getElementById('terminal-content');
        const terminalCursorLine = document.getElementById('terminal-cursor-line');
        const clearTerminalBtn = document.getElementById('clear-terminal-btn');
        
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');

        // Sohbet geçmişini tarayıcıda tutalım
        let chatHistory = [];

        // Sayfa yüklendiğinde LocalStorage'dan ayarları yükle
        window.addEventListener('DOMContentLoaded', () => {
            const savedApiKey = localStorage.getItem('gemini_api_key');
            if (savedApiKey) {
                apiKeyInput.value = savedApiKey;
            }
            
            // Backend'den varsayılan çalışma dizinini çek
            fetch('/api/get-default-cwd')
                .then(res => res.json())
                .then(data => {
                    cwdInput.value = data.cwd;
                })
                .catch(err => console.error("Çalışma dizini çekilemedi:", err));
        });

        // API Key Kaydetme (Yazıldıkça kaydeder)
        apiKeyInput.addEventListener('input', () => {
            localStorage.setItem('gemini_api_key', apiKeyInput.value.trim());
        });

        // API Key Gizle / Göster
        toggleKeyVisibility.addEventListener('click', () => {
            const isPassword = apiKeyInput.type === 'password';
            apiKeyInput.type = isPassword ? 'text' : 'password';
            toggleKeyVisibility.innerHTML = isPassword ? 
                '<i class="fa-regular fa-eye-slash"></i>' : 
                '<i class="fa-regular fa-eye"></i>';
        });

        // Sistem Talimatı Çekmecesini Aç/Kapat
        instructionToggleBtn.addEventListener('click', () => {
            instructionDrawer.classList.toggle('open');
        });

        // Sohbeti Temizle
        clearChatBtn.addEventListener('click', () => {
            if (confirm("Sohbet geçmişini temizlemek istediğinize emin misiniz?")) {
                chatHistory = [];
                // İlk hoşgeldiniz mesajı hariç temizle
                const firstMessage = messagesList.firstElementChild.outerHTML;
                messagesList.innerHTML = firstMessage;
            }
        });

        // Terminali Temizle
        clearTerminalBtn.addEventListener('click', () => {
            terminalContent.innerHTML = '';
            terminalContent.appendChild(terminalCursorLine);
        });

        // Önerilen Şablon Tıklamaları
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                chatInputField.value = chip.getAttribute('data-prompt');
                chatInputField.focus();
            });
        });

        // Sohbet Giriş Alanı Enter ile Tetikleme
        chatInputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !sendBtn.disabled && chatInputField.value.trim() !== '') {
                sendMessage();
            }
        });

        sendBtn.addEventListener('click', () => {
            if (chatInputField.value.trim() !== '') {
                sendMessage();
            }
        });

        // Ajan Durumunu Güncelleme Fonksiyonu
        function updateStatus(state) {
            if (state === 'thinking') {
                statusDot.className = 'status-dot thinking';
                statusText.innerText = 'Ajan Düşünüyor...';
            } else if (state === 'executing') {
                statusDot.className = 'status-dot thinking';
                statusDot.style.backgroundColor = 'var(--color-info)';
                statusDot.style.boxShadow = '0 0 8px var(--color-info)';
                statusText.innerText = 'Komut Çalıştırılıyor...';
            } else {
                statusDot.className = 'status-dot';
                statusDot.style.backgroundColor = 'var(--color-success)';
                statusDot.style.boxShadow = '0 0 8px var(--color-success)';
                statusText.innerText = 'Ajan Çevrimiçi';
            }
        }

        // Sohbet İçinde Tool Logu Açıp Kapatma
        window.toggleToolLog = function(element) {
            const body = element.nextElementSibling;
            const chevron = element.querySelector('.chevron-icon');
            body.classList.toggle('open');
            if (body.classList.contains('open')) {
                chevron.className = 'fa-solid fa-chevron-up chevron-icon';
            } else {
                chevron.className = 'fa-solid fa-chevron-down chevron-icon';
            }
        };

        // Mesaj Gönderme
        async function sendMessage() {
            const prompt = chatInputField.value.trim();
            const apiKey = apiKeyInput.value.trim();

            if (!apiKey) {
                alert("Lütfen önce üst kısımdan Gemini API Anahtarınızı (API Key) girin.");
                apiKeyInput.focus();
                return;
            }

            // Girdi temizliği ve buton kilitleme
            chatInputField.value = '';
            chatInputField.disabled = true;
            sendBtn.disabled = true;
            updateStatus('thinking');

            // Kullanıcı mesajını arayüze ekle
            appendMessage('user', prompt);

            // Terminal Arayüzünde Komut Bekleyen Ajan Efekti
            addTerminalEntry('user_prompt', `user > ${prompt}`);

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: prompt,
                        api_key: apiKey,
                        cwd: cwdInput.value.trim(),
                        system_instruction: systemInstructionTextarea.value.trim(),
                        history: chatHistory
                    })
                });

                const data = await response.json();

                if (data.status === 'error') {
                    // Hata mesajını arayüze ekle
                    appendMessage('agent', `❌ **Bir Hata Oluştu:** ${data.message}`);
                    addTerminalEntry('error', `SYSTEM HATA: ${data.message}`);
                } else {
                    // Çalıştırılan araç/terminal komutları varsa bunları arayüze ekle
                    if (data.command_logs && data.command_logs.length > 0) {
                        data.command_logs.forEach(log => {
                            // Hem sohbet içine hem terminal paneline ekle
                            appendToolExecution(log);
                            addTerminalEntry('command', log.command, log.stdout, log.stderr, log.returncode);
                        });
                    }

                    // Ajanın son cevabını arayüze ekle
                    appendMessage('agent', data.response);

                    // Sohbet geçmişini güncelle
                    chatHistory.push({ role: 'user', text: prompt });
                    chatHistory.push({ role: 'model', text: data.response });
                }
            } catch (err) {
                console.error("İstek hatası:", err);
                appendMessage('agent', `❌ **Sunucu İletişim Hatası:** ${err.message}`);
                addTerminalEntry('error', `SYSTEM HATA: Sunucuya bağlanılamadı.`);
            } finally {
                chatInputField.disabled = false;
                sendBtn.disabled = false;
                chatInputField.focus();
                updateStatus('idle');
            }
        }

        // Sohbet Paneline Düz Mesaj Ekleme
        function appendMessage(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const senderSpan = document.createElement('div');
            senderSpan.className = 'message-sender';
            if (sender === 'user') {
                senderSpan.innerHTML = '<i class="fa-regular fa-user"></i> Siz';
            } else {
                senderSpan.innerHTML = '<i class="fa-solid fa-robot"></i> Gemini Ajanı';
            }

            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            
            // Markdown render
            if (sender === 'agent') {
                bubbleDiv.innerHTML = marked.parse(text);
            } else {
                bubbleDiv.innerText = text;
            }

            messageDiv.appendChild(senderSpan);
            messageDiv.appendChild(bubbleDiv);
            messagesList.appendChild(messageDiv);
            
            // Sohbeti en aşağı kaydır
            messagesList.scrollTop = messagesList.scrollHeight;
        }

        // Sohbet Paneline Terminal Çalıştırma Detayı Ekleme
        function appendToolExecution(log) {
            const logDiv = document.createElement('div');
            logDiv.className = 'tool-log-container';
            
            const isSuccess = log.returncode === 0;
            const statusClass = isSuccess ? 'success' : 'error';
            const statusIcon = isSuccess ? 
                '<i class="fa-regular fa-circle-check"></i>' : 
                '<i class="fa-regular fa-circle-xmark"></i>';
                
            logDiv.innerHTML = `
                <div class="tool-log-header" onclick="toggleToolLog(this)">
                    <div class="tool-log-title ${statusClass}">
                        ${statusIcon}
                        <span>Terminal Komutu Yürütüldü</span>
                    </div>
                    <i class="fa-solid fa-chevron-down chevron-icon"></i>
                </div>
                <div class="tool-log-body">
                    <div class="tool-command">$ ${log.command}</div>
                    <div class="tool-output">${log.stdout ? log.stdout : ''}${log.stderr ? '\\n[HATA ÇIKTISI]:\\n' + log.stderr : ''}</div>
                </div>
            `;
            
            messagesList.appendChild(logDiv);
            messagesList.scrollTop = messagesList.scrollHeight;
        }

        // Sağ Terminal Simülatörüne Log Ekleme
        function addTerminalEntry(type, cmdText, stdout = '', stderr = '', returncode = 0) {
            const entryDiv = document.createElement('div');
            entryDiv.className = 'terminal-log-entry';

            if (type === 'user_prompt') {
                entryDiv.innerHTML = `
                    <div class="terminal-prompt-line">
                        <span class="terminal-user">agent@local:~$</span>
                        <span class="terminal-cmd" style="color: var(--text-muted);">${cmdText}</span>
                    </div>
                `;
            } else if (type === 'error') {
                entryDiv.innerHTML = `
                    <div class="terminal-prompt-line">
                        <span class="terminal-user" style="color: var(--color-error)">[SİSTEM HATA]</span>
                    </div>
                    <div class="terminal-res error">${cmdText}</div>
                `;
            } else if (type === 'command') {
                const isSuccess = returncode === 0;
                const statusClass = isSuccess ? 'success' : 'error';
                
                let resHtml = '';
                if (stdout) {
                    resHtml += `<div class="terminal-res success">${stdout}</div>`;
                }
                if (stderr) {
                    resHtml += `<div class="terminal-res error">${stderr}</div>`;
                }
                if (!stdout && !stderr) {
                    resHtml += `<div class="terminal-res success">[Komut başarıyla tamamlandı, çıktı üretilmedi]</div>`;
                }

                entryDiv.innerHTML = `
                    <div class="terminal-prompt-line">
                        <span class="terminal-user">agent@local:~$</span>
                        <span class="terminal-cmd">${cmdText}</span>
                    </div>
                    ${resHtml}
                `;
            }

            // İmleç satırından hemen önceye yerleştir
            terminalContent.insertBefore(entryDiv, terminalCursorLine);
            
            // Terminali en aşağı kaydır
            terminalContent.scrollTop = terminalContent.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Gömülü HTML arayüzünü döndürür."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/get-default-cwd', methods=['GET'])
def get_default_cwd():
    """Varsayılan çalışma dizinini arayüze döner."""
    return jsonify({"cwd": DEFAULT_CWD})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Tarayıcıdan gelen mesajı alır, Gemini modelini ve terminal araçlarını çalıştırır."""
    data = request.get_json() or {}
    
    user_message = data.get('message')
    api_key = data.get('api_key')
    cwd = data.get('cwd') or DEFAULT_CWD
    system_instruction = data.get('system_instruction')
    history = data.get('history') or []
    
    if not user_message:
        return jsonify({"status": "error", "message": "Boş mesaj gönderilemez."}), 400
        
    if not api_key:
        return jsonify({"status": "error", "message": "API anahtarı eksik."}), 400
        
    # Flask global nesnesi g içine, bu istek boyunca geçerli olacak cwd yerleştir
    g.cwd = cwd
    
    try:
        # google-generativeai kütüphanesini API Key ile konfigüre et
        genai.configure(api_key=api_key)
        
        # Sohbet geçmişini yapılandır
        sdk_history = []
        for msg in history:
            role = msg.get('role')
            text = msg.get('text')
            if role and text:
                sdk_history.append({
                    "role": "user" if role == "user" else "model",
                    "parts": [text]
                })
                
        # Ajan modelini tanımla ve mesajı göndermeyi dene.
        # Gemini 2.5 Flash / Gemini 2.0 Flash denemesi yapalım.
        # Eğer bir model adı desteklenmiyorsa (404 / not found hatası), sonraki modele fallback yapalım.
        model_names = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        response = None
        last_error = None
        
        for name in model_names:
            try:
                # Her denemede log listesini sıfırla
                g.command_logs = []
                
                model = genai.GenerativeModel(
                    model_name=name,
                    tools=[run_terminal_command],
                    system_instruction=system_instruction
                )
                
                chat_session = model.start_chat(
                    history=sdk_history, 
                    enable_automatic_function_calling=True
                )
                
                # Mesajı gönder (bu aşamada API bağlantısı kurulur ve model adı doğrulanır)
                response = chat_session.send_message(user_message)
                break  # Başarılı olursa döngüyü kır
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                # Eğer hata model adı kaynaklıysa (404, not found, invalid vb.) sıradaki modele geç
                if any(x in err_str for x in ["not found", "not_found", "404", "invalid"]):
                    continue
                else:
                    # Model adı dışındaki genel hatalarda (örn. geçersiz API Key) doğrudan hata fırlat
                    raise e
                    
        if not response:
            raise Exception(f"Denenen modellerden hiçbiri çalıştırılamadı. Son hata: {str(last_error)}")
            
        # İstek boyunca çalıştırılan komutları g.command_logs'dan al
        command_logs = getattr(g, 'command_logs', [])
        
        return jsonify({
            "status": "success",
            "response": response.text,
            "command_logs": command_logs
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Gemini API veya Sunucu Hatası: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Flask sunucusunu localde 5001 portundan ayağa kaldıralım
    # (Genelde 5000 portu Mac OS AirPlay alıcısı tarafından kullanılabiliyor)
    app.run(host='127.0.0.1', port=5001, debug=True)
