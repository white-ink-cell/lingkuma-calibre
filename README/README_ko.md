# LingKuma for Calibre

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | **한국어**

오픈소스 프로젝트 **LingKuma 1.1.0**을 Calibre에서 사용할 수 있도록 만든 비공식 데스크톱 포팅 버전입니다. LingKuma의 하이라이트, 단어 조회, 번역 / AI, 문장 분석, 단어장, TTS, 테마 기능을 Calibre 독서 환경에서 사용할 수 있습니다.

> **Calibre 포팅 버전 배포 / 유지보수: [`white-ink-cell`](https://github.com/white-ink-cell)**  
> 이 저장소는 LingKuma의 공식 Calibre 버전이 아닙니다. LingKuma 원 프로젝트의 저자 표기, 저작권 및 라이선스는 변경하지 않습니다. `white-ink-cell`은 이 Calibre 포팅 버전의 배포자 및 유지보수자임을 나타낼 뿐입니다.

## 스크린샷

<p align="center">
  <img src="docs/calibre-ja-zh-light.png" width="48%" alt="Japanese to Chinese in light mode">
  <img src="docs/calibre-en-ko-dark.png" width="48%" alt="English to Korean in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-zh-en-light.png" width="48%" alt="Chinese to English in light mode">
  <img src="docs/calibre-zh-it-dark.png" width="48%" alt="Chinese to Italian in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-en-ja-light.png" width="65%" alt="English to Japanese in light mode">
</p>

## 주요 변경 사항

이 포팅 버전은 주로 다음 네 가지 호환성 작업을 포함합니다.

### 1. Calibre 실행 환경 대응

LingKuma 외부에 Calibre 호환 레이어를 추가하여, 원래 브라우저 확장 환경에서 제공되던 실행 기능을 Calibre / Qt WebEngine에서 사용할 수 있도록 했습니다.

가능한 한 LingKuma의 기존 기능과 코드 구조를 유지합니다.

### 2. 문장 선택 개선

Calibre 독서 환경에 맞는 문장 경계 판정 및 텍스트 재구성 규칙을 추가하여 EPUB, PDF, 괄호, 약어, 특수 문장부호가 포함된 텍스트에서 완전한 문장을 더 안정적으로 가져옵니다.

**1.0 추가 사항:** 일본어와 한국어에서는 5자 미만이라도 둘 이상의 어휘 단위를 포함한 의미 있는 짧은 문장이나 구절이면 Word Explosion 패널을 열 수 있습니다. 단어 하나만 선택된 경우에는 문장으로 처리하지 않습니다.

### 3. 반투명 유리 효과 호환

LingKuma 원본의 일부 유리 효과는 브라우저 전용 Web 컴포넌트와 렌더링 동작에 의존합니다.

이 포팅 버전은 기존 UI와 테마 로직을 유지하면서 Calibre의 Qt WebEngine에서 사용할 수 있는 반투명 유리 호환 효과를 제공합니다.

### 4. 다국어 번역 지원

LingKuma 원본의 일부 AI Prompt와 언어 처리 경로는 중국어를 고정 대상 언어로 사용합니다.

이 포팅 버전은 원문 언어 감지와 대상 언어 처리를 추가하여 번역, AI 설명, TTS 언어 메타데이터 및 관련 표시가 사용자가 선택한 언어를 따르도록 했습니다.

## 설치

1. **Calibre → 환경 설정 → 플러그인**을 엽니다.
2. 이전 버전의 LingKuma for Calibre가 설치되어 있다면 먼저 제거하고 Calibre를 완전히 종료합니다.
3. Calibre를 다시 실행하고 **파일에서 플러그인 불러오기**를 선택합니다.
4. GitHub Releases의 `lingkuma-calibre-1.0.zip`을 설치합니다.
5. Calibre를 다시 시작합니다.

> GitHub가 자동 생성하는 Source code ZIP을 Calibre 플러그인 설치 파일로 사용하지 마세요.

## 번역 설정

`LingKuma → Full Settings → AI / API Configuration`

사용 가능한 서비스:

- Google Web Translate(실험적, API 키 불필요)
- Microsoft Translator
- Google Cloud Translation
- LingKuma AI

## 지원 형식 및 환경

직접 열 수 있는 형식:

- EPUB
- HTMLZ
- TXT
- HTML / XHTML

그 밖의 형식은 Calibre를 사용해 EPUB으로 변환할 수 있습니다. PDF 품질은 텍스트 레이어와 원본 레이아웃에 따라 달라집니다.

실행 환경:

- Calibre 7.0+
- Windows / macOS / Linux
- 주로 Calibre 9.x에서 테스트

## 데이터 및 개인정보 보호

설정, 단어장, 예문 및 독서 진행 상황은 Calibre의 로컬 설정 디렉터리에 저장됩니다.

번역 또는 AI 서비스를 사용할 경우 요청 처리에 필요한 단어, 문장 또는 문맥만 선택한 서비스로 전송됩니다. 전자책 전체 파일, Calibre 인증 정보 또는 라이브러리 메타데이터를 의도적으로 업로드하지 않습니다.

API 키는 로컬 플러그인 상태 파일에 저장됩니다. WebDAV 동기화는 사용자가 명시적으로 요청한 경우에만 실행됩니다.

## 업스트림 프로젝트 및 저작자 표기

- 원 프로젝트: **LingKuma**
- 업스트림 버전: **LingKuma 1.1.0**
- Calibre 포팅 버전 유지보수 / 배포: **white-ink-cell**

LingKuma 원 프로젝트의 저자 표기, 저작권, 라이선스, 핵심 UI 및 포함된 업스트림 리소스의 귀속은 변경하지 않습니다.

자세한 내용은 [`UPSTREAM_ko.md`](UPSTREAM_ko.md)를 참조하세요.

## 라이선스

LingKuma 원 프로젝트의 저자 표기, 저작권 및 라이선스는 변경하지 않습니다.

Calibre 어댑터 / 호환 레이어는 `LICENSE-ADAPTER.txt`, LingKuma 원 라이선스는 `LICENSE-LINGKUMA.txt`, 제3자 리소스의 라이선스와 고지는 `THIRD-PARTY-NOTICES.txt` 및 `licenses/`를 참조하세요.
