# NotebookLM MCP Server

[![Python 3.12.8](https://img.shields.io/badge/python-3.12.8-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🔗 **Google NotebookLM을 AI 코딩 어시스턴트에 연결하세요**  
> 🔗 **Connect Google NotebookLM to your AI coding assistant**

---

## 🇰🇷 한국어 가이드 | 🇺🇸 [English Guide](#-english-guide)

---

# 🇰🇷 한국어 가이드

## NotebookLM MCP란?

[Google NotebookLM](https://notebooklm.google.com/)의 RAG 기능을 AI 코딩 어시스턴트 (Antigravity, Claude, Cursor 등)에서 사용할 수 있게 해주는 MCP 서버입니다.

**할 수 있는 것들:**
- 📚 노트북에 문서 추가하고 질문하기
- 🎙️ 오디오 개요, 퀴즈 등 콘텐츠 생성
- � 웹/드라이브 리서치
- 🤝 노트북 공유

---

## � 설치 가이드 (Step by Step)

### Step 1: 저장소 클론

```bash
git clone https://github.com/cool25th/notebooklm_mcp.git
cd notebooklm_mcp
```

### Step 2: Python 가상환경 생성

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> 💡 Windows의 경우: `.venv\Scripts\activate`

### Step 3: 패키지 설치

```bash
pip install -e .
```

### Step 4: 브라우저 엔진 설치

```bash
mkdir -p .tmp .browsers
TMPDIR=$(pwd)/.tmp PLAYWRIGHT_BROWSERS_PATH=$(pwd)/.browsers python -m patchright install chromium
```

> ⚠️ macOS에서 권한 오류가 나면 위 명령어를 그대로 사용하세요. 시스템 폴더 대신 프로젝트 폴더에 설치됩니다.

### Step 5: Google 계정 인증

```bash
python -m notebooklm_mcp.auth
```

브라우저 창이 열리면 **Google 계정으로 로그인**하세요. 로그인 완료 후 자동으로 인증 정보가 저장됩니다.

### Step 6: Antigravity IDE에 MCP 서버 등록

1. Antigravity 열기
2. `Cmd + Shift + P` (Mac) 또는 `Ctrl + Shift + P` (Windows)
3. "Preferences: Open User Settings (JSON)" 선택
4. 아래 내용을 추가:

```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "/경로/notebooklm-mcp/.venv/bin/python",
      "args": ["-m", "notebooklm_mcp.server"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "/경로/notebooklm-mcp/.browsers"
      }
    }
  }
}
```

> 💡 `/경로/`를 실제 프로젝트 경로로 변경하세요. 예: `/Users/username/notebooklm-mcp/`

5. 저장 후 **Antigravity 재시작**

### Step 7: 테스트

Antigravity에서 에이전트에게 말해보세요:
```
"내 NotebookLM 노트북 목록을 보여줘"
```

---

## 🔧 문제 해결

### "Executable doesn't exist" 오류
브라우저가 설치되지 않았습니다. Step 4를 다시 실행하세요.

### 인증 만료
다시 로그인하세요:
```bash
source .venv/bin/activate
python -m notebooklm_mcp.auth
```

### MCP 서버가 보이지 않음
1. settings.json 경로 확인
2. JSON 문법 오류 확인 (쉼표, 괄호)
3. Antigravity 완전히 재시작

---

# 🇺🇸 English Guide

## What is NotebookLM MCP?

An MCP server that connects [Google NotebookLM](https://notebooklm.google.com/)'s RAG capabilities to AI coding assistants (Antigravity, Claude, Cursor, etc.).

**What you can do:**
- 📚 Add documents to notebooks and query them
- 🎙️ Generate audio overviews, quizzes, and more
- 🔍 Web/Drive research
- 🤝 Share notebooks

---

## 📋 Installation Guide (Step by Step)

### Step 1: Clone Repository

```bash
git clone https://github.com/cool25th/notebooklm_mcp.git
cd notebooklm_mcp
```

### Step 2: Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> 💡 On Windows: `.venv\Scripts\activate`

### Step 3: Install Package

```bash
pip install -e .
```

### Step 4: Install Browser Engine

```bash
mkdir -p .tmp .browsers
TMPDIR=$(pwd)/.tmp PLAYWRIGHT_BROWSERS_PATH=$(pwd)/.browsers python -m patchright install chromium
```

> ⚠️ If you get permission errors on macOS, use the exact command above. It installs to the project folder instead of system folders.

### Step 5: Authenticate with Google

```bash
python -m notebooklm_mcp.auth
```

A browser window will open. **Log in with your Google account**. Authentication info is saved automatically.

### Step 6: Register MCP Server in Antigravity

1. Open Antigravity
2. `Cmd + Shift + P` (Mac) or `Ctrl + Shift + P` (Windows)
3. Select "Preferences: Open User Settings (JSON)"
4. Add this configuration:

```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "/path/to/notebooklm-mcp/.venv/bin/python",
      "args": ["-m", "notebooklm_mcp.server"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "/path/to/notebooklm-mcp/.browsers"
      }
    }
  }
}
```

> 💡 Replace `/path/to/` with your actual project path. Example: `/Users/username/notebooklm-mcp/`

5. Save and **restart Antigravity**

### Step 7: Test

Ask the agent in Antigravity:
```
"List my NotebookLM notebooks"
```

---

## � Troubleshooting

### "Executable doesn't exist" Error
Browser not installed. Run Step 4 again.

### Authentication Expired
Log in again:
```bash
source .venv/bin/activate
python -m notebooklm_mcp.auth
```

### MCP Server Not Visible
1. Check settings.json path
2. Check JSON syntax (commas, brackets)
3. Fully restart Antigravity

---

## 🛠️ Available Tools (사용 가능한 도구) - 25개

### 📚 Notebooks (노트북 관리)
| Tool | Description (설명) |
|------|-------------------|
| `notebook_list` | List all notebooks (노트북 목록 조회) |
| `notebook_create` | Create a new notebook (새 노트북 생성) |
| `notebook_get` | Get notebook details (노트북 상세 정보) |
| `notebook_describe` | Get AI summary of notebook (AI 노트북 요약) |
| `notebook_rename` | Rename a notebook (노트북 이름 변경) |
| `notebook_delete` | Delete a notebook (노트북 삭제) |

### 📄 Sources (소스 관리)
| Tool | Description (설명) |
|------|-------------------|
| `source_add` | Add URL, text, or file to notebook (URL/텍스트/파일 추가) |
| `source_list` | List all sources in notebook (소스 목록 조회) |
| `source_delete` | Remove a source (소스 삭제) |
| `source_describe` | Get AI summary of source (AI 소스 요약) |
| `source_get_content` | Get raw source content (소스 원본 내용) |

### 💬 Query & Chat (질문 및 채팅)
| Tool | Description (설명) |
|------|-------------------|
| `notebook_query` | Ask questions about notebook content (노트북 내용 질문) |
| `chat_configure` | Configure chat settings (채팅 설정 변경) |

### 🎙️ Studio (콘텐츠 생성)
| Tool | Description (설명) |
|------|-------------------|
| `studio_create` | Generate audio, quiz, report, etc. (오디오/퀴즈/리포트 생성) |
| `studio_status` | Check generation progress (생성 진행 상태) |
| `download_artifact` | Download generated content (생성된 콘텐츠 다운로드) |

### 🔬 Research (리서치)
| Tool | Description (설명) |
|------|-------------------|
| `research_start` | Start web or Drive research (웹/드라이브 리서치 시작) |
| `research_status` | Check research progress (리서치 진행 상태) |
| `research_import` | Import discovered sources (발견된 소스 가져오기) |

### 🤝 Sharing (공유)
| Tool | Description (설명) |
|------|-------------------|
| `notebook_share_status` | Get sharing settings (공유 설정 조회) |
| `notebook_share_public` | Enable/disable public link (공개 링크 설정) |
| `notebook_share_invite` | Invite collaborator (협업자 초대) |

### 🔐 Auth & Server (인증 및 서버)
| Tool | Description (설명) |
|------|-------------------|
| `refresh_auth` | Refresh authentication tokens (인증 토큰 갱신) |
| `server_info` | Get server version and status (서버 정보 조회) |

---

## 🙏 Credits

- Inspired by [jacob-bd/notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)
- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Browser automation via [Patchright](https://github.com/AuroraEchoes/Patchright)

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Note**: This is an unofficial integration. NotebookLM is a product of Google.
