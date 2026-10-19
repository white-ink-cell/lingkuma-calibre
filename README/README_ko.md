# LingKuma for Calibre

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md)

**See it. Click it. Learn it.**<br>
**모르는 부분은 클릭하세요.**

[LingKuma 원본 프로젝트](https://github.com/lingkuma/LingKuma) · [LingKuma Wiki](https://docs.lingkuma.org) · [LingKuma 웹사이트](https://lingkuma.org/) · [Zotero 포트](https://github.com/white-ink-cell/lingkuma-zotero)

LingKuma — *언어의 장벽을 넘어 지식이 퍼질 수 있도록* — 는 독서를 중심으로 설계된 번역 및 언어 학습 도구입니다.

어떤 언어를 완전히 "배운" 뒤에야 그 언어로 된 논문, 책, 문서를 읽기 시작할 필요는 없습니다.

모르는 단어를 만나면 **클릭하세요**.  
이해하기 어려운 문장을 만나면 **클릭하세요**.

LingKuma는 아직 배우고 있는 언어로 된 콘텐츠를 읽을 수 있도록 도와줍니다. 독서를 즐기는 과정에서 자연스럽게 어휘를 늘리고, 문법과 표현에 익숙해지며, 해당 언어에 대한 이해도를 높일 수 있습니다.

> **먼저 독서를 즐기고, 그 과정에서 새로운 언어를 배워 보세요.**

## LingKuma로 무엇을 할 수 있나요?

- 단어를 클릭하여 뜻 확인
- 전체 문장 번역 및 분석
- **Dictionary + Quick Context + AI Detail**을 이용한 더 빠르고 정확한 단어 조회
- 사전 실제 녹음 음성으로 단어 발음을 듣고, 미국식 / 영국식 발음을 각각 선택. 녹음이 없을 때는 TTS 사용
- 읽으면서 어휘, 뜻, 개인 학습 기록 저장
- AI를 활용한 문법, 문맥, 어려운 문장 설명
- Word Explosion으로 현재 문장의 여러 단어 빠르게 확인
- 사용자 지정 버튼으로 외부 사전, 검색 엔진, Wikipedia 같은 백과사전 열기
- Bionic Reading, Reading Ruler, POS Highlight
- 선택적 WebDAV 학습 데이터 백업 / 복원
- 라이트 / 다크 테마

더 자세한 사용법과 플랫폼 문서는 [LingKuma Wiki](https://docs.lingkuma.org)를 참고하세요.

## 스크린샷

<div align="center">

<p><i>LingKuma in action across different languages and themes.</i></p>

<table>
  <tr>
    <td align="center" width="50%">
      <img src="../docs/calibre-ja-zh-light.png" alt="Japanese to Chinese in light mode" width="95%">
      <br>
      <sub><b>Japanese → Chinese</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="../docs/calibre-en-ko-dark.png" alt="English to Korean in dark mode" width="95%">
      <br>
      <sub><b>English → Korean</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../docs/calibre-zh-en-light.png" alt="Chinese to English in light mode" width="95%">
      <br>
      <sub><b>Chinese → English</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="../docs/calibre-zh-it-dark.png" alt="Chinese to Italian in dark mode" width="95%">
      <br>
      <sub><b>Chinese → Italian</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
</table>

<br>

<img src="../docs/calibre-en-ja-light.png" alt="English to Japanese in light mode" width="70%">
<br>
<sub><b>English → Japanese</b></sub><br>
<sub>Light mode</sub>

</div>

## Calibre 포팅 버전

이 프로젝트는 오픈 소스 LingKuma 프로젝트의 비공식 Calibre 포팅 버전입니다.

원본 LingKuma에는 단어 강조 표시, 문장 번역 및 분석, 어휘 학습, 음성 읽기, Edge TTS 등의 기능이 이미 포함되어 있습니다. Calibre 포팅 버전은 이러한 핵심 기능을 유지하면서 Calibre의 독립적인 읽기 환경에 맞게 조정했습니다.

Calibre 포팅 버전에는 주로 다음과 같은 기능이 추가되거나 조정되었습니다:

- Calibre의 전자책 읽기 환경과 통합하여 별도의 Qt WebEngine 리더 창에서 LingKuma 사용
- EPUB 읽기, 장 탐색, 읽기 진행 상태 및 페이지 표시 설정 지원
- EPUB 읽기 환경에서 문장 선택 및 줄바꿈 복원 개선
- 더 완전한 문장 경계 처리와 문장 재구성, 의미 있는 일본어 및 한국어 짧은 문장 인식
- 명시적인 영어 하이픈 복합어 인식
- Dictionary + Quick Context 기반 빠른 영어 단어 조회
- Calibre와 호환되는 반투명 유리 효과
- Calibre에 통합된 LingKuma 설정 화면에서 언어, 어휘, TTS, 읽기 보조 및 데이터 관리 기능 제공
- Calibre 실행 환경에서 Edge TTS 재생, 미리 듣기 및 중지 처리 수정

## v1.1.2 주요 업데이트

### Calibre 읽기 환경 대응

이번 릴리스는 **LingKuma 1.1.1**을 기반으로 Calibre 안에서의 독립적인 읽기 경험을 더욱 개선했습니다.

LingKuma의 읽기, 번역, 학습 및 툴팁 인터페이스는 원본 프로젝트의 디자인과 기능을 계속 유지합니다. Calibre 어댑터는 전자책 파싱, Qt WebEngine 리더 창, 장 탐색, 읽기 진행 상태 및 브라우저 확장 실행 인터페이스와의 호환성을 담당합니다.

이번 릴리스에서는 언어 설정, 어휘 관리, TTS 설정과 미리 듣기, 읽기 보조 및 데이터 관리 기능도 더욱 보완했습니다.

### 더 빠른 조회: Dictionary + Quick Context + AI

이전 버전은 일반적인 단어 뜻도 AI에 많이 의존했기 때문에 간단한 조회에서도 생성 대기 시간이 생길 수 있었고, 형용사와 뒤의 명사를 모두 같은 전체 구로 설명하는 식의 과도한 결과가 나올 때도 있었습니다.

이제 역할을 세 층으로 나눕니다:

1. **Dictionary(사전)** — 기본 의미, 품사, 형태 정보, IPA, 발음 메타데이터 같은 안정적인 어휘 정보를 빠르게 제공합니다.
2. **Quick Context(빠른 문맥 번역)** — **현재 문장 전체**를 사용하는 빠른 비생성형 문맥 번역을 수행한 뒤, 선택한 단어가 해당 문장에서 가지는 의미를 추출합니다.
3. **AI Detail(AI 상세 설명)** — 문법, 복잡한 용법, 문장 분석, 더 깊은 설명을 계속 담당합니다.

따라서 일반적인 단어 조회가 AI 생성 속도에 크게 의존하지 않으면서도, 기본 어휘 정보의 안정성을 높이고 AI를 더 깊은 이해에 계속 활용할 수 있습니다.

사용 가능한 뜻이 있을 경우 사용자는 어휘 관리 화면에서 저장된 뜻을 확인, 수정 또는 삭제할 수 있습니다. 서로 다른 출처의 뜻을 하나의 항목으로 억지로 합칠 필요는 없습니다.

### Word Explosion 속도 개선

Word Explosion의 각 단어 짧은 뜻은 정상 경로에서 단어마다 AI 응답을 기다리지 않고 Quick Context를 우선 사용합니다. 기존에 저장된 뜻도 유지합니다.

전체 문장 번역과 더 깊은 AI 분석은 계속 사용할 수 있습니다.

### 문장 선택 및 경계 처리 개선

이번 릴리스는 LingKuma의 기존 문장 처리 기능을 유지하면서 Calibre의 EPUB 읽기 환경에 맞춰 다음을 더욱 개선했습니다:

- EPUB에서 줄바꿈과 여러 텍스트 노드에 걸친 문장 선택 개선;
- 반쪽 문장 또는 잘못된 문장 넘김 감소;
- 약어, 이니셜, 소수점, 따옴표, 괄호, 콜론, 세미콜론의 보수적 처리;
- EPUB 레이아웃 줄바꿈으로 생긴 명백한 하이픈 분할 복원;
- 의미 있는 일본어 및 한국어 짧은 문장 인식 개선.

Calibre 포팅 버전은 PDF 파일을 자동 변환하거나 처리하지 않습니다. PDF를 읽으려면 원본 LingKuma 브라우저 확장을 사용할 수 있습니다.

### 하이픈 복합어 지원

이전에는 다음과 같은 단어가 잘못 분리될 수 있었습니다:

- `well-known`
- `out-of-sample`
- `peer-on-peer`

이제 이러한 명시적인 영어 하이픈 복합어를 가능한 한 하나의 조회 및 학습 단위로 처리합니다.

반면 `inter-` + 줄바꿈 + `national`처럼 레이아웃 때문에 나뉜 경우는 별도로 처리하며, 명확할 때만 `international`로 보수적으로 복원합니다.

### 발음 개선: 사전 녹음 + IPA + 미국식 / 영국식

영어 단어 발음에는 신뢰할 수 있는 사전 발음 데이터를 우선 사용합니다:

- 신뢰할 수 있는 데이터가 있을 때 실제 단어 형태에 맞는 IPA 표시;
- 미국식 / 영국식 발음을 별도로 표시하고 각각 독립적으로 재생;
- 사전의 실제 녹음이 있으면 우선 사용;
- 실제 단어 형태의 녹음이 없을 때 TTS 사용.

상단 단어 발음 버튼은:

- 미국식 녹음만 있음 → 미국식 재생;
- 영국식 녹음만 있음 → 영국식 재생;
- 둘 다 있음 → **미국식을 기본값**으로 사용;
- 둘 다 없음 → TTS 폴백.

`books`, `worked`, `studies`, `working` 같은 활용형에서 특히 유용합니다.

### Calibre의 Edge TTS 수정

**Edge TTS는 원본 LingKuma에 이미 포함된 기능이며, 이 포팅 버전에서 새롭게 추가한 음성 제공자가 아닙니다.**

이번 릴리스에서는 주로 Calibre 실행 환경과의 호환성 문제를 수정하여 음성 합성, 미리 듣기, 매개변수 전달 및 재생 중지 처리를 개선했습니다. 필요한 종속성과 함께 포함된 `edge-tts` 클라이언트를 사용합니다.

Windows Calibre 9.16의 실제 설치 테스트에서 사용자가 다음 동작을 확인했습니다:

- Edge TTS 미국식 영어 음성이 정상적으로 재생됨;
- Edge TTS 영국식 영어 음성이 정상적으로 재생됨;
- 중지 버튼이 정상적으로 작동함.

Calibre 설정 화면에는 시스템 로컬 음성, Edge TTS, GPT TTS의 설정 항목과 미리 듣기 컨트롤도 제공됩니다. 각 음성 제공자는 자체 설정과 서비스 요구 사항에 따라 동작합니다.

### 읽기 및 학습 기능 유지

Calibre에서 적용 가능한 LingKuma의 읽기 워크플로를 계속 유지하거나 복원합니다:

- 어휘 상태와 저장한 뜻;
- 예문 및 학습 기록;
- AI 문장 분석과 더 깊은 단어 설명;
- Bionic Reading;
- Reading Ruler;
- POS Highlight;
- 사용자 지정 외부 검색 / 사전 / 백과사전 버튼;
- 로컬 어휘 관리;
- WebDAV 백업 / 복원;
- EPUB 읽기 및 텍스트 복원;
- Calibre 호환 테마 및 팝업 동작;
- 장 탐색, 읽기 진행 상태 및 페이지 표시 설정.

## 현재 언어 범위

LingKuma 자체는 다국어 도구이지만, 이번에 추가된 **로컬 사전 가속은 현재 주로 영어 원문에 초점을 맞추고 있습니다**.

이번 릴리스에서는:

- 포함된 로컬 사전이 **영어 → 중국어 간체**;
- Quick Context는 번역 서비스가 지원하는 경우 사용자가 설정한 대상 언어를 따를 수 있음;
- 다른 원문 언어에서도 지원되는 번역 및 AI 기능을 계속 사용할 수 있음;
- 다른 원문 언어용 로컬 사전 팩은 아직 포함하지 않음.

따라서 이번 릴리스에서 가장 큰 속도 및 어휘 의미의 안정성 향상은 **영어 원문 읽기**에서 나타납니다. 다른 원문 언어에 대응하는 로컬 사전이 없더라도 기존 번역 및 AI 기능을 잃는 것은 아닙니다.

## 설치

1. **[GitHub Releases](https://github.com/white-ink-cell/lingkuma-calibre/releases)**에서 `lingkuma-calibre-1.1.2.zip`을 다운로드합니다.
2. **Calibre → 환경 설정 → 플러그인**을 엽니다.
3. **파일에서 플러그인 불러오기**를 선택합니다.
4. 다운로드한 `lingkuma-calibre-1.1.2.zip` 파일을 선택합니다.
5. Calibre의 안내에 따라 설치를 확인하고 Calibre를 다시 시작합니다.

> GitHub가 자동으로 생성하는 `Source code (zip)` 파일은 Calibre 플러그인으로 설치하지 마세요. Release에 첨부된 `lingkuma-calibre-1.1.2.zip` 플러그인 패키지를 사용하세요.

## 다른 버전

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)
- [LingKuma](https://github.com/lingkuma/LingKuma)

## 지원 환경

- **Windows x64**
- 최소 요구 버전: **Calibre 9.16**
- Windows Calibre 9.16 / Python 3.14 환경에서 검증
- EPUB 읽기 지원
- 이 포팅 버전은 PDF를 자동 변환하거나 처리하지 않음
- **macOS 및 Linux는 이번 릴리스의 지원 대상이 아닙니다**

포함된 Edge TTS 네이티브 종속성은 Windows AMD64 / Python 3.14용입니다.

## 설정

설정 인터페이스는 Calibre에 통합되어 있습니다.

설치 후 Calibre 안에서 **LingKuma → 전체 설정(完整设置)**을 열 수 있습니다.

언어 / 번역, AI Provider / 프롬프트, 어휘 관리, Dictionary, 로컬 / Edge / GPT TTS, 팝업 및 읽기 보조 기능, 선택적 WebDAV 백업 / 복원 등을 설정할 수 있습니다.

인터페이스 언어와 번역 대상 언어는 각각 독립적으로 설정할 수 있습니다. 인터페이스 언어를 변경해도 번역 대상 언어가 자동으로 바뀌지는 않습니다.

## 개인정보 보호

LingKuma for Calibre는 로컬 상태를 Calibre 플러그인 데이터 디렉터리에 저장합니다.

번역, AI, 원격 TTS 및 WebDAV 기능을 사용할 경우 선택한 외부 서비스를 이용하는 데 필요한 텍스트나 데이터가 전송될 수 있습니다.

일반적인 단어 또는 문장 조회 과정에서 전자책 전체를 자동으로 업로드하지 않습니다.

## 원본 프로젝트 및 저작자 표시

- 원본 프로젝트: **[LingKuma](https://github.com/lingkuma/LingKuma)**
- LingKuma Wiki: **[docs.lingkuma.org](https://docs.lingkuma.org)**
- 원본 버전: **LingKuma 1.1.1**
- Calibre 포팅 버전 유지보수 및 배포: **white-ink-cell**

이 저장소는 LingKuma의 비공식 Calibre 포팅 버전을 제공합니다.

이 포팅 버전은 LingKuma를 Calibre의 읽기 환경에 맞게 조정하면서 원본 프로젝트의 핵심 기능, 인터페이스, 리소스 및 전체적인 디자인을 가능한 한 그대로 유지합니다. Calibre 전용 변경 사항은 실행 환경 호환성, 문장 선택, Dictionary / Quick Context 통합, 발음 대응, 복합어 처리, 반투명 유리 호환성 및 다국어 번역 지원에 중점을 둡니다.

자세한 내용은 [UPSTREAM.md](../UPSTREAM.md)를 참조하세요.

## 사전 데이터

포함된 영어 사전은 **English Wiktionary** 기여자 데이터를 **Wiktextract**로 추출하고 **Kaikki.org**가 배포한 데이터를 기반으로 생성했습니다.

사전 텍스트 데이터는 **CC BY-SA 4.0**으로 배포됩니다. 원격 Wikimedia Commons 발음 파일은 각 원본 페이지에 표시된 개별 라이선스를 따릅니다.

자세한 내용은 `licenses/ENGLISH-WIKTIONARY-DATA-NOTICE.txt`와 `THIRD-PARTY-NOTICES.txt`를 참고하세요.

## 라이선스

원본 LingKuma의 저작자 표시, 저작권 및 라이선스는 변경되지 않습니다.

Calibre 어댑터 및 호환성 레이어에는 `licenses/LICENSE-ADAPTER.txt`의 라이선스가 적용됩니다. 원본 LingKuma 라이선스는 `LICENSE-LINGKUMA.txt`에 보존되어 있으며, 포함된 타사 라이선스 및 고지는 `THIRD-PARTY-NOTICES.txt`에 기록되어 있습니다.
